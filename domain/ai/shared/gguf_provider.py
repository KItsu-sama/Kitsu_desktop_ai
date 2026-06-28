"""domain/ai/shared/gguf_provider.py

Local GGUF inference provider using llama-cpp-python.

This module is intentionally lightweight:
- Uses environment variables for model path and minimal tuning.
- Provides an async-friendly API (sync llama call wrapped in async method).
- llama_cpp is imported lazily inside initialize() so this module is safe
  to import on HF Spaces or any environment where llama-cpp-python is absent.
  Callers should check is_available() before calling infer().

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
from typing import TYPE_CHECKING, Optional, Sequence

# llama_cpp is NOT imported at module level — it requires C++ compilation and
# is absent on HF Spaces free tier. Import happens lazily inside initialize().
# TYPE_CHECKING guard lets type checkers see the type without a runtime import.
if TYPE_CHECKING:
    from llama_cpp import Llama as _LlamaType
else:
    _LlamaType = None

logger = logging.getLogger(__name__)

# Module-level availability flag set on first initialize() call.
_LLAMA_CPP_AVAILABLE: Optional[bool] = None


def _check_llama_cpp_available() -> bool:
    """Return True if llama-cpp-python can be imported. Cached after first call."""
    global _LLAMA_CPP_AVAILABLE
    if _LLAMA_CPP_AVAILABLE is not None:
        return _LLAMA_CPP_AVAILABLE
    try:
        import llama_cpp  # noqa: F401
        _LLAMA_CPP_AVAILABLE = True
    except ImportError:
        logger.debug("llama-cpp-python not installed; GGUF inference unavailable")
        _LLAMA_CPP_AVAILABLE = False
    return _LLAMA_CPP_AVAILABLE


@dataclass(frozen=True)
class GGUFConfig:
    model_path: str
    n_ctx: int = 2048
    n_threads: int = 2
    n_batch: int = 512


class GGUFInferenceProvider:
    """Local GGUF inference wrapper around llama-cpp-python.

    Safe to instantiate on any platform — llama_cpp is imported lazily in
    initialize(). Call initialize() before infer(); check is_available() to
    confirm the model loaded successfully.
    """

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

        # _llm is typed as Optional[Any] at runtime since _LlamaType is None
        # outside TYPE_CHECKING. The actual llama_cpp.Llama instance is stored
        # here after a successful initialize().
        self._llm: Optional[object] = None
        self._initialized = False

    def initialize(self) -> bool:
        """Load the GGUF model. Safe to call multiple times (idempotent).

        Returns True if the model is ready, False otherwise.
        Does NOT raise — callers should check is_available() instead.
        """
        if self._initialized:
            return self._llm is not None

        # Fast-path: llama_cpp not installed
        if not _check_llama_cpp_available():
            logger.info(
                "GGUF provider skipped: llama-cpp-python not installed "
                "(expected on HF Spaces / API-only deployments)"
            )
            self._initialized = True
            return False

        if not self.model_path:
            logger.warning("GGUF model path empty (env fallback missing).")
            self._initialized = True
            return False

        if not os.path.exists(self.model_path):
            logger.warning("GGUF model file not found at: %s", self.model_path)
            self._initialized = True
            return False

        try:
            from llama_cpp import Llama  # lazy import

            logger.info(
                "Loading GGUF via llama-cpp-python: %s "
                "(n_ctx=%d, n_threads=%d, n_batch=%d)",
                self.model_path,
                self.n_ctx,
                self.n_threads,
                self.n_batch,
            )
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
        """True only after a successful initialize() with a model loaded."""
        return self._llm is not None

    def _build_prompt(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        sys_p = system_prompt if system_prompt is not None else self.system_prompt
        return (
            f"<sh_role>system\n{sys_p}\n"
            f"<sh_role>user\n{user_prompt}\n"
            f"<sh_role>assistant\n"
        )

    async def infer(self, user_prompt: str, *, system_prompt: Optional[str] = None) -> Optional[str]:
        """Run inference. Returns None if unavailable or on error."""
        if self._llm is None:
            return None

        formatted = self._build_prompt(user_prompt, system_prompt=system_prompt)
        llm = self._llm  # local ref avoids closure-over-self issues in thread

        def _run() -> Optional[str]:
            try:
                resp = llm(  # type: ignore[operator]
                    formatted,
                    max_tokens=int(os.environ.get("KITSU_GGUF_MAX_TOKENS", "150")),
                    stop=self.stop_tokens,
                )
                return resp["choices"][0]["text"].strip() if resp else None
            except Exception:
                logger.exception("GGUF infer() failed inside thread")
                return None

        return await asyncio.to_thread(_run)