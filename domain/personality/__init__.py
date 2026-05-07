"""
RULE: PURE LOGIC ONLY.
- Contains the "Soul" of Kitsu (Emotion models, Behavior Trees).
- Zero dependencies on external libraries (no TTS, no LLM APIs).
- Must be framework-agnostic.
"""

__version__ = "0.0.1"

# Core domain exports
from .emotion_engine import EmotionEngine
from .emotion_stack_manager import EmotionStackManager
from .personality_mapper import PersonalityMapper
from .memory_manager import MemoryManager
from .kitsu_self import KitsuSelf
# Single entry point for all consumers
from .emotion_config import Personality, build_personality
from .basis import calculate_vibe_vector
from .emotion_controller import EmotionController

__all__ = [
    "Personality", "build_personality", "calculate_vibe_vector",
    "EmotionEngine",
    "EmotionStackManager",
    "PersonalityMapper",
    "MemoryManager",
    "KitsuSelf",
    "EmotionController",
]

# Quick-start
def get_kitsu_response(user_input: str, context: dict) -> dict:
    controller = EmotionController()
    personality = controller.update_emotion(user_input, context)
    vibe = calculate_vibe_vector(personality)
    return {"personality": personality, "vibe": vibe}