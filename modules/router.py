import os
import json
from core.event_bus import bus
from core.context import RequestContext

# In a real system, these would be shared or loaded from a common source
CACHE_FILE = "data/reflex_cache.json"
TEMPLATES = ["what time is it", "tell me a random fact", "hi"]

def check_reflex_cache(ctx: RequestContext) -> bool:
    # 1. Check learned cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                if ctx.simhash in cache:
                    return True
        except Exception:
            pass

    # 2. Check template match
    if ctx.text.lower().strip() in TEMPLATES:
        return True

    return False

def get_complexity_score(text: str) -> float:
    tokens = text.split()
    score = len(tokens) / 50.0
    if any(kw in text.lower() for kw in ["why", "how", "reason", "explain", "detail"]):
        score += 0.2
    return min(score, 1.0)

async def on_preprocess_done(ctx: RequestContext):
    """
    Subscribes to PREPROCESS_DONE.
    Checks reflex cache hit first (SimHash lookup, O(1)).
    If hit → emit REFLEX_PATH.
    Else compute complexity score.
    Complexity < 0.3 → SLM_PATH.
    Else → LLM_PATH.
    """
    if check_reflex_cache(ctx):
        ctx.route = "reflex"
        await bus.emit("REFLEX_PATH", ctx)
        return

    complexity = get_complexity_score(ctx.text)
    if complexity < 0.3:
        ctx.route = "slm"
        await bus.emit("SLM_PATH", ctx)
    else:
        ctx.route = "llm"
        await bus.emit("LLM_PATH", ctx)

bus.subscribe("PREPROCESS_DONE", on_preprocess_done)
