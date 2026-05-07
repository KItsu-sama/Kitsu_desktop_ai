import time
import logging
from typing import List, Tuple
from core.event_bus import bus
from core.context import RequestContext
from utils.timing import within_budget
from modules.judge import judge_response

logger = logging.getLogger(__name__)

class SLMInterface:
    def load(self):
        logger.info("SLM (Qwen2.5-1.5B Q4) loaded.")

    def generate(self, text: str, vibe: List[float], mode: str, max_tokens: int = 256) -> Tuple[str, float]:
        """
        Returns (response_text, raw_logit_confidence)
        Personality injection happens inside - system prompt built from vibe floats.
        """
        # Mocking generation
        # In real impl, use llama-cpp-python or similar
        vibe_str = ",".join([f"{v:.2f}" for v in vibe])
        response = f"I am a kitsu fox with vibe {vibe_str}. You said: {text}."
        confidence = 0.8
        return response, confidence

    def unload(self):
        logger.info("SLM unloaded.")

slm_instance = SLMInterface()
slm_instance.load()

async def on_slm_path(ctx: RequestContext):
    """
    Subscribes to SLM_PATH.
    If judge score < theta AND within_budget(ctx) → emit LLM_PATH.
    Otherwise emit RESPONSE_READY.
    Budget: 500ms hard cap.
    """
    theta = 0.65

    # Check budget before starting
    if not within_budget(ctx):
        await bus.emit("LLM_PATH", ctx)
        return

    # Mocking hard cap
    response_text, logit_conf = slm_instance.generate(ctx.text, ctx.vibe, ctx.mode)

    # Judge call
    judge_result = judge_response(ctx, response_text)
    score = judge_result.confidence(ctx.mode)

    if score < theta and within_budget(ctx):
        await bus.emit("LLM_PATH", ctx)
    else:
        ctx.response = response_text
        await bus.emit("RESPONSE_READY", ctx)

bus.subscribe("SLM_PATH", on_slm_path)
