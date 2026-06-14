"""
application/modules/router.py

Lightweight routing layer for Kitsu runtime.

Responsibilities:
    - Run after REFLEX_PREPROCESS and before any response generation
    - Decide whether request should go to SLM_PATH, or LLM_PATH
    - Use reflex cache (exclusive) and template hits
    - Apply lightweight complexity scoring

Architecture Notes:
    - Router NEVER generates responses
    - Router NEVER mutates memory
    - Router ONLY decides execution path
    - Cache is managed exclusively by reflex module
"""

from __future__ import annotations

import logging
import re
import time

from ..core.context import RequestContext, within_budget
from ..core.event_bus import bus
from ..core.subscriptions import register
from .reflex import cache_has
from shared.debug_timer import (
    debug_route_decision,
    debug_timer,
    debug_response_routing
)

logger = logging.getLogger("router")

# Fast template triggers (no cache needed)
TEMPLATES = {
    # greetings
    "hi", "hello", "hey",

    # identity / creator (deterministic reflexes)
    "who is your creator",
    "who made you",
    "who created you",
    "who built you",
    "what are you",
    "are you an ai",
    "are you a fox",
    "what kind of ai are you",
    "what does your shirt mean",

    # time + facts
    "what time is it",
    "tell me a fact",
    "tell me a random fact",
}

# Lightweight reasoning detector
_REASONING_KW = re.compile(
    r"\b("
    r"why|how|explain|compare|analyze|analyse|difference|"
    r"because|reason|cause|consequence|evaluate|"
    r"summarize|summarise|describe"
    r")\b",
    re.IGNORECASE,
)

def _normalize(text: str) -> str:
    """Aggressive normalization for template matching.

    - lowercase
    - strip punctuation so variants like "who is your creator?" match
    - collapse whitespace
    """
    import string

    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip()

def check_reflex_cache(ctx: RequestContext) -> bool:
    """Check if request can route through reflex layer."""
    # Reflex exclusive cache check
    if cache_has(ctx.simhash):
        debug_route_decision(
            ctx.text, "REFLEX",
            "cache entry found",
            1.0
        )
        return True
    
    # Template hit (fast path)
    if _normalize(ctx.text) in TEMPLATES:
        debug_route_decision(
            ctx.text, "REFLEX",
            "template match",
            0.95
        )
        return True
    
    return False

def get_complexity_score(text: str) -> float:
    """Cheap heuristic complexity estimate (0.0 → 1.0)."""
    token_count = len(text.split())
    token_score = min(token_count / 30.0, 1.0) * 0.5
    kw_hits = len(_REASONING_KW.findall(text))
    kw_score = min(kw_hits * 0.1, 0.5)
    return round(token_score + kw_score, 3)

async def on_preprocess_done(ctx: RequestContext) -> None:
    """Subscribe to PREPROCESS_DONE, emit REFLEX_PATH/SLM_PATH/LLM_PATH."""
    start_time = time.time()
    
    if not within_budget(ctx):
        debug_response_routing("PREPROCESS", "ABORT", "budget exceeded")
        return
    
    # Check reflex cache first (fastest path)
    if check_reflex_cache(ctx):
        elapsed_ms = (time.time() - start_time) * 1000
        ctx.route = "REFLEX"
        debug_response_routing(
            "REFLEX_CHECK", "REFLEX_PATH",
            "cache hit or template match",
            1.0
        )
        logger.debug("router: REFLEX_PATH id=%s (%.1fms)", ctx.id, elapsed_ms)
        await bus.emit("REFLEX_PATH", ctx)
        return
    
    # Score complexity for SLM vs LLM decision
    score = get_complexity_score(ctx.text)
    elapsed_ms = (time.time() - start_time) * 1000
    
    if score < 0.3:
        ctx.route = "SLM"
        debug_response_routing(
            "COMPLEXITY", "SLM_PATH",
            f"low complexity (score={score:.3f})",
            1.0 - score
        )
        logger.debug("router: SLM_PATH complexity=%.2f id=%s (%.1fms)", score, ctx.id, elapsed_ms)
        await bus.emit("SLM_PATH", ctx)
    else:
        ctx.route = "LLM"
        debug_response_routing(
            "COMPLEXITY", "LLM_PATH",
            f"high complexity (score={score:.3f})",
            score
        )
        logger.debug("router: LLM_PATH complexity=%.2f id=%s (%.1fms)", score, ctx.id, elapsed_ms)
        await bus.emit("LLM_PATH", ctx)

# Event registration
register("PREPROCESS_DONE", on_preprocess_done)


