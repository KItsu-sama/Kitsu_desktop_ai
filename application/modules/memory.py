import json
import os
import logging
import time
from ..core.event_bus import bus
from ..core.context import RequestContext
from .judge import judge_response

# Import debug logging
try:
    from shared.debug_timer import (
        debug_cache_put,
        debug_response_pipeline,
        _debug
    )
except ImportError:
    def debug_cache_put(*args, **kwargs): pass
    def debug_response_pipeline(*args, **kwargs): pass
    def _debug(*args, **kwargs): pass

# simhash is treated as a stable identifier for cache keys.
# Some preprocessing versions may produce int or str, so we normalize to str.


logger = logging.getLogger(__name__)

CACHE_FILE = "data/reflex_cache.json"
MAX_ENTRIES = 10000

async def on_response_sent(payload: dict):
    """
    Subscribes to RESPONSE_SENT which emits a dict with ctx and judge_score.
    If ctx.route == 'llm' AND judge score was ≥ 0.8 → store simhash → response in reflex cache.
    Always logs interaction.
    """
    # Extract ctx and judge_score from the dict payload
    ctx = payload.get("ctx")
    judge_score = payload.get("judge_score", 0.0)
    
    if not isinstance(ctx, RequestContext):
        logger.error("on_response_sent: payload missing valid RequestContext")
        return
    
    # 2. Store in Reflex Cache if high quality and from LLM
    if ctx.route == "llm" and judge_score >= 0.8:
        _debug("MEMORY", "QUALITY_HIT", f"LLM response quality={judge_score:.2f} - caching")
        await update_reflex_cache(str(ctx.simhash), ctx.response, judge_score)
    else:
        reason = ""
        if ctx.route != "llm":
            reason = f"route={ctx.route} (not llm)"
        else:
            reason = f"quality={judge_score:.2f} (below 0.8)"
        _debug("MEMORY", "QUALITY_MISS", f"not caching: {reason}")

    # 3. Log interaction
    logger.info(f"Interaction: input={ctx.text[:40]}, route={ctx.route}, score={judge_score:.2f}")

async def update_reflex_cache(simhash: str, response: str, quality_score: float = 0.8):
    os.makedirs("data", exist_ok=True)
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    cache[simhash] = {"text": response, "quality": quality_score, "timestamp": time.time()}
    
    # Debug output
    debug_cache_put(simhash, response, quality_score)

    # LRU Eviction (simplified: just keep last MAX_ENTRIES)
    if len(cache) > MAX_ENTRIES:
        # Remove first key (oldest in some Python versions, but good enough for mock)
        first_key = next(iter(cache))
        del cache[first_key]
        _debug("MEMORY", "EVICT", f"cache size={len(cache)}/{MAX_ENTRIES}")

    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

from ..core.subscriptions import register

register("RESPONSE_SENT", on_response_sent)

