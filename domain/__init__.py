"""
RULE: PURE LOGIC ONLY.
- Contains the "Soul" of Kitsu (Emotion models, Behavior Trees).
- Zero dependencies on external libraries (no TTS, no LLM APIs).
- Must be framework-agnostic.
"""

__version__ = "0.0.1"

# Core domain exports
from .personality.emotion_engine import EmotionEngine
from .personality.emotion_stack_manager import EmotionStackManager
from .personality.personality_mapper import PersonalityMapper
from .personality.memory_manager import MemoryManager
from .ai.llm.provider import LLMProvider
from .interaction.input_manager import InputManager

__all__ = [
    "EmotionEngine",
    "EmotionStackManager", 
    "PersonalityMapper",
    "MemoryManager",
    "LLMProvider",
    "InputManager"
]
