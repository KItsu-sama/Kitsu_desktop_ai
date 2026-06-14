"""
application/core/event_bus.py

Async pub/sub event bus — in-process only with Priority Queues & Circuit Breakers.

Rules:
- emit() executes handlers by PRIORITY ORDER (critical first)
- Circuit breakers SKIP failing handlers after 5 consecutive errors
- emit() fans out to REMAINING subscribers concurrently via asyncio.gather
- Subscriber errors are logged but never propagate to the emitter
- Only one EventBus instance exists (module-level singleton `bus`)
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .context import RequestContext

logger = logging.getLogger("event_bus")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class HandlerStats:
    """Per-handler error tracking."""

    consecutive_errors: int = 0
    total_errors: int = 0
    last_error_time: float = 0.0
    total_calls: int = 0
    successful_calls: int = 0


@dataclass
class EventMetrics:
    """Event bus metrics."""

    events_emitted: int = 0
    handlers_executed: int = 0
    handlers_skipped: int = 0
    handler_errors: int = 0
    total_execution_time_ns: int = 0


@dataclass
class HandlerInfo:
    """Handler metadata."""

    handler: Callable[[Any], Any]
    priority: int = 0

    stats: HandlerStats = field(default_factory=HandlerStats)

    circuit_state: CircuitState = CircuitState.CLOSED

    # Allow one test request during HALF_OPEN
    half_open_in_progress: bool = False

    # Per-handler synchronization
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class EventBus:
    """Async-safe event bus."""

    CIRCUIT_BREAK_THRESHOLD = 5
    CIRCUIT_RESET_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._handlers: Dict[str, List[HandlerInfo]] = defaultdict(list)
        self._metrics: Dict[str, EventMetrics] = defaultdict(EventMetrics)

        self._started: bool = False
        self._lock = asyncio.Lock()

        # Track running tasks for shutdown
        self._active_tasks: Set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the event bus."""
        async with self._lock:
            if self._started:
                logger.debug("EventBus already started")
                return

            self._started = True

            # Apply any import-time deferred subscriptions.
            pending = getattr(self, "pending_subscriptions", None)
            if pending:
                self.pending_subscriptions = []
                for event, handler, priority in list(pending):
                    self._unsubscribe_unlocked(event, handler)
                    info = HandlerInfo(handler=handler, priority=priority)
                    self._handlers[event].append(info)
                    self._handlers[event].sort(key=lambda h: h.priority)

            logger.info("🚀 EventBus started (Priority + Circuit Breaker)")

    async def stop(self) -> None:
        """Stop the event bus."""
        async with self._lock:
            if not self._started:
                logger.debug("EventBus already stopped")
                return

            self._started = False
            active = list(self._active_tasks)

        for task in active:
            task.cancel()

        if active:
            await asyncio.gather(*active, return_exceptions=True)

        logger.info("🛑 EventBus stopped")

    def is_running(self) -> bool:
        return self._started

    # ─────────────────────────────────────────────────────────
    # Subscription
    # ─────────────────────────────────────────────────────────

    def _unsubscribe_unlocked(self, event: str, handler: Callable) -> None:
        handlers = self._handlers[event]
        self._handlers[event] = [h for h in handlers if h.handler != handler]

        if not self._handlers[event]:
            del self._handlers[event]

    async def subscribe(self, event: str, handler: Callable, priority: int = 0) -> None:
        async with self._lock:
            # Prevent duplicates
            self._unsubscribe_unlocked(event, handler)

            info = HandlerInfo(handler=handler, priority=priority)
            self._handlers[event].append(info)
            self._handlers[event].sort(key=lambda h: h.priority)

    async def unsubscribe(self, event: str, handler: Callable) -> None:
        async with self._lock:
            self._unsubscribe_unlocked(event, handler)

    # ─────────────────────────────────────────────────────────
    # Circuit Breaker
    # ─────────────────────────────────────────────────────────

    async def _should_skip_handler(self, handler_info: HandlerInfo) -> bool:
        async with handler_info.lock:
            state = handler_info.circuit_state

            if state == CircuitState.OPEN:
                elapsed = time.monotonic() - handler_info.stats.last_error_time
                if elapsed >= self.CIRCUIT_RESET_TIMEOUT:
                    handler_info.circuit_state = CircuitState.HALF_OPEN
                    handler_info.half_open_in_progress = False
                else:
                    return True

            if handler_info.circuit_state == CircuitState.HALF_OPEN:
                if handler_info.half_open_in_progress:
                    return True
                handler_info.half_open_in_progress = True

            return False

    async def _update_handler_stats(self, handler_info: HandlerInfo, success: bool) -> None:
        async with handler_info.lock:
            stats = handler_info.stats
            stats.total_calls += 1

            if success:
                stats.successful_calls += 1
                stats.consecutive_errors = 0

                if handler_info.circuit_state == CircuitState.HALF_OPEN:
                    handler_info.circuit_state = CircuitState.CLOSED
                    handler_info.half_open_in_progress = False
            else:
                stats.consecutive_errors += 1
                stats.total_errors += 1
                stats.last_error_time = time.monotonic()

                if handler_info.circuit_state == CircuitState.HALF_OPEN:
                    handler_info.circuit_state = CircuitState.OPEN
                    handler_info.half_open_in_progress = False
                elif stats.consecutive_errors >= self.CIRCUIT_BREAK_THRESHOLD:
                    handler_info.circuit_state = CircuitState.OPEN

    # ─────────────────────────────────────────────────────────
    # Emit
    # ─────────────────────────────────────────────────────────

    async def emit(self, event: str, payload: Any = None) -> None:
        if not self._started:
            logger.warning("emit called on stopped EventBus: %s", event)
            return

        async with self._lock:
            handlers = list(self._handlers.get(event, []))
            self._metrics[event].events_emitted += 1

        if not handlers:
            return

        start_time = time.monotonic_ns()

        executed = 0
        errors = 0
        for handler_info in handlers:
            # Note: circuit breaker skipping should apply per-handler.
            # Existing codebase behavior didn't rely heavily on this for now.
            if await self._should_skip_handler(handler_info):
                self._metrics[event].handlers_skipped += 1
                continue

            try:
                await self._run_handler_tracked(handler_info, payload, event)
                executed += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                errors += 1

        duration = time.monotonic_ns() - start_time
        async with self._lock:
            self._metrics[event].handlers_executed += executed
            self._metrics[event].handler_errors += errors
            self._metrics[event].total_execution_time_ns += duration

        # Emit a small metadata event for RESPONSE_READY so UI adapters can
        # quickly consume structured attributes like debug_reason without
        # relying on the full RequestContext shape. Fire-and-forget to avoid
        # coupling to payload consumers.
        try:
            if event == "RESPONSE_READY":
                # payload may be a RequestContext or dict; extract id/debug_reason conservatively.
                pid = None
                dreason = None
                try:
                    pid = payload.id if hasattr(payload, "id") else (payload.get("id") if isinstance(payload, dict) else None)
                except Exception:
                    pid = None
                try:
                    dreason = getattr(payload, "debug_reason", None) if hasattr(payload, "debug_reason") else (payload.get("debug_reason") if isinstance(payload, dict) else None)
                except Exception:
                    dreason = None

                # Schedule emission of metadata event without awaiting to keep latency low.
                asyncio.create_task(self.emit("RESPONSE_READY_META", {"id": pid, "debug_reason": dreason}))
        except Exception:
            logger.exception("Failed to emit RESPONSE_READY_META")

    # ─────────────────────────────────────────────────────────
    # Streaming Support
    # ─────────────────────────────────────────────────────────

    async def stream(
        self,
        event: str,
        request_id: str,
        timeout: float = 30.0,
        max_tokens: int = 512,
    ) -> Any:
        """Temporary async iterator over stream events for a specific request id.

        Usage:
            async for payload in bus.stream("RESPONSE_STREAM", request_id):
                # payload: dict with keys {'id','chunk','done'}
        """
        if not self._started:
            logger.warning("stream called on stopped EventBus: %s", event)
            return

        queue: asyncio.Queue = asyncio.Queue()
        token_count = 0

        async def _collector(payload: Any) -> None:
            try:
                pid = payload.get("id") if isinstance(payload, dict) else getattr(payload, "id", None)
                if pid != request_id:
                    return
                await queue.put(payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("stream collector failed")

        await self.subscribe(event, _collector, priority=0)

        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    return

                # Conservative token estimation for backpressure
                chunk_text = payload.get("chunk", "") if isinstance(payload, dict) else ""
                token_count += len(str(chunk_text).split())

                if token_count > max_tokens:
                    await self.emit("TOKEN_LIMIT_REACHED", {"id": request_id})
                    return

                yield payload

                done = bool(payload.get("done", False)) if isinstance(payload, dict) else bool(getattr(payload, "done", False))
                if done:
                    return

        finally:
            try:
                await self.unsubscribe(event, _collector)
            except Exception:
                logger.exception("failed to unsubscribe stream collector")

    # ─────────────────────────────────────────────────────────
    # Monitoring
    # ─────────────────────────────────────────────────────────

    async def get_metrics(self) -> Dict[str, EventMetrics]:
        async with self._lock:
            return dict(self._metrics)

    async def _run_handler_tracked(self, handler_info: HandlerInfo, payload: Any, event: str) -> None:
        handler = handler_info.handler
        try:
            if inspect.iscoroutinefunction(handler):
                await handler(payload)
            else:
                result = await asyncio.to_thread(handler, payload)
                if inspect.isawaitable(result):
                    await result
        except Exception:
            await self._update_handler_stats(handler_info, success=False)
            raise
        else:
            await self._update_handler_stats(handler_info, success=True)


bus = EventBus()

