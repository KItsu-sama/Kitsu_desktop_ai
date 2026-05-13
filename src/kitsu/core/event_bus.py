"""
src/kitsu/core/event_bus.py

Async pub/sub event bus — in-process only.

Rules:
- emit() fans out to ALL subscribers concurrently via asyncio.gather.
- Subscriber errors are logged but never propagate to the emitter.
- RESPONSE_READY is the only event that checks ctx.responded latch.
  That check lives in the *handler* (modules call can_respond), not here.
- Only one EventBus instance exists (module-level singleton `bus`).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from kitsu.core.context import RequestContext

# Configure logger for core
logger = logging.getLogger("kitsu.event_bus")


@dataclass
class EventMetrics:
    """Event bus metrics for monitoring."""
    events_emitted: int = 0
    handlers_executed: int = 0
    handler_errors: int = 0
    total_execution_time_ns: int = 0


class EventBus:
    """
    Async pub/sub event bus with modern architecture integration.
    
    Maintains backward compatibility while adding:
    - Proper lifecycle integration
    - Enhanced error handling and monitoring
    - Performance metrics
    - Resource-aware execution
    """
    
    def __init__(self) -> None:
        # event_name → list[handler]
        # handlers can be async def or plain def
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._metrics: Dict[str, EventMetrics] = defaultdict(EventMetrics)
        self._started: bool = False
        self._monitoring: bool = False

    # ── Lifecycle Management ────────────────────────────────────────────────────
    
    async def start(self) -> None:
        """Start the event bus."""
        if self._started:
            logger.debug("EventBus already started")
            return
        self._started = True
        self._monitoring = True
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Stop the event bus."""
        if not self._started:
            logger.debug("EventBus already stopped")
            return
        self._started = False
        self._monitoring = False
        logger.info("EventBus stopped")

    def is_running(self) -> bool:
        """Check if event bus is running."""
        return self._started

    # ── Subscription Management ────────────────────────────────────────────────
    
    def subscribe(self, event: str, handler: Callable) -> None:
        """
        Register *handler* for *event*.  Duplicate subscriptions are ignored.
        """
        if handler not in self._handlers[event]:
            self._handlers[event].append(handler)
            logger.debug("subscribe: %s → %s", event, handler.__qualname__)

    def unsubscribe(self, event: str, handler: Callable) -> None:
        """Unsubscribe handler from event."""
        try:
            self._handlers[event].remove(handler)
            logger.debug("unsubscribe: %s → %s", event, handler.__qualname__)
        except ValueError:
            pass

    def get_subscribers(self, event: str) -> List[Callable]:
        """Get list of subscribers for an event."""
        return list(self._handlers.get(event, []))

    def get_all_events(self) -> List[str]:
        """Get all registered event names."""
        return list(self._handlers.keys())

    # ── Event Emission ────────────────────────────────────────────────────────
    
    async def emit(self, event: str, payload: Any = None) -> None:
        """
        Fire *event* with *payload* to all registered handlers concurrently.

        Each handler runs in its own task; exceptions are caught and logged so
        a broken handler never blocks the pipeline.
        """
        if not self._started:
            logger.warning("emit called on stopped EventBus: %s", event)
            return

        handlers = list(self._handlers.get(event, []))
        if not handlers:
            logger.debug("emit: %s (no handlers)", event)
            return

        logger.debug("emit: %s → %d handler(s)", event, len(handlers))
        
        # Update metrics
        self._metrics[event].events_emitted += 1
        
        start_time = time.monotonic_ns()

        # Create tasks for all handlers
        tasks = [_run_handler(h, payload, event) for h in handlers]
        
        # Execute concurrently, collecting results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results for metrics
        execution_time = time.monotonic_ns() - start_time
        self._metrics[event].total_execution_time_ns += execution_time
        self._metrics[event].handlers_executed += len(handlers)
        
        # Count errors
        for result in results:
            if isinstance(result, Exception):
                self._metrics[event].handler_errors += 1

    # ── Metrics and Monitoring ─────────────────────────────────────────────────
    
    def get_metrics(self, event: Optional[str] = None) -> Dict[str, EventMetrics]:
        """Get event metrics."""
        if event:
            return {event: self._metrics.get(event, EventMetrics())}
        return dict(self._metrics)

    def reset_metrics(self, event: Optional[str] = None) -> None:
        """Reset event metrics."""
        if event:
            self._metrics[event] = EventMetrics()
        else:
            self._metrics.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive event bus statistics."""
        total_events = sum(m.events_emitted for m in self._metrics.values())
        total_handlers = sum(m.handlers_executed for m in self._metrics.values())
        total_errors = sum(m.handler_errors for m in self._metrics.values())
        
        return {
            "started": self._started,
            "monitoring": self._monitoring,
            "total_events": total_events,
            "total_handlers_executed": total_handlers,
            "total_errors": total_errors,
            "registered_events": len(self._handlers),
            "total_subscribers": sum(len(handlers) for handlers in self._handlers.values()),
            "event_metrics": {k: {
                "events_emitted": v.events_emitted,
                "handlers_executed": v.handlers_executed,
                "handler_errors": v.handler_errors,
                "avg_execution_time_ms": v.total_execution_time_ns / 1_000_000 / max(v.handlers_executed, 1)
            } for k, v in self._metrics.items()}
        }

    # ── Legacy Compatibility ───────────────────────────────────────────────────
    
    async def emit_request_context(self, event_name: str, ctx: RequestContext) -> None:
        """Legacy compatibility method for RequestContext-based events."""
        await self.emit(event_name, ctx)


# ── Helper Functions ───────────────────────────────────────────────────────────

async def _run_handler(handler: Callable, payload: Any, event: str) -> None:
    """
    Run a single handler with proper error handling.
    
    This is separated to keep the emit method clean and to make
    error handling consistent across all handler executions.
    """
    try:
        result = handler(payload)
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        logger.exception("handler %s raised on event %s", handler.__qualname__, event)
        # Re-raise to be caught by gather for metrics
        raise


# ── Module-level singleton ────────────────────────────────────────────────────
bus = EventBus()
