"""
application/modules/slm.py

Subscribes to: SLM_PATH
Emits:         RESPONSE_READY  (on pass)
               LLM_PATH        (on judge fail or budget exceeded)

Rules:
- can_respond() is ONLY called when committing RESPONSE_READY, never at entry.
- If the SLM backend is a mock/stub, route straight to LLM_PATH so the mock
  string never reaches the user.
- Budget hard cap: 500 ms. Exceeded → escalate to LLM_PATH.
"""

from __future__ import annotations

import logging
import time
import asyncio
import random

from typing import List, Tuple, Optional

from ..core.event_bus import bus
from ..core.context import RequestContext, can_respond, within_budget
from infrastructure.llm.llm_fallback_generator import LLMFallback
from .judge import judge_response
# Debug helpers
try:
    from shared.debug_timer import (
        debug_escalate,
        debug_response_pipeline,
        debug_judge_score,
        _debug,
    )
except Exception:
    def debug_escalate(*args, **kwargs):
        pass
    def debug_response_pipeline(*args, **kwargs):
        pass
    def debug_judge_score(*args, **kwargs):
        pass
    def _debug(*args, **kwargs):
        pass

logger = logging.getLogger("app.slm")

THETA: float = 0.65
BUDGET_MS: int = 500


# ── SLM backend ───────────────────────────────────────────────────────────────

try:
    # Prefer the modern domain provider
    from domain.ai.slm.provider import SLMProvider
    _MODERN_SLM_AVAILABLE = True
except Exception as e:
    _MODERN_SLM_AVAILABLE = False
    logger.warning("Modern domain.ai.slm.provider.SLMProvider not available: %s", e)


class LegacySLMInterface:
    """Legacy interface that bridges to the modern domain/ai/slm provider."""

    def __init__(self) -> None:
        self._provider: Optional[SLMProvider] = None
        if _MODERN_SLM_AVAILABLE:
            try:
                self._provider = SLMProvider()
            except Exception:
                logger.exception("Failed to construct SLMProvider; will use LLMFallback")
                self._provider = None

    async def generate(
        self,
        text: str,
        vibe: List[float],
        mode: str,
        max_tokens: int = 150,
    ) -> Tuple[str, float, bool]:
        """Return (response_text, confidence).

        Notes:
        - Modern provider already does confidence estimation and escalation trigger.
        - We still run legacy judge_response() + THETA here for policy consistency.
        """
        if self._provider is not None:
            # Modern provider ignores max_tokens param; keep signature for compatibility.
            ctx = {"personality_hint": "", "emotion_state": "", "memory_context": ""}
            # Build a minimal personality_hint from existing emotion engine if available.
            try:
                from domain.personality.emotion_engine import EmotionEngine

                ee = EmotionEngine.get_singleton()
                emotional_state = ee.get_emotional_state()
                ctx["personality_hint"] = f"mood={emotional_state.get('mood', 'behave')}; style={emotional_state.get('style', 'sweet')}"
                ctx["emotion_state"] = emotional_state.get("dominant_emotion", "neutral")
            except Exception as e:
                logger.debug("Could not build personality_hint for SLMProvider: %s", e)

            response, confidence = await self._provider.infer_with_confidence(text, context=ctx)
            if response:
                # Safety: if model didn't follow character formatting, escalate to LLM.
                # (SLM returning placeholder-like text should not reach the user.)
                tmp_ctx = RequestContext(text=text, mode=mode)
                jr = judge_response(tmp_ctx, response)
                passes = jr.passes(mode)
                # Debug: record provider output and judge decision
                _debug("SLM", "PROVIDER_OUTPUT", f"conf={confidence:.2f} passes={passes}")
                if passes:
                    return response, confidence, False
                return "", 0.0, False


        # Ultimate fallback (never expose mock markers)
        # Use lightweight deterministic fallback generator.
        try:
            text_fallback = slm_fallback.generate(
                mood="behave",
                style="sweet",
                cause="slm_failed",
                raw_input=text,
            )
            # Mark that this came from SLM fallback generator (helps debug attribution)
            _debug("SLM", "FALLBACK", "using slm fallback generator")
            return text_fallback, 0.3, True
        except Exception:
            _debug("SLM", "FALLBACK_FAIL", "fallback generator failed")
            return "Hmm... I’m having trouble right now. Please try again in a moment! ✨", 0.0, True





slm_instance = LegacySLMInterface()
slm_fallback = LLMFallback()


# ── Handler ───────────────────────────────────────────────────────────────────

async def on_slm_path(ctx: RequestContext) -> None:
    """
    SLM_PATH handler.

    Fast path:
      budget check → generate → judge → RESPONSE_READY  (if score ≥ theta)

    Escalation paths:
      mock backend        → LLM_PATH  (never show mock to user)
      budget exceeded     → LLM_PATH
      judge score < theta → LLM_PATH  (if still in budget)
      judge score < theta + out of budget → best-effort RESPONSE_READY
    """
    t0 = time.monotonic_ns()

    # Budget check before doing any work
    if not within_budget(ctx):
        logger.debug("slm: budget exhausted before generate, escalating id=%s", ctx.id)
        debug_escalate("budget exhausted before generate", "SLM")
        setattr(ctx, "debug_reason", "budget_exhausted_before_generate")
        await bus.emit("LLM_PATH", ctx)
        return

    # Generate (async call)
    response_text, logit_conf, is_fallback = await slm_instance.generate(ctx.text, ctx.vibe, ctx.mode, max_tokens=150)

    # If the legacy SLM returned the deterministic fallback generator, tag the context
    # so UI/ops can show the explicit reason why a fallback was returned.
    if is_fallback:
        setattr(ctx, "debug_reason", "slm_fallback_used")

    elapsed_ms = (time.monotonic_ns() - t0) / 1_000_000

    # Mock guard: legacy code no longer exposes mock markers.
    # Modern provider already escalates based on confidence.


    # Hard budget cap after generation
    if elapsed_ms > BUDGET_MS:
        logger.warning(
            "slm: exceeded %dms budget (%.0fms), escalating id=%s",
            BUDGET_MS,
            elapsed_ms,
            ctx.id,
        )
        debug_escalate(f"exceeded {BUDGET_MS}ms budget after generate (%.0fms)" % elapsed_ms, "SLM")
        setattr(ctx, "debug_reason", f"exceeded_budget_after_generate_{int(elapsed_ms)}ms")
        await bus.emit("LLM_PATH", ctx)
        return

    # Judge
    judge_result = judge_response(ctx, response_text)
    score = judge_result.confidence(ctx.mode)



    logger.debug("slm: judge score=%.2f theta=%.2f id=%s", score, THETA, ctx.id)
    # Debug judge decision
    debug_judge_score(score, THETA, score >= THETA, "SLM judge check")

    if score < THETA:
        if within_budget(ctx):
            logger.debug("slm: score below theta, escalating to LLM id=%s", ctx.id)
            debug_escalate("score below theta, escalating to LLM", "SLM")
            setattr(ctx, "debug_reason", f"score_below_theta_{score:.2f}")
            await bus.emit("LLM_PATH", ctx)
        else:
            # Out of budget and score is low — emit best-effort rather than silence
            logger.warning("slm: low score + budget gone, best-effort response id=%s", ctx.id)
            debug_response_pipeline("best-effort response due to low score + budget gone", response_text[:80])
            ctx.response = response_text
            if can_respond(ctx):
                await bus.emit("RESPONSE_READY", ctx)
        return

    # Pass — commit response
    ctx.response = response_text
    ctx.response_confidence = score
    # Tag for debug attribution (reflex vs slm vs llm vs fallback)
    ctx.response_owner = "slm"
    if can_respond(ctx):
        logger.debug("slm: RESPONSE_READY id=%s score=%.2f", ctx.id, score)
        debug_response_pipeline("RESPONSE_READY", f"slm id={ctx.id} score={score:.2f}")
        await bus.emit("RESPONSE_READY", ctx)
    else:
        logger.debug("slm: request already responded id=%s", ctx.id)



# ── Subscription ──────────────────────────────────────────────────────────────

from ..core.subscriptions import register

register("SLM_PATH", on_slm_path)