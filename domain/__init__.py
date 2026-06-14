"""
RULE: PURE LOGIC ONLY.
- Contains the "Soul" of Kitsu (Emotion models, Behavior Trees).
- Zero dependencies on external libraries (no TTS, no LLM APIs).
- Must be framework-agnostic.

ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- EmotionEngine (personality core)
- BehaviorStateMachine (state management)
- CapabilityManager (safety system)
- ToolGroundingSystem (hallucination prevention)
- FailureRecoverySystem (stability system)

What can import this?
- runtime/ (for domain coordination)
- interfaces/ (for UI integration)
- features/ (for feature implementation)
- infra/ (for infrastructure services)

What imports it?
- runtime/ (orchestrator coordination)
- interfaces/ (avatar/desktop integration)
- features/ (browser/quiz features)
- infra/ (LLM/storage integration)

Is it active or deprecated?
- ACTIVE: All domain systems are active
- NO DEPRECATED: Core domain logic never deprecated

Is it runtime-critical?
- CRITICAL: Core AI and personality systems
- SEMI-CRITICAL: Some subsystems can degrade
- Failure here = personality loss but system may continue
"""

__version__ = "0.0.1"

# Core domain exports
from .personality.emotion_engine import EmotionEngine
from .personality.emotion_stack_manager import EmotionStackManager
from .personality.personality_mapper import PersonalityMapper
from .personality.memory_manager import MemoryManager
from .interaction.input_manager import InputManager

__all__ = [
    "EmotionEngine",
    "EmotionStackManager",
    "PersonalityMapper",
    "MemoryManager",
    "InputManager"
]
