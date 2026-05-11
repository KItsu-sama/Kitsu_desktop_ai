"""
core/bus.py

Unified EventBus + MessageBus for Kitsu.
Supports both publish/subscribe events and request/response messaging.

Usage:

# Events (fire-and-forget)
from runtime.bus import bus
from runtime.events import InputReceived

bus.subscribe(InputReceived, my_handler)
bus.publish(InputReceived(text="hello"))

# Requests (RPC-style)
result = await bus.request("ai.infer", {"prompt": "hello"})
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Type, Union

logger = logging.getLogger('kitsu.core.bus')


class BusTimeout(Exception):
    """Raised when a request times out."""
    pass


class MessageBus:
    """Unified event bus with pub/sub + request/response capabilities."""
    
    module_id = 'core.bus'
    required_flags: list[str] = []

    def __init__(self) -> None:
        self._event_subscribers: Dict[Type, List[Callable]] = defaultdict(list)
        self._request_handlers: Dict[str, Callable[[Any], Union[Any, Coroutine[Any, Any, Any]]]] = {}

    # --- Event Pub/Sub (synchronous + async) ---

    def subscribe(self, event_type: Type, handler: Callable) -> None:
        """Register a handler for a specific event type (legacy + new)."""
        self._event_subscribers[event_type].append(handler)
        logger.debug('Subscribed to event %s', getattr(event_type, 'name', str(event_type)))

    def unsubscribe(self, event_type: Type, handler: Callable) -> None:
        """Remove a previously registered event handler."""
        handlers = self._event_subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Any) -> None:
        """
        Publish an event synchronously to all handlers.
        Exceptions are logged but do not stop other handlers.
        """
        event_type = type(event)
        handlers = list(self._event_subscribers.get(event_type, []))
        
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    # Fire async handlers in background tasks
                    asyncio.create_task(self._safe_async_invoke(result, handler, event_type, event))
            except Exception as exc:
                self._log_handler_error(handler, event_type, exc)

    async def publish_async(self, event: Any) -> None:
        """
        Publish an event asynchronously, awaiting all handlers.
        Use for critical events where you need confirmation all handlers completed.
        """
        event_type = type(event)
        handlers = list(self._event_subscribers.get(event_type, []))
        
        tasks = []
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    tasks.append(self._safe_async_invoke(result, handler, event_type, event))
                else:
                    # Sync handlers run immediately
                    pass
            except Exception as exc:
                self._log_handler_error(handler, event_type, exc)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # --- Request/Response (RPC) ---

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
        if channel not in self._request_handlers:
            logger.warning('No handler registered for channel: %s', channel)
            raise BusTimeout(f'No handler for channel {channel}')

        handler = self._request_handlers[channel]
        try:
            if asyncio.iscoroutinefunction(handler):
                # Native async handler
                coro = handler(payload)
            else:
                # Sync handler → run in threadpool
                loop = asyncio.get_running_loop()
                coro = loop.run_in_executor(None, handler, payload)

            return await asyncio.wait_for(coro, timeout=timeout_ms / 1000.0)
            
        except asyncio.TimeoutError as exc:
            logger.warning('Request timeout on channel %s (%.1fs)', channel, timeout_ms/1000)
            raise BusTimeout(f'Timeout waiting for {channel}') from exc
        except Exception as exc:
            logger.error('Request handler failed on channel %s: %s', channel, exc)
            raise

    # --- Lifecycle (ModuleContract compliance) ---

    async def start(self) -> bool:
        """ModuleContract: Initialize bus (already ready on construction)."""
        logger.info('EventBus started')
        return True

    async def stop(self) -> bool:
        """ModuleContract: Clear all handlers and subscribers."""
        self._event_subscribers.clear()
        self._request_handlers.clear()
        logger.info('EventBus stopped')
        return True

    async def health_check(self) -> Dict[str, Any]:
        """ModuleContract: Return bus health status."""
        event_count = sum(len(handlers) for handlers in self._event_subscribers.values())
        return {
            'ok': True,
            'latency_ms': 0.0,
            'event_handlers': event_count,
            'request_handlers': len(self._request_handlers)
        }

    # --- Utilities ---

    def clear(self) -> None:
        """Remove all subscriptions and handlers. Useful in tests."""
        self._event_subscribers.clear()
        self._request_handlers.clear()

    def subscriber_count(self, event_type: Type) -> int:
        """Get number of subscribers for an event type."""
        return len(self._event_subscribers.get(event_type, []))

    def handler_count(self, channel: str) -> int:
        """Get number of handlers for a request channel (always 0 or 1)."""
        return 1 if channel in self._request_handlers else 0

    # --- Internal helpers ---

    async def _safe_async_invoke(self, coro: Coroutine, handler: Callable, event_type: Type, event: Any) -> None:
        """Safely invoke async event handler."""
        try:
            await coro
        except Exception as exc:
            self._log_handler_error(handler, event_type, exc)

    def _log_handler_error(self, handler: Callable, event_type: Type, exc: Exception) -> None:
        """Log handler exception with context."""
        handler_name = (getattr(handler, '__name__', None) or 
                       getattr(handler, '__qualname__', None) or 
                       repr(handler))
        logger.error(
            "EventBus: handler %s raised %s for event %s",
            handler_name,
            type(exc).__name__,
            getattr(event_type, 'name', str(event_type)),
            exc_info=True,
        )


# Module-level singleton. Import this everywhere.
bus: MessageBus = MessageBus()

"""
# 1. Events (fire-and-forget)
bus.subscribe(InputReceived, handler)
bus.publish(InputReceived(text="hi"))

# 2. Async events (await completion)  
await bus.publish_async(ResponseReady(...)) 

# 3. Requests (RPC)
bus.register_handler("tts.speak", tts_handler)
audio = await bus.request("tts.speak", "hello")

# 4. Mixed pipeline
bus.publish(InputReceived(text="hi"))
result = await bus.request("ai.infer", {"prompt": "hi"})
bus.publish(ResponseReady(...))
"""