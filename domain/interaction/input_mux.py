"""
Input Multiplexer: Normalize all input streams (text, speech) into unified pipeline.

Flow:
  Raw Input (text | speech) → InputMux.process() → Unified string → Event Bus

Design:
  - ASR is async but lazy-loaded (only on balanced+)
  - Text passthrough is instant (< 1ms)
  - All input goes through Event Bus for decoupling
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from domain.contracts.contracts import ModuleContract
from runtime.events import EventBus, EventType, EventPayload

logger = logging.getLogger('kitsu.multimodal.input_mux')


class InputType(Enum):
    """Input source classification."""
    TEXT = 'text'
    SPEECH = 'speech'
    COMMAND = 'command'


@dataclass
class NormalizedInput:
    """Result of input normalization."""
    content: str
    input_type: InputType
    confidence: float = 1.0  # for speech recognition confidence
    original_source: str = 'unknown'

    def is_empty(self) -> bool:
        """Check if normalized input is essentially empty."""
        return not self.content or not self.content.strip()


class InputMultiplexer(ModuleContract):
    """
    Normalize text and speech inputs into unified pipeline.
    
    Responsibilities:
    - Accept raw text input
    - Accept speech input (async, lazy-loaded ASR)
    - Normalize both to standard format
    - Emit through Event Bus
    - Handle context (session, user, etc.)
    """

    module_id = 'multimodal.input_mux'
    required_flags = []

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._asr_engine: Optional[Any] = None
        self._asr_available = False

    async def start(self) -> bool:
        """Initialize input mux. ASR lazy-loads on demand."""
        logger.info('InputMultiplexer started')
        return True

    async def stop(self) -> bool:
        """Cleanup resources."""
        if self._asr_engine:
            try:
                await self._asr_engine.stop()
            except Exception:
                logger.exception('Error stopping ASR engine')
        return True

    async def health_check(self):
        """Report on input mux health."""
        from runtime.health import HealthStatus
        return HealthStatus(
            module_id=self.module_id,
            ok=True,
            latency_ms=0.0,
            details={'asr_available': self._asr_available}
        )

    async def _ensure_asr(self) -> bool:
        """Lazy-load ASR engine on first speech request."""
        if self._asr_available or self._asr_engine:
            return True

        try:
            from interfaces.desktop.speech.asr_factory import create_asr_engine
            from shared.capability_flags import CAPABILITY_FLAGS
            
            if not CAPABILITY_FLAGS.use_voice:
                logger.debug('Voice not enabled in this tier; speech disabled')
                return False

            self._asr_engine = await create_asr_engine()
            if self._asr_engine:
                self._asr_available = True
                logger.info('ASR engine loaded on demand')
                return True
        except Exception:
            logger.exception('Failed to load ASR engine')
            self._asr_available = False

        return False

    def normalize_text(self, text: str, source: str = 'user') -> NormalizedInput:
        """
        Normalize raw text input.
        
        Args:
            text: Raw text input
            source: Origin (user, widget, etc.)
        
        Returns:
            NormalizedInput with stripped/normalized content
        """
        if not text:
            return NormalizedInput(
                content='',
                input_type=InputType.TEXT,
                confidence=0.0,
                original_source=source
            )

        # Normalize whitespace and common patterns
        normalized = ' '.join(text.split())
        
        # Detect command prefix
        input_type = InputType.COMMAND if normalized.startswith('/') else InputType.TEXT

        return NormalizedInput(
            content=normalized,
            input_type=input_type,
            confidence=1.0,
            original_source=source
        )

    async def process_speech(
        self,
        audio_data: bytes,
        language: str = 'en-US',
        source: str = 'voice'
    ) -> NormalizedInput:
        """
        Convert speech to text via ASR.
        
        Args:
            audio_data: Raw audio bytes
            language: Language code (IETF tag)
            source: Origin marker (voice, recording, etc.)
        
        Returns:
            NormalizedInput with transcribed text and confidence
        """
        if not await self._ensure_asr():
            logger.warning('ASR not available; cannot process speech')
            return NormalizedInput(
                content='',
                input_type=InputType.SPEECH,
                confidence=0.0,
                original_source=source
            )

        try:
            result = await self._asr_engine.transcribe(
                audio_data=audio_data,
                language=language
            )
            
            normalized = self.normalize_text(
                text=result.get('text', ''),
                source=source
            )
            normalized.confidence = result.get('confidence', 0.8)
            normalized.input_type = InputType.SPEECH
            
            return normalized
        except Exception:
            logger.exception('ASR transcription failed')
            return NormalizedInput(
                content='',
                input_type=InputType.SPEECH,
                confidence=0.0,
                original_source=source
            )

    async def emit_input(self, normalized: NormalizedInput) -> None:
        """
        Emit normalized input through Event Bus.
        
        Decouples input from processing via async pub/sub.
        
        Args:
            normalized: Normalized input ready for routing
        """
        if normalized.is_empty():
            logger.debug('Skipping empty input')
            return

        try:
            self.event_bus.emit(
                EventType.USER_INPUT,
                EventPayload(
                    source=self.module_id,
                    data={
                        'content': normalized.content,
                        'input_type': normalized.input_type.value,
                        'confidence': normalized.confidence,
                        'original_source': normalized.original_source,
                    }
                )
            )
            logger.debug('Emitted input: %s (type=%s, conf=%.2f)', 
                        normalized.content[:50], 
                        normalized.input_type.value,
                        normalized.confidence)
        except Exception:
            logger.exception('Failed to emit input through Event Bus')

    async def handle_text_input(self, text: str, source: str = 'user') -> None:
        """
        Handle incoming text input.
        
        Public API: Called by UI/widgets when user types text.
        """
        normalized = self.normalize_text(text, source=source)
        await self.emit_input(normalized)

    async def handle_speech_input(
        self,
        audio_data: bytes,
        language: str = 'en-US',
        source: str = 'voice'
    ) -> None:
        """
        Handle incoming speech input.
        
        Public API: Called by UI/voice capture when user speaks.
        """
        normalized = await self.process_speech(
            audio_data=audio_data,
            language=language,
            source=source
        )
        await self.emit_input(normalized)


# Singleton instance
_input_mux: Optional[InputMultiplexer] = None


async def get_input_mux(event_bus: EventBus) -> InputMultiplexer:
    """Get or create singleton InputMultiplexer."""
    global _input_mux
    if _input_mux is None:
        _input_mux = InputMultiplexer(event_bus=event_bus)
    return _input_mux
