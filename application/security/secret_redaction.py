from __future__ import annotations

from typing import Any


_DEFAULT_SECRET_KEYS = {
    "api_key",
    "apikey",
    "token",
    "bearer",
    "authorization",
    "hf_token",
    "hftoken",
    "llm_api_key",
    "openai_api_key",
    "huggingfacehub_api_token",
    "huggingface_api_token",
    "secret",
    "password",
}


def _is_probably_secret_key(key: str, secrets_keys: set[str] | None) -> bool:
    lk = key.strip().lower()
    if secrets_keys and lk in {s.lower() for s in secrets_keys}:
        return True
    return lk in _DEFAULT_SECRET_KEYS


def redact_secrets(data: Any, *, secrets_keys: set[str] | None = None, redaction: str = "[REDACTED]") -> Any:
    """Recursively redact secret-like values.

    - Redacts values when the *key name* matches typical secret key patterns.
    - Leaves other values untouched.

    Intended for logs/status payloads only.
    """

    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(k, str) and _is_probably_secret_key(k, secrets_keys):
                out[k] = redaction
            else:
                out[k] = redact_secrets(v, secrets_keys=secrets_keys, redaction=redaction)
        return out

    if isinstance(data, list):
        return [redact_secrets(x, secrets_keys=secrets_keys, redaction=redaction) for x in data]

    return data

