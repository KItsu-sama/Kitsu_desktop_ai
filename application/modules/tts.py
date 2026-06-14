"""application.modules.tts

Text-to-Speech - async queue (safe stub).

Design note (async TTS queue):
- Create an asyncio.Queue of utterances.
- Subscribe to RESPONSE_READY; enqueue the response text.
- A worker task consumes the queue sequentially.
- Throttle/skip policy:
  - if new response arrives, we keep them all (safe stub).
  - later we can implement cancellation/preemption.

This is stub-only; it does not call a real TTS engine yet.
Instead it:
- logs what would be spoken
- emits TTS_UTTERANCE_READY with the text

Failure categories:
- If queue operations fail, categorize as CPU/MEMORY.
- If later a real engine is added, wrap those exceptions with
  failure_categorizer.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from ..core.event_bus import bus
from ..core.subscriptions import register

logger = logging.getLogger("tts")


@dataclass
class TTSItem:
    ctx_id: Any
    text: str
    created_at: float


_queue: asyncio.Queue[TTSItem] = asyncio.Queue()
_worker_task: Optional[asyncio.Task] = None


async def _ensure_worker() -> None:
    global _worker_task
    if _worker_task is not None and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_tts_worker())


async def _tts_worker() -> None:
    while True:
        item = await _queue.get()
        try:
            logger.info("TTS stub speaking ctx_id=%s text=%r", item.ctx_id, item.text[:120])
            await bus.emit(
                "TTS_UTTERANCE_READY",
                {"ctx_id": item.ctx_id, "text": item.text, "created_at": item.created_at},
            )
            # Stub "playback duration" estimate
            await asyncio.sleep(min(2.5, max(0.6, len(item.text) / 220.0)))
        except Exception:
            logger.exception("TTS worker failed")
        finally:
            _queue.task_done()


async def on_response_ready(ctx: Any) -> None:

    try:
        await _ensure_worker()
        text = getattr(ctx, "response", None) or ""
        if not text.strip():
            return
        item = TTSItem(ctx_id=getattr(ctx, "id", None), text=text, created_at=time.time())
        await _queue.put(item)
        logger.debug("TTS enqueued ctx_id=%s queue_size=%d", item.ctx_id, _queue.qsize())
    except Exception:
        logger.exception("TTS enqueue failed")

