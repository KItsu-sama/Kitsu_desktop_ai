"""
src/kitsu/main.py

Entry point for the modern Kitsu pipeline.

Flow:
  stdin → RAW_INPUT → InputMux → INPUT_RECEIVED → Preprocess → Router
       → [REFLEX|SLM|LLM]_PATH → … → RESPONSE_READY → display → RESPONSE_SENT

ChatApp holds a per-request Future keyed by ctx.id.
The RESPONSE_READY subscriber resolves it.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict

# Ensure src/ is importable when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

# ── Optional splash ───────────────────────────────────────────────────────────
try:
    from kitsu.splash import ModernSplash
    _SPLASH_AVAILABLE = True
except ImportError:
    _SPLASH_AVAILABLE = False

# ── Register all pipeline modules ────────────────────────────────────────────
# Import order = subscription order; keep stable.
import kitsu.modules.input_mux      # RAW_INPUT → INPUT_RECEIVED
import kitsu.modules.preprocess     # INPUT_RECEIVED → PREPROCESS_DONE
import kitsu.modules.router         # PREPROCESS_DONE → *_PATH
import kitsu.modules.reflex         # REFLEX_PATH → RESPONSE_READY
import kitsu.modules.slm            # SLM_PATH → RESPONSE_READY | LLM_PATH
import kitsu.modules.llm            # LLM_PATH → RESPONSE_READY
import kitsu.modules.memory         # RESPONSE_SENT (async, learning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("kitsu.main")


class ChatApp:
    """
    Terminal chat front-end.

    Sends user input as RAW_INPUT, waits for RESPONSE_READY via a Future,
    then fires RESPONSE_SENT so the memory module can learn.
    """

    def __init__(self) -> None:
        self._pending: Dict[str, asyncio.Future] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── RESPONSE_READY subscriber ─────────────────────────────────────────

    async def _on_response_ready(self, ctx: RequestContext) -> None:
        future = self._pending.get(ctx.id)
        if future and not future.done():
            future.set_result(ctx)

    # ── Main loop ─────────────────────────────────────────────────────────

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()

        if _SPLASH_AVAILABLE:
            ModernSplash().display_splash()
        else:
            print("\n🦊 Kitsu AI — type a message, 'exit' to quit.\n")

        # Subscribe once
        bus.subscribe("RESPONSE_READY", self._on_response_ready)

        while True:
            try:
                raw = await self._loop.run_in_executor(None, sys.stdin.readline)
                raw = raw.rstrip("\n")
            except (EOFError, KeyboardInterrupt):
                break

            if not raw.strip():
                continue

            if raw.strip().lower() in ("exit", "quit", "q"):
                print("Goodbye! 🦊")
                break

            await self._handle(raw)

    async def _handle(self, raw: str) -> None:
        # Reserve a Future for this request.
        # We need the ctx.id before InputMux creates it — so we create a
        # temporary placeholder Future keyed by a sentinel, then use the
        # real id once InputMux emits INPUT_RECEIVED.
        #
        # Simpler approach: create the ctx HERE and emit RAW_INPUT with it
        # directly so we know the id upfront.
        ctx = RequestContext(text=raw.strip(), original_text=raw)
        future: asyncio.Future[RequestContext] = self._loop.create_future()
        self._pending[ctx.id] = future

        # Emit INPUT_RECEIVED directly (bypassing InputMux normalization for
        # the main chat path so we keep the id we registered).
        # InputMux normalization already happened conceptually — raw text from
        # stdin is already normalized (stripped, single-line).
        await bus.emit("INPUT_RECEIVED", ctx)

        try:
            result_ctx = await asyncio.wait_for(future, timeout=10.0)
            response = result_ctx.response or "(no response)"
        except asyncio.TimeoutError:
            response = "(timed out — no response within 10 s)"
            result_ctx = ctx

        print(f"\nKitsu: {response}\n")

        # Fire RESPONSE_SENT so memory module can learn
        from kitsu.modules.judge import judge
        score = 0.0
        if result_ctx.response:
            j = judge(result_ctx.response, result_ctx.text, result_ctx.vibe, result_ctx.mode)
            score = j.confidence(result_ctx.mode)

        await bus.emit("RESPONSE_SENT", {"ctx": result_ctx, "judge_score": score})

        # Cleanup
        self._pending.pop(ctx.id, None)


# ── Entry point ───────────────────────────────────────────────────────────────

async def _main() -> None:
    await ChatApp().run()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    app = ChatApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        pass
