# application/modules/llm.py

import asyncio
import enum
import json
import logging
import os
from typing import Any, Optional


import aiohttp

from ..core.context import RequestContext, can_respond
from ..core.event_bus import bus
from shared.utils.timing import within_budget


# NOTE: within_budget is currently imported but not used in this module.


from .judge import judge_response
from .personality_integration import personality

from infrastructure.llm.llm_fallback_generator import LLMFallback

logger = logging.getLogger(__name__)

llm_fallback = LLMFallback()

# ── Configuration (env-driven so HF Space and local PC differ only in .env) ──
_SAFE_MODE = os.environ.get("KITSU_SAFE_MODE", "0") == "1"

# LLM_BASE_URL: full base URL of the inference server.
#   Local Ollama:  http://localhost:11434
#   Groq / OpenRouter:  https://api.groq.com/openai/v1  (OpenAI-compat)
#   Empty string → no inference available (gateway-only mode)
_LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434").rstrip("/")
_LLM_MODEL = os.environ.get("LLM_MODEL", "tinyllama:1.1b")
_HF_FALLBACK_URL = os.environ.get("HF_FALLBACK_URL", "").strip().rstrip("/")


class LLMProvider(enum.Enum):
    OLLAMA = "ollama"
    OPENAI_COMPAT = "openai_compat"
    HF_INFERENCE = "hf_inference"


def _detect_provider() -> LLMProvider:
    explicit = os.environ.get("LLM_PROVIDER", "").lower()
    if explicit in ("groq", "openai", "openrouter", "openai_compat"):
        return LLMProvider.OPENAI_COMPAT
    if explicit in ("hf", "huggingface", "hf_inference"):
        return LLMProvider.HF_INFERENCE
    if explicit == "ollama":
        return LLMProvider.OLLAMA

    url = _LLM_BASE_URL.lower()
    if "huggingface.co" in url or "hf.co" in url:
        return LLMProvider.HF_INFERENCE
    if any(kw in url for kw in ("openai", "groq", "openrouter", "anthropic", "together")):
        return LLMProvider.OPENAI_COMPAT
    return LLMProvider.OLLAMA


def _build_generate_url(base_url: str, provider: LLMProvider) -> str:
    if not base_url:
        return ""
    if provider == LLMProvider.OPENAI_COMPAT:
        return f"{base_url}/chat/completions"
    if provider == LLMProvider.HF_INFERENCE:
        if base_url.endswith("/models") or "/models/" in base_url:
            return base_url if base_url.endswith(_LLM_MODEL) else f"{base_url.rstrip('/')}/{_LLM_MODEL}"
        return f"{base_url.rstrip('/')}/models/{_LLM_MODEL}"
    return f"{base_url}/api/generate"


_PROVIDER = _detect_provider()
_GENERATE_URL = _build_generate_url(_LLM_BASE_URL, _PROVIDER)


def _request_headers(provider: LLMProvider, *, base_url: str | None = None) -> dict[str, str]:
    if provider == LLMProvider.HF_INFERENCE:
        token = (
            os.environ.get("HF_TOKEN", "").strip()
            or os.environ.get("HUGGINGFACEHUB_API_TOKEN", "").strip()
            or os.environ.get("LLM_API_KEY", "").strip()
        )
        return {"Authorization": f"Bearer {token}"} if token else {}
    if provider == LLMProvider.OPENAI_COMPAT:
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return {}


def _build_request_body(
    prompt: str,
    vibe: list[float],
    provider: LLMProvider,
    *,
    stream: bool = True,
) -> dict:
    temperature = 0.7 + (vibe[0] * 0.3)
    if provider == LLMProvider.OPENAI_COMPAT:
        return {
            "model": _LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "temperature": temperature,
            "top_p": 0.9,
        }
    if provider == LLMProvider.HF_INFERENCE:
        body: dict = {
            "inputs": prompt,
            "parameters": {"temperature": temperature, "top_p": 0.9, "return_full_text": False},
        }
        if stream:
            body["stream"] = True
        return body
    return {
        "model": _LLM_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 40,
        },
    }


def _extract_hf_text(payload: Any) -> str:
    if isinstance(payload, list) and payload:
        item = payload[0]
        if isinstance(item, dict):
            text = item.get("generated_text") or item.get("translation_text")
            if isinstance(text, str):
                return text.strip()
    if isinstance(payload, dict):
        text = payload.get("generated_text")
        if isinstance(text, str):
            return text.strip()
    return ""


def _parse_stream_chunk(chunk_data: dict, provider: LLMProvider) -> tuple[str, bool]:
    if provider == LLMProvider.OPENAI_COMPAT:
        chunk = (
            chunk_data.get("choices", [{}])[0]
            .get("delta", {})
            .get("content", "")
        )
        done = chunk_data.get("choices", [{}])[0].get("finish_reason") is not None
        return chunk or "", done
    if provider == LLMProvider.HF_INFERENCE:
        token = chunk_data.get("token", {}) if isinstance(chunk_data.get("token"), dict) else {}
        chunk = token.get("text") or chunk_data.get("generated_text") or ""
        done = bool(chunk_data.get("done"))
        return str(chunk), done
    chunk = chunk_data.get("response", "")
    done = chunk_data.get("done", False)
    return chunk or "", bool(done)


def _llm_available() -> bool:
    """Return False when inference cannot work (for example gateway-only mode)."""
    if not _LLM_BASE_URL:
        return False
    if _SAFE_MODE and not os.environ.get("LLM_BASE_URL"):
        return False
    return True


def _get_watchdog():
    """Load the watchdog lazily so safe mode never crashes during import."""
    try:
        from .ollama_watchdog import watchdog as watchdog_instance
    except Exception:
        logger.debug("LLM watchdog unavailable; continuing without it", exc_info=True)
        return None
    return watchdog_instance


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


async def _emit_stream_text(
    text: str, ctx: RequestContext, chunk_size: int = 40, delay: float = 0.02
) -> None:
    """Emit a text response as RESPONSE_STREAM chunks."""
    try:
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            await bus.emit(
                "RESPONSE_STREAM",
                {"id": ctx.id, "chunk": chunk, "done": False},
            )
            await asyncio.sleep(delay)
        await bus.emit(
            "RESPONSE_STREAM",
            {"id": ctx.id, "chunk": "", "done": True},
        )
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
    try:
        setattr(ctx, "debug_reason", "llm_fallback_used")
    except Exception:
        pass
    await _emit_stream_text(text, ctx)
    return text


async def llm_generate_hf(
    prompt: str,
    ctx: RequestContext,
    *,
    base_url: str | None = None,
) -> str | None:
    """Non-streaming HuggingFace Inference API call."""
    url_base = (base_url or _HF_FALLBACK_URL or _LLM_BASE_URL).strip().rstrip("/")
    if not url_base:
        return None

    generate_url = _build_generate_url(url_base, LLMProvider.HF_INFERENCE)
    headers = _request_headers(LLMProvider.HF_INFERENCE)
    request_body = _build_request_body(prompt, getattr(ctx, "vibe", [0.0, 0.0, 0.0]), LLMProvider.HF_INFERENCE, stream=False)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                generate_url,
                json=request_body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45.0),
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        "HF inference request failed status=%d url=%s",
                        resp.status,
                        generate_url,
                    )
                    return None
                payload = await resp.json(content_type=None)
                text = _extract_hf_text(payload)
                if text:
                    await _emit_stream_text(text, ctx)
                    return text
                return None
    except Exception as exc:
        logger.warning("HF inference failed for id=%s: %s", ctx.id, exc)
        return None


async def llm_generate_streaming(
    prompt: str, vibe: list[float], ctx: RequestContext
) -> str | None:
    """Stream from the configured LLM endpoint to the event bus.

    Returns the full response string, or None on any failure.
    Returns None immediately if no inference endpoint is configured.
    """
    if not _llm_available():
        logger.info(
            "LLM: no inference endpoint configured (gateway-only mode), skipping"
        )
        return None

    watchdog = _get_watchdog()
    provider = _PROVIDER
    generate_url = _GENERATE_URL

    try:
        async with aiohttp.ClientSession() as session:
            headers = _request_headers(provider)
            request_body = _build_request_body(prompt, vibe, provider, stream=True)

            async with session.post(
                generate_url,
                json=request_body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45.0),
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        "LLM streaming request failed with status %d url=%s",
                        resp.status,
                        generate_url,
                    )
                    debug_escalate(
                        f"LLM streaming HTTP status {resp.status}", "LLM"
                    )
                    if watchdog is not None:
                        try:
                            watchdog.record_failure(
                                Exception(f"LLM bad status {resp.status}")
                            )
                        except Exception:
                            pass
                    return None

                buffer = ""
                full_response: list[str] = []

                if provider == LLMProvider.HF_INFERENCE:
                    payload = await resp.json(content_type=None)
                    text = _extract_hf_text(payload)
                    if text:
                        await _emit_stream_text(text, ctx)
                        return text
                    return None

                async for chunk_bytes in resp.content.iter_chunked(4096):
                    if not chunk_bytes:
                        continue

                    decoded = chunk_bytes.decode("utf-8", errors="ignore")
                    buffer += decoded

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            line = line[6:]

                        try:
                            chunk_data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        chunk, done = _parse_stream_chunk(chunk_data, provider)

                        if chunk:
                            full_response.append(chunk)

                            from .judge import stream_validate

                            should_continue, reason = await stream_validate(
                                "".join(full_response), ctx
                            )
                            if not should_continue:
                                await bus.emit(
                                    "RESPONSE_FILTERED",
                                    {"id": ctx.id, "reason": reason},
                                )
                                await bus.emit("SLM_PATH", ctx)
                                return "".join(full_response)

                            await bus.emit(
                                "RESPONSE_STREAM",
                                {"id": ctx.id, "chunk": chunk, "done": False},
                            )

                        if done:
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
        if watchdog is not None:
            try:
                watchdog.record_failure(exc)
            except Exception:
                pass
        return None
    except Exception as exc:
        logger.exception("LLM streaming failed for id=%s: %s", ctx.id, exc)
        debug_escalate("LLM streaming exception", "LLM")
        setattr(ctx, "debug_reason", "llm_stream_exception")
        if watchdog is not None:
            try:
                watchdog.record_failure(exc)
            except Exception:
                pass
        return None


async def on_llm_path(ctx: RequestContext):
    """
    Subscribes to LLM_PATH.
    Uses personality prompt enrichment and streams final LLM output.
    Falls back gracefully when no inference endpoint is available.
    """
    await personality.initialize()

    prompt, vibe = await personality.build_prompt_context(ctx.text)
    ctx.vibe = vibe

    response_text = await llm_generate_streaming(prompt, vibe, ctx)

    if response_text is None and _PROVIDER == LLMProvider.OPENAI_COMPAT:
        hf_url = _HF_FALLBACK_URL
        if hf_url:
            logger.info("Primary OpenAI-compat LLM failed; trying HF fallback url=%s", hf_url)
            response_text = await llm_generate_hf(prompt, ctx, base_url=hf_url)

    if response_text is None:
        logger.warning(
            "LLM streaming produced no response (unavailable or failed); using fallback"
        )
        debug_response_pipeline("LLM unavailable — using fallback generator")
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
        debug_judge_score(
            ctx.response_confidence,
            0.8,
            ctx.response_confidence >= 0.8,
            "LLM judge exception",
        )

    if can_respond(ctx):
        try:
            await personality.update_after_response(response_text, ctx.original_text)
        except Exception:
            logger.exception("Personality update failed after response")

        try:
            from .reflex import cache_put

            judge_result_final = judge_response(ctx, response_text)
            if judge_result_final.passes(ctx.mode):
                debug_cache_put(
                    str(ctx.simhash)[:8],
                    response_text[:30],
                    judge_result_final.confidence(ctx.mode),
                )
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
