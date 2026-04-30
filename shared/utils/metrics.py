"""
infra/metrics.py

Lightweight in-process metrics for Kitsu.
No external dependencies. Counters and timers only.
"""

from __future__ import annotations
import time
from collections import defaultdict
from typing import Optional


class _Metrics:
    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._timings: dict[str, list[float]] = defaultdict(list)

    def increment(self, key: str, amount: int = 1) -> None:
        self._counters[key] += amount

    def record_time(self, key: str, seconds: float) -> None:
        self._timings[key].append(seconds)
        if len(self._timings[key]) > 1000:
            self._timings[key] = self._timings[key][-500:]

    def get_counter(self, key: str) -> int:
        return self._counters[key]

    def get_avg_time(self, key: str) -> Optional[float]:
        samples = self._timings.get(key)
        if not samples:
            return None
        return sum(samples) / len(samples)

    def snapshot(self) -> dict:
        return {
            "counters": dict(self._counters),
            "avg_timings": {
                k: sum(v) / len(v) for k, v in self._timings.items() if v
            },
        }

    def reset(self) -> None:
        self._counters.clear()
        self._timings.clear()


class _Timer:
    """Context manager for recording elapsed time."""

    def __init__(self, metrics: _Metrics, key: str) -> None:
        self._metrics = metrics
        self._key = key
        self._start: float = 0.0

    def __enter__(self) -> "_Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        elapsed = time.perf_counter() - self._start
        self._metrics.record_time(self._key, elapsed)


# Module-level singleton
metrics = _Metrics()


def timer(key: str) -> _Timer:
    """Usage: with timer('fast_brain.query'): ..."""
    return _Timer(metrics, key)