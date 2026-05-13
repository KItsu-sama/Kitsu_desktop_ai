import json
import logging
import re
from pathlib import Path

from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext, within_budget

logger = logging.getLogger("kitsu.router")

# ── Reflex cache (loaded once at startup) ────────────────────────────────────
_CACHE_PATH = Path("data/reflex_cache.json")
_reflex_cache: dict[str, str] = {}

TEMPLATES = {
    "what time is it",
    "tell me a random fact",
    "hi",
    "hello",
    "hey",
}

_REASONING_KW = re.compile(
    r"\b(why|how|explain|compare|analyze|analyse|difference|because|"
    r"reason|cause|consequence|evaluate|summarize|summarise|describe)\b",
    re.IGNORECASE,
)


def _load_cache() -> None:
    global _reflex_cache
    if not _CACHE_PATH.exists():
        return

    try:
        raw = json.loads(_CACHE_PATH.read_text())
        _reflex_cache = {str(k): str(v) for k, v in raw.items()}
        logger.info("router: loaded %d reflex cache entries", len(_reflex_cache))
    except Exception:
        logger.exception("router: failed to load reflex cache")


_load_cache()


def check_reflex_cache(ctx: RequestContext) -> bool:
    if ctx.simhash in _reflex_cache:
        return True

    if ctx.text.lower().strip() in TEMPLATES:
        return True

    return False


def get_complexity_score(text: str) -> float:
    token_count = len(text.split())
    token_score = min(token_count / 30.0, 1.0) * 0.5
    kw_score = min(len(_REASONING_KW.findall(text)) * 0.1, 0.5)
    return round(token_score + kw_score, 3)


async def on_preprocess_done(ctx: RequestContext) -> None:
    """
    Subscribes to PREPROCESS_DONE.
    Emits REFLEX_PATH, SLM_PATH or LLM_PATH based on cache and complexity.
    Budget: 5 ms.
    """
    if not within_budget(ctx):
        return

    if check_reflex_cache(ctx):
        ctx.route = "REFLEX"
        logger.debug("router: REFLEX_PATH (cache/template hit) id=%s", ctx.id)
        await bus.emit("REFLEX_PATH", ctx)
        return

    score = get_complexity_score(ctx.text)
    if score < 0.3:
        ctx.route = "SLM"
        logger.debug("router: SLM_PATH (complexity=%.2f) id=%s", score, ctx.id)
        await bus.emit("SLM_PATH", ctx)
    else:
        ctx.route = "LLM"
        logger.debug("router: LLM_PATH (complexity=%.2f) id=%s", score, ctx.id)
        await bus.emit("LLM_PATH", ctx)


bus.subscribe("PREPROCESS_DONE", on_preprocess_done)
