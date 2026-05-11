import logging
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext, can_respond
from kitsu.utils.timing import within_budget
from kitsu.modules.judge import judge_response

logger = logging.getLogger(__name__)

async def llm_generate(text: str, vibe: list[float]) -> str:
    # Mocking LLM call (e.g., deep reasoning)
    return f"[LLM Reasoning] I have thought deeply about your input: {text}."

async def on_llm_path(ctx: RequestContext):
    """
    Subscribes to LLM_PATH.
    Inner loop: while ctx.loop_count < 3 and within_budget(ctx).
    Each iteration: generate → judge all 3 signals → if score ≥ θ break.
    On exit, emit RESPONSE_READY.
    """
    if not can_respond(ctx): return

    theta = 0.65
    best_response = None
    max_score = -1.0

    while ctx.loop_count < 3 and within_budget(ctx):
        ctx.loop_count += 1

        # Generation
        response_text = await llm_generate(ctx.text, ctx.vibe)

        # Judging
        judge_result = judge_response(ctx, response_text)
        score = judge_result.confidence(ctx.mode)

        if score > max_score:
            max_score = score
            best_response = response_text

        if score >= theta:
            break

    ctx.response = best_response or "I'm sorry, I couldn't think of a good response within the time limit."
    await bus.emit("RESPONSE_READY", ctx)

bus.subscribe("LLM_PATH", on_llm_path)
