"""
personality/personality_mapper.py

Maps emotions to personality dimensions (mood, style, state).

Extracted from EmotionEngine to reduce complexity and improve modularity.
"""

import random
import time
import logging
from typing import Tuple, Optional, Dict, Any

from domain.personality.emotion_config import (
    EMOTION_TO_MOOD, EMOTION_TO_STYLE, EMOTION_TO_STATE,
    UNSAFE_COMBINATIONS, validate_mood, validate_style
)

log = logging.getLogger(__name__)


class PersonalityMapper:
    """
    Maps emotions to personality dimensions with rules and constraints.
    
    Responsibilities:
    - Map emotion → mood/style/state
    - Apply role modifiers
    - Enforce safety constraints
    - Handle manual overrides and resistance
    """
    
    def __init__(self):
        self.manual_mood_override: Optional[str] = None
        self.manual_mood_override_expire: float = 0.0
    
    def map_emotion_to_personality(
        self, 
        emotion: str, 
        intensity: float,
        current_mood: str = "behave",
        current_style: str = "chaotic",
        current_state: str = "normal",
        resistance: float = 0.0,
        role: str = "default"
    ) -> Tuple[str, str, str]:
        """
        Map emotion to personality dimensions.
        
        Args:
            emotion: Current dominant emotion
            intensity: Emotion intensity (0.0 - 1.0)
            current_mood: Current mood (for resistance calculations)
            current_style: Current style
            current_state: Current state
            resistance: Current resistance level
            role: Current role
            
        Returns:
            Tuple of (mood, style, state)
        """
        e = (emotion or "").lower()
        
        # Check manual override
        now = time.time()
        manual_locked = False
        if self.manual_mood_override and now < self.manual_mood_override_expire:
            manual_locked = True
            mood = self.manual_mood_override
        else:
            mood = self._map_emotion_to_mood(e, intensity, current_mood, resistance)
        
        style = self._map_emotion_to_style(e, current_style)
        state = self._map_emotion_to_state(e)
        
        # Apply role modifiers
        mood, style = self._apply_role_modifiers(mood, style, role)
        
        # Apply safety overrides
        mood, style = self._apply_safety_overrides(mood, style)
        
        return mood, style, state
    
    def _map_emotion_to_mood(self, emotion: str, intensity: float, current_mood: str, resistance: float) -> str:
        """Map emotion to mood with resistance and intensity logic."""
        mapped_mood = EMOTION_TO_MOOD.get(emotion, "behave")
        
        # Strong emotions override current mood
        if mapped_mood == "mean" and emotion in {"angry", "offended", "irritated", "disgust", "betrayed"}:
            if intensity > 0.4:
                log.info(f"Mood shift: {current_mood} -> mean (emotion: {emotion})")
                return "mean"
        
        elif mapped_mood == "flirty" and emotion in {"love", "fond", "affection", "desire",
                                                    "flattered", "praise", "admire", "joy"}:
            if intensity > 0.4:
                log.info(f"Mood shift: {current_mood} -> flirty (emotion: {emotion})")
                return "flirty"
        
        elif mapped_mood == "protective" and emotion in {"protective", "defensive", "concerned", "worried"}:
            if intensity > 0.4:
                log.info(f"Mood shift: {current_mood} -> protective (emotion: {emotion})")
                return "protective"
        
        else:
            # Default: behave (with resistance)
            if current_mood != "behave":
                if resistance <= 0:
                    # No active emotions → freeze current mood
                    log.debug("No active stack → keeping current mood frozen")
                    return current_mood
                else:
                    # Resistance makes it harder to return to behave
                    chance_to_change = max(0.0, 1.0 - resistance)
                    roll = random.random()
                    if roll < chance_to_change:
                        log.info(f"Mood drift: {current_mood} -> behave")
                        return "behave"
                    else:
                        log.debug(f"Mood change resisted (resistance={resistance:.2f})")
                        return current_mood
        
        return current_mood
    
    def _map_emotion_to_style(self, emotion: str, current_style: str) -> str:
        """Map emotion to style with priority transitions."""
        mapped_style = EMOTION_TO_STYLE.get(emotion, "sweet")
        
        # Priority style transitions
        if emotion in {"hurt", "betrayed", "ashamed", "offended"}:
            if current_style != "cold":
                log.info(f"Style shift: {current_style} -> cold (emotion: {emotion})")
            return "cold"
        elif emotion in {"sad", "sadness", "fear", "anxiety", "lonely", "tired"}:
            if current_style != "direct":
                log.info(f"Style shift: {current_style} -> direct (emotion: {emotion})")
            return "direct"
        elif emotion in {"sarcastic", "witty", "ironic", "dry"}:
            if current_style != "sarcastic":
                log.info(f"Style shift: {current_style} -> sarcastic (emotion: {emotion})")
            return "sarcastic"
        elif emotion in {"playful", "joking", "teasing"} and mapped_style == "playful":
            if current_style != "playful":
                log.debug(f"Style shift: {current_style} -> playful (emotion: {emotion})")
            return "playful"
        elif mapped_style == "chaotic":
            # Would need intensity parameter here - simplified for now
            return "chaotic"
        elif emotion in {"eerie", "mysterious", "unsettling"} or (emotion == "calm" and mapped_style == "eerie"):
            if current_style != "eerie":
                log.debug(f"Style shift: {current_style} -> eerie (emotion: {emotion})")
            return "eerie"
        else:
            # Default: sweet
            return "sweet"
    
    def _map_emotion_to_state(self, emotion: str) -> str:
        """Map emotion to state."""
        return EMOTION_TO_STATE.get(emotion, "normal")
    
    def _apply_role_modifiers(self, mood: str, style: str, role: str) -> Tuple[str, str]:
        """Apply role-based personality modifiers."""
        if role == "caretaker" and mood == "mean":
            mood = "behave"
        
        if role == "observer":
            if style in {"chaotic", "playful"}:
                style = "cold"
        
        if role == "tutor" and style == "chaotic":
            style = "sweet"
        
        return mood, style
    
    def _apply_safety_overrides(self, mood: str, style: str) -> Tuple[str, str]:
        """Enforce safety constraints on mood/style combinations."""
        combo = (mood, style)
        action = UNSAFE_COMBINATIONS.get(combo)
        
        if action == "convert_to_sarcastic":
            log.debug("Unsafe combo detected (mean+cold) → converting to sarcastic")
            style = "sarcastic"
        
        return mood, style
    
    def set_manual_mood_override(self, mood: str, duration: float = 300.0) -> bool:
        """Set manual mood override with validation."""
        if validate_mood(mood):
            self.manual_mood_override = mood
            self.manual_mood_override_expire = time.time() + float(duration)
            log.info(f"Manual mood override set: {mood} for {duration}s")
            return True
        else:
            log.warning(f"Invalid mood for override: {mood}")
            return False
    
    def clear_manual_mood_override(self) -> None:
        """Clear manual mood override."""
        self.manual_mood_override = None
        self.manual_mood_override_expire = 0.0
        log.info("Manual mood override cleared")
    
    def is_manual_override_active(self) -> bool:
        """Check if manual override is still active."""
        if not self.manual_mood_override:
            return False
        return time.time() < self.manual_mood_override_expire
