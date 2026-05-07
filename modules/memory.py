import json
import os
import logging
from core.event_bus import bus
from core.context import RequestContext
from modules.judge import judge_response

logger = logging.getLogger(__name__)

CACHE_FILE = "data/reflex_cache.json"
MAX_ENTRIES = 10000

async def on_response_ready(ctx: RequestContext):
    """
    Subscribes to RESPONSE_READY (or a virtual RESPONSE_SENT).
    If ctx.route == 'llm' AND judge score was ≥ 0.8 → store simhash → response in reflex cache.
    Always logs interaction.
    """
    # 1. Judge for quality check before storing
    judge_result = judge_response(ctx, ctx.response or "")
    score = judge_result.confidence(ctx.mode)

    # 2. Store in Reflex Cache if high quality and from LLM
    if ctx.route == "llm" and score >= 0.8:
        await update_reflex_cache(ctx.simhash, ctx.response)

    # 3. Log interaction
    logger.info(f"Interaction: input={ctx.text}, route={ctx.route}, score={score:.2f}")

async def update_reflex_cache(simhash: str, response: str):
    os.makedirs("data", exist_ok=True)
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    cache[simhash] = {"text": response}

    # LRU Eviction (simplified: just keep last MAX_ENTRIES)
    if len(cache) > MAX_ENTRIES:
        # Remove first key (oldest in some Python versions, but good enough for mock)
        first_key = next(iter(cache))
        del cache[first_key]

    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

bus.subscribe("RESPONSE_READY", on_response_ready)
