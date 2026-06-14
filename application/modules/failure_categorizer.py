"""application.modules.failure_categorizer

Central place to categorize failures for logging + ops.

Failure Categories:
- MEMORY
- CPU
- MODEL
- NETWORK
- FILESYSTEM
- PERMISSION
- DEPENDENCY
- TIMEOUT

Usage:
    from application.modules.failure_categorizer import categorize_exception
    category, details = categorize_exception(exc)
"""

from __future__ import annotations

import asyncio
import errno
import os
import socket
import traceback
from dataclasses import dataclass
from typing import Any, Optional, Tuple


CATEGORIES = {
    "MEMORY",
    "CPU",
    "MODEL",
    "NETWORK",
    "FILESYSTEM",
    "PERMISSION",
    "DEPENDENCY",
    "TIMEOUT",
}


@dataclass(frozen=True)
class FailureInfo:
    category: str
    summary: str
    details: str


def _is_permission_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if isinstance(exc, PermissionError):
        return True
    return "permission" in msg or "access denied" in msg


def _is_filesystem_error(exc: BaseException) -> bool:
    return isinstance(exc, (FileNotFoundError, OSError))


def _is_timeout_error(exc: BaseException) -> bool:
    return isinstance(exc, (asyncio.TimeoutError, TimeoutError))


def _is_network_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if isinstance(exc, (ConnectionError, socket.error)):
        return True
    return any(
        s in msg
        for s in (
            "connection refused",
            "connection reset",
            "broken pipe",
            "timed out",
            "failed to establish",
            "cannot connect",
            "network is unreachable",
        )
    )


def _is_dependency_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "importerror" in msg or "module" in msg or "not found" in msg


def _is_memory_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if isinstance(exc, MemoryError):
        return True
    return any(s in msg for s in ("out of memory", "malloc", "memoryerror"))


def _is_cpu_overload_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in ("cpu", "overload", "too many computations"))


def _is_model_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in ("ollama", "model", "inference", "generate", "llm"))


def categorize_exception(exc: BaseException, fallback: str = "MODEL") -> Tuple[str, str, str]:
    """Return (category, summary, details).

    The categorization is best-effort and intentionally conservative.
    """
    category = fallback

    if _is_timeout_error(exc):
        category = "TIMEOUT"
    elif _is_permission_error(exc):
        category = "PERMISSION"
    elif _is_filesystem_error(exc):
        category = "FILESYSTEM"
    elif _is_memory_error(exc):
        category = "MEMORY"
    elif _is_cpu_overload_error(exc):
        category = "CPU"
    elif _is_network_error(exc):
        category = "NETWORK"
    elif _is_dependency_error(exc):
        category = "DEPENDENCY"
    elif _is_model_error(exc):
        category = "MODEL"

    summary = f"{exc.__class__.__name__}: {str(exc)[:180]}"
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return category, summary, details

