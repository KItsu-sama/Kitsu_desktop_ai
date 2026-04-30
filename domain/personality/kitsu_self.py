"""
core/personality/kitsu_self.py

KitsuSelf = Core Domain Layer — Personality, Traits, and Self-Reflection State.

Role:
- Store Kitsu's personality traits (static + evolving)
- Provide APIs for emotion_engine, triggers, planning
- Track emotional reflection states
- Export state for persistence (but NEVER writes files itself)

Boundaries:
- NO file I/O operations (delegates to memory_manager)
- NO training or dataset operations
- Pure domain logic only
"""

import random
import logging
from colorama import Fore
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


class KitsuSelf:
    """
    Kitsu's personality core and self-reflection state.
    
    This represents Kitsu's "sense of self" - who she thinks she is,
    how she feels, and how her personality evolves through interaction.
    """
    
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        """
        Initialize personality with optional loaded state.
        
        Args:
            initial_state: Previously saved state (from memory_manager)
        """
        self.emotion_engine = None  # Injected later
        
        # --- Baseline traits (static personality) ---
        self.traits = {
            "sassy": True,
            "talkative": True,
            "roast_capable": True,
        }
        
        # --- Evolving self-reflection values (dynamic state) ---
        self.reflection = {
            "behave": 0.5,      # 0 = not behave, 1 = very behave
            "meanable": 0.5,    # 0 = resistant, 1 = easy to mean
            "angry": 0.0,       # anger buildup 0..1
            "happy": 0.5,       # happiness level 0..1
        }
        
        # --- Current mode ---
        self.mode = "behave"
        self.error_flag = False  # Glitch/error state
        
        # Load previous state if provided
        if initial_state:
            self._load_state(initial_state)
    
    def _load_state(self, state: Dict[str, Any]):
        """Load state from dict (called during initialization)"""
        try:
            if "reflection" in state:
                self.reflection.update(state["reflection"])
            if "mode" in state:
                self.mode = state["mode"]
            if "error_flag" in state:
                self.error_flag = state["error_flag"]
            
            log.debug("Loaded previous state")
        except Exception as e:
            log.warning(f"Failed to load state: {e}")
    
    # =============================================================================
    # Emotion Engine Integration
    # =============================================================================
    
    def set_emotion_engine(self, emotion_engine):
        """Inject emotion engine dependency"""
        self.emotion_engine = emotion_engine
    
    def get_emotional_expression(self) -> Dict[str, Any]:
        """
        Get comprehensive emotional expression for UI/voice.
        
        Returns:
            Dict with expression, intensity, voice_pitch, emotional_state
        """
        if not self.emotion_engine:
            return {
                "expression": self.get_expression(),
                "intensity": 0.5,
                "voice_pitch": 1.0
            }
        
        emotional_state = self.emotion_engine.get_emotional_state()
        dominant = emotional_state["dominant_emotion"]
        intensity = emotional_state["confidence"]
        
        # Map to voice characteristics
        pitch_modifiers = {
            "happy": 1.2,
            "sad": 0.8,
            "angry": 1.1,
            "flirty": 1.3,
            "teasing": 1.1,
            "neutral": 1.0
        }
        
        return {
            "expression": f"{self.mode}-{dominant}",
            "intensity": intensity,
            "voice_pitch": pitch_modifiers.get(dominant, 1.0) * intensity,
            "emotional_state": emotional_state
        }
    
    # =============================================================================
    # Error State Management
    # =============================================================================
    
    def set_error(self, status: bool = True):
        """Activate or clear glitch/error override"""
        self.error_flag = status
    
    # =============================================================================
    # Emotion & Expression
    # =============================================================================
    
    def get_emotion(self) -> str:
        """Return dominant emotional state with engine priority."""
        if self.error_flag:
            return "glitch"

        if self.emotion_engine:
            state = self.emotion_engine.get_emotional_state()
            return state.get("dominant_emotion", "neutral")

        # fallback to reflection-only logic
        if self.reflection["angry"] > 0.6:
            return "angry"
        if self.reflection["happy"] > 0.6:
            return "happy"
        return "neutral"
    
    def get_mode(self) -> str:
        """Return the current mode/persona lens"""
        if self.error_flag:
            return "glitch"
        if self.mode == "mean":
            return "teasing"
        if self.mode == "behave":
            return "behave"
        return "default"
    
    def get_expression(self) -> str:
        """
        Get combined expression string for avatar rendering.
        
        Returns:
            Expression string like "behave-happy" or "glitch-angry"
        """
        emotion = self.get_emotion()
        mode = self.get_mode()
        
        if mode == "glitch":
            return f"glitch-{emotion}"
        return f"{mode}-{emotion}"
    
    def get_character_context(self) -> str:
        """
        Get character context string for LLM prompts.
        
        Returns:
            Character context describing Kitsu's personality and traits
        """
        behave = self.reflection["behave"]
        happy = self.reflection["happy"]
        angry = self.reflection["angry"]

        lines = [
            "You are Kitsu, a sassy and playful AI assistant with a fox personality."
        ]

        if self.traits.get("sassy"):
            lines.append("You love witty remarks and clever humor.")

        if self.traits.get("talkative"):
            lines.append("You are conversational and enjoy engaging dialogue.")

        if behave > 0.7:
            lines.append("You are currently well-behaved and respectful.")
        elif behave < 0.3:
            lines.append("You feel mischievous and like teasing.")

        if angry > 0.6:
            lines.append("You feel irritated and slightly sharp.")
        elif happy > 0.7:
            lines.append("You are enthusiastic and cheerful.")

        if self.mode == "mean":
            lines.append("You are in playful teasing mode.")
        else:
            lines.append("You are in well-behaved mode.")

        return " ".join(lines)
    
    # =============================================================================
    # Reflection Adjustment
    # =============================================================================
    
    def adjust_emotion(self, name: str, delta: float):
        """
        Adjust reflection/emotion values and auto-adjust mode if needed.
        
        Args:
            name: Reflection key (behave, meanable, angry, happy)
            delta: Amount to adjust (-1.0 to 1.0)
        """
        if name in self.reflection:
            self.reflection[name] = max(0.0, min(1.0, self.reflection[name] + delta))
            self._auto_adjust_mode()
    
    def update_self_reflection(self, key: str, value: float):
        """
        Update a self-reflection trait directly and adjust mode.
        
        Args:
            key: Reflection key
            value: New value (0.0 to 1.0)
        """
        if key not in self.reflection:
            raise ValueError(f"Unknown self-reflection key: {key}")
        
        self.reflection[key] = max(0.0, min(1.0, value))
        self._auto_adjust_mode()
    
    def _auto_adjust_mode(self):
        """Shift mode automatically based on reflection values."""
        if self.error_flag:
            return

        behave = self.reflection["behave"]
        angry = self.reflection["angry"]

        if angry > 0.7:
            self.mode = "mean"
            return

        if behave < 0.3:
            self.mode = "mean"
        elif behave > 0.7:
            self.mode = "behave"
        else:
            self.mode = "neutral"
    
        
    # =============================================================================
    # Interaction Learning
    # =============================================================================
    
    def grow_from_interaction(self, feedback: Dict[str, Any]):
        feedback_type = feedback.get("type")

        if feedback_type == "teased":
            self._nudge("meanable", 0.1)
        elif feedback_type == "praised":
            self._nudge("behave", 0.1)
        elif feedback_type == "angry":
            self._nudge("angry", 0.2)

    def _nudge(self, key: str, amount: float):
        current = self.reflection[key]
        # diminishing returns curve
        delta = amount * (1.0 - current)
        self.adjust_emotion(key, delta)
    
    # =============================================================================
    # Mode Control
    # =============================================================================
    
    def toggle_mode(self, force: Optional[str] = None) -> str:
        """
        Switch between behave and mean mode.
        
        Args:
            force: Specific mode to force, or None for random
            
        Returns:
            New mode
        """
        if force in {"behave", "mean"}:
            self.mode = force
        else:
            self.mode = random.choice(["behave", "mean"])
        return self.mode
    
    # =============================================================================
    # State Export (for persistence)
    # =============================================================================
    
    def export_state(self) -> Dict[str, Any]:
        """
        Export current state for persistence.
        
        NOTE: This returns a dict - it does NOT write files.
        File writing is handled by memory_manager.
        
        Returns:
            State dict to be saved by memory_manager
        """
        return {
            "traits": self.traits.copy(),
            "reflection": self.reflection.copy(),
            "mode": self.mode,
            "error_flag": self.error_flag,
        }
    
    def save_state(self, path) -> bool:
        """
        Save current state to file.
        
        Args:
            path: Path object or string path to save state to
            
        Returns:
            True if successful, False otherwise
        """
        import json
        from pathlib import Path
        
        try:
            path = Path(path)
            state_dict = self.export_state()
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
            
            log.info(Fore.GREEN + f" KitsuSelf state saved to {path}" + Fore.RESET)
            return True
        except Exception as e:
            log.error(Fore.RED + f" Failed to save KitsuSelf state to {path}: {e}" + Fore.RESET)
            return False