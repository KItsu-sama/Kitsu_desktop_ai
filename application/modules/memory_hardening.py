"""application.modules.memory_hardening

Runnable memory facade + hardening.

Design:
- Provide simple synchronous timeouts / bounded IO for short-term memory.
- Support retrieval as a sliding window by default.

Memory retrieval strategy clarification (per request):
- Default: sliding window (last N items) with naive text overlap scoring.
- Embedding search: intentionally NOT implemented yet (needs model + vector store).

This module is written to be safe and to log categorized failures.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .failure_categorizer import categorize_exception

logger = logging.getLogger("memory.hardening")


@dataclass(frozen=True)
class MemoryRetrievalConfig:
    persistence_path: str = "data/memory/short_term_memory.json"
    max_items: int = 200
    top_k: int = 5
    retrieval_timeout_seconds: float = 0.08


class SimpleSlidingWindowRetriever:
    """Sliding window + naive overlap scoring.

    If the underlying memory store already implements `search`, we can
    call into it later. For now, we keep a runtime buffer in-memory and
    fall back if persistence layer isn't accessible.
    """

    def __init__(self, cfg: MemoryRetrievalConfig | None = None) -> None:
        self.cfg = cfg or MemoryRetrievalConfig()
        self._buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        # Placeholder for future persistence load.
        return

    async def store_turn(self, key: str, item: Dict[str, Any]) -> None:
        async with self._lock:
            self._buffer.append({"key": key, **item})
            if len(self._buffer) > self.cfg.max_items:
                self._buffer = self._buffer[-self.cfg.max_items :]

    def _score(self, query: str, text: str) -> float:
        q = (query or "").lower().strip()
        t = (text or "").lower()
        if not q or not t:
            return 0.0

        # naive: token overlap
        q_tokens = set(q.split())
        if not q_tokens:
            return 0.0

        t_tokens = set(t.split())
        overlap = len(q_tokens.intersection(t_tokens))
        return min(overlap / max(len(q_tokens), 1), 1.0)

    async def retrieve(self, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        top_k = top_k or self.cfg.top_k
        async with self._lock:
            items = list(self._buffer)

        # Score against (user + assistant) concatenation.
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for it in items:
            text = " ".join(
                [
                    str(it.get("user", "")),
                    str(it.get("assistant", "")),
                    str(it.get("response", "")),
                ]
            )
            scored.append((self._score(query, text), it))

        scored.sort(key=lambda x: x[0], reverse=True)
        # If all scores are 0, just return most recent window.
        if scored and scored[0][0] <= 0.0:
            return items[-top_k:]
        return [it for _, it in scored[:top_k]]


retriever = SimpleSlidingWindowRetriever()


async def memory_store_turn(key: str, item: Dict[str, Any]) -> None:
    try:
        await asyncio.wait_for(retriever.store_turn(key, item), timeout=0.25)
    except Exception as exc:
        category, summary, details = categorize_exception(exc, fallback="FILESYSTEM")
        logger.error("MEMORY_STORE_FAIL category=%s summary=%s", category, summary)
        logger.debug("details=%s", details)


async def memory_retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    try:
        return await asyncio.wait_for(retriever.retrieve(query, top_k=top_k), timeout=retriever.cfg.retrieval_timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning("MEMORY_RETRIEVE_TIMEOUT")
        return []
    except Exception as exc:
        category, summary, details = categorize_exception(exc, fallback="MEMORY")
        logger.error("MEMORY_RETRIEVE_FAIL category=%s summary=%s", category, summary)
        logger.debug("details=%s", details)
        return []


async def memory_initialize() -> None:
    try:
        await retriever.initialize()
    except Exception:
        logger.exception("memory_initialize failed")

