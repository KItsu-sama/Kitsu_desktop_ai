"""Synchronous LLM proxy for the health gateway /chat endpoint."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_OPENAI_COMPAT_KEYWORDS = ("openai", "groq", "openrouter", "anthropic", "together")


def _llm_base_url() -> str:
    return os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")


def _llm_model() -> str:
    return os.environ.get("LLM_MODEL", "tinyllama:1.1b")


def _is_openai_compat(base_url: str) -> bool:
    lowered = base_url.lower()
    return any(kw in lowered for kw in _OPENAI_COMPAT_KEYWORDS) or lowered.endswith("/v1")


def _generate_url(base_url: str) -> str:
    if _is_openai_compat(base_url):
        return f"{base_url}/chat/completions"
    return f"{base_url}/api/generate"


def llm_configured() -> bool:
    return bool(_llm_base_url())


def _http_post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, Any] | str]:
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            if not raw:
                return response.status, {}
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"error": raw[:500] or exc.reason}


def _extract_reply(status: int, payload: dict[str, Any] | str, *, openai_compat: bool) -> str | None:
    if status != 200 or not isinstance(payload, dict):
        return None
    if openai_compat:
        choices = payload.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            delta = choices[0].get("text")
            if isinstance(delta, str) and delta.strip():
                return delta.strip()
        return None
    response_text = payload.get("response")
    if isinstance(response_text, str) and response_text.strip():
        return response_text.strip()
    return None


def complete_chat(prompt: str) -> tuple[int, dict[str, Any]]:
    """Forward *prompt* to the configured LLM endpoint."""
    text = (prompt or "").strip()
    if not text:
        return 400, {"error": "Prompt text must not be empty"}

    base_url = _llm_base_url()
    if not base_url:
        return 503, {
            "error": "LLM endpoint not configured",
            "hint": "Set LLM_BASE_URL (and LLM_API_KEY for OpenAI-compatible APIs) in the Space settings.",
        }

    model = _llm_model()
    openai_compat = _is_openai_compat(base_url)
    url = _generate_url(base_url)

    if openai_compat:
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        request_body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": text}],
            "stream": False,
            "temperature": 0.7,
        }
    else:
        headers = {}
        request_body = {
            "model": model,
            "prompt": text,
            "stream": False,
            "options": {"temperature": 0.7, "top_p": 0.9},
        }

    try:
        status, payload = _http_post_json(url, request_body, headers=headers)
    except urllib.error.URLError as exc:
        logger.warning("Gateway chat upstream unreachable url=%s error=%s", url, exc)
        return 502, {
            "error": "LLM endpoint unreachable",
            "hint": f"Could not connect to {base_url}",
            "detail": str(getattr(exc, "reason", exc)),
        }
    except TimeoutError:
        return 504, {"error": "LLM endpoint timed out", "hint": f"Request to {url} exceeded timeout"}
    except Exception as exc:
        logger.exception("Gateway chat failed url=%s", url)
        return 500, {"error": "Gateway chat failed", "detail": str(exc)}

    reply = _extract_reply(status, payload, openai_compat=openai_compat)
    if reply is None:
        detail = payload if isinstance(payload, dict) else {"raw": str(payload)[:500]}
        return status if status >= 400 else 502, {
            "error": "LLM returned no text",
            "upstream_status": status,
            "upstream": detail,
        }

    return 200, {
        "input": text,
        "text": reply,
        "reply": reply,
        "response": reply,
        "model": model,
        "source": "gateway",
        "endpoint": base_url,
    }
