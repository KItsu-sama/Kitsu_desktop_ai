# runtime/bus.py
"""
Unified EventBus + MessageBus for Kitsu.
Supports both publish/subscribe events (with priorities & circuit breakers) 
and request/response messaging (RPC).

Usage:

# Events (fire-and-forget with priorities)
bus.subscribe("INPUT_RECEIVED", handler, priority=-100)  # high priority
bus.emit("INPUT_RECEIVED", {"text": "hello"})

# Requests (RPC-style)
result = await bus.request("ai.infer", {"prompt": "hello"})

# Streams
async for chunk in bus.stream("RESPONSE_STREAM", request_id):
    process(chunk)
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Type, Union

logger = logging.getLogger('kitsu.runtime.bus')


# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class BusTimeout(Exception):
    """Raised when a request times out."""
    pass


class CircuitOpenError(Exception):
    """Raised when attempting to use a circuit that's open."""
    pass


# ─────────────────────────────────────────────────────────────
# Circuit Breaker State
# ─────────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ─────────────────────────────────────────────────────────────
# Stats & Metrics
# ─────────────────────────────────────────────────────────────

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
    half_open_in_progress: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


# ─────────────────────────────────────────────────────────────
# EventBus (Main Implementation)
# ─────────────────────────────────────────────────────────────

class EventBus:
    """
    Async-safe event bus with:
    - Priority handlers (lower = executes first)
    - Circuit breaker (skip after 5 consecutive failures)
    - Request/Response (RPC) support
    - Thread-safe metrics
    - Async/sync handler support
    """

    CIRCUIT_BREAK_THRESHOLD = 5
    CIRCUIT_RESET_TIMEOUT = 30.0

    def __init__(self) -> None:
        # Event system
        self._event_handlers: Dict[str, List[HandlerInfo]] = defaultdict(list)
        self._event_metrics: Dict[str, EventMetrics] = defaultdict(EventMetrics)
        
        # Request/Response system
        self._request_handlers: Dict[str, Callable[[Any], Union[Any, Coroutine[Any, Any, Any]]]] = {}
        
        # Lifecycle
        self._started: bool = False
        self._lock = asyncio.Lock()
        self._active_tasks: Set[asyncio.Task] = set()

    # ─────────────────────────────────────────────────────────────
    # Lifecycle (ModuleContract compliance)
    # ─────────────────────────────────────────────────────────────

    async def start(self) -> bool:
        """Start the event bus."""
        async with self._lock:
            if self._started:
                logger.debug("EventBus already started")
                return True

            self._started = True
            logger.info("🚀 EventBus started (Priority + Circuit Breaker + RPC)")
            return True

    async def stop(self) -> bool:
        """Stop the event bus."""
        async with self._lock:
            if not self._started:
                return True

            self._started = False
            active = list(self._active_tasks)

        # Cancel outside lock
        for task in active:
            task.cancel()

        if active:
            await asyncio.gather(*active, return_exceptions=True)

        # Clear all handlers
        self._event_handlers.clear()
        self._request_handlers.clear()
        self._event_metrics.clear()

        logger.info("🛑 EventBus stopped")
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Return bus health status."""
        async with self._lock:
            event_count = sum(len(handlers) for handlers in self._event_handlers.values())
            circuits = await self.get_circuit_status()
            
            return {
                'ok': True,
                'started': self._started,
                'event_handlers': event_count,
                'request_handlers': len(self._request_handlers),
                'open_circuits': len(circuits),
                'circuit_status': circuits
            }

    # ─────────────────────────────────────────────────────────────
    # Event Subscription (with priorities)
    # ─────────────────────────────────────────────────────────────

    async def subscribe(
        self,
        event: str,
        handler: Callable,
        priority: int = 0
    ) -> None:
        """
        Register handler with PRIORITY (lower = executes first).
        
        Examples:
            await bus.subscribe("PREPROCESS_DONE", router, priority=-100)  # CRITICAL
            await bus.subscribe("LLM_PATH", llm_handler, priority=100)     # LOW
        """
        handler_name = getattr(handler, "__qualname__", repr(handler))

        async with self._lock:
            # Remove existing subscription
            self._unsubscribe_unlocked(event, handler)

            info = HandlerInfo(handler=handler, priority=priority)
            self._event_handlers[event].append(info)
            
            # Sort by priority (lower = higher priority)
            self._event_handlers[event].sort(key=lambda h: h.priority)

            logger.debug("➕ subscribe: %s → %s (priority=%d)", event, handler_name, priority)

    async def unsubscribe(self, event: str, handler: Callable) -> None:
        """Unsubscribe handler from event."""
        async with self._lock:
            self._unsubscribe_unlocked(event, handler)

    def _unsubscribe_unlocked(self, event: str, handler: Callable) -> None:
        """Remove existing handler subscription (caller must hold lock)."""
        handlers = self._event_handlers.get(event, [])
        handler_name = f"{handler.__module__}.{handler.__qualname__}"

        self._event_handlers[event] = [
            h for h in handlers if h.handler != handler
        ]

        if not self._event_handlers[event]:
            del self._event_handlers[event]

        logger.debug("➖ unsubscribe: %s → %s", event, handler_name)

    # ─────────────────────────────────────────────────────────────
    # Event Emission (with circuit breakers)
    # ─────────────────────────────────────────────────────────────

    async def emit(self, event: str, payload: Any = None) -> None:
        """
        Fire event with PRIORITY EXECUTION + CIRCUIT BREAKERS.
        
        1. Sort handlers by priority (router first)
        2. Skip circuit-breaker-tripped handlers  
        3. Execute remaining handlers CONCURRENTLY
        """
        if not self._started:
            logger.warning("emit called on stopped EventBus: %s", event)
            return

        async with self._lock:
            handlers = list(self._event_handlers.get(event, []))

        if not handlers:
            logger.debug("emit: %s (no handlers)", event)
            return

        start_time = time.monotonic_ns()

        async with self._lock:
            self._event_metrics[event].events_emitted += 1

        skipped = 0
        tasks: List[asyncio.Task] = []

        for handler_info in handlers:
            if await self._should_skip_handler(handler_info):
                skipped += 1
                logger.debug("⏭️ SKIP %s (circuit breaker)", 
                           getattr(handler_info.handler, "__qualname__", repr(handler_info.handler)))
                continue

            task = asyncio.create_task(
                self._run_handler_tracked(handler_info, payload, event)
            )
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)
            tasks.append(task)

        async with self._lock:
            self._event_metrics[event].handlers_skipped += skipped

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            async with self._lock:
                self._event_metrics[event].handlers_executed += len(tasks)
                for result in results:
                    if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                        self._event_metrics[event].handler_errors += 1

        duration = time.monotonic_ns() - start_time
        async with self._lock:
            self._event_metrics[event].total_execution_time_ns += duration

    # ─────────────────────────────────────────────────────────────
    # Request/Response (RPC)
    # ─────────────────────────────────────────────────────────────

    def register_handler(self, channel: str, handler: Callable[[Any], Union[Any, Coroutine[Any, Any, Any]]]) -> None:
        """Register a request handler for a named channel."""
        if channel in self._request_handlers:
            raise RuntimeError(f'Handler already registered for channel: {channel}')
        self._request_handlers[channel] = handler
        logger.debug('Registered handler for channel %s', channel)

    async def request(self, channel: str, payload: Any, timeout_ms: int = 500) -> Any:
        """
        Send a request to a channel and await response.
        Supports both sync and async handlers.
        """
        if not self._started:
            raise RuntimeError(f"Request on {channel} failed: EventBus not started")

        start_time = time.perf_counter()
        
        if channel not in self._request_handlers:
            logger.warning("[BUS] No handler registered for channel: %s", channel)
            raise BusTimeout(f'No handler for channel {channel}')

        handler = self._request_handlers[channel]
        logger.debug("[BUS] Requesting on channel '%s' (timeout: %dms)", channel, timeout_ms)
        
        try:
            handler_start = time.perf_counter()
            if asyncio.iscoroutinefunction(handler):
                logger.debug("[BUS] Using async handler for '%s'", channel)
                coro = handler(payload)
            else:
                logger.debug("[BUS] Using sync handler for '%s'", channel)
                loop = asyncio.get_running_loop()
                coro = loop.run_in_executor(None, handler, payload)

            result = await asyncio.wait_for(coro, timeout=timeout_ms / 1000.0)
            handler_time = (time.perf_counter() - handler_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000
            
            logger.debug("[BUS] Request on '%s' completed: handler=%.1fms, total=%.1fms", 
                        channel, handler_time, total_time)
            return result
            
        except asyncio.TimeoutError as exc:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.warning('[BUS] Request timeout on channel %s (%.1fms > %dms)', 
                          channel, total_time, timeout_ms)
            raise BusTimeout(f'Timeout waiting for {channel}') from exc
        except Exception as exc:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.error('[BUS] Request handler failed on channel %s after %.1fms: %s', 
                        channel, total_time, exc)
            raise

    # ─────────────────────────────────────────────────────────────
    # Streaming Support
    # ─────────────────────────────────────────────────────────────

    async def stream(self, event: str, request_id: str, timeout: float = 30.0) -> Any:
        """
        Stream events matching request_id until timeout.
        
        Usage: `async for chunk in bus.stream("RESPONSE_STREAM", ctx.id):`
        """
        # TODO: Implement per-request channels/polling
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.01)
        raise asyncio.TimeoutError(f"Stream timeout: {event} ({timeout}s)")

    # ─────────────────────────────────────────────────────────────
    # Circuit Breaker Logic
    # ─────────────────────────────────────────────────────────────

    async def _should_skip_handler(self, handler_info: HandlerInfo) -> bool:
        """Check if handler should be skipped (circuit breaker logic)."""
        async with handler_info.lock:
            state = handler_info.circuit_state

            if state == CircuitState.OPEN:
                elapsed = time.monotonic() - handler_info.stats.last_error_time

                # Move to HALF_OPEN after timeout
                if elapsed >= self.CIRCUIT_RESET_TIMEOUT:
                    handler_info.circuit_state = CircuitState.HALF_OPEN
                    handler_info.half_open_in_progress = False
                    logger.info("🔄 Circuit HALF_OPEN: %s", 
                               getattr(handler_info.handler, "__qualname__", repr(handler_info.handler)))
                else:
                    return True

            # HALF_OPEN allows ONE test request
            if handler_info.circuit_state == CircuitState.HALF_OPEN:
                if handler_info.half_open_in_progress:
                    return True
                handler_info.half_open_in_progress = True

            return False

    async def _update_handler_stats(self, handler_info: HandlerInfo, success: bool) -> None:
        """Update handler stats and circuit breaker state."""
        async with handler_info.lock:
            stats = handler_info.stats
            stats.total_calls += 1

            if success:
                stats.successful_calls += 1
                stats.consecutive_errors = 0

                # HALF_OPEN success closes breaker
                if handler_info.circuit_state == CircuitState.HALF_OPEN:
                    handler_info.circuit_state = CircuitState.CLOSED
                    handler_info.half_open_in_progress = False
                    logger.info("✅ Circuit CLOSED: %s recovered",
                               getattr(handler_info.handler, "__qualname__", repr(handler_info.handler)))
            else:
                stats.consecutive_errors += 1
                stats.total_errors += 1
                stats.last_error_time = time.monotonic()

                # HALF_OPEN failure reopens immediately
                if handler_info.circuit_state == CircuitState.HALF_OPEN:
                    handler_info.circuit_state = CircuitState.OPEN
                    handler_info.half_open_in_progress = False
                    logger.warning("🚫 Circuit REOPENED: %s",
                                  getattr(handler_info.handler, "__qualname__", repr(handler_info.handler)))
                elif stats.consecutive_errors >= self.CIRCUIT_BREAK_THRESHOLD:
                    handler_info.circuit_state = CircuitState.OPEN
                    logger.warning("🚫 Circuit OPEN: %s (%d consecutive failures)",
                                  getattr(handler_info.handler, "__qualname__", repr(handler_info.handler)),
                                  stats.consecutive_errors)

    async def _run_handler_tracked(self, handler_info: HandlerInfo, payload: Any, event: str) -> None:
        """Execute handler with error tracking."""
        success = True
        try:
            handler = handler_info.handler

            if inspect.iscoroutinefunction(handler):
                await handler(payload)
            else:
                result = await asyncio.to_thread(handler, payload)
                if inspect.isawaitable(result):
                    await result

        except asyncio.CancelledError:
            raise
        except Exception:
            success = False
            logger.exception("💥 handler %s failed on %s",
                           getattr(handler_info.handler, "__qualname__", repr(handler_info.handler)),
                           event)
            raise
        finally:
            await self._update_handler_stats(handler_info, success)

    # ─────────────────────────────────────────────────────────────
    # Monitoring & Metrics
    # ─────────────────────────────────────────────────────────────

    async def get_circuit_status(self) -> Dict[str, List[str]]:
        """Get all OPEN circuit breakers."""
        async with self._lock:
            open_circuits = {}
            for event, handlers in self._event_handlers.items():
                open_handlers = [
                    getattr(h.handler, "__qualname__", repr(h.handler))
                    for h in handlers 
                    if h.circuit_state == CircuitState.OPEN
                ]
                if open_handlers:
                    open_circuits[event] = open_handlers
            return open_circuits

    async def reset_circuits(self, event: Optional[str] = None) -> None:
        """Reset circuit breakers to CLOSED state."""
        async with self._lock:
            if event:
                handlers = self._event_handlers.get(event, [])
            else:
                handlers = []
                for h_list in self._event_handlers.values():
                    handlers.extend(h_list)
            
            for handler_info in handlers:
                async with handler_info.lock:
                    handler_info.circuit_state = CircuitState.CLOSED
                    handler_info.stats = HandlerStats()
                    handler_info.half_open_in_progress = False

    async def get_metrics(self) -> Dict[str, EventMetrics]:
        """Get event metrics."""
        async with self._lock:
            return dict(self._event_metrics)

    async def get_handler_stats(self, event: str) -> List[dict]:
        """Get detailed handler stats for event."""
        async with self._lock:
            handlers = self._event_handlers.get(event, [])
            result = []
            for h in handlers:
                result.append({
                    "handler": getattr(h.handler, "__qualname__", repr(h.handler)),
                    "priority": h.priority,
                    "circuit_state": h.circuit_state.value,
                    "consecutive_errors": h.stats.consecutive_errors,
                    "total_errors": h.stats.total_errors,
                    "total_calls": h.stats.total_calls,
                    "successful_calls": h.stats.successful_calls,
                    "success_rate": (h.stats.successful_calls / max(h.stats.total_calls, 1) * 100)
                })
            return result

    async def get_stats(self) -> Dict[str, Any]:
        """Comprehensive production stats."""
        metrics = await self.get_metrics()
        circuits = await self.get_circuit_status()
        
        total_events = sum(m.events_emitted for m in metrics.values())
        total_errors = sum(m.handler_errors for m in metrics.values())
        
        total_handlers = sum(len(h) for h in self._event_handlers.values())
        avg_execution = sum(
            m.total_execution_time_ns / 1_000_000 / max(m.handlers_executed, 1)
            for m in metrics.values()
        ) / max(len(metrics), 1)
        
        return {
            "started": self._started,
            "total_events": total_events,
            "total_errors": total_errors,
            "total_handlers": total_handlers,
            "request_handlers": len(self._request_handlers),
            "open_circuits": len(circuits),
            "circuit_status": circuits,
            "avg_execution_ms": avg_execution
        }

    # ─────────────────────────────────────────────────────────────
    # Legacy Compatibility (sync publish)
    # ─────────────────────────────────────────────────────────────

    def publish(self, event: Any) -> None:
        """
        Legacy sync publish for event objects.
        Creates task to emit asynchronously.
        """
        event_name = type(event).__name__
        asyncio.create_task(self.emit(event_name, event))


# ─────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────

MessageBus = EventBus
bus = EventBus()