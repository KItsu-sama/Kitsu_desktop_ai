"""
core/unified_events.py

Unified event system consolidating legacy and modern event handling.
This fixes event system chaos by providing a single, coherent
event architecture with proper typing and routing.
"""

from __future__ import annotations

import logging
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Set, Union, Type
from enum import Enum
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels for ordering."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class UnifiedEvent:
    """Unified event structure."""
    event_type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    target: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Ensure data is a dict
        if not isinstance(self.data, dict):
            self.data = {'value': self.data}
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data field with default."""
        return self.data.get(key, default)
    
    def set_data(self, key: str, value: Any) -> None:
        """Set data field."""
        self.data[key] = value
    
    def has_data(self, key: str) -> bool:
        """Check if data field exists."""
        return key in self.data


class EventHandler:
    """Event handler with metadata."""
    
    def __init__(
        self, 
        handler: Callable[[UnifiedEvent], Union[Any, None]],
        event_type: str,
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: Optional[Callable[[UnifiedEvent], bool]] = None,
        once: bool = False,
        weak_ref: bool = False
    ):
        self.handler = handler
        self.event_type = event_type
        self.priority = priority
        self.filter_func = filter_func
        self.once = once
        self.weak_ref = weak_ref
        self.call_count = 0
        self.last_called = 0.0
        self.id = id(handler)
    
    def should_handle(self, event: UnifiedEvent) -> bool:
        """Check if handler should process this event."""
        if self.event_type != event.event_type:
            return False
        
        if self.filter_func and not self.filter_func(event):
            return False
        
        if self.once and self.call_count > 0:
            return False
        
        return True
    
    async def handle(self, event: UnifiedEvent) -> Any:
        """Handle the event."""
        try:
            self.call_count += 1
            self.last_called = time.time()
            
            if asyncio.iscoroutinefunction(self.handler):
                return await self.handler(event)
            else:
                return self.handler(event)
        except Exception as e:
            logger.error(f"Error in event handler for {event.event_type}: {e}")
            return None


class EventSubscription:
    """Manages a subscription to an event type."""
    
    def __init__(self, event_type: str):
        self.event_type = event_type
        self.handlers: List[EventHandler] = []
        self.handler_ids: Set[int] = set()
    
    def add_handler(self, handler: EventHandler) -> None:
        """Add a handler to this subscription."""
        self.handlers.append(handler)
        self.handler_ids.add(handler.id)
        # Sort by priority (higher priority first)
        self.handlers.sort(key=lambda h: h.priority.value, reverse=True)
    
    def remove_handler(self, handler_id: int) -> bool:
        """Remove a handler by ID."""
        self.handlers = [h for h in self.handlers if h.id != handler_id]
        self.handler_ids.discard(handler_id)
        return handler_id in self.handler_ids
    
    def get_handlers(self) -> List[EventHandler]:
        """Get all handlers for this event type."""
        return self.handlers.copy()
    
    def get_matching_handlers(self, event: UnifiedEvent) -> List[EventHandler]:
        """Get handlers that should handle this event."""
        return [h for h in self.handlers if h.should_handle(event)]


class UnifiedEventBus:
    """Unified event bus consolidating all event handling."""
    
    def __init__(self):
        self._subscriptions: Dict[str, EventSubscription] = defaultdict(EventSubscription)
        self._global_handlers: List[EventHandler] = []
        self._event_history: List[UnifiedEvent] = []
        self._max_history = 1000
        self._middleware: List[Callable[[UnifiedEvent], UnifiedEvent]] = []
        self._stats = {
            'events_published': 0,
            'events_handled': 0,
            'handlers_registered': 0,
            'middleware_registered': 0
        }
    
    def subscribe(
        self, 
        event_type: str,
        handler: Callable[[UnifiedEvent], Union[Any, None]],
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: Optional[Callable[[UnifiedEvent], bool]] = None,
        once: bool = False,
        weak_ref: bool = False
    ) -> int:
        """Subscribe to an event type."""
        event_handler = EventHandler(
            handler=handler,
            event_type=event_type,
            priority=priority,
            filter_func=filter_func,
            once=once,
            weak_ref=weak_ref
        )
        
        subscription = self._subscriptions[event_type]
        subscription.add_handler(event_handler)
        
        self._stats['handlers_registered'] += 1
        logger.debug(f"Subscribed to {event_type} with handler {event_handler.id}")
        
        return event_handler.id
    
    def unsubscribe(self, handler_id: int) -> bool:
        """Unsubscribe a handler by ID."""
        # Remove from all subscriptions
        removed = False
        for subscription in self._subscriptions.values():
            if subscription.remove_handler(handler_id):
                removed = True
        
        # Remove from global handlers
        self._global_handlers = [h for h in self._global_handlers if h.id != handler_id]
        
        if removed:
            self._stats['handlers_registered'] -= 1
            logger.debug(f"Unsubscribed handler {handler_id}")
        
        return removed
    
    def subscribe_all(
        self, 
        handler: Callable[[UnifiedEvent], Union[Any, None]],
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: Optional[Callable[[UnifiedEvent], bool]] = None,
        once: bool = False,
        weak_ref: bool = False
    ) -> int:
        """Subscribe to all events."""
        event_handler = EventHandler(
            handler=handler,
            event_type="*",  # Wildcard for all events
            priority=priority,
            filter_func=filter_func,
            once=once,
            weak_ref=weak_ref
        )
        
        self._global_handlers.append(event_handler)
        self._stats['handlers_registered'] += 1
        logger.debug(f"Subscribed to all events with handler {event_handler.id}")
        
        return event_handler.id
    
    def publish(self, event: UnifiedEvent) -> int:
        """Publish an event to all subscribers."""
        self._stats['events_published'] += 1
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Apply middleware
        processed_event = event
        for middleware in self._middleware:
            try:
                if asyncio.iscoroutinefunction(middleware):
                    processed_event = await middleware(processed_event)
                else:
                    processed_event = middleware(processed_event)
            except Exception as e:
                logger.error(f"Error in event middleware: {e}")
        
        # Route to specific handlers
        handlers_called = 0
        subscription = self._subscriptions.get(processed_event.event_type)
        if subscription:
            matching_handlers = subscription.get_matching_handlers(processed_event)
            for handler in matching_handlers:
                try:
                    result = await handler.handle(processed_event)
                    if result is not None:
                        handlers_called += 1
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
        
        # Route to global handlers
        for handler in self._global_handlers:
            if handler.should_handle(processed_event):
                try:
                    result = await handler.handle(processed_event)
                    if result is not None:
                        handlers_called += 1
                except Exception as e:
                    logger.error(f"Error in global event handler: {e}")
        
        self._stats['events_handled'] += handlers_called
        return handlers_called
    
    def add_middleware(self, middleware: Callable[[UnifiedEvent], UnifiedEvent]) -> None:
        """Add event middleware."""
        self._middleware.append(middleware)
        self._stats['middleware_registered'] += 1
        logger.debug("Added event middleware")
    
    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[UnifiedEvent]:
        """Get event history."""
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda e: e.timestamp, reverse=True)
        
        return history[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            'active_subscriptions': len([s for s in self._subscriptions.values() if s.handlers]),
            'global_handlers': len(self._global_handlers),
            'event_history_size': len(self._event_history)
        }
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        logger.info("Cleared event history")
    
    def clear_all_subscriptions(self) -> None:
        """Clear all subscriptions."""
        self._subscriptions.clear()
        self._global_handlers.clear()
        self._stats['handlers_registered'] = 0
        logger.info("Cleared all event subscriptions")


# Legacy compatibility layer
class LegacyEventAdapter:
    """Adapter for legacy event system."""
    
    def __init__(self, unified_bus: UnifiedEventBus):
        self.unified_bus = unified_bus
        self._legacy_mappings = {}
    
    def register_legacy_event(self, legacy_class: Type, unified_type: str) -> None:
        """Register a mapping from legacy event class to unified type."""
        self._legacy_mappings[legacy_class] = unified_type
        logger.debug(f"Mapped legacy event {legacy_class.__name__} to {unified_type}")
    
    def publish_legacy(self, legacy_event, source: str = "legacy") -> int:
        """Publish a legacy event."""
        # Try to get mapping
        unified_type = self._legacy_mappings.get(type(legacy_event))
        if not unified_type:
            # Use class name as fallback
            unified_type = legacy_event.__class__.__name__
        
        # Convert to unified event
        unified_event = UnifiedEvent(
            event_type=unified_type,
            source=source,
            data=getattr(legacy_event, '__dict__', {}),
            timestamp=getattr(legacy_event, 'timestamp', time.time())
        )
        
        return self.unified_bus.publish(unified_event)
    
    def subscribe_legacy(self, legacy_class: Type, handler: Callable) -> int:
        """Subscribe to a legacy event type."""
        unified_type = self._legacy_mappings.get(legacy_class, legacy_class.__name__)
        return self.unified_bus.subscribe(unified_type, handler)


# Global event bus instance
_event_bus: Optional[UnifiedEventBus] = None


def get_event_bus() -> UnifiedEventBus:
    """Get the global event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = UnifiedEventBus()
    return _event_bus


def set_event_bus(event_bus: UnifiedEventBus) -> None:
    """Set the global event bus (for testing)."""
    global _event_bus
    _event_bus = event_bus


def get_legacy_adapter() -> LegacyEventAdapter:
    """Get the legacy event adapter."""
    unified_bus = get_event_bus()
    return LegacyEventAdapter(unified_bus)


# Convenience functions
def subscribe(event_type: str, handler: Callable, **kwargs) -> int:
    """Convenience function to subscribe to events."""
    bus = get_event_bus()
    return bus.subscribe(event_type, handler, **kwargs)


def publish(event_type: str, data: Dict[str, Any] = None, **kwargs) -> int:
    """Convenience function to publish events."""
    bus = get_event_bus()
    event = UnifiedEvent(
        event_type=event_type,
        source="convenience",
        data=data or {},
        **kwargs
    )
    return bus.publish(event)


def subscribe_all(handler: Callable, **kwargs) -> int:
    """Convenience function to subscribe to all events."""
    bus = get_event_bus()
    return bus.subscribe_all(handler, **kwargs)
