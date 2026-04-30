"""
core/personality/reaction_mapper.py

Maps user interactions, emojis, and system events to emotional reactions.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

log = logging.getLogger(__name__)


class InteractionType(Enum):
    """Types of user interactions"""
    HEADPAT = "headpat"
    CHEEK_POKE = "cheek_poke"
    CHIN_LIFT = "chin_lift"
    BELLY_POKE = "belly_poke"
    EMOJI = "emoji"
    SYSTEM_EVENT = "system_event"
    IDLE_TIMEOUT = "idle_timeout"


class ReactionMapper:
    """
    Maps interactions to emotional reactions and visual responses.
    
    Handles:
    - Mouse gesture → emotion mapping
    - Emoji → animation mapping  
    - System event → reaction mapping
    - Visual reaction definitions
    """
    
    def __init__(self):
        # Mouse gesture → emotion mappings
        self.gesture_emotions = {
            InteractionType.HEADPAT: {
                "primary_emotion": "happy",
                "intensity": 0.7,
                "duration": 8.0,
                "mood_shift": "behave",
                "style_shift": "sweet",
                "triggers": ["praised", "affection"]
            },
            InteractionType.CHEEK_POKE: {
                "primary_emotion": "annoyed",
                "intensity": 0.4,
                "duration": 3.0,
                "mood_shift": "mean",
                "style_shift": "chaotic",
                "triggers": ["teased", "poked"]
            },
            InteractionType.CHIN_LIFT: {
                "primary_emotion": "flustered",
                "intensity": 0.6,
                "duration": 5.0,
                "mood_shift": "flirty",
                "style_shift": "sweet",
                "triggers": ["flattered", "teased"]
            },
            InteractionType.BELLY_POKE: {
                "primary_emotion": "embarrassed",
                "intensity": 0.8,
                "duration": 6.0,
                "mood_shift": "mean",
                "style_shift": "cold",
                "triggers": ["embarrassed", "violated"]
            }
        }
        
        # Emoji → reaction mappings
        self.emoji_reactions = {
            "🥰": {
                "emotion": "love",
                "intensity": 0.8,
                "animation": "blush_heavy",
                "voice_pitch": 1.3,
                "response_type": "affectionate"
            },
            "😡": {
                "emotion": "angry",
                "intensity": 0.7,
                "animation": "angry_face",
                "voice_pitch": 1.1,
                "response_type": "defensive"
            },
            "😭": {
                "emotion": "sad",
                "intensity": 0.6,
                "animation": "crying",
                "voice_pitch": 0.8,
                "response_type": "comforting"
            },
            "😏": {
                "emotion": "teasing",
                "intensity": 0.5,
                "animation": "smirk",
                "voice_pitch": 1.0,
                "response_type": "playful"
            },
            "🤔": {
                "emotion": "curious",
                "intensity": 0.4,
                "animation": "thinking",
                "voice_pitch": 1.0,
                "response_type": "inquisitive"
            },
            "😴": {
                "emotion": "tired",
                "intensity": 0.3,
                "animation": "sleepy",
                "voice_pitch": 0.9,
                "response_type": "quiet"
            }
        }
        
        # System event → reaction mappings
        self.system_reactions = {
            "notification": {
                "emotion": "startled",
                "intensity": 0.3,
                "animation": "jump",
                "duration": 2.0
            },
            "error_dialog": {
                "emotion": "concerned",
                "intensity": 0.4,
                "animation": "worried",
                "duration": 3.0
            },
            "file_download_complete": {
                "emotion": "excited",
                "intensity": 0.5,
                "animation": "bounce",
                "duration": 4.0
            },
            "user_switch": {
                "emotion": "curious",
                "intensity": 0.3,
                "animation": "peek",
                "duration": 3.0
            },
            "low_battery": {
                "emotion": "worried",
                "intensity": 0.6,
                "animation": "concerned",
                "duration": 5.0
            }
        }
        
        # Visual reaction definitions
        self.visual_reactions = {
            "blush_light": {
                "duration": 3.0,
                "intensity": 0.3,
                "layers": ["cheeks_red"]
            },
            "blush_heavy": {
                "duration": 5.0,
                "intensity": 0.7,
                "layers": ["cheeks_red", "ears_red"]
            },
            "angry_face": {
                "duration": 4.0,
                "intensity": 0.8,
                "layers": ["eyebrows_down", "mouth_frown"]
            },
            "crying": {
                "duration": 6.0,
                "intensity": 0.6,
                "layers": ["tears", "mouth_sad"]
            },
            "jump": {
                "duration": 1.5,
                "intensity": 1.0,
                "layers": ["position_up", "surprised_eyes"]
            },
            "hide": {
                "duration": 10.0,
                "intensity": 0.5,
                "layers": ["position_hidden", "eyes_closed"]
            },
            "peek": {
                "duration": 3.0,
                "intensity": 0.4,
                "layers": ["position_partial", "curious_eyes"]
            }
        }
    
    def map_gesture(self, gesture_type: InteractionType) -> Dict[str, Any]:
        """
        Map a mouse gesture to emotional reaction.
        
        Args:
            gesture_type: Type of gesture
            
        Returns:
            Dict with emotion, intensity, mood/style shifts, and triggers
        """
        return self.gesture_emotions.get(gesture_type, {
            "primary_emotion": "surprised",
            "intensity": 0.3,
            "duration": 2.0,
            "mood_shift": None,
            "style_shift": None,
            "triggers": ["surprised"]
        })
    
    def map_emoji(self, emoji: str) -> Dict[str, Any]:
        """
        Map an emoji to emotional reaction.
        
        Args:
            emoji: Emoji character
            
        Returns:
            Dict with emotion, animation, voice modifications
        """
        return self.emoji_reactions.get(emoji, {
            "emotion": "curious",
            "intensity": 0.3,
            "animation": "head_tilt",
            "voice_pitch": 1.0,
            "response_type": "neutral"
        })
    
    def map_system_event(self, event_type: str) -> Dict[str, Any]:
        """
        Map a system event to emotional reaction.
        
        Args:
            event_type: System event type
            
        Returns:
            Dict with emotion, animation, duration
        """
        return self.system_reactions.get(event_type, {
            "emotion": "neutral",
            "intensity": 0.2,
            "animation": "glance",
            "duration": 2.0
        })
    
    def get_visual_reaction(self, reaction_name: str) -> Dict[str, Any]:
        """
        Get visual reaction definition.
        
        Args:
            reaction_name: Name of visual reaction
            
        Returns:
            Dict with duration, intensity, and visual layers
        """
        return self.visual_reactions.get(reaction_name, {
            "duration": 2.0,
            "intensity": 0.3,
            "layers": ["default"]
        })
    
    def plan_reaction_sequence(
        self,
        interaction_type: InteractionType,
        current_mood: str,
        current_style: str
    ) -> List[Dict[str, Any]]:
        """
        Plan a sequence of reactions for an interaction.
        
        Args:
            interaction_type: Type of interaction
            current_mood: Current mood
            current_style: Current style
            
        Returns:
            List of reaction steps in sequence
        """
        sequence = []
        
        if interaction_type == InteractionType.HEADPAT:
            # Initial surprise → happiness → affection
            sequence.extend([
                {"phase": "surprise", "emotion": "surprised", "duration": 0.5},
                {"phase": "realization", "emotion": "happy", "duration": 2.0},
                {"phase": "enjoyment", "emotion": "affection", "duration": 5.0}
            ])
        
        elif interaction_type == InteractionType.CHEEK_POKE:
            # Annoyance → playful retaliation
            sequence.extend([
                {"phase": "initial", "emotion": "annoyed", "duration": 1.0},
                {"phase": "reaction", "emotion": "teasing", "duration": 3.0},
                {"phase": "recovery", "emotion": "playful", "duration": 2.0}
            ])
        
        elif interaction_type == InteractionType.BELLY_POKE:
            # Shock → embarrassment → anger
            sequence.extend([
                {"phase": "shock", "emotion": "shocked", "duration": 1.0},
                {"phase": "embarrassment", "emotion": "embarrassed", "duration": 3.0},
                {"phase": "anger", "emotion": "angry", "duration": 4.0}
            ])
        
        else:
            # Default simple reaction
            reaction = self.map_gesture(interaction_type)
            sequence.append({
                "phase": "reaction",
                "emotion": reaction["primary_emotion"],
                "duration": reaction["duration"]
            })
        
        return sequence
    
    def get_idle_reactions(self, idle_minutes: int) -> Dict[str, Any]:
        """
        Get idle-time reactions.
        
        Args:
            idle_minutes: Minutes of inactivity
            
        Returns:
            Dict with reaction type and parameters
        """
        if idle_minutes >= 10:
            return {
                "type": "sleep_mode",
                "emotion": "sleepy",
                "animation": "sleep",
                "message": "Are you still there...? *yawn*"
            }
        elif idle_minutes >= 5:
            return {
                "type": "check_in",
                "emotion": "curious",
                "animation": "peek",
                "message": "Hellooo? Still awake?"
            }
        else:
            return {
                "type": "none",
                "emotion": "neutral",
                "animation": "idle",
                "message": None
            }
