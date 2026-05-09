import hashlib
import re
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

# Mock emotion engine state
EMOTION_ENGINE_STATE = {
    "vibe": [0.1, 0.5, 0.2, 0.8, 0.4, 0.3, 0.6, 0.9, 0.7, 0.0]
}

def compute_simhash(text: str) -> str:
    """
    Computes SimHash from sorted deduplicated tokens.
    Keeps stopwords out (simplified for now).
    """
    # Simplified stopword list
    stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'and', 'or', 'to', 'of'}

    # Tokenize and clean
    tokens = re.findall(r'\w+', text.lower())
    tokens = [t for t in tokens if t not in stopwords]
    tokens = sorted(list(set(tokens)))

    if not tokens:
        return hashlib.md5(text.encode()).hexdigest()

    return hashlib.md5(" ".join(tokens).encode()).hexdigest()

async def on_input_received(ctx: RequestContext):
    """
    Subscribes to INPUT_RECEIVED.
    Computes SimHash and extracts vibe.
    Emits PREPROCESS_DONE.
    Budget: 10ms.
    """
    ctx.simhash = compute_simhash(ctx.text)

    # Extracts vibe floats from emotion engine state
    ctx.vibe = EMOTION_ENGINE_STATE["vibe"]

    await bus.emit("PREPROCESS_DONE", ctx)

bus.subscribe("INPUT_RECEIVED", on_input_received)
