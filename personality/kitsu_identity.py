"""
core/personality/kitsu_identity.py

KitsuIdentity = Core Domain Layer — Personality, Traits, and Self-Reflection State.

Role:
- Store Kitsu's personality traits (static + evolving)
- Provide APIs for emotion system, triggers, planning
- Track emotional reflection states
- Export state for persistence (but NEVER writes files itself)

Boundaries:
- NO file I/O operations (delegates to manager/memory_manager.py)
- NO training or dataset operations
- Pure domain logic only
- NO emotion stack management (that's manager/emotion_manager.py)
"""

import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


class KitsuIdentity:
    """
    Kitsu's personality core and self-reflection state.
    
    This represents Kitsu's "sense of self" - who she thinks she is,
    how she feels, and how her personality evolves through interaction.
    
    This is a PURE DOMAIN MODEL:
    - Stores identity and personality traits
    - Provides accessors and mutators
    - NO file I/O (delegates to memory_manager)
    - NO emotion stack management (delegates to emotion_manager)
    """
    
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        """
        Initialize personality with optional loaded state.
        
        Args:
            initial_state: Previously saved state (from memory_manager)
        """
        # --- Baseline traits (static personality) ---
        self.traits = {
            "sassy": True,
            "talkative": True,
            "roast_capable": True,
            "playful": True,
            "affectionate": True,
        }
        
        # --- Evolving self-reflection values (dynamic state) ---
        self.reflection = {
            "behave": 0.5,      # 0 = not behave, 1 = very behave
            "meanable": 0.5,     # 0 = resistant, 1 = easy to mean
            "angry": 0.0,        # anger buildup 0..1
            "happy": 0.5,        # happiness level 0..1
            "affection": 0.5,    # affection level 0..1
            "trust": 0.5,        # trust level 0..1
        }
        
        # --- Current mode preference (not enforced, just preference) ---
        self.mode_preference: str = "behave"
        
        # --- Error/glitch state ---
        self.error_flag: bool = False
        
        # Load previous state if provided
        if initial_state:
            self._load_state(initial_state)
    
    def _load_state(self, state: Dict[str, Any]) -> None:
        """
        Load state from dict (called during initialization).
        
        Args:
            state: State dictionary from memory_manager
        """
        try:
            if "traits" in state:
                self.traits.update(state["traits"])
            if "reflection" in state:
                self.reflection.update(state["reflection"])
            if "mode_preference" in state:
                self.mode_preference = state["mode_preference"]
            if "error_flag" in state:
                self.error_flag = state["error_flag"]
            
            log.debug("Loaded previous identity state")
        except Exception as e:
            log.warning(f"Failed to load identity state: {e}")
    
    # =============================================================================
    # Error State Management
    # =============================================================================
    
    def set_error(self, status: bool = True) -> None:
        """
        Activate or clear glitch/error override.
        
        Args:
            status: True to set error, False to clear
        """
        self.error_flag = status
    
    def is_in_error_state(self) -> bool:
        """Check if in error/glitch state."""
        return self.error_flag
    
    # =============================================================================
    # Reflection Adjustment
    # =============================================================================
    
    def adjust_reflection(self, name: str, delta: float) -> None:
        """
        Adjust reflection/emotion values.
        
        Args:
            name: Reflection key (behave, meanable, angry, happy, etc.)
            delta: Amount to adjust (-1.0 to 1.0)
        """
        if name in self.reflection:
            old_value = self.reflection[name]
            new_value = max(0.0, min(1.0, old_value + delta))
            self.reflection[name] = new_value
            log.debug(f"Adjusted {name}: {old_value:.2f} -> {new_value:.2f}")
        else:
            log.warning(f"Unknown reflection key: {name}")
    
    def update_reflection(self, key: str, value: float) -> None:
        """
        Update a self-reflection trait directly.
        
        Args:
            key: Reflection key
            value: New value (0.0 to 1.0)
        """
        if key not in self.reflection:
            raise ValueError(f"Unknown self-reflection key: {key}")
        
        old_value = self.reflection[key]
        self.reflection[key] = max(0.0, min(1.0, value))
        log.debug(f"Updated {key}: {old_value:.2f} -> {value:.2f}")
    
    def get_reflection(self, key: str) -> float:
        """
        Get reflection value.
        
        Args:
            key: Reflection key
        
        Returns:
            Reflection value (0.0 - 1.0)
        """
        return self.reflection.get(key, 0.5)
    
    # =============================================================================
    # Mode Preference
    # =============================================================================
    
    def set_mode_preference(self, mode: str) -> None:
        """
        Set mode preference (not enforced, just preference).
        
        Args:
            mode: Preferred mode (behave, mean, flirty, protective)
        """
        from core.config.personality_config import validate_mood
        if validate_mood(mode):
            self.mode_preference = mode
            log.debug(f"Mode preference set to: {mode}")
        else:
            log.warning(f"Invalid mode preference: {mode}")
    
    def get_mode_preference(self) -> str:
        """Get current mode preference."""
        return self.mode_preference
    
    # =============================================================================
    # Interaction Learning
    # =============================================================================
    
    def grow_from_interaction(self, feedback: Dict[str, Any]) -> None:
        """
        Adjust reflection traits based on feedback.
        
        This is how Kitsu "learns" from interactions over time.
        Pure domain logic - no I/O, no training.
        
        Args:
            feedback: Dict with type and optional modifiers
                Example: {"type": "teased", "intensity": 0.1}
        """
        feedback_type = feedback.get("type")
        intensity = feedback.get("intensity", 0.1)
        
        if feedback_type == "teased":
            self.adjust_reflection("meanable", intensity)
            self.adjust_reflection("happy", intensity * 0.5)  # Can be fun
        elif feedback_type == "praised":
            self.adjust_reflection("behave", intensity)
            self.adjust_reflection("happy", intensity)
        elif feedback_type == "angry":
            self.adjust_reflection("angry", intensity)
            self.adjust_reflection("behave", -intensity * 0.5)
        elif feedback_type == "affection":
            self.adjust_reflection("affection", intensity)
            self.adjust_reflection("happy", intensity * 0.5)
        elif feedback_type == "betrayed":
            self.adjust_reflection("trust", -intensity)
            self.adjust_reflection("angry", intensity)
        elif feedback_type == "protected":
            self.adjust_reflection("trust", intensity)
            self.adjust_reflection("affection", intensity * 0.5)
    
    # =============================================================================
    # Trait Access
    # =============================================================================
    
    def has_trait(self, trait: str) -> bool:
        """
        Check if Kitsu has a specific trait.
        
        Args:
            trait: Trait name
        
        Returns:
            True if trait exists and is True
        """
        return self.traits.get(trait, False)
    
    def set_trait(self, trait: str, value: bool) -> None:
        """
        Set a trait value.
        
        Args:
            trait: Trait name
            value: Trait value
        """
        self.traits[trait] = value
        log.debug(f"Trait {trait} set to {value}")
    
    # =============================================================================
    # State Export (for persistence)
    # =============================================================================
    
    def export_state(self) -> Dict[str, Any]:
        """
        Export current state for persistence.
        
        NOTE: This returns a dict - it does NOT write files.
        File writing is handled by manager/memory_manager.py.
        
        Returns:
            State dict to be saved by memory_manager
        """
        return {
            "traits": self.traits.copy(),
            "reflection": self.reflection.copy(),
            "mode_preference": self.mode_preference,
            "error_flag": self.error_flag,
        }
    
    def get_emotional_summary(self) -> Dict[str, Any]:
        """
        Get summary of emotional state for external systems.
        
        Returns:
            Dict with emotional summary (no emotion stack - that's emotion_manager)
        """
        return {
            "mode_preference": self.mode_preference,
            "reflection": self.reflection.copy(),
            "traits": {k: v for k, v in self.traits.items() if v},
            "error_flag": self.error_flag,
        }
