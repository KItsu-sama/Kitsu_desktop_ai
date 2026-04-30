"""
core/personality/emotion_model.py

Pure data structures for emotion state.

This module defines:
- EmotionState: Current emotion state data structure
- EmotionStack: Stack-based emotion tracking
- EmotionEntry: Individual emotion entry in stack

Responsibilities:
- Define emotion data structures
- Provide pure data models (no logic, no I/O)

Non-responsibilities:
- State management (manager/emotion_manager.py)
- File I/O
- Logic or decision making
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

# ============================================================================
# Emotion Entry (Stack Item)
# ============================================================================

@dataclass
class EmotionEntry:
    """
    Single emotion entry in the emotion stack.
    
    Pure data structure - no methods, no logic.
    """
    name: str                    # Emotion name (e.g., "happy", "angry")
    intensity: float             # 0.0 - 1.0
    timestamp: float             # Unix timestamp when emotion was added
    expire: float                # Unix timestamp when emotion expires
    source: Optional[str] = None  # Source of emotion (trigger, user_input, etc.)

# ============================================================================
# Emotion Stack
# ============================================================================

@dataclass
class EmotionStack:
    """
    Stack-based emotion tracking.
    
    Pure data structure - stores emotions but doesn't manage them.
    Logic is handled by manager/emotion_manager.py
    """
    entries: List[EmotionEntry] = field(default_factory=list)
    
    def add(self, entry: EmotionEntry) -> None:
        """Add emotion entry to stack."""
        self.entries.append(entry)
    
    def remove_expired(self, current_time: float) -> None:
        """Remove expired entries (pure data operation)."""
        self.entries = [
            entry for entry in self.entries
            if entry.expire >= current_time and entry.intensity > 0.0
        ]
    
    def get_active(self, current_time: float) -> List[EmotionEntry]:
        """Get active (non-expired) entries."""
        return [
            entry for entry in self.entries
            if entry.expire >= current_time and entry.intensity > 0.0
        ]
    
    def clear(self) -> None:
        """Clear all entries."""
        self.entries.clear()

    def get_expired(self, current_time: float) -> List[EmotionEntry]:
        """Return expired entries without mutating stack."""
        return [
            entry for entry in self.entries
            if entry.expire < current_time or entry.intensity <= 0.0
        ]
    
    def is_manual_override_active(self, current_time: float) -> bool:
        """
            Check if manual mood override is still active.
            Pure helper.
        """
        if not self.manual_mood_override:
            return False
        return current_time < self.manual_mood_override_expire

# ============================================================================
# Emotion State
# ============================================================================

@dataclass
class EmotionState:
    """
    Current emotion state data structure.
    
    Represents Kitsu's current emotional state:
    - Current mood and style
    - Emotion stack
    - Resistance level
    - Hidden/sleep state
    
    Pure data structure - no logic, no I/O.
    """
    mood: str = "behave"              # Current mood (from VALID_MOODS)
    style: str = "chaotic"             # Current style (from VALID_STYLES)
    stack: EmotionStack = field(default_factory=EmotionStack)
    resistance: float = 0.0           # Resistance to mood changes (0.0 - 1.0)
    is_hidden: bool = False           # Sleep/hide state
    manual_mood_override: Optional[str] = None  # Manual mood override
    manual_mood_override_expire: float = 0.0    # Override expiration time
    
    def get_dominant_emotion(
        self,
        current_time: float,
        decay_rate: float = 0.01,
        minimum_decay: float = 0.0
    ) -> str:
        """
        Calculate dominant emotion from stack.

        Pure calculation - no side effects.

        Args:
            current_time: Current Unix timestamp
            decay_rate: Linear decay per second
            minimum_decay: Floor for decay factor (default 0.0)

        Returns:
            Dominant emotion name, or "neutral"
        """
        active = self.stack.get_active(current_time)
        if not active:
            return "neutral"

        weighted: Dict[str, float] = {}

        for entry in active:
            age = current_time - entry.timestamp
            decay_factor = max(minimum_decay, 1.0 - age * decay_rate)
            score = entry.intensity * decay_factor

            weighted[entry.name] = weighted.get(entry.name, 0.0) + score

        if not weighted:
            return "neutral"

        # Deterministic tie-breaker (recent wins)
        return max(
            weighted.items(),
            key=lambda item: (item[1], max(
                e.timestamp for e in active if e.name == item[0]
            ))
        )[0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export state to dictionary (for persistence)."""
        return {
            "mood": self.mood,
            "style": self.style,
            "resistance": self.resistance,
            "is_hidden": self.is_hidden,
            "manual_mood_override": self.manual_mood_override,
            "manual_mood_override_expire": self.manual_mood_override_expire,
            "stack_entries": [
                {
                    "name": entry.name,
                    "intensity": entry.intensity,
                    "timestamp": entry.timestamp,
                    "expire": entry.expire,
                    "source": entry.source
                }
                for entry in self.stack.entries
            ]
        }
    
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmotionState':
        """Create EmotionState from dictionary (for loading)."""
        state = cls(
            mood=data.get("mood", "behave"),
            style=data.get("style", "chaotic"),
            resistance=data.get("resistance", 0.0),
            is_hidden=data.get("is_hidden", False),
            manual_mood_override=data.get("manual_mood_override"),
            manual_mood_override_expire=data.get("manual_mood_override_expire", 0.0)
        )
        
        # Restore stack entries
        for entry_data in data.get("stack_entries", []):
            entry = EmotionEntry(
                name=entry_data["name"],
                intensity=entry_data["intensity"],
                timestamp=entry_data["timestamp"],
                expire=entry_data["expire"],
                source=entry_data.get("source")
            )
            state.stack.add(entry)
        
        return state
