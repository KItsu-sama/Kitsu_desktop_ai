import json
import os
import random
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

CACHE_FILE = "data/reflex_cache.json"

# In-memory learned cache
LEARNED_CACHE = {}

def load_cache():
    global LEARNED_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                LEARNED_CACHE = json.load(f)
        except Exception:
            LEARNED_CACHE = {}

load_cache()

# Template layer
TEMPLATES = {
    "what time is it": ["It's currently {time}.", "The clock says {time}."],
    "tell me a random fact": ["Did you know that foxes are related to dogs?", "Kitsu is the best fox AI!"],
    "hi": ["Kon!", "Hi there!", "Hey!"]
}

def get_markov_response(ctx: RequestContext) -> str:
    # Simplified Markov/template matcher
    text = ctx.text.lower().strip()
    if text in TEMPLATES:
        return random.choice(TEMPLATES[text])
    return None

async def on_reflex_path(ctx: RequestContext):
    """
    Subscribes to REFLEX_PATH.
    Learned cache lookup (JSON on disk, loaded into memory).
    Markov/template layer for ambient/tool patterns.
    Applies vibe vector last before emitting.
    Budget: under 100ms total.
    """
    # 1. Learned Cache Lookup
    if ctx.simhash in LEARNED_CACHE:
        ctx.response = LEARNED_CACHE[ctx.simhash]["text"]
        await bus.emit("RESPONSE_READY", ctx)
        return

    # 2. Template/Markov Layer
    response = get_markov_response(ctx)
    if response:
        # Template substitution (simplified)
        if "{time}" in response:
            from datetime import datetime
            response = response.replace("{time}", datetime.now().strftime("%H:%M"))

        ctx.response = response
        await bus.emit("RESPONSE_READY", ctx)
        return

    # If reflex failed, fall back to SLM
    await bus.emit("SLM_PATH", ctx)

bus.subscribe("REFLEX_PATH", on_reflex_path)
