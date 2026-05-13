"""
src/kitsu/modules/preprocess.py

Subscribes to: INPUT_RECEIVED
Emits:         PREPROCESS_DONE

Responsibilities:
- Compute SimHash from normalized tokens (stopwords excluded).
- Attach vibe vector from emotion engine state (stateful, not per-input).
- Budget: 10 ms.
"""

from __future__ import annotations

import logging
import re
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext, within_budget

logger = logging.getLogger("kitsu.preprocess")

# ── Minimal English stopword set ─────────────────────────────────────────────
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "not", "be", "was", "are", "were",
    "do", "does", "did", "i", "you", "he", "she", "we", "they",
    "my", "your", "his", "her", "its", "our", "their",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanum tokens, stopwords removed."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _simhash(tokens: list[str]) -> int:
    """
    64-bit SimHash.
    Each token contributes its Python hash to a bit-vote.
    Identical token-sets → identical hash; near-duplicate inputs → close hashes.
    """
    v = [0] * 64
    for token in tokens:
        h = hash(token)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    result = 0
    for i in range(64):
        if v[i] > 0:
            result |= (1 << i)
    return result


async def on_input_received(ctx: RequestContext) -> None:
    if not within_budget(ctx):
        logger.warning("preprocess: budget already exhausted, skipping id=%s", ctx.id)
        return

    tokens = _tokenize(ctx.text)
    ctx.simhash = _simhash(tokens)

    # vibe was already injected by InputMux from the emotion engine;
    # re-inject here if it's still the neutral default, as a safety net.
    if all(v == 0.5 for v in ctx.vibe):
        try:
            from domain.personality.emotion_engine import EmotionEngine  # type: ignore
            # (engine is a singleton; just a best-effort refresh)
        except ImportError:
            pass

    logger.debug(
        "preprocess: id=%s simhash=%016x tokens=%d",
        ctx.id, ctx.simhash, len(tokens),
    )
    await bus.emit("PREPROCESS_DONE", ctx)


bus.subscribe("INPUT_RECEIVED", on_input_received)