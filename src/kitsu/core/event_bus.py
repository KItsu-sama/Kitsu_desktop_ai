import asyncio
import logging
from typing import Callable, Any, Dict, List
from kitsu.core.context import RequestContext

# Configure logger for core
logger = logging.getLogger("kitsu.core.event_bus")

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, handler: Callable):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(handler)
        logger.debug(f"Subscribed to {event_name}: {handler.__name__}")

    def unsubscribe(self, event_name: str, handler: Callable):
        if event_name in self.subscribers:
            try:
                self.subscribers[event_name].remove(handler)
                logger.debug(f"Unsubscribed from {event_name}: {handler.__name__}")
            except ValueError:
                pass

    async def emit(self, event_name: str, ctx: RequestContext):
        """
        Emits an event to all subscribers.
        Implements safety lock for RESPONSE_READY and structured logging.
        """
        logger.info(f"Event emitted: {event_name} [Request ID: {ctx.id}]")

        if event_name == "RESPONSE_READY":
            if ctx.responded:
                logger.debug(f"Blocked duplicate RESPONSE_READY for request {ctx.id}")
                return
            ctx.responded = True

        if event_name in self.subscribers:
            handlers = list(self.subscribers[event_name]) # Snapshot to avoid modification during iteration

            # Execute handlers and catch exceptions to prevent system-wide crash
            tasks = []
            for handler in handlers:
                tasks.append(self._invoke_handler(handler, event_name, ctx))

            await asyncio.gather(*tasks)

    async def _invoke_handler(self, handler: Callable, event_name: str, ctx: RequestContext):
        try:
            # Check if it's a coroutine function
            if asyncio.iscoroutinefunction(handler):
                await handler(ctx)
            else:
                # Run synchronous handlers in a threadpool to avoid blocking the event loop
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, handler, ctx)
        except Exception as e:
            logger.error(f"Error in handler {handler.__name__} for event {event_name}: {e}", exc_info=True)

bus = EventBus()
