"""
core/contracts.py

Abstract base classes / protocols for every Kitsu subsystem.
No imports from anywhere else in the project.

Rules:
- Every optional subsystem implements one of these interfaces.
- Every subsystem has a Null implementation in its own module.
- Call sites import only these contracts — never the concrete implementations.
- bootstrap.py is the only file that imports concrete implementations.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Module Lifecycle (New)
# ---------------------------------------------------------------------------

class ModuleContract(ABC):
    """Base contract for all pluggable Kitsu modules."""
    
    module_id: str
    required_flags: List[str]

    @abstractmethod
    async def start(self) -> bool:
        """Initialize and start the module. Return True if successful."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Gracefully shut down the module. Return True if successful."""
        pass

    @abstractmethod
    async def health_check(self) -> Any:
        """Return health status. Format: {'ok': bool, 'latency_ms': float, ...}"""
        pass


# ---------------------------------------------------------------------------
# AI Providers
# ---------------------------------------------------------------------------

class AIProviderContract(ABC):
    """Modern async interface for AI inference providers."""

    @abstractmethod
    async def infer(self, prompt: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Process input text and return a response string, or None if this
        provider cannot handle the input (triggers escalation).
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """True if the provider is loaded and ready to respond."""
        pass

    @abstractmethod
    async def train(self, input_text: str, response_text: str) -> None:
        """Feed a finalized response back into the provider for learning."""
        pass


class AIProvider(AIProviderContract):
    """Legacy synchronous interface (deprecated but supported)."""
    
    @abstractmethod
    def query(self, text: str, context: Optional[Dict] = None) -> Optional[str]:
        """Synchronous version of infer()."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Synchronous version of is_available()."""
        pass

    @abstractmethod
    def train(self, input_text: str, response_text: str) -> None:
        """Synchronous version of train()."""
        pass


class NullAIProvider(AIProviderContract):
    """Null implementation for disabled AI tiers."""

    async def infer(self, prompt: str, context: Optional[Dict] = None) -> Optional[str]:
        return None

    async def is_available(self) -> bool:
        return False

    async def train(self, input_text: str, response_text: str) -> None:
        pass


# ---------------------------------------------------------------------------
# Emotion
# ---------------------------------------------------------------------------

class EmotionProvider(ABC):
    """Interface for the emotion engine."""

    @abstractmethod
    def push(self, emotion: str, intensity: float, source: str = "system") -> None:
        """Push an emotion onto the stack."""

    @abstractmethod
    def get_state(self) -> Dict:
        """Return current mood, style, state as a dict."""

    @abstractmethod
    def tick(self, delta_seconds: float) -> None:
        """Advance decay by delta_seconds. Called by the clock."""


class NullEmotionProvider(EmotionProvider):
    """Returns a neutral emotion state. Used in tests and ultra-minimal mode."""

    def push(self, emotion: str, intensity: float, source: str = "system") -> None:
        pass

    def get_state(self) -> Dict:
        return {
            "mood": "behave", 
            "style": "sweet", 
            "state": "normal", 
            "dominant": "neutral", 
            "intensity": 0.0
        }

    def tick(self, delta_seconds: float) -> None:
        pass


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------

class AvatarContract(ABC):
    """Modern async interface for avatar rendering."""

    @abstractmethod
    async def set_expression(self, mood: str, style: str, state: str) -> None:
        """Update the avatar's expression based on emotion state."""

    @abstractmethod
    async def switch_mode(self, mode: str) -> None:
        """Switch between '2d' and '3d' rendering."""

    @abstractmethod
    async def is_visible(self) -> bool:
        """True if the avatar is currently rendered on screen."""

    @abstractmethod
    async def render_frame(self) -> Optional[bytes]:
        """Render a single frame (for streaming/video export)."""


class AvatarController(AvatarContract):
    """Legacy synchronous interface (deprecated but supported)."""
    
    @abstractmethod
    def set_expression(self, mood: str, style: str, state: str) -> None:
        pass

    @abstractmethod
    def switch_mode(self, mode: str) -> None:
        pass

    @abstractmethod
    def is_visible(self) -> bool:
        pass


class NullAvatarController(AvatarContract):
    """No-op avatar. Used when USE_2D and USE_3D are both False."""

    async def set_expression(self, mood: str, style: str, state: str) -> None:
        pass

    async def switch_mode(self, mode: str) -> None:
        pass

    async def is_visible(self) -> bool:
        return False

    async def render_frame(self) -> Optional[bytes]:
        return None


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class MemoryStoreContract(ABC):
    """Modern async interface for memory stores."""

    @abstractmethod
    async def write(self, key: str, value: Dict) -> None:
        """Persist a key-value record."""

    @abstractmethod
    async def read(self, key: str) -> Optional[Dict]:
        """Retrieve a record by key, or None if not found."""

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic or keyword search, returns ranked list of records."""

    @abstractmethod
    async def clear(self) -> None:
        """Wipe all stored data. Used on shutdown or session reset."""


class MemoryStore(MemoryStoreContract):
    """Legacy synchronous interface (deprecated but supported)."""
    
    @abstractmethod
    def write(self, key: str, value: Dict) -> None:
        pass

    @abstractmethod
    def read(self, key: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


class NullMemoryStore(MemoryStoreContract):
    """In-memory dict store. Used in Phase 0 before real stores are wired."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict] = {}

    async def write(self, key: str, value: Dict) -> None:
        self._data[key] = value

    async def read(self, key: str) -> Optional[Dict]:
        return self._data.get(key)

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        return []

    async def clear(self) -> None:
        self._data.clear()


# ---------------------------------------------------------------------------
# Speech (TTS/ASR)
# ---------------------------------------------------------------------------

class ASRProvider(ABC):
    """Interface for automatic speech recognition."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> Optional[str]:
        """Convert audio to text, or None if recognition failed."""


class TTSProvider(ABC):
    """Interface for text-to-speech synthesis."""

    @abstractmethod
    async def synthesize(self, text: str) -> Optional[bytes]:
        """Convert text to audio bytes, or None if synthesis failed."""


class NullASRProvider(ASRProvider):
    async def transcribe(self, audio_bytes: bytes) -> Optional[str]:
        return None


class NullTTSProvider(TTSProvider):
    async def synthesize(self, text: str) -> Optional[bytes]:
        return None


# ---------------------------------------------------------------------------
# System Gateway
# ---------------------------------------------------------------------------

class SystemAdapterContract(ABC):
    """Modern async interface for system actions."""

    @abstractmethod
    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a named system action.
        Returns {'success': bool, 'result': Any, 'error': str | None}.
        """


class SystemGateway(SystemAdapterContract):
    """Legacy synchronous interface (deprecated but supported)."""
    
    @abstractmethod
    def execute(self, action: str, params: Dict) -> Dict[str, Any]:
        """
        Execute a named system action.
        Returns {'success': bool, 'result': Any, 'error': str | None}.
        """

    @abstractmethod
    def is_permitted(self, action: str) -> bool:
        """True if the action is currently permitted by permission_manager."""


class NullSystemGateway(SystemAdapterContract):
    """Denies all system actions. Used when USE_SYSTEM_CONTROL is False."""

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False, 
            "result": None, 
            "error": "System control is disabled."
        }