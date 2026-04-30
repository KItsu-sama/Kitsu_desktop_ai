"""
ai/llm/ollama_client.py

Shared Ollama HTTP client used by both SLMProvider and LLMProvider.
Single place for all Ollama API logic — retry, timeout, error handling.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Lightweight Ollama REST client using stdlib only (no httpx/aiohttp needed).
    Handles /api/generate with timeout and clean error reporting.
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    def is_reachable(self) -> bool:
        """Quick ping to check if Ollama server is up."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Return names of all pulled models."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning("Could not list Ollama models: %s", e)
            return []

    def model_exists(self, model: str) -> bool:
        """Check if a specific model is available."""
        pulled = self.list_models()
        # Check exact match OR base name match (e.g. "qwen2.5:1.5b" in "qwen2.5:1.5b")
        return any(model in m or m in model for m in pulled)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 256,
        stream: bool = False,
    ) -> Optional[str]:
        """
        Call /api/generate and return the response text.

        Args:
            model:       Ollama model name (e.g. "qwen2.5:1.5b")
            prompt:      User-facing prompt text
            system:      System prompt injected before the conversation
            temperature: Sampling temperature
            top_p:       Nucleus sampling
            max_tokens:  Max tokens to generate
            stream:      Must be False — streaming not used here

        Returns:
            Generated text string, or None on failure.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }

        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                data = json.loads(raw)
                text = data.get("response", "").strip()
                if not text:
                    logger.warning("Ollama returned empty response for model %s", model)
                    return None
                return text

        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.error(
                "Ollama HTTP %s for model %s: %s", e.code, model, body_text[:200]
            )
            return None

        except urllib.error.URLError as e:
            logger.error("Ollama unreachable (%s). Is Ollama running?", e.reason)
            return None

        except json.JSONDecodeError as e:
            logger.error("Ollama returned invalid JSON: %s", e)
            return None

        except TimeoutError:
            logger.error("Ollama request timed out after %ss for model %s", self.timeout, model)
            return None

        except Exception as e:
            logger.error("Unexpected Ollama error: %s", e)
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def build_kitsu_prompt(
        self,
        user_input: str,
        personality_hint: str = "",
        memory_context: str = "",
        emotion_state: str = "",
    ) -> str:
        """
        Build the user-facing prompt with Kitsu context injected.
        Keeps the system prompt clean and puts context in the user prompt.
        """
        parts: list[str] = []

        if emotion_state:
            parts.append(f"[Emotional context: {emotion_state}]")

        if personality_hint:
            parts.append(f"[Personality: {personality_hint}]")

        if memory_context:
            parts.append(f"[Memory: {memory_context}]")

        parts.append(f"User: {user_input}")
        parts.append("Kitsu:")

        return "\n".join(parts)