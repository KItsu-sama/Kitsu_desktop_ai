"""
RULE: PURE LOGIC ONLY.
- Contains the "Soul" of Kitsu (Emotion models, Behavior Trees).
- Zero dependencies on external libraries (no TTS, no LLM APIs).
- Must be framework-agnostic.
"""

__version__ = "0.0.1"

# Core domain exports
from .emotion_config import build_personality
from .emotion_engine import EmotionEngine
from .emotion_stack_manager import EmotionStackManager
from .personality_mapper import PersonalityMapper
from .memory_manager import MemoryManager
from .kitsu_self import KitsuSelf
from .emotion_controller import EmotionController



__all__ = [
    "EmotionEngine",
    "EmotionStackManager",
    "PersonalityMapper",
    "MemoryManager",
    "KitsuSelf",
    "EmotionController",
]
