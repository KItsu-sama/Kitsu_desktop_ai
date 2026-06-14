"""application.modules.personality_real_time

Real-time personality change integration.

Design note:
- The existing personality_integration updates personality only AFTER a
  RESPONSE_READY event.
- To support "change personality in real time", we also update during
  generation by listening to streaming chunks or filtered events.

Implementation approach (safe, non-invasive):
- Subscribe to RESPONSE_STREAM (chunk events) and apply lightweight
  updates on chunk boundaries.
- Throttle updates to avoid CPU overload.
- Use judge/heuristics where available; otherwise use incremental text.

This module is implemented as best-effort; if events/ctx attrs don't
exist, it will degrade gracefully.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from ..core.event_bus import bus
from ..core.subscriptions import register

logger = logging.getLogger("personality.real_time")


# Try to import the global personality context from personality_integration.
try:
    from .personality_integration import personality
except Exception:  # pragma: no cover
    personality = None


class _ThrottledUpdater:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_update_ts: float = 0.0
        self.min_interval_seconds: float = 0.35

    async def maybe_update(self, user_input: str | None, partial_assistant: str, full_seen: bool = False) -> None:
        if personality is None:
            return

        now = time.time()
        if (now - self._last_update_ts) < self.min_interval_seconds and not full_seen:
            return

        async with self._lock:
            now = time.time()
            if (now - self._last_update_ts) < self.min_interval_seconds and not full_seen:
                return

            # Update emotion engine based on what we have so far.
            # We call process_interaction_context with partial assistant content.
            # If the emotion engine expects full responses, this still yields
            # a "direction" update, then personality_integration will finalize
            # after RESPONSE_READY.
            try:
                if user_input:
                    personality.emotion.process_interaction_context(user_input, partial_assistant)
                    self._last_update_ts = now
                    logger.debug("personality real-time updated")
            except Exception:
                logger.exception("personality real-time update failed")


_updater = _ThrottledUpdater()


async def on_response_stream(payload: dict):
    """Receive streamed chunks; periodically update personality."""

    try:
        ctx = payload.get("ctx")
        if ctx is None:
            # Some implementations stream without ctx; fallback to id-based map
            return
    except Exception:
        return

    try:
        chunk = payload.get("chunk", "") or ""
        done = bool(payload.get("done", False))
        if not chunk:
            if done:
                # final update with empty chunk shouldn't happen; ignore
                pass
            return

        user_input = getattr(ctx, "original_text", None) or getattr(ctx, "text", None)
        # We don't have full accumulated assistant text here; we update
        # using the chunk content.
        await _updater.maybe_update(user_input=user_input, partial_assistant=chunk, full_seen=done)
    except Exception:
        logger.exception("on_response_stream personality update failed")

