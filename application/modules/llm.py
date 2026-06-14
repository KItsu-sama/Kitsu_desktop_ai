# application/modules/llm.py

import json
import logging
import time
from ..core.event_bus import bus
from ..core.context import RequestContext, can_respond
from shared.utils.timing import within_budget

from .judge import judge_response
from .personality_integration import personality
from .ollama_watchdog import watchdog


from infrastructure.llm.llm_fallback_generator import LLMFallback

logger = logging.getLogger(__name__)

llm_fallback = LLMFallback()

import aiohttp
import asyncio
# Debug helpers
try:
    from shared.debug_timer import (
        debug_escalate,
        debug_response_pipeline,
        debug_judge_score,
        debug_cache_put,
        _debug,
    )
except Exception:
    def debug_escalate(*args, **kwargs):
        pass
    def debug_response_pipeline(*args, **kwargs):
        pass
    def debug_judge_score(*args, **kwargs):
        pass
    def debug_cache_put(*args, **kwargs):
        pass
    def _debug(*args, **kwargs):
        pass


async def _emit_stream_text(text: str, ctx: RequestContext, chunk_size: int = 40, delay: float = 0.02) -> None:
    """Emit a text response as RESPONSE_STREAM chunks."""
    try:
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            await bus.emit("RESPONSE_STREAM", {"id": ctx.id, "chunk": chunk, "done": False})
            await asyncio.sleep(delay)
        await bus.emit("RESPONSE_STREAM", {"id": ctx.id, "chunk": "", "done": True})
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Fallback stream emission failed for id=%s", ctx.id)


async def _fallback_response(ctx: RequestContext) -> str:
    """Produce a fallback response and stream it."""
    text = llm_fallback.generate(
        mood="behave",
        style="sweet",
        cause="llm_failed",
        raw_input=ctx.original_text or ctx.text,
    )
    ctx.response_owner = "llm_fallback_generator"
    ctx.response_confidence = 0.3
    # Mark fallback attribution for UI/ops
    try:
        setattr(ctx, "debug_reason", "llm_fallback_used")
    except Exception:
        pass
    await _emit_stream_text(text, ctx)
    return text


async def llm_generate_streaming(prompt: str, vibe: list[float], ctx: RequestContext) -> str | None:
    """Stream directly from Ollama to event bus."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:11434/api/generate",
                json={
                        "model": "tinyllama:1.1b",
                        # ollama /api/generate has no explicit role separation.
                        # Ensure "system" instructions are baked into the prompt.
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": 0.7 + (vibe[0] * 0.3),
                            "top_p": 0.9,
                            "top_k": 40,
                        },
                    },
                timeout=aiohttp.ClientTimeout(total=45.0),
            ) as resp:
                if resp.status != 200:
                    logger.warning("LLM streaming request failed with status %d", resp.status)
                    debug_escalate(f"LLM streaming HTTP status {resp.status}", "LLM")
                    try:
                        watchdog.record_failure(Exception(f"Ollama bad status {resp.status}"))
                    except Exception:
                        pass
                    return None


                buffer = ""
                full_response: list[str] = []
                async for chunk_bytes in resp.content.iter_chunked(4096):
                    if not chunk_bytes:
                        continue

                    decoded = chunk_bytes.decode("utf-8", errors="ignore")
                    buffer += decoded

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if not line.strip():
                            continue

                        try:
                            chunk_data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        chunk = chunk_data.get("response", "")
                        if chunk:
                            full_response.append(chunk)
                            buffer = buffer + chunk

                            # Stream mid-validation
                            from .judge import stream_validate

                            should_continue, reason = await stream_validate(buffer, ctx)
                            if not should_continue:
                                await bus.emit("RESPONSE_FILTERED", {"id": ctx.id, "reason": reason})
                                await bus.emit("SLM_PATH", ctx)
                                return "".join(full_response)

                            await bus.emit(
                                "RESPONSE_STREAM",
                                {"id": ctx.id, "chunk": chunk, "done": False},
                            )



                        if chunk_data.get("done", False):
                            await bus.emit(
                                "RESPONSE_STREAM",
                                {"id": ctx.id, "chunk": "", "done": True},
                            )
                            return "".join(full_response)


                if full_response:
                    await bus.emit(
                        "RESPONSE_STREAM",
                        {"id": ctx.id, "chunk": "", "done": True},
                    )
                    return "".join(full_response)

                return None
    except asyncio.TimeoutError as exc:
        logger.warning("LLM streaming timeout for id=%s: %s", ctx.id, exc)
        debug_escalate("LLM streaming timeout", "LLM")
        setattr(ctx, "debug_reason", "llm_stream_timeout")
        try:
            watchdog.record_failure(exc)
        except Exception:
            logger.debug("watchdog.record_failure failed (timeout)")
        return None
    except Exception as exc:
        logger.exception("LLM streaming failed for id=%s: %s", ctx.id, exc)
        debug_escalate("LLM streaming exception", "LLM")
        setattr(ctx, "debug_reason", "llm_stream_exception")
        try:
            watchdog.record_failure(exc)
        except Exception:
            logger.debug("watchdog.record_failure failed (exception)")
        return None



async def on_llm_path(ctx: RequestContext):
    """
    Subscribes to LLM_PATH.
    Uses personality prompt enrichment and streams final LLM output.
    """
    await personality.initialize()

    prompt, vibe = await personality.build_prompt_context(ctx.text)
    ctx.vibe = vibe

    response_text = await llm_generate_streaming(prompt, vibe, ctx)
    if response_text is None:
        logger.warning("LLM streaming did not produce a valid response; using fallback generator")
        debug_response_pipeline("LLM streaming failed — using fallback generator")
        setattr(ctx, "debug_reason", "llm_stream_no_response_fallback")
        response_text = await _fallback_response(ctx)
    else:
        ctx.response_owner = "llm"

    ctx.response = response_text

    try:
        judge_result = judge_response(ctx, response_text)
        ctx.response_confidence = judge_result.confidence(ctx.mode)
    except Exception:
        ctx.response_confidence = 0.5
        logger.exception("Failed to score LLM response")
        debug_judge_score(ctx.response_confidence, 0.8, ctx.response_confidence >= 0.8, "LLM judge exception")

    if can_respond(ctx):
        try:
            await personality.update_after_response(response_text, ctx.original_text)
        except Exception:
            logger.exception("Personality update failed after response")

        # Cache successful LLM responses in reflex cache.
        try:
            from .reflex import cache_put
            # Only store if judge passed in final verification.
            judge_result_final = judge_response(ctx, response_text)
            if judge_result_final.passes(ctx.mode):
                debug_cache_put(str(ctx.simhash)[:8], response_text[:30], judge_result_final.confidence(ctx.mode))
                try:
                    cache_put(int(ctx.simhash), response_text)
                    setattr(ctx, "debug_reason", "llm_cached_response")
                except Exception:
                    _debug("LLM", "CACHE_PUT_FAIL", "failed to write cache")
        except Exception:
            logger.exception("Failed to cache LLM response")

        await bus.emit("RESPONSE_READY", ctx)



from ..core.subscriptions import register

register("LLM_PATH", on_llm_path)
