"""
runtime/communication/events.py

Plain dataclass event definitions for the Kitsu event bus.
No logic. No imports from anywhere else in the project.

Adding a new event: define a dataclass here, publish/subscribe via core/bus.py.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time
import logging

from runtime.communication.bus import MessageBus

logger = logging.getLogger('kitsu.core.events')

EventBus = MessageBus


class EventType(Enum):
    """Enum for all known event types."""
    # System lifecycle
    APP_READY = 'APP_READY'
    APP_SHUTDOWN = 'APP_SHUTDOWN'
    MODULE_STARTED = 'MODULE_STARTED'
    MODULE_FAILED = 'MODULE_FAILED'
    MODULE_DEGRADED = 'MODULE_DEGRADED'
    
    # Input pipeline
    USER_INPUT = 'USER_INPUT'
    INPUT_RECEIVED = 'INPUT_RECEIVED'
    SPAM_DETECTED = 'SPAM_DETECTED'
    ROUTING_DECISION = 'ROUTING_DECISION'
    ROUTE_DECIDED = 'ROUTE_DECIDED'
    
    # Resource & tier management
    STRIP_TIER_CHANGED = 'STRIP_TIER_CHANGED'
    HEALTH_CHECK_FAILED = 'HEALTH_CHECK_FAILED'
    IDLE_STATE_CHANGED = 'IDLE_STATE_CHANGED'
    PERMISSION_CHANGED = 'PERMISSION_CHANGED'
    LOADING_PROGRESS = 'LOADING_PROGRESS'
    PERFORMANCE_PRESSURE = 'PERFORMANCE_PRESSURE'
    
    # AI processing
    AI_REQUEST = 'AI_REQUEST'
    AI_RESPONSE = 'AI_RESPONSE'
    RESPONSE_READY = 'RESPONSE_READY'
    
    # UI & presentation
    CHARACTER_LOADED = 'CHARACTER_LOADED'
    
    # Emotion
    EMOTION_SIGNAL = 'EMOTION_SIGNAL'
    EMOTION_CHANGED = 'EMOTION_CHANGED'
    
    # Avatar
    AVATAR_EXPRESSION_REQUEST = 'AVATAR_EXPRESSION_REQUEST'
    AVATAR_SWITCHED = 'AVATAR_SWITCHED'
    
    # Safety & system
    SUBSYSTEM_FAILED = 'SUBSYSTEM_FAILED'
    SHUTDOWN_REQUESTED = 'SHUTDOWN_REQUESTED'
    KILL_SWITCH_ACTIVATED = 'KILL_SWITCH_ACTIVATED'
    LOOP_DETECTED = 'LOOP_DETECTED'
    
    # Background tasks
    BACKGROUND_TASK_STARTED = 'BACKGROUND_TASK_STARTED'
    BACKGROUND_TASK_COMPLETED = 'BACKGROUND_TASK_COMPLETED'
    BACKGROUND_TASKS_STOPPED = 'BACKGROUND_TASKS_STOPPED'


@dataclass(frozen=True)
class EventPayload:
    """Generic event payload wrapper."""
    event_type: EventType
    source: str
    data: Any | None = None
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Input Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InputReceived:
    """A raw user input arrived (text or voice transcript)."""
    text: str
    source: str = "text"          # "text" | "voice"
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SpamDetected:
    """Same input repeated >= threshold times within the spam window."""
    text: str
    count: int
    window_seconds: float
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# AI Pipeline Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResponseReady:
    """A final response has been produced and is ready to display."""
    input_text: str
    response_text: str
    source: str = "fast_brain"    # "fast_brain" | "slm" | "llm" | "template"
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class RouteDecided:
    """PolicyRouter has determined which pipeline tier will handle this input."""
    input_text: str
    route: str                    # "fast_brain" | "slm" | "llm" | "cache"
    confidence: float
    freshness_required: bool
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Emotion Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmotionSignal:
    """An emotion event to push onto the emotion stack."""
    emotion: str
    intensity: float              # 0.0–1.0
    source: str = "system"        # who triggered it
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class EmotionChanged:
    """The dominant emotion state has changed after stack recalculation."""
    mood: str
    style: str
    state: str
    dominant_emotion: str
    intensity: float
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Avatar Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AvatarExpressionRequest:
    """Ask the avatar to switch to a specific expression."""
    mood: str
    style: str
    state: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AvatarSwitched:
    """Avatar renderer has switched between 2D and 3D."""
    new_mode: str                 # "2d" | "3d"
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# System Lifecycle Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IdleStateChanged:
    """User activity state changed."""
    new_state: str                # "active" | "idle" | "sleep"
    previous_state: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SubsystemFailed:
    """A subsystem reported a failure. Orchestrator degrades gracefully."""
    subsystem: str
    error: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ShutdownRequested:
    """A clean shutdown has been requested."""
    reason: str = "user"
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Safety Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KillSwitchActivated:
    """The kill switch hotkey was pressed. All automation stops immediately."""
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class LoopDetected:
    """loop_guard.py detected a repeating action loop."""
    action: str
    count: int
    window_seconds: float
    timestamp: float = field(default_factory=time.time)


# Legacy event mapping for backwards compatibility
_EVENT_TYPE_MAP = {
    EventType.INPUT_RECEIVED: InputReceived,
    EventType.SPAM_DETECTED: SpamDetected,
    EventType.RESPONSE_READY: ResponseReady,
    EventType.ROUTE_DECIDED: RouteDecided,
    EventType.EMOTION_SIGNAL: EmotionSignal,
    EventType.EMOTION_CHANGED: EmotionChanged,
    EventType.AVATAR_EXPRESSION_REQUEST: AvatarExpressionRequest,
    EventType.AVATAR_SWITCHED: AvatarSwitched,
    EventType.IDLE_STATE_CHANGED: IdleStateChanged,
    EventType.SUBSYSTEM_FAILED: SubsystemFailed,
    EventType.SHUTDOWN_REQUESTED: ShutdownRequested,
    EventType.KILL_SWITCH_ACTIVATED: KillSwitchActivated,
    EventType.LOOP_DETECTED: LoopDetected,
}


def create_event_payload(event_type: EventType, **kwargs: Any) -> EventPayload:
    """Helper to create EventPayload from EventType and data."""
    event_class = _EVENT_TYPE_MAP.get(event_type)
    if event_class:
        try:
            event_instance = event_class(**kwargs)
            return EventPayload(event_type=event_type, source="system", data=event_instance)
        except Exception as e:
            logger.warning("Failed to create event instance for %s: %s", event_type, e)
    
    return EventPayload(event_type=event_type, source="system", data=kwargs)