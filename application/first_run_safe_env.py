from __future__ import annotations

import os
import platform
import sys
from typing import Any, Dict


def safe_collect_first_run_environment() -> Dict[str, Any]:
    """Collect only non-secret, deterministic-ish facts for first-run.

    This must not include any token/API key values.
    """

    def _bool_env(key: str) -> bool:
        return os.environ.get(key) in {"1", "true", "True", "TRUE"}

    # Do not include LLM base URLs/tokens. We only report whether an
    # inference endpoint is configured in a boolean fashion.
    llm_base_url_configured = bool(os.environ.get("LLM_BASE_URL", "").strip())
    hf_token_configured = bool(os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGINGFACEHUB_API_TOKEN", "").strip())

    return {
        "system": {
            "platform": platform.system().lower(),
            "platform_version": platform.version(),
            "python_version": sys.version,
            "headless": not sys.stdin.isatty() if hasattr(sys, "stdin") and sys.stdin else True,
            "capabilities": {
                # Keep these coarse; do not import heavy modules here.
                "gpu": False,
                "cuda": False,
                "audio_input": False,
                "audio_output": False,
                "display": True,
                "network": True,
            },
        },
        "inference": {
            "llm_configured": llm_base_url_configured,
            "hf_token_configured": hf_token_configured,
        },
        "features": {
            "safe_mode": _bool_env("KITSU_SAFE_MODE") or _bool_env("kitsu_SAFE_MODE"),
        },
    }

