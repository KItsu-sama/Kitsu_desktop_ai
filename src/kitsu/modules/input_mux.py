"""
src/kitsu/modules/input_mux.py

InputMux — sanity & normalization layer.

Subscribes to:  RAW_INPUT  (emitted by ChatApp / voice capture / any UI)
Emits:          INPUT_RECEIVED  (with a clean RequestContext)

Responsibilities:
- Strip whitespace, collapse internal runs.
- Detect /command prefix → route to COMMAND_RECEIVED instead.
- Reject empty inputs silently.
- Construct RequestContext with original_text preserved.
- Pull the current vibe vector from the EmotionEngine singleton (if loaded).

Budget: <1 ms (pure Python, no I/O).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext, create_request_context
from domain.contracts.lifecycle import RuntimeModule, ModuleState


logger = logging.getLogger("kitsu.input_mux")

# Lazy-loaded emotion engine — only imported if the module is available.
_emotion_engine = None


def _get_vibe() -> list[float]:
    """Pull current vibe from EmotionEngine or return neutral defaults."""
    global _emotion_engine
    if _emotion_engine is None:
        try:
            from domain.personality.emotion_engine import EmotionEngine  # type: ignore
            # The engine is a singleton managed by the orchestrator.
            # If it hasn't been started yet we just get neutral defaults.
        except ImportError:
            pass
    try:
        if _emotion_engine is not None:
            state = _emotion_engine.get_emotional_state()
            return state.get("vibe", [0.5] * 10)
    except Exception:
        pass
    return [0.5] * 10


def _normalize(raw: str) -> str:
    """Collapse whitespace, strip leading/trailing."""
    return re.sub(r"\s+", " ", raw).strip()


class InputMux(RuntimeModule):
    """
    InputMux — sanity & normalization layer with modern architecture integration.
    
    Maintains all original responsibilities while adding:
    - Proper lifecycle management
    - Performance monitoring
    - Resource-aware processing
    - Enhanced error handling
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.module_id = "input_mux"
        self._started = False
        self._metrics = {
            "inputs_processed": 0,
            "commands_detected": 0,
            "empty_inputs_rejected": 0,
            "processing_time_ns": 0
        }

    async def start(self) -> None:
        """Start the InputMux module."""
        self._started = True
        self._state = ModuleState.RUNNING
        logger.info("InputMux started")

    async def stop(self) -> None:
        """Stop the InputMux module."""
        self._started = False
        self._state = ModuleState.STOPPED
        logger.info("InputMux stopped")

    async def health_check(self) -> bool:
        """Check if InputMux is healthy."""
        return self._started and self._state == ModuleState.RUNNING

    def get_state(self) -> ModuleState:
        """Get current module state."""
        return self._state

    def get_metrics(self) -> dict:
        """Get processing metrics."""
        avg_time_ms = self._metrics["processing_time_ns"] / 1_000_000 / max(self._metrics["inputs_processed"], 1)
        return {
            **self._metrics,
            "average_processing_time_ms": avg_time_ms,
            "started": self._started
        }

    async def on_raw_input(self, raw: str) -> None:
        """
        Handle a raw string from any input source.

        Called by:
          - ChatApp (terminal stdin)
          - Voice capture (after ASR)
          - Any future UI widget

        Emits INPUT_RECEIVED or COMMAND_RECEIVED.
        """
        start_time = time.monotonic_ns()
        
        try:
            # Reject empty inputs silently
            if not raw or not raw.strip():
                self._metrics["empty_inputs_rejected"] += 1
                return

            normalized = _normalize(raw)

            if normalized.startswith("/"):
                # Commands bypass the AI pipeline entirely.
                logger.debug("InputMux: command detected → COMMAND_RECEIVED")
                self._metrics["commands_detected"] += 1
                await bus.emit("COMMAND_RECEIVED", normalized)
                return

            # Create RequestContext with all required fields
            ctx = create_request_context(
                text=normalized,
                original_text=raw,
                mode="chat"  # Default mode, can be overridden by downstream modules
            )
            
            # Pull current vibe from EmotionEngine
            ctx.vibe = _get_vibe()
            
            # Set input type for tracking
            ctx.input_type = "text"

            logger.debug("InputMux: emitting INPUT_RECEIVED id=%s text=%r", ctx.id, ctx.text[:60])
            await bus.emit("INPUT_RECEIVED", ctx)
            
            self._metrics["inputs_processed"] += 1
            
        except Exception as e:
            logger.error("InputMux error processing raw input: %s", e, exc_info=True)
        finally:
            # Track processing time
            processing_time = time.monotonic_ns() - start_time
            self._metrics["processing_time_ns"] += processing_time
            
            # Log if exceeding budget (<1ms = 1,000,000 ns)
            if processing_time > 1_000_000:
                logger.warning("InputMux processing exceeded budget: %.2f ms", processing_time / 1_000_000)


# ── Module instance and registration ───────────────────────────────────────────

# Singleton instance
input_mux = InputMux()


# Legacy handler function for backward compatibility
async def on_raw_input(raw: str) -> None:
    """
    Legacy handler function that delegates to the InputMux instance.
    
    This maintains the original interface while using the modern
    module architecture internally.
    """
    await input_mux.on_raw_input(raw)


# Register once at import time
bus.subscribe("RAW_INPUT", on_raw_input)
logger.debug("InputMux subscribed to RAW_INPUT events")
