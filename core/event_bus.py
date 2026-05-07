import asyncio
import logging
from typing import Callable, Any, Dict, List
from core.context import RequestContext

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, handler: Callable):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(handler)

    async def emit(self, event_name: str, ctx: RequestContext):
        if event_name == "RESPONSE_READY":
            if ctx.responded:
                logger.warning(f"Blocked duplicate RESPONSE_READY for request {ctx.id}")
                return
            ctx.responded = True

        if event_name in self.subscribers:
            handlers = self.subscribers[event_name]
            await asyncio.gather(*(handler(ctx) for handler in handlers))

bus = EventBus()
