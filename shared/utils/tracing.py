"""
infra/tracing.py

Minimal span-based tracing for Kitsu pipeline calls.
No external dependencies. Traces print to the logger at DEBUG level.
Replace with OpenTelemetry later if needed — same API.
"""

from __future__ import annotations
import logging
import time
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger("kitsu.trace")


@contextmanager
def span(name: str, **attrs) -> Generator[None, None, None]:
    """
    Usage:
        with span("fast_brain.query", input_len=len(text)):
            result = engine.query(text)
    """
    start = time.perf_counter()
    attr_str = " ".join(f"{k}={v}" for k, v in attrs.items())
    logger.debug("SPAN START  %s  %s", name, attr_str)
    try:
        yield
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        logger.debug("SPAN ERROR  %s  %.1fms  %s: %s", name, elapsed, type(exc).__name__, exc)
        raise
    else:
        elapsed = (time.perf_counter() - start) * 1000
        logger.debug("SPAN END    %s  %.1fms", name, elapsed)