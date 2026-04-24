"""
personality/emotion_stack_manager.py

Manages emotion stack operations and decay logic.

Extracted from EmotionEngine to reduce complexity and improve modularity.
"""

import time
import random
import logging
from typing import Dict, List, Any, Optional

log = logging.getLogger(__name__)


class EmotionStackManager:
    """
    Manages emotion stack operations and decay logic.
    
    Responsibilities:
    - Add/remove emotions from stack
    - Calculate dominant emotion with decay
    - Apply temporal decay and random drift
    - Clean expired emotions
    
    This is a pure manager - no external dependencies.
    """
    
    def __init__(self, decay_rate: float = 0.01, random_drift: float = 0.005):
        self.stack: List[Dict[str, Any]] = []
        self.decay_rate = decay_rate
        self.random_drift = random_drift
        
    def add_emotion(self, name: str, intensity: float, duration: float) -> None:
        """Add emotion to stack with validation."""
        now = time.time()
        self.stack.append({
            "name": name,
            "intensity": max(0.0, min(1.0, intensity)),
            "timestamp": now,
            "expire": now + float(duration)
        })
        log.debug(f"Emotion added: {name} (intensity={intensity:.2f}, duration={duration}s)")
    
    def get_dominant_emotion(self, personality_modifiers: Optional[Dict[str, float]] = None) -> str:
        """
        Calculate dominant emotion from stack with decay and modifiers.
        
        Args:
            personality_modifiers: Optional dict of emotion modifiers from KitsuSelf
            
        Returns:
            Dominant emotion name or "neutral"
        """
        if not self.stack:
            return "neutral"

        weighted: Dict[str, float] = {}
        now = time.time()

        for emo in self.stack:
            # Skip expired emotions
            if emo.get("expire", 0) < now:
                continue

            # Apply decay based on age
            age = now - emo.get("timestamp", now)
            decay_factor = max(0.0, 1.0 - age * self.decay_rate)
            score = emo.get("intensity", 0.0) * decay_factor
            name = emo.get("name", "neutral")

            weighted[name] = weighted.get(name, 0.0) + score

        # Apply personality modifiers if provided
        if personality_modifiers:
            for emotion, modifier in personality_modifiers.items():
                weighted[emotion] = weighted.get(emotion, 0.0) + modifier

        if not weighted:
            return "neutral"

        # Return emotion with highest score
        return max(weighted, key=weighted.get)
    
    def get_current_intensity(self) -> float:
        """Get normalized intensity for dominant emotion."""
        if not self.stack:
            return 0.0

        weighted: Dict[str, float] = {}
        now = time.time()

        for emo in self.stack:
            if emo.get("expire", 0) < now:
                continue

            age = now - emo.get("timestamp", now)
            decay_factor = max(0.0, 1.0 - age * self.decay_rate)
            score = emo.get("intensity", 0.0) * decay_factor
            name = emo.get("name", "neutral")
            weighted[name] = weighted.get(name, 0.0) + score

        if not weighted:
            return 0.0

        dominant = max(weighted, key=weighted.get)
        dom_value = weighted.get(dominant, 0.0)
        total = sum(weighted.values())
        try:
            confidence = float(dom_value) / float(total) if total > 0 else 0.0
        except Exception:
            confidence = 0.0

        return max(0.0, min(1.0, confidence))
    
    def apply_decay(self) -> None:
        """Apply decay to all emotions in stack."""
        now = time.time()
        
        # Remove expired emotions
        self.stack = [
            emo for emo in self.stack
            if emo.get("expire", 0) >= now and emo.get("intensity", 0.0) > 0
        ]

        # Apply decay with random drift
        for emo in self.stack:
            drift = random.uniform(-self.random_drift, self.random_drift)
            old = emo.get("intensity", 0.0)
            new = max(0.0, min(1.0, old - self.decay_rate + drift))
            emo["intensity"] = new
    
    def clear(self) -> None:
        """Clear all emotions from stack."""
        self.stack.clear()
    
    def get_stack_size(self) -> int:
        """Get current stack size."""
        return len(self.stack)
    
    def get_resistance(self) -> float:
        """Calculate resistance based on active emotions."""
        now = time.time()
        active = [emo for emo in self.stack if emo.get("expire", 0) >= now]

        if not active:
            return 0.0

        total_intensity = sum(emo.get("intensity", 0.0) for emo in active)
        avg_intensity = total_intensity / max(1, len(active))
        return max(0.0, min(1.0, avg_intensity))
