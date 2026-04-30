"""
personality/emotion_manager.py

EmotionManager = Single Source of Truth for Kitsu's emotional state.

Three-Layer Model:
- Layer 1 (Raw): Stack of active emotions with temporal decay
- Layer 2 (Stable): Mood (behave, mean, flirty, protective) + Style (chaotic, sweet, cold, direct, sarcastic, playful, eerie)
- Layer 3 (Output): Consistent state for Avatar, LLM Prompt, Voice Tone

Responsibilities:
- Manage emotion stack with decay and physics
- Map volatile emotions to stable Mood/Style axes
- Handle emotional momentum and resistance
- Provide unified state export for all subsystems
- Run continuous decay loop (orchestrator heartbeat)

Non-responsibilities:
- File I/O (delegates to memory_manager for persistence)
- Training or learning
- UI rendering
- Direct LLM prompt generation (uses mood/style for other systems)
"""

import asyncio
import random
import time
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from domain.personality.emotion_model import EmotionState, EmotionEntry, EmotionStack
from shared.personality_config import (
    VALID_MOODS, VALID_STYLES,
    EMOTION_TO_MOOD, EMOTION_TO_STYLE,
    get_legacy_mode, validate_mood, validate_style
)

if TYPE_CHECKING:
    from domain.personality.kitsu_identity import KitsuIdentity

log = logging.getLogger(__name__)


class EmotionManager:
    """
    Single Source of Truth for Kitsu's emotional state.
    
    Three-Layer Architecture:
    - Raw Emotions: Stack-based emotion system with temporal decay
    - Stable Personality: Mood + Style axes for consistent behavior
    - Subsystem Output: Unified state for Avatar, LLM, Voice
    
    Features:
    - Emotional physics (decay, momentum, resistance)
    - Manual overrides with duration
    - Thread-safe async tick integration
    - Configuration-driven mappings and thresholds
    """
    
    def __init__(
        self,
        kitsu_identity: Optional['KitsuIdentity'] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        continuous_decay: bool = False  # Changed default - orchestrator controls timing
    ):
        """
        Initialize emotion manager as Single Source of Truth.
        
        Args:
            kitsu_identity: KitsuIdentity instance for personality integration
            initial_state: Previously saved state (from memory_manager)
            continuous_decay: If True, run background decay. If False, decay only on tick()
        """
        self.kitsu_identity = kitsu_identity
        
        # Initialize emotion state
        if initial_state:
            self.state = EmotionState.from_dict(initial_state)
        else:
            self.state = EmotionState(
                mood="behave",
                style="chaotic",
                stack=EmotionStack()
            )
        
        # Physics parameters (config-driven)
        self.decay_rate = 0.01  # PERSONALITY_DECAY_RATE from config
        self.random_drift = 0.005  # PERSONALITY_RANDOM_DRIFT from config
        self.continuous_decay = continuous_decay
        
        # Emotional momentum for resistance system
        self.momentum_factor = 0.7  # How much past emotions affect current resistance
        
        log.info(f"EmotionManager initialized as SSoT: {self.state.mood}/{self.state.style}")
    
    # =========================================================================
    # Core Emotion Stack Management (Layer 1: Raw Emotions)
    # =========================================================================
    
    def add_emotion(
        self,
        name: str,
        intensity: float = 0.5,
        duration: float = 5.0,
        source: Optional[str] = None
    ) -> None:
        """
        Add emotion to raw emotion stack.
        
        Args:
            name: Emotion name (e.g., "happy", "angry")
            intensity: Emotion strength (0.0 - 1.0)
            duration: How long emotion lasts (seconds)
            source: Source of emotion (trigger, user_input, etc.)
        """
        now = time.time()
        entry = EmotionEntry(
            name=name,
            intensity=max(0.0, min(1.0, intensity)),
            timestamp=now,
            expire=now + float(duration),
            source=source
        )
        self.state.stack.add(entry)
        log.debug(f"Raw emotion added: {name} (intensity={intensity:.2f}, duration={duration}s)")
        
        # Update stable personality from new emotion
        self._update_stable_personality_from_emotion(name)
    
    def get_dominant_emotion(self) -> str:
        """
        Return the currently dominant emotion from raw stack.
        
        Calculates weighted scores with decay and personality modifiers.
        
        Returns:
            Dominant emotion name (e.g., "happy", "angry", "neutral")
        """
        now = time.time()
        dominant = self.state.get_dominant_emotion(now)
        
        # Apply personality modifiers from KitsuIdentity
        if self.kitsu_identity and dominant == "neutral":
            # If no active emotions, check identity reflection
            try:
                if hasattr(self.kitsu_identity, 'get_reflection'):
                    if self.kitsu_identity.get_reflection("angry") > 0.5:
                        return "angry"
                    if self.kitsu_identity.get_reflection("happy") > 0.5:
                        return "happy"
            except Exception as e:
                log.debug(f"Could not get reflection from kitsu_identity: {e}")
        
        return dominant

    def get_dominant_intensity(self) -> float:
        """
        Return normalized intensity/confidence for the currently dominant emotion.

        Uses the active stack entries to compute weighted scores and returns the
        dominant emotion's share (0.0 - 1.0).
        """
        now = time.time()
        active = self.state.stack.get_active(now)

        if not active:
            return 0.0

        weighted: Dict[str, float] = {}
        for entry in active:
            age = now - entry.timestamp
            decay_factor = max(0.1, 1.0 - age * 0.01)
            score = entry.intensity * decay_factor
            weighted[entry.name] = weighted.get(entry.name, 0.0) + score

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
    
    def update_intensity(self, name: str, delta: float) -> None:
        """
        Adjust intensity of most recent matching emotion.
        
        Args:
            name: Emotion name to update
            delta: Amount to change intensity by
        """
        now = time.time()
        active = self.state.stack.get_active(now)
        
        for entry in reversed(active):
            if entry.name == name:
                old = entry.intensity
                new = max(0.0, min(1.0, old + delta))
                entry.intensity = new
                log.debug(f"Updated {name} intensity: {old:.2f} -> {new:.2f}")
                return
    
    # =========================================================================
    # Stable Personality Mapping (Layer 2: Mood + Style)
    # =========================================================================
    
    def _update_stable_personality_from_emotion(self, emotion: str) -> None:
        """
        Map dominant raw emotion to stable (mood, style) axes.
        
        Fast shifts on strong triggers, slow drift otherwise.
        Respects manual mood overrides.
        
        Args:
            emotion: Raw emotion name that was just added
        """
        if self.state.is_hidden:
            self.state.style = "direct"
            return
        
        e = emotion.lower()
        
        # Check manual override
        now = time.time()
        manual_locked = False
        if (self.state.manual_mood_override and 
            now < self.state.manual_mood_override_expire):
            manual_locked = True
            self.state.mood = self.state.manual_mood_override
        
        # Compute current resistance with emotional momentum
        resistance = self._calculate_emotional_resistance()
        self.state.resistance = resistance
        
        # --- Primary mood axis (Layer 2 Stable) ---
        mapped_mood = EMOTION_TO_MOOD.get(e, "behave")
        
        # Strong emotions override current mood
        if mapped_mood == "mean" and e in {"angry", "offended", "irritated", "disgust", "betrayed"}:
            if not manual_locked:
                if self.state.mood != "mean":
                    log.info(f"Mood shift: {self.state.mood} -> mean (emotion: {e})")
                self.state.mood = "mean"
        
        elif mapped_mood == "flirty" and e in {"love", "fond", "affection", "desire", 
                                                "flattered", "praise", "admire", "joy"}:
            if not manual_locked:
                if self.state.mood != "flirty":
                    log.info(f"Mood shift: {self.state.mood} -> flirty (emotion: {e})")
                self.state.mood = "flirty"
        
        elif mapped_mood == "protective" and e in {"protective", "defensive", "concerned", "worried"}:
            if not manual_locked:
                if self.state.mood != "protective":
                    log.info(f"Mood shift: {self.state.mood} -> protective (emotion: {e})")
                self.state.mood = "protective"
        
        else:
            # Default: behave (with resistance)
            if not manual_locked and self.state.mood != "behave":
                if resistance <= 0:
                    # No active emotions → freeze current mood
                    log.debug("No active stack → keeping current mood frozen")
                else:
                    # Resistance makes it harder to return to behave
                    chance_to_change = max(0.0, 1.0 - resistance)
                    roll = random.random()
                    if roll < chance_to_change:
                        log.info(f"Mood drift: {self.state.mood} -> behave")
                        self.state.mood = "behave"
        
        # --- Style overlay (Layer 2 Stable) ---
        mapped_style = EMOTION_TO_STYLE.get(e, "sweet")
        
        # Priority style transitions
        if e in {"hurt", "betrayed", "ashamed", "offended"}:
            if self.state.style != "cold":
                log.info(f"Style shift: {self.state.style} -> cold (emotion: {e})")
            self.state.style = "cold"
        elif e in {"sad", "sadness", "fear", "anxiety", "lonely", "tired"}:
            if self.state.style != "direct":
                log.info(f"Style shift: {self.state.style} -> direct (emotion: {e})")
            self.state.style = "direct"
        elif e in {"sarcastic", "witty", "ironic", "dry"}:
            if self.state.style != "sarcastic":
                log.info(f"Style shift: {self.state.style} -> sarcastic (emotion: {e})")
            self.state.style = "sarcastic"
        elif e in {"playful", "excited", "teasing", "mischief", "chaotic",
                   "teased", "joked_with"} and mapped_style == "chaotic":
            if self.state.style != "chaotic":
                log.debug(f"Style shift: {self.state.style} -> chaotic (emotion: {e})")
            self.state.style = "chaotic"
        elif e in {"eerie", "mysterious", "unsettling"} or (e == "calm" and mapped_style == "eerie"):
            if self.state.style != "eerie":
                log.debug(f"Style shift: {self.state.style} -> eerie (emotion: {e})")
            self.state.style = "eerie"
        else:
            # Default: sweet
            if self.state.style not in {"sweet", "chaotic", "playful"}:
                log.debug(f"Style drift: {self.state.style} -> sweet")
            self.state.style = "sweet"
    
    def update_stable_personality(self) -> None:
        """
        Update stable personality from current dominant raw emotion.
        
        Called during tick() to update mood/style based on current stack state.
        """
        if self.state.is_hidden:
            self.state.style = "direct"
            return
        
        dominant = self.get_dominant_emotion()
        self._update_stable_personality_from_emotion(dominant)
    
    # =========================================================================
    # Manual Controls (Override System)
    # =========================================================================
    
    def set_mood(self, mood: str, duration: float = 300.0) -> None:
        """
        Manually set mood with temporary override.
        
        Args:
            mood: Mood to set (behave, mean, flirty, protective)
            duration: Seconds to keep override active (default 5 minutes)
        """
        if validate_mood(mood):
            old = self.state.mood
            self.state.mood = mood
            self.state.manual_mood_override = mood
            self.state.manual_mood_override_expire = time.time() + float(duration)
            log.info(f"Mood manually set: {old} -> {mood} (override for {duration}s)")
        else:
            log.warning(f"Invalid mood: {mood}")
    
    def set_style(self, style: str, duration: Optional[float] = None) -> None:
        """
        Manually set style with optional duration.
        
        Args:
            style: Style to set (chaotic, sweet, cold, direct, sarcastic, playful, eerie)
            duration: Optional duration for temporary override
        """
        if validate_style(style):
            old = self.state.style
            self.state.style = style
            log.info(f"Style manually set: {old} -> {style}")
        else:
            log.warning(f"Invalid style: {style}")
    
    def clear_mood_override(self) -> None:
        """Clear any manual mood override immediately."""
        self.state.manual_mood_override = None
        self.state.manual_mood_override_expire = 0.0
        log.info("Manual mood override cleared")
    
    def hide(self) -> None:
        """Hide avatar (sleep mode)."""
        self.state.is_hidden = True
        self.state.style = "direct"
        self.state.mood = "behave"
        log.info("Kitsu hidden (sleep mode)")
    
    def unhide(self) -> None:
        """Wake from hide."""
        self.state.is_hidden = False
        self.state.mood = "behave"
        self.state.style = "chaotic"
        
        # Recompute from current emotions
        self.update_stable_personality()
        log.info("Kitsu unhidden")
    
    # =========================================================================
    # Emotional Physics (Decay & Resistance)
    # =========================================================================
    
    async def tick(self) -> None:
        """
        Single tick of emotion processing - called by orchestrator heartbeat.
        
        - Removes expired emotions from raw stack
        - Applies decay to active emotions with random drift
        - Updates stable personality from dominant emotion
        - Applies emotional momentum to resistance
        """
        try:
            now = time.time()
            
            # Remove expired emotions from raw stack
            self.state.stack.remove_expired(now)
            
            # Apply decay with random drift to active emotions
            active = self.state.stack.get_active(now)
            for entry in active:
                drift = random.uniform(-self.random_drift, self.random_drift)
                old = entry.intensity
                new = max(0.0, min(1.0, old - self.decay_rate + drift))
                entry.intensity = new
            
            # Update stable personality from raw emotions
            if not self.state.is_hidden:
                self.update_stable_personality()
        except Exception as e:
            log.error(f"Error in EmotionManager.tick(): {e}")
            # Don't re-raise - let orchestrator continue
    
    async def run(self) -> None:
        """
        Background loop for continuous emotion decay.
        
        Only runs if continuous_decay is True.
        Normally, orchestrator calls tick() on heartbeat.
        """
        log.info("Emotion manager background loop started")
        
        while True:
            if not self.continuous_decay:
                await asyncio.sleep(1)
                continue
            
            await self.tick()
            await asyncio.sleep(1)
    
    def _calculate_emotional_resistance(self) -> float:
        """
        Compute emotional resistance with momentum system.
        
        Resistance increases when high-intensity emotions are present.
        Momentum makes it harder to change moods when emotionally charged.
        
        Returns:
            Resistance value (0.0 - 1.0)
        """
        now = time.time()
        active = self.state.stack.get_active(now)
        
        if not active:
            return 0.0
        
        # Calculate base resistance from intensity
        total_intensity = sum(entry.intensity for entry in active)
        avg_intensity = total_intensity / max(1, len(active))
        base_resistance = max(0.0, min(1.0, avg_intensity))
        
        # Apply momentum factor (emotional inertia)
        momentum_resistance = self.state.resistance * self.momentum_factor
        final_resistance = max(base_resistance, momentum_resistance)
        
        return max(0.0, min(1.0, final_resistance))
    
    def apply_resistance(self, level: float = 1.0, duration: float = 30.0) -> None:
        """
        Apply temporary resistance by pushing a high-intensity emotion.
        
        Args:
            level: Resistance level (0.0 - 1.0)
            duration: Duration in seconds
        """
        self.add_emotion("angry", intensity=level, duration=duration, source="resistance")
        log.debug(f"Resistance applied: level={level} duration={duration}s")
    
    # =========================================================================
    # State Export (Layer 3: Subsystem Output)
    # =========================================================================
    
    def export_state(self) -> Dict[str, Any]:
        """
        Export complete state for persistence (no file I/O).
        
        Returns:
            State dict to be saved by memory_manager
        """
        return self.state.to_dict()
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current emotional state for subsystems (Avatar, LLM, Voice).
        
        This is the Single Source of Truth output that all subsystems use.
        
        Returns:
            Dict with mood, style, dominant_emotion, confidence, etc.
        """
        dominant = self.get_dominant_emotion()
        confidence = self.get_dominant_intensity()
        resistance = self.state.resistance
        
        return {
            "mood": self.state.mood,
            "style": self.state.style,
            "dominant_emotion": dominant,
            "confidence": confidence,
            "resistance": resistance,
            "is_hidden": self.state.is_hidden,
            "stack_size": len(self.state.stack.entries),
            "current_mode": get_legacy_mode(self.state.mood, self.state.style)
        }
    
    def get_emotional_state(self) -> Dict[str, Any]:
        """
        Get emotional state for UI/voice (legacy compatibility).
        
        Returns:
            Dict with dominant_emotion and confidence
        """
        return self.get_current_state()
    
    def get_state_dict(self) -> Dict[str, Any]:
        """
        Get current state as dictionary (legacy compatibility).
        
        Returns:
            Dict with mood, style, mode, emotions, etc.
        """
        return self.get_current_state()
