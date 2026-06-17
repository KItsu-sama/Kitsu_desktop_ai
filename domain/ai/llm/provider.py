"""
ai/llm/provider.py

LLM provider — Ollama backend, large model tier.
Called by Orchestrator when SLM signals low confidence or input is complex.

Pipeline position:  FastBrain → SLM → [LLM]  ← you are here
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any

import yaml

from domain.contracts.contracts import AIProviderContract
from domain.ai.llm.ollama_client import OllamaClient
from domain.ai.shared.gguf_provider import GGUFInferenceProvider


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _load_ollama_config() -> Dict[str, Any]:
    """Load config/ollama.yaml, fall back to sensible defaults."""
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "ollama.yaml"
    )
    try:
        with open(os.path.abspath(config_path), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("ollama", {})
    except FileNotFoundError:
        logger.warning("config/ollama.yaml not found — using LLM defaults")
        return {}
    except Exception as e:
        logger.warning("Failed to load ollama config: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class LLMProvider(AIProviderContract):

    """
    Large Language Model provider using Ollama.

    Responsible for:
    - Complex reasoning queries that SLM can't handle confidently
    - Long-form responses (writing, code, deep explanations)
    - Personality-injected generation via PromptSignalBuilder
    """

    def __init__(self):
        self._available = False
        self._initialized = False
        self._client: Optional[OllamaClient] = None

        # Local GGUF mode (llama-cpp-python)
        self._use_gguf = os.environ.get("KITSU_USE_GGUF", "false").lower() in ("1", "true", "yes")
        self._gguf_engine: Optional[GGUFInferenceProvider] = None

        if self._use_gguf:
            self._gguf_engine = GGUFInferenceProvider(
                model_env_var="KITSU_LLM_GGUF_PATH",
                default_path="./data/models/llama-3.2-3b-instruct-q4_k_m.gguf",
                system_prompt="You are Kitsu, a fox-spirit AI companion. Be warm, clever, and in character.",
            )

        # Load config
        cfg = _load_ollama_config()
        llm_cfg = cfg.get("llm", {})
        routing_cfg = cfg.get("routing", {})

        self._base_url: str = cfg.get("base_url", "http://localhost:11434")
        self._timeout: int = cfg.get("timeout", 30)
        self._model: str = llm_cfg.get("model", "llama3.2:3b")
        self._temperature: float = llm_cfg.get("temperature", 0.8)
        self._top_p: float = llm_cfg.get("top_p", 0.95)
        self._max_tokens: int = llm_cfg.get("max_tokens", 512)
        self._system_prompt: str = llm_cfg.get(
            "system_prompt",
            "You are Kitsu, a fox-spirit AI companion. Be warm, clever, and in character."
        )

        # Routing hints (used by Orchestrator to decide LLM vs SLM)
        self._llm_keywords: list[str] = routing_cfg.get("llm_keywords", [
            "explain", "why", "how does", "analyze", "compare",
            "write a", "create", "code", "debug", "help me with",
        ])
        self._llm_length_threshold: int = routing_cfg.get(
            "llm_input_length_threshold", 200
        )

    # ------------------------------------------------------------------
    # AIProviderContract
    # ------------------------------------------------------------------

    async def initialize(self) -> bool:
        """Initialize provider (GGUF if enabled, otherwise Ollama)."""
        if self._use_gguf and self._gguf_engine is not None:
            ok = self._gguf_engine.initialize()
            self._available = ok
            self._initialized = True
            return ok

        self._client = OllamaClient(self._base_url, self._timeout)


        if not self._client.is_reachable():
            logger.warning(
                "LLM: Ollama not reachable at %s. "
                "Start Ollama with: ollama serve",
                self._base_url,
            )
            self._available = False
            self._initialized = True
            return False

        pulled = self._client.list_models()
        if not self._client.model_exists(self._model):
            logger.warning(
                "LLM model '%s' not found. Available: %s\n"
                "Pull it with: ollama pull %s",
                self._model,
                pulled,
                self._model,
            )
            self._available = False
            self._initialized = True
            return False

        logger.info("LLMProvider ready → model=%s at %s", self._model, self._base_url)
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
        Generate a response using the large model.

        Args:
            prompt:  The assembled user prompt (may include personality/memory hints)
            context: Optional dict with keys:
                       - personality_hint (str)
                       - memory_context   (str)
                       - emotion_state    (str)
                       - system_override  (str)  — replaces default system prompt

        Returns:
            Response text or None on failure.
        """
        if not await self.is_available():
            logger.debug("LLM not available, skipping")
            return None

        ctx = context or {}
        system = ctx.get("system_override", self._system_prompt)

        # Enrich the system prompt with personality signal if provided
        personality_hint = ctx.get("personality_hint", "")
        if personality_hint:
            system = f"{system}\n\nPersonality guidance: {personality_hint}"

        emotion_state = ctx.get("emotion_state", "")
        memory_context = ctx.get("memory_context", "")

        # Local GGUF path (no Ollama daemon required)
        if self._use_gguf and self._gguf_engine is not None and self._gguf_engine.is_available():
            enriched = f"{memory_context}\n\n{emotion_state}\n\n{prompt}".strip()
            return await self._gguf_engine.infer(enriched, system_prompt=system)

        # Build full prompt
        full_prompt = self._client.build_kitsu_prompt(
            user_input=prompt,
            personality_hint=personality_hint,
            memory_context=memory_context,
            emotion_state=emotion_state,
        )

        logger.debug("LLM generating with model=%s (prompt_len=%d)", self._model, len(full_prompt))

        result = self._client.generate(
            model=self._model,
            prompt=full_prompt,
            system=system,
            temperature=self._temperature,
            top_p=self._top_p,
            max_tokens=self._max_tokens,
        )


        if result:
            logger.debug("LLM response: %d chars", len(result))
        else:
            logger.warning("LLM returned no response")

        return result

    async def train(self, input_text: str, response_text: str) -> None:
        """
        Log good (input, response) pairs for future fine-tuning.
        Actual LoRA/QLoRA training happens offline via training scripts.
        """
        if not await self.is_available():
            return
        # TODO: append to data/learning/llm_training_pairs.jsonl
        logger.debug(
            "LLM training pair logged (len_in=%d, len_out=%d)",
            len(input_text), len(response_text),
        )

    async def shutdown(self) -> None:
        """Clean up."""
        self._available = False
        self._initialized = False
        logger.info("LLMProvider shut down")

    # ------------------------------------------------------------------
    # Routing helpers (used by Orchestrator)
    # ------------------------------------------------------------------

    def should_use_llm(self, user_input: str) -> bool:
        """
        Heuristic: should this input go straight to LLM, skipping SLM?
        Called by Orchestrator before routing.
        """
        if len(user_input) > self._llm_length_threshold:
            return True
        lowered = user_input.lower()
        return any(kw in lowered for kw in self._llm_keywords)

    # ------------------------------------------------------------------
    # Legacy sync compatibility
    # ------------------------------------------------------------------

    def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Synchronous wrapper for legacy code that calls .query() directly.
        Runs the async infer() in a new event loop if needed.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.infer(prompt, context))
                    return future.result(timeout=self._timeout)
            else:
                return loop.run_until_complete(self.infer(prompt, context))
        except Exception as e:
            logger.error("LLM sync query failed: %s", e)
            return None