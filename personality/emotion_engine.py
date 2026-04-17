"""
core/personality/emotion_engine.py

EmotionEngine = Manager — Lifecycle and state of emotion system.

Responsibilities:
- Manage emotion stack with decay
- Map emotions to mood/style
- Handle triggers and reactions
- Provide current emotional state
- Run decay loop (if continuous mode)

Non-responsibilities:
- File I/O (delegates to trigger_manager)
- Training or learning
- UI rendering
- Direct personality state (delegates to kitsu_self)
"""

import asyncio
import random
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from personality.emotion_config import (
    VALID_MOODS, VALID_STYLES, VALID_STATES,
    EMOTION_TO_MOOD, EMOTION_TO_STYLE, EMOTION_TO_STATE,
    get_legacy_mode, validate_mood, validate_style,
    UNSAFE_COMBINATIONS
)

if TYPE_CHECKING:
    from personality.kitsu_self import KitsuSelf
    from brain.state import KitsuState

log = logging.getLogger(__name__)


class EmotionEngine:
    """
    Two-layer personality system manager.

    Layers:
    - mood: behave | mean | flirty | protective (primary emotional axis)
    - style: chaotic | sweet | cold | direct | sarcastic | playful | eerie (expression overlay)

    Features:
    - Stack-based emotion system with decay
    - Trigger-based reactions
    - Fast shifts on strong emotions
    - Slow drift for natural personality changes
    - Resistance system to prevent rapid mood swings
    """

    def __init__(
        self,
        kitsu_self: Optional['KitsuSelf'] = None,
        triggers_path: Optional[Path] = None,
        continuous_decay: bool = True
    ):
        """
        Initialize emotion engine.

        Args:
            kitsu_self: KitsuSelf instance for personality integration
            triggers_path: Path to triggers.json
            continuous_decay: If True, run background decay loop. If False, decay only on tick()
        """
        self.kitsu_self = kitsu_self
        self.trigger_manager = None
        self.shared_state: Optional['KitsuState'] = None

        # Initialize trigger manager if path provided
        if triggers_path:
            try:
                from core.personality.trigger_manager import TriggerManager
                self.trigger_manager = TriggerManager(triggers_path)
                log.info("TriggerManager loaded")
            except Exception as e:
                log.warning(f"TriggerManager not available: {e}")

        # Emotion stack
        self.stack: List[Dict[str, Any]] = []
        self.decay_rate = 0.01
        self.random_drift = 0.005
        self.continuous_decay = continuous_decay

        # Two-layer personality (baseline: behave + chaotic)
        self.mood: str = "behave"
        self.style: str = "chaotic"
        
        # Third layer: state (micro-behavior)
        self.state: str = "normal"
        
        # Personality persistence cache
        self.personality_cache = {
            "state": "normal",
            "ttl": 0  # Start at 0 to force immediate update on first call
        }
        self.state_persistence_duration = 3  # turns

        # Manual override system
        self._manual_mood_override: Optional[str] = None
        self._manual_mood_override_expire: float = 0.0

        # Legacy compatibility
        self.current_mode: str = "Gremlin"

        # Hide flag
        self.is_hidden: bool = False

        log.info(f"EmotionEngine initialized: {self.mood}/{self.style}/{self.state}")

    # =========================================================================
    # Core Emotion Stack
    # =========================================================================

    def get_current_state(self) -> str:
        """
        Return the current personality state with persistence caching.
        
        Returns:
            Current state name (e.g., "normal", "fox", "glitch", "analyst", "submissive", "detached")
        """
        # Check cache TTL first - if > 0, return cached state
        if self.personality_cache["ttl"] > 0:
            self.personality_cache["ttl"] -= 1
            return self.personality_cache["state"]
        
        # TTL is 0, need to update state
        # Get dominant emotion
        dominant = self.get_current_emotion()
        
        # Map emotion to state
        mapped_state = EMOTION_TO_STATE.get(dominant, "normal")
        
        # Debug logging
        log.debug(f"State mapping: {dominant} -> {mapped_state}")
        
        # Update cache
        self.state = mapped_state
        self.personality_cache["state"] = mapped_state
        self.personality_cache["ttl"] = self.state_persistence_duration
        
        return mapped_state

    def get_current_emotion(self) -> str:
        """
        Return the currently dominant emotion from stack.

        Calculates weighted scores with decay and personality modifiers.

        Returns:
            Dominant emotion name (e.g., "happy", "angry", "neutral")
        """
        if not self.stack:
            # Don't call kitsu_self.get_expression() to avoid recursion
            # (it calls back to this method through get_emotional_state)
            return "neutral"

        # Calculate weighted scores with decay
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

        # Apply personality modifiers from KitsuSelf
        if self.kitsu_self:
            try:
                reflection = self.kitsu_self.reflection

                if reflection.get("angry", 0) > 0.5:
                    weighted["angry"] = weighted.get("angry", 0) + 0.2

                if getattr(self.kitsu_self, "mode", None) == "behave":
                    weighted["behave"] = weighted.get("behave", 0) + 0.1

                if getattr(self.kitsu_self, "mode", None) == "mean":
                    weighted["teasing"] = weighted.get("teasing", 0) + 0.1

            except Exception as e:
                log.debug(f"Personality modifier failed: {e}")

        if not weighted:
            return "neutral"

        # Return emotion with highest score
        return max(weighted, key=weighted.get)

    def get_current_intensity(self) -> float:
        """
        Return a normalized intensity/confidence for the currently dominant emotion.

        Returns:
            Float between 0.0 and 1.0 representing how strong/confident the dominant
            emotion is relative to other active emotions.
        """
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

    def set_emotion(
        self,
        name: str,
        intensity: float = 0.5,
        duration: float = 5.0
    ):
        """
        Push emotion onto stack.

        Args:
            name: Emotion name (e.g., "happy", "angry")
            intensity: Emotion strength (0.0 - 1.0)
            duration: How long emotion lasts (seconds)
        """
        now = time.time()
        self.stack.append({
            "name": name,
            "intensity": max(0.0, min(1.0, intensity)),
            "timestamp": now,
            "expire": now + float(duration)
        })
        log.debug(f"Emotion added: {name} (intensity={intensity:.2f}, duration={duration}s)")

    def add_emotion(self, name: str, intensity: float = 0.5, duration: float = 5.0):
        """Public API alias for set_emotion"""
        self.set_emotion(name, intensity, duration)

    def update_intensity(self, name: str, delta: float):
        """
        Adjust intensity of most recent matching emotion.

        Args:
            name: Emotion name to update
            delta: Amount to change intensity by
        """
        for emo in reversed(self.stack):
            if emo.get("name") == name:
                old = emo.get("intensity", 0.0)
                new = max(0.0, min(1.0, old + delta))
                emo["intensity"] = new
                log.debug(f"Updated {name} intensity: {old:.2f} -> {new:.2f}")
                return

    # =========================================================================
    # Trigger System
    # =========================================================================

    def fire_trigger(self, trigger_name: str):
        """
        Fire a trigger by name.

        - Adds emotions to stack
        - Updates personality
        - Applies modifiers to KitsuSelf

        Args:
            trigger_name: Name of trigger to fire
        """
        if not self.trigger_manager:
            log.warning("No trigger manager available")
            return

        try:
            emotions = self.trigger_manager.fire_trigger(trigger_name)
        except Exception as e:
            log.error(f"Trigger firing failed: {e}")
            emotions = None

        if emotions:
            # Add emotions to stack
            for emo in emotions:
                self.add_emotion(
                    emo.get("name", "neutral"),
                    emo.get("intensity", 0.5),
                    emo.get("duration", 5.0)
                )

            # Apply personality modifiers
            if self.kitsu_self:
                try:
                    modifiers = self.trigger_manager.get_modifiers(trigger_name)
                    for key, value in modifiers.items():
                        if key in self.kitsu_self.reflection:
                            old = self.kitsu_self.reflection[key]
                            new = max(0.0, min(1.0, old + value))
                            self.kitsu_self.reflection[key] = new
                            log.debug(f"Applied modifier {key}: {old:.2f} -> {new:.2f}")
                except Exception as e:
                    log.debug(f"Modifier application failed: {e}")

        # Update personality after trigger
        dominant = self.get_current_emotion()

        # Apply resistance after angry triggers
        if dominant in {"angry", "offended", "irritated", "betrayed", "disgust"}:
            try:
                self.apply_resistance(level=1.0, duration=60.0)
                log.debug("Applied resistance after angry trigger")
            except Exception:
                pass

        if not self.is_hidden:
            self.update_personality(dominant)
            self._update_shared_state()

    # =========================================================================
    # Shared State Integration
    # =========================================================================

    def set_shared_state(self, state: 'KitsuState'):
        """
        Set shared state reference for integration.

        Args:
            state: KitsuState instance to update
        """
        self.shared_state = state
        log.debug("EmotionEngine shared state reference set")

    def _update_shared_state(self):
        """
        Update shared state with current emotional state.

        This method is called automatically after personality updates
        to keep shared state synchronized.
        """
        if not self.shared_state:
            return

        try:
            dominant = self.get_current_emotion()
            intensity = self.get_current_intensity()

            self.shared_state.update_emotional_state(
                mood=self.mood,
                style=self.style,
                state=self.state,
                emotion=dominant,
                intensity=intensity
            )

            log.debug(f"Updated shared state: {self.mood}/{self.style} -> {dominant} ({intensity:.2f})")
        except Exception as e:
            log.warning(f"Failed to update shared state: {e}")

    def process_user_input(self, user_input: str, state: 'KitsuState') -> Dict[str, Any]:
        """
        Process user input and update emotional state.

        This is the main integration point for the shared state system.

        Args:
            user_input: User's input text
            state: KitsuState instance to update

        Returns:
            Dictionary with processing results
        """
        # Set shared state reference if not already set
        if not self.shared_state:
            self.set_shared_state(state)

        # Store user input in state
        state.user_input = user_input

        # Check for emotional triggers in input
        self._check_emotional_triggers(user_input)

        # Update personality based on current emotions
        dominant = self.get_current_emotion()
        self.update_personality(dominant)

        # Update shared state with current emotional state
        self._update_shared_state()

        return {
            "dominant_emotion": dominant,
            "mood": self.mood,
            "style": self.style,
            "state": self.state,
            "intensity": self.get_current_intensity(),
            "legacy_mode": self.current_mode
        }

    def _check_emotional_triggers(self, user_input: str):
        """
        Check user input for emotional triggers and fire them.

        Args:
            user_input: User's input text to analyze
        """
        if not self.trigger_manager:
            return

        try:
            # Get available triggers
            triggers = self.trigger_manager.get_triggers()

            # Simple keyword-based trigger detection
            user_input_lower = user_input.lower()

            for trigger_name, trigger_data in triggers.items():
                # Check if trigger keywords are in user input
                keywords = trigger_data.get("keywords", [])
                if any(keyword in user_input_lower for keyword in keywords):
                    self.fire_trigger(trigger_name)
                    log.debug(f"Fired trigger from input: {trigger_name}")
                    break  # Only fire one trigger per input for now

        except Exception as e:
            log.warning(f"Emotional trigger checking failed: {e}")

    # =========================================================================
    # Personality Mapping (mood + style)
    # =========================================================================

    def _apply_role_modifiers(self):
        """
        Optional personality shaping from KitsuSelf role.
        """
        if not self.kitsu_self:
            return

        role = getattr(self.kitsu_self, "role", "default")

        if role == "caretaker" and self.mood == "mean":
            self.mood = "behave"

        if role == "observer":
            if self.style in {"chaotic", "playful"}:
                self.style = "cold"

        if role == "tutor" and self.style == "chaotic":
            self.style = "sweet"

    def _apply_safety_overrides(self):
        """
        Enforce safety constraints on mood/style combinations.
        """
        combo = (self.mood, self.style)
        action = UNSAFE_COMBINATIONS.get(combo)

        if action == "convert_to_sarcastic":
            log.debug("Unsafe combo detected (mean+cold) → converting to sarcastic")
            self.style = "sarcastic"

    def update_personality(self, emotion: str):
        """
        Map dominant emotion to (mood, style, state).
        
        Fast shifts on strong triggers, slow drift otherwise.
        Respects manual mood overrides and state persistence.
        
        Args:
            emotion: Dominant emotion name
        """
        intensity = self.get_current_intensity()

        if self.is_hidden:
            self.style = "direct"
            self.state = "normal"
            self._update_legacy_mode()
            return

        e = (emotion or "").lower()

        # Check manual override
        now = time.time()
        manual_locked = False
        if self._manual_mood_override and now < self._manual_mood_override_expire:
            manual_locked = True
            self.mood = self._manual_mood_override

        # Compute current resistance
        resistance = self.get_resistance()

        # --- Primary mood axis ---
        mapped_mood = EMOTION_TO_MOOD.get(e, "behave")

        # Strong emotions override current mood
        if mapped_mood == "mean" and e in {"angry", "offended", "irritated", "disgust", "betrayed"}:
            if not manual_locked:
                if mapped_mood == "mean" and intensity > 0.4:
                    log.info(f"Mood shift: {self.mood} -> mean (emotion: {e})")
                self.mood = "mean"

        elif mapped_mood == "flirty" and e in {"love", "fond", "affection", "desire",
                                                "flattered", "praise", "admire", "joy"}:
            if not manual_locked:
                if mapped_mood == "flirty" and intensity > 0.4:
                    log.info(f"Mood shift: {self.mood} -> flirty (emotion: {e})")
                self.mood = "flirty"

        elif mapped_mood == "protective" and e in {"protective", "defensive", "concerned", "worried"}:
            if not manual_locked:
                if mapped_mood == "protective" and intensity > 0.4:
                    log.info(f"Mood shift: {self.mood} -> protective (emotion: {e})")
                self.mood = "protective"

        else:
            # Default: behave (with resistance)
            if not manual_locked and self.mood != "behave":
                if resistance <= 0:
                    # No active emotions → freeze current mood
                    log.debug("No active stack → keeping current mood frozen")
                else:
                    # Resistance makes it harder to return to behave
                    chance_to_change = max(0.0, 1.0 - resistance)
                    roll = random.random()
                    if roll < chance_to_change:
                        log.info(f"Mood drift: {self.mood} -> behave")
                        self.mood = "behave"
                    else:
                        log.debug(f"Mood change resisted (resistance={resistance:.2f})")

        # --- Style overlay ---
        mapped_style = EMOTION_TO_STYLE.get(e, "sweet")

        # Priority style transitions
        if e in {"hurt", "betrayed", "ashamed", "offended"}:
            if self.style != "cold":
                log.info(f"Style shift: {self.style} -> cold (emotion: {e})")
            self.style = "cold"
        elif e in {"sad", "sadness", "fear", "anxiety", "lonely", "tired"}:
            if self.style != "direct":
                log.info(f"Style shift: {self.style} -> direct (emotion: {e})")
            self.style = "direct"
        elif e in {"sarcastic", "witty", "ironic", "dry"}:
            if self.style != "sarcastic":
                log.info(f"Style shift: {self.style} -> sarcastic (emotion: {e})")
            self.style = "sarcastic"
        elif e in {"playful", "joking", "teasing"} and mapped_style == "playful":
            if self.style != "playful":
                log.debug(f"Style shift: {self.style} -> playful (emotion: {e})")
            self.style = "playful"
        elif mapped_style == "chaotic":
            if intensity > 0.5:
                if self.style != "chaotic":
                    log.debug("High intensity → chaotic style")
                self.style = "chaotic"
            else:
                # Low intensity chaos becomes playful instead
                self.style = "playful"
        elif e in {"eerie", "mysterious", "unsettling"} or (e == "calm" and mapped_style == "eerie"):
            if self.style != "eerie":
                log.debug(f"Style shift: {self.style} -> eerie (emotion: {e})")
            self.style = "eerie"
        else:
            # Default: sweet
            if self.style not in {"sweet", "chaotic", "playful"}:
                log.debug(f"Style drift: {self.style} -> sweet")
            self.style = "sweet"

        # --- State layer (with persistence) ---
        current_state = self.get_current_state()
        if current_state != self.state:
            log.debug(f"State shift: {self.state} -> {current_state}")
            self.state = current_state

        self._apply_role_modifiers()
        self._apply_safety_overrides()
        self._update_legacy_mode()

    def _update_legacy_mode(self):
        """Map (mood, style) to legacy current_mode for backward compatibility"""
        if self.is_hidden:
            self.current_mode = "Hide"
            return

        self.current_mode = get_legacy_mode(self.mood, self.style)

    # =========================================================================
    # Manual Controls
    # =========================================================================

    def set_mood(self, mood: str, duration: float = 300.0, persist: bool = False):
        """
        Manually set mood with temporary override.

        Args:
            mood: Mood to set (behave, mean, flirty, protective)
            duration: Seconds to keep override active (default 5 minutes)
            persist: If True, save override to data/config.json
        """
        if validate_mood(mood):
            old = self.mood
            self.mood = mood
            self._manual_mood_override = mood
            self._manual_mood_override_expire = time.time() + float(duration)
            self._update_legacy_mode()
            log.info(f"Mood manually set: {old} -> {mood} (override for {duration}s)")

            # Persist if requested (NOTE: This violates our no-file-IO rule)
            # TODO: Move persistence to memory_manager
            if persist:
                log.warning("Mood persistence requested but not implemented (violates architecture)")
        else:
            log.warning(f"Invalid mood: {mood}")

    def clear_mood_override(self):
        """Clear any manual mood override immediately"""
        self._manual_mood_override = None
        self._manual_mood_override_expire = 0.0
        log.info("Manual mood override cleared")

    def set_style(self, style: str):
        """
        Manually set style.

        Args:
            style: Style to set (chaotic, sweet, cold, direct, sarcastic, playful, eerie)
        """
        if validate_style(style):
            old = self.style
            self.style = style
            self._update_legacy_mode()
            log.info(f"Style manually set: {old} -> {style}")
        else:
            log.warning(f"Invalid style: {style}")

    def hide(self):
        """Hide avatar (sleep mode)"""
        self.is_hidden = True
        self.style = "direct"
        self.mood = "behave"
        self.current_mode = "Hide"
        log.info("Kitsu hidden")

    def unhide(self):
        """Wake from hide"""
        self.is_hidden = False
        self.mood = "behave"
        self.style = "chaotic"

        # Recompute from current emotions
        dominant = self.get_current_emotion()
        self.update_personality(dominant)
        self._update_legacy_mode()
        log.info("Kitsu unhidden")

    # =========================================================================
    # Tick Loop (Decay & Updates)
    # =========================================================================

    async def tick(self):
        """
        Single tick of emotion processing.

        - Removes expired emotions
        - Applies decay to active emotions
        - Updates personality from dominant emotion
        """
        now = time.time()

        # Remove expired emotions
        self.stack = [
            emo for emo in self.stack
            if emo.get("expire", 0) >= now and emo.get("intensity", 0.0) > 0
        ]

        # Apply decay
        for emo in self.stack:
            drift = random.uniform(-self.random_drift, self.random_drift)
            old = emo.get("intensity", 0.0)
            new = max(0.0, min(1.0, old - self.decay_rate + drift))
            emo["intensity"] = new

        # Update personality
        if not self.is_hidden:
            dominant = self.get_current_emotion()
            self.update_personality(dominant)
        else:
            self.current_mode = "Hide"

    async def run(self):
        """
        Background loop for continuous emotion decay.

        Only runs if continuous_decay is True.
        Otherwise, decay is handled by external tick() calls.
        """
        log.info("Emotion engine loop started")

        while True:
            if not self.continuous_decay:
                await asyncio.sleep(1)
                continue

            await asyncio.sleep(1)
            now = time.time()

            new_stack: List[Dict[str, Any]] = []
            for emo in self.stack:
                # Skip expired
                if emo.get("expire", 0) < now:
                    continue

                # Apply linear decay per tick
                old_intensity = emo.get("intensity", 0.0)
                drift = random.uniform(-self.random_drift, self.random_drift)

                new_intensity = max(
                    0.0,
                    min(1.0, old_intensity - self.decay_rate + drift)
                )

                emo["intensity"] = new_intensity
                new_stack.append(emo)

            self.stack = new_stack

            # Update personality
            if not self.is_hidden:
                dominant = self.get_current_emotion()
                self.update_personality(dominant)
            else:
                self.current_mode = "Hide"

    # =========================================================================
    # Resistance System
    # =========================================================================

    def get_resistance(self) -> float:
        """
        Compute resistance score based on stack intensity.

        Resistance increases when high-intensity emotions are present.
        Makes it harder to change moods when emotionally charged.

        Returns:
            Resistance value (0.0 - 1.0)
        """
        now = time.time()
        active = [emo for emo in self.stack if emo.get("expire", 0) >= now]

        if not active:
            return 0.0

        total_intensity = sum(emo.get("intensity", 0.0) for emo in active)
        avg_intensity = total_intensity / max(1, len(active))
        return max(0.0, min(1.0, avg_intensity))

    def apply_resistance(self, level: float = 1.0, duration: float = 30.0):
        """
        Apply temporary resistance by pushing a high-intensity emotion.

        Args:
            level: Resistance level (0.0 - 1.0)
            duration: Duration in seconds
        """
        now = time.time()
        self.stack.append({
            "name": "angry",
            "intensity": max(0.0, min(1.0, float(level))),
            "timestamp": now,
            "expire": now + float(duration)
        })
        log.debug(f"Resistance applied: level={level} duration={duration}s")

    # =========================================================================
    # State Export
    # =========================================================================

    def get_state_dict(self) -> Dict[str, Any]:
        """
        Get current state as dictionary.

        Returns:
            Dict with mood, style, mode, emotions, etc.
        """
        return {
            "mood": self.mood,
            "style": self.style,
            "state": self.state,
            "current_mode": self.current_mode,
            "is_hidden": self.is_hidden,
            "dominant_emotion": self.get_current_emotion(),
            "stack_size": len(self.stack),
            "resistance": self.get_resistance()
        }

    def get_emotional_state(self) -> Dict[str, Any]:
        """
        Get emotional state for UI/voice.

        Returns:
            Dict with dominant_emotion and confidence
        """
        dominant = self.get_current_emotion()
        resistance = self.get_resistance()

        return {
            "dominant_emotion": dominant,
            "confidence": resistance,
            "mood": self.mood,
            "style": self.style,
            "state": self.state
        }

    def get_avatar_hint(self) -> str:
        """
        Get avatar animation hint based on current mood/style.

        Returns:
            Animation hint string (e.g., "playful_bounce", "cold_stare")
        """
        if self.is_hidden:
            return "hide"

        if self.style == "direct":
            return "withdrawn"

        # Combine mood + style for specific animations
        if self.mood == "behave":
            if self.style == "chaotic":
                return "playful_bounce"
            elif self.style == "sweet":
                return "soft_idle"
            elif self.style == "cold":
                return "polite_distance"

        elif self.mood == "mean":
            if self.style == "chaotic":
                return "energetic_smirk"
            elif self.style == "cold":
                return "cold_stare"
            elif self.style == "sweet":
                return "fake_sweet"
            elif self.style == "sarcastic":
                return "sarcastic_smirk"
            elif self.style == "playful":
                return "teasing_grin"
            elif self.style == "eerie":
                return "mysterious_gaze"

        elif self.mood == "flirty":
            if self.style == "chaotic":
                return "playful_wink"
            elif self.style == "sweet":
                return "affectionate_smile"
            elif self.style == "cold":
                return "seductive_gaze"
            elif self.style == "sarcastic":
                return "flirty_smirk"
            elif self.style == "playful":
                return "playful_wink"
            elif self.style == "eerie":
                return "mysterious_gaze"

        elif self.mood == "protective":
            if self.style == "chaotic":
                return "alert_bounce"
            elif self.style == "sweet":
                return "protective_hug"
            elif self.style == "cold":
                return "defensive_stance"
            elif self.style == "direct":
                return "alert_stance"
            elif self.style == "sarcastic":
                return "protective_smirk"
            elif self.style == "playful":
                return "playful_protect"
            elif self.style == "eerie":
                return "watchful_gaze"

        return "idle"