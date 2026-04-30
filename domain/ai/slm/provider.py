"""
ai/slm/provider.py

SLM provider — Ollama backend, small/fast model tier.
Called by Orchestrator when FastBrain can't answer.
Escalates to LLM when confidence is low.

Pipeline position:  FastBrain → [SLM] → LLM
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any, Tuple

import yaml

from domain.contracts.contracts import AIProviderContract
from domain.ai.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _load_ollama_config() -> Dict[str, Any]:
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "ollama.yaml"
    )
    try:
        with open(os.path.abspath(config_path), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("ollama", {})
    except FileNotFoundError:
        logger.warning("config/ollama.yaml not found — using SLM defaults")
        return {}
    except Exception as e:
        logger.warning("Failed to load ollama config: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Confidence estimation
# ---------------------------------------------------------------------------

def _estimate_confidence(response: str, user_input: str) -> float:
    """
    Lightweight heuristic confidence score for an SLM response.
    Returns 0.0–1.0. Low score → escalate to LLM.

    Checks:
    - Response is not empty or suspiciously short
    - Response doesn't contain known uncertainty markers
    - Length is appropriate relative to input complexity
    """
    if not response or len(response.strip()) < 5:
        return 0.0

    low_conf_markers = [
        "i don't know", "i'm not sure", "i cannot", "i can't",
        "i'm unable", "as an ai", "i apologize", "i don't have",
        "unclear", "not certain",
    ]
    lowered = response.lower()
    for marker in low_conf_markers:
        if marker in lowered:
            return 0.4

    # Very short response to a long question = possibly uncertain
    if len(user_input) > 100 and len(response) < 20:
        return 0.5

    # Reasonable response
    return 0.8


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class SLMProvider(AIProviderContract):
    """
    Small Language Model provider using Ollama.

    Responsible for:
    - Fast personality-aware responses to typical conversational inputs
    - Emotion/style injection via personality signal
    - Confidence estimation → escalation trigger for LLM
    """

    def __init__(self):
        self._available = False
        self._initialized = False
        self._client: Optional[OllamaClient] = None

        cfg = _load_ollama_config()
        slm_cfg = cfg.get("slm", {})

        self._base_url: str = cfg.get("base_url", "http://localhost:11434")
        self._timeout: int = cfg.get("timeout", 30)
        self._model: str = slm_cfg.get("model", "qwen2.5:1.5b")
        self._temperature: float = slm_cfg.get("temperature", 0.7)
        self._top_p: float = slm_cfg.get("top_p", 0.9)
        self._max_tokens: int = slm_cfg.get("max_tokens", 256)
        self._system_prompt: str = slm_cfg.get(
            "system_prompt",
            "You are Kitsu, a fox-spirit AI companion. Be warm, playful, and concise."
        )
        self._confidence_threshold: float = cfg.get("slm_confidence_threshold", 0.65)

    # ------------------------------------------------------------------
    # AIProviderContract
    # ------------------------------------------------------------------

    async def initialize(self) -> bool:
        """Connect to Ollama and verify the SLM model exists."""
        self._client = OllamaClient(self._base_url, self._timeout)

        if not self._client.is_reachable():
            logger.warning(
                "SLM: Ollama not reachable at %s. "
                "Start Ollama with: ollama serve",
                self._base_url,
            )
            self._available = False
            self._initialized = True
            return False

        pulled = self._client.list_models()
        if not self._client.model_exists(self._model):
            logger.warning(
                "SLM model '%s' not found. Available: %s\n"
                "Pull it with: ollama pull %s",
                self._model,
                pulled,
                self._model,
            )
            self._available = False
            self._initialized = True
            return False

        logger.info("SLMProvider ready → model=%s at %s", self._model, self._base_url)
        self._available = True
        self._initialized = True
        return True

    async def is_available(self) -> bool:
        return self._available and self._initialized

    async def infer(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Generate a fast response using the small model.

        Args:
            prompt:  User input text
            context: Optional dict with personality_hint, emotion_state, memory_context

        Returns:
            Response text or None on failure.
        """
        if not await self.is_available():
            logger.debug("SLM not available, skipping")
            return None

        ctx = context or {}
        system = self._system_prompt

        # Personality injection
        personality_hint = ctx.get("personality_hint", "")
        if personality_hint:
            system = f"{system}\n\nTone: {personality_hint}"

        emotion_state = ctx.get("emotion_state", "")
        memory_context = ctx.get("memory_context", "")

        full_prompt = self._client.build_kitsu_prompt(
            user_input=prompt,
            personality_hint=personality_hint,
            memory_context=memory_context,
            emotion_state=emotion_state,
        )

        logger.debug(
            "SLM generating with model=%s (prompt_len=%d)",
            self._model, len(full_prompt),
        )

        result = self._client.generate(
            model=self._model,
            prompt=full_prompt,
            system=system,
            temperature=self._temperature,
            top_p=self._top_p,
            max_tokens=self._max_tokens,
        )

        return result

    async def infer_with_confidence(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], float]:
        """
        Generate response AND estimate confidence.
        Used by Orchestrator to decide whether to escalate to LLM.

        Returns:
            (response_text, confidence_score)
            confidence < threshold → Orchestrator should call LLM instead
        """
        response = await self.infer(prompt, context)
        if response is None:
            return None, 0.0
        confidence = _estimate_confidence(response, prompt)
        logger.debug("SLM confidence=%.2f for response len=%d", confidence, len(response))
        return response, confidence

    def needs_llm_escalation(self, confidence: float) -> bool:
        """True if this confidence score means we should try the LLM instead."""
        return confidence < self._confidence_threshold

    async def train(self, input_text: str, response_text: str) -> None:
        """Log training pairs for future SLM fine-tuning."""
        if not await self.is_available():
            return
        # TODO: append to data/learning/slm_training_pairs.jsonl
        logger.debug(
            "SLM training pair logged (len_in=%d, len_out=%d)",
            len(input_text), len(response_text),
        )

    async def shutdown(self) -> None:
        self._available = False
        self._initialized = False
        logger.info("SLMProvider shut down")

    # ------------------------------------------------------------------
    # Legacy sync compatibility
    # ------------------------------------------------------------------

    def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Synchronous wrapper for legacy code."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.infer(prompt, context))
                    return future.result(timeout=self._timeout)
            else:
                return loop.run_until_complete(self.infer(prompt, context))
        except Exception as e:
            logger.error("SLM sync query failed: %s", e)
            return None