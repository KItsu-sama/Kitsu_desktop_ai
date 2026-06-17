"""domain/ai/shared/gguf_provider.py

Local GGUF inference provider using llama-cpp-python.

This module is intentionally lightweight:
- Uses environment variables for model path and minimal tuning.
- Provides an async-friendly API (sync llama call wrapped in async method).

Environment variables:
- KITSU_USE_GGUF: "true" to enable GGUF providers.
- KITSU_SLM_GGUF_PATH: GGUF file path for SLM tier.
- KITSU_LLM_GGUF_PATH: GGUF file path for LLM tier.
- KITSU_GGUF_N_CTX: context length (default 2048)
- KITSU_GGUF_N_THREADS: CPU threads (default 2)
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional, Sequence

from llama_cpp import Llama

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GGUFConfig:
    model_path: str
    n_ctx: int = 2048
    n_threads: int = 2
    n_batch: int = 512


class GGUFInferenceProvider:
    """Local GGUF inference wrapper around llama-cpp-python."""

    def __init__(
        self,
        *,
        model_env_var: str,
        default_path: str,
        n_ctx_env_var: str = "KITSU_GGUF_N_CTX",
        n_threads_env_var: str = "KITSU_GGUF_N_THREADS",
        n_batch: int = 512,
        prompt_stop_tokens: Optional[Sequence[str]] = None,
        system_prompt: str = "You are Kitsu, a fox-spirit AI companion.",
    ) -> None:
        self.model_path = os.environ.get(model_env_var, default_path)
        self.n_ctx = int(os.environ.get(n_ctx_env_var, "2048"))
        self.n_threads = int(os.environ.get(n_threads_env_var, "2"))
        self.n_batch = int(os.environ.get("KITSU_GGUF_N_BATCH", str(n_batch)))
        self.system_prompt = os.environ.get("KITSU_GGUF_SYSTEM_PROMPT", system_prompt)
        self.stop_tokens = list(
            prompt_stop_tokens
            if prompt_stop_tokens is not None
            else ["<sh_role>", "user\n"]
        )

        self._llm: Optional[Llama] = None
        self._initialized = False

    def initialize(self) -> bool:
        if self._initialized:
            return self._llm is not None

        if not self.model_path:
            logger.warning("GGUF model path empty (env fallback missing).")
            self._initialized = True
            return False

        if not os.path.exists(self.model_path):
            logger.warning("GGUF model file not found at: %s", self.model_path)
            self._initialized = True
            return False

        try:
            logger.info(
                "Loading GGUF via llama-cpp-python: %s (n_ctx=%d, n_threads=%d, n_batch=%d)",
                self.model_path,
                self.n_ctx,
                self.n_threads,
                self.n_batch,
            )
            # Keep verbose off to prevent noisy logs in HF Spaces.
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_batch=self.n_batch,
                verbose=False,
            )
            self._initialized = True
            return True
        except Exception:
            logger.exception("Failed to initialize GGUF llama model")
            self._initialized = True
            self._llm = None
            return False

    def is_available(self) -> bool:
        return self._llm is not None

    def _build_prompt(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        sys_p = system_prompt if system_prompt is not None else self.system_prompt
        # Match the user-provided format snippet.
        return (
            f"<sh_role>system\n{sys_p}\n"
            f"<sh_role>user\n{user_prompt}\n"
            f"<sh_role>assistant\n"
        )

    async def infer(self, user_prompt: str, *, system_prompt: Optional[str] = None) -> Optional[str]:
        if self._llm is None:
            return None

        formatted = self._build_prompt(user_prompt, system_prompt=system_prompt)

        # llama-cpp-python call is sync; run it off the event loop.
        def _run() -> Optional[str]:
            resp = self._llm(
                formatted,
                max_tokens=int(os.environ.get("KITSU_GGUF_MAX_TOKENS", "150")),
                stop=self.stop_tokens,
            )
            try:
                return resp["choices"][0]["text"].strip() if resp else None
            except Exception:
                return None

        return await asyncio.to_thread(_run)

