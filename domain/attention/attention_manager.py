"""
domain/attention/attention_manager.py

Attention engine for dynamic prioritization.

Makes Kitsu feel "alive" by dynamically scoring and prioritizing
events, user focus, and environmental factors.
"""

import time
import logging
import math
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger(__name__)


class AttentionType(Enum):
    """Types of attention events."""
    USER_INPUT = "user_input"
    NOTIFICATION = "notification"
    DESKTOP_EVENT = "desktop_event"
    EMOTIONAL_TRIGGER = "emotional_trigger"
    SYSTEM_EVENT = "system_event"
    IDLE_TIMEOUT = "idle_timeout"
    BOREDOM = "boredom"
    MUSIC_ACTIVITY = "music_activity"
    FOCUS_CHANGE = "focus_change"


class UrgencyLevel(Enum):
    """Urgency levels for attention events."""
    LOW = 0.2
    NORMAL = 0.5
    HIGH = 0.8
    CRITICAL = 1.0


@dataclass
class AttentionEvent:
    """An event that can capture Kitsu's attention."""
    event_type: AttentionType
    urgency: UrgencyLevel
    novelty: float  # 0.0 - 1.0, how new/unexpected is this
    emotional_weight: float  # 0.0 - 1.0, emotional impact
    persistence: float  # 0.0 - 1.0, how long should this stay relevant
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_score(self) -> float:
        """Calculate attention score for this event."""
        # Decay based on age
        age = time.time() - self.timestamp
        age_decay = math.exp(-age / 10.0)  # 10-second half-life
        
        # Base score from urgency, novelty, and emotional weight
        base_score = (
            self.urgency.value * 0.4 +
            self.novelty * 0.3 +
            self.emotional_weight * 0.3
        )
        
        return base_score * age_decay * self.persistence


@dataclass
class AttentionState:
    """Current attention state of the system."""
    focus_target: Optional[str] = None
    focus_score: float = 0.0
    boredom_level: float = 0.0
    last_interaction: float = field(default_factory=time.time)
    dominant_event: Optional[AttentionEvent] = None
    active_events: List[AttentionEvent] = field(default_factory=list)


class AttentionManager:
    """
    Manages attention allocation and prioritization.
    
    Features:
    - Dynamic scoring of events based on novelty, emotion, and urgency
    - Boredom detection and idle behavior triggering
    - Focus management and interruption handling
    - Environmental awareness (music activity, desktop events)
    """
    
    def __init__(self):
        self.state = AttentionState()
        self.event_history: List[AttentionEvent] = []
        self.attention_callbacks: Dict[AttentionType, List[Callable]] = {}
        self.focus_threshold = 0.3
        self.boredom_threshold = 0.7
        self.max_events = 50
        
        # Environmental state tracking
        self.user_active = True
        self.last_user_activity = time.time()
        self.music_active = False
        self.desktop_activity_level = 0.0
        
        # Attention parameters
        self.novelty_decay_rate = 0.1
        self.emotional_decay_rate = 0.05
        self.boredom_growth_rate = 0.01
    
    def register_callback(self, event_type: AttentionType, callback: Callable) -> None:
        """Register callback for attention events."""
        if event_type not in self.attention_callbacks:
            self.attention_callbacks[event_type] = []
        self.attention_callbacks[event_type].append(callback)
    
    def add_event(
        self,
        event_type: AttentionType,
        urgency: UrgencyLevel = UrgencyLevel.NORMAL,
        novelty: float = 0.5,
        emotional_weight: float = 0.5,
        persistence: float = 0.5,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a new attention event."""
        event = AttentionEvent(
            event_type=event_type,
            urgency=urgency,
            novelty=novelty,
            emotional_weight=emotional_weight,
            persistence=persistence,
            source=source,
            metadata=metadata or {}
        )
        
        self.state.active_events.append(event)
        self.event_history.append(event)
        
        # Trigger callbacks
        if event_type in self.attention_callbacks:
            for callback in self.attention_callbacks[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    log.error(f"Attention callback error: {e}")
        
        # Update attention state
        self._update_attention_state()
        
        # Clean up old events
        self._cleanup_events()
        
        log.debug(f"Attention event: {event_type.value} (score={event.calculate_score():.2f})")
    
    def _update_attention_state(self) -> None:
        """Update current attention state based on active events."""
        if not self.state.active_events:
            self.state.focus_score = 0.0
            self.state.focus_target = None
            self.state.dominant_event = None
            return
        
        # Find highest scoring event
        best_event = None
        best_score = 0.0
        
        for event in self.state.active_events:
            score = event.calculate_score()
            if score > best_score:
                best_score = score
                best_event = event
        
        self.state.dominant_event = best_event
        self.state.focus_score = best_score
        
        if best_event and best_score >= self.focus_threshold:
            self.state.focus_target = best_event.source
        else:
            self.state.focus_target = None
    
    def _cleanup_events(self) -> None:
        """Remove expired events and limit history size."""
        now = time.time()
        
        # Remove very old/low-score events from active list
        self.state.active_events = [
            event for event in self.state.active_events
            if event.calculate_score() > 0.01 or (now - event.timestamp) < 300
        ]
        
        # Limit active events
        if len(self.state.active_events) > self.max_events:
            # Keep highest scoring events
            self.state.active_events.sort(key=lambda e: e.calculate_score(), reverse=True)
            self.state.active_events = self.state.active_events[:self.max_events]
        
        # Limit history
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-500:]
    
    def update_user_activity(self, active: bool = True) -> None:
        """Update user activity state."""
        was_active = self.user_active
        self.user_active = active
        
        if active:
            self.last_user_activity = time.time()
            self.state.boredom_level = max(0.0, self.state.boredom_level - 0.2)
            
            if not was_active:
                # User returned from idle
                self.add_event(
                    AttentionType.FOCUS_CHANGE,
                    urgency=UrgencyLevel.HIGH,
                    novelty=0.3,
                    emotional_weight=0.6,
                    source="user_return"
                )
        else:
            # User went idle - will trigger boredom
            pass
    
    def update_music_activity(self, active: bool, intensity: float = 0.5) -> None:
        """Update music activity state."""
        was_active = self.music_active
        self.music_active = active
        
        if active and not was_active:
            self.add_event(
                AttentionType.MUSIC_ACTIVITY,
                urgency=UrgencyLevel.NORMAL,
                novelty=0.4,
                emotional_weight=0.3,
                source="music",
                metadata={"intensity": intensity}
            )
    
    def update_desktop_activity(self, activity_level: float) -> None:
        """Update desktop activity level (0.0 - 1.0)."""
        old_level = self.desktop_activity_level
        self.desktop_activity_level = activity_level
        
        # Significant change in activity
        if abs(activity_level - old_level) > 0.3:
            self.add_event(
                AttentionType.DESKTOP_EVENT,
                urgency=UrgencyLevel.NORMAL,
                novelty=0.2,
                emotional_weight=0.1,
                source="desktop",
                metadata={"activity_level": activity_level}
            )
    
    def trigger_emotional_event(
        self,
        emotion: str,
        intensity: float,
        source: str = "emotion_system"
    ) -> None:
        """Trigger an emotional attention event."""
        self.add_event(
            AttentionType.EMOTIONAL_TRIGGER,
            urgency=UrgencyLevel.HIGH if intensity > 0.7 else UrgencyLevel.NORMAL,
            novelty=0.3,  # Emotions are somewhat expected
            emotional_weight=intensity,
            persistence=0.8,  # Emotions persist longer
            source=source,
            metadata={"emotion": emotion, "intensity": intensity}
        )
    
    def trigger_user_input(
        self,
        input_type: str,
        urgency: UrgencyLevel = UrgencyLevel.NORMAL,
        novelty: float = 0.5
    ) -> None:
        """Trigger user input attention event."""
        self.add_event(
            AttentionType.USER_INPUT,
            urgency=urgency,
            novelty=novelty,
            emotional_weight=0.6,  # User input is emotionally important
            persistence=0.3,  # User input doesn't persist as long
            source="user",
            metadata={"input_type": input_type}
        )
        
        self.update_user_activity(True)
    
    def trigger_notification(
        self,
        message: str,
        urgency: UrgencyLevel = UrgencyLevel.NORMAL,
        source: str = "system"
    ) -> None:
        """Trigger notification attention event."""
        self.add_event(
            AttentionType.NOTIFICATION,
            urgency=urgency,
            novelty=0.6,  # Notifications are somewhat novel
            emotional_weight=0.4,
            persistence=0.5,
            source=source,
            metadata={"message": message}
        )
    
    def update_boredom(self) -> None:
        """Update boredom level based on inactivity."""
        if not self.user_active:
            # Increase boredom when user is inactive
            idle_time = time.time() - self.last_user_activity
            boredom_increase = idle_time * self.boredom_growth_rate
            
            # Reduce boredom increase if there are other events
            if self.state.active_events:
                boredom_increase *= 0.5
            
            self.state.boredom_level = min(1.0, self.state.boredom_level + boredom_increase)
            
            # Trigger boredom event if threshold crossed
            if self.state.boredom_level >= self.boredom_threshold:
                self.add_event(
                    AttentionType.BOREDOM,
                    urgency=UrgencyLevel.LOW,
                    novelty=0.8,  # Boredom events are novel
                    emotional_weight=0.3,
                    persistence=0.2,
                    source="attention_system"
                )
    
    def get_attention_score(self) -> float:
        """Get current overall attention score."""
        return self.state.focus_score
    
    def get_dominant_event(self) -> Optional[AttentionEvent]:
        """Get the currently dominant attention event."""
        return self.state.dominant_event
    
    def should_interrupt(self, current_task_priority: float = 0.5) -> bool:
        """
        Determine if current attention justifies interruption.
        
        Args:
            current_task_priority: Priority of current task (0.0 - 1.0)
            
        Returns:
            True if should interrupt, False otherwise
        """
        if not self.state.dominant_event:
            return False
        
        # Critical urgency always interrupts
        if self.state.dominant_event.urgency == UrgencyLevel.CRITICAL:
            return True
        
        # High urgency interrupts if current task isn't critical
        if (self.state.dominant_event.urgency == UrgencyLevel.HIGH and 
            current_task_priority < 0.8):
            return True
        
        # Normal urgency interrupts if attention score is high enough
        if (self.state.dominant_event.urgency == UrgencyLevel.NORMAL and
            self.state.focus_score > current_task_priority + 0.2):
            return True
        
        return False
    
    def get_reflex_speed_modifier(self) -> float:
        """
        Get reflex speed modifier based on attention state.
        
        Returns:
            Multiplier for reflex speed (0.5 - 2.0)
        """
        if not self.state.dominant_event:
            return 1.0
        
        # High urgency = faster reflexes
        if self.state.dominant_event.urgency in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]:
            return 1.5 + (0.5 * self.state.focus_score)
        
        # Low urgency = slower reflexes
        if self.state.dominant_event.urgency == UrgencyLevel.LOW:
            return 0.8
        
        return 1.0
    
    def get_animation_priority(self) -> float:
        """
        Get animation priority based on attention state.
        
        Returns:
            Animation priority (0.0 - 1.0)
        """
        if not self.state.dominant_event:
            return 0.3  # Default low priority
        
        # Higher emotional weight = more expressive animation
        base_priority = self.state.dominant_event.emotional_weight * 0.6
        
        # Urgency affects animation speed/intensity
        urgency_bonus = self.state.dominant_event.urgency.value * 0.3
        
        # Novelty affects animation variety
        novelty_bonus = self.state.dominant_event.novelty * 0.1
        
        return min(1.0, base_priority + urgency_bonus + novelty_bonus)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current attention state."""
        return {
            "focus_score": self.state.focus_score,
            "focus_target": self.state.focus_target,
            "boredom_level": self.state.boredom_level,
            "user_active": self.user_active,
            "music_active": self.music_active,
            "desktop_activity": self.desktop_activity_level,
            "active_events": len(self.state.active_events),
            "dominant_event": {
                "type": self.state.dominant_event.event_type.value if self.state.dominant_event else None,
                "urgency": self.state.dominant_event.urgency.value if self.state.dominant_event else None,
                "score": self.state.dominant_event.calculate_score() if self.state.dominant_event else 0.0
            } if self.state.dominant_event else None,
            "should_interrupt": self.should_interrupt(),
            "reflex_modifier": self.get_reflex_speed_modifier(),
            "animation_priority": self.get_animation_priority()
        }
    
    def tick(self) -> None:
        """Regular tick to update attention state."""
        self.update_boredom()
        self._update_attention_state()
        self._cleanup_events()


# Global instance
ATTENTION_MANAGER = AttentionManager()
