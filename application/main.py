"""
application/main.py

Entry point for the modern Kitsu pipeline.

Flow:
  stdin → RAW_INPUT → InputMux → INPUT_RECEIVED → Preprocess → Router
       → [REFLEX|SLM|LLM]_PATH → … → RESPONSE_READY → display → RESPONSE_SENT

User types: "hello"
  ↓ (0ms)
ChatApp: ctx = RequestContext(id="abc123", text="hello")
  ↓ (1ms)
await bus.emit("INPUT_RECEIVED", ctx)
  ↓ (2ms)
input_mux: RAW_INPUT → INPUT_RECEIVED (normalized)
  ↓ (7ms)
preprocess: SimHash + vibe → PREPROCESS_DONE
  ↓ (9ms)
router: complexity=0.1 → REFLEX_PATH
  ↓ (15ms)
reflex: cache hit → RESPONSE_READY(ctx.response="Hey! 😊")
  ↓ (16ms)
ChatApp._on_response_ready(): future.set_result(ctx)
  ↓ (16ms)
await future → "Hey! 😊" (displayed)
  ↓ (20ms)
RESPONSE_SENT → memory.learn() (async, non-blocking)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

# Ensure application package root and project root are importable
APP_ROOT = Path(__file__).parent
PROJECT_ROOT = APP_ROOT.parent
for path in (str(APP_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from .core.event_bus import bus
from .core.context import RequestContext

# ── Optional splash ───────────────────────────────────────────────────────────
try:
    from .splash import Splash  # deleted -> use application.terminal_ui
    _SPLASH_AVAILABLE = True
except ImportError:
    _SPLASH_AVAILABLE = False

# ── Register all pipeline modules ────────────────────────────────────────────
# Import order = subscription order; keep stable.
from .modules import input_mux  # RAW_INPUT → INPUT_RECEIVED
from .modules import preprocess  # INPUT_RECEIVED → PREPROCESS_DONE
from .modules import router  # PREPROCESS_DONE → *_PATH
from .modules import reflex  # REFLEX_PATH → RESPONSE_READY
from .modules import system_state_reflex  # early intercept small-talk direct snapshot
from .modules import slm  # SLM_PATH → RESPONSE_READY | LLM_PATH
from .modules import llm  # LLM_PATH → RESPONSE_READY | RESPONSE_STREAM
from .modules import memory  # RESPONSE_SENT (async, learning)

logger = logging.getLogger("main")

_PIPELINE_MODULES_LOADED = False
_request_bridge: Optional["RequestBridge"] = None


def ensure_pipeline_modules_loaded() -> None:
    """Import pipeline modules so their bus subscriptions register."""
    global _PIPELINE_MODULES_LOADED
    if _PIPELINE_MODULES_LOADED:
        return
    # Import order = subscription order; keep stable.
    from .modules import input_mux  # noqa: F401
    from .modules import preprocess  # noqa: F401
    from .modules import router  # noqa: F401
    from .modules import reflex  # noqa: F401
    from .modules import system_state_reflex  # noqa: F401
    from .modules import slm  # noqa: F401
    from .modules import llm  # noqa: F401
    from .modules import memory  # noqa: F401
    _PIPELINE_MODULES_LOADED = True


class RequestBridge:
    """Correlate RAW_INPUT requests to RESPONSE_READY via per-id Futures."""

    def __init__(self) -> None:
        self._pending: Dict[str, asyncio.Future] = {}
        self._registered = False

    async def ensure_registered(self) -> None:
        if self._registered:
            return
        from .core.subscriptions import register

        register("RESPONSE_READY", self._on_response_ready)
        self._registered = True

    async def _on_response_ready(self, ctx) -> None:
        rid = getattr(ctx, "id", None)
        if rid is None:
            return
        future = self._pending.get(rid)
        if future and not future.done():
            future.set_result(ctx)

    async def submit(
        self,
        text: str,
        *,
        original_text: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
    ) -> RequestContext:
        ensure_pipeline_modules_loaded()
        await self.ensure_registered()

        if not bus.is_running():
            await bus.start()

        if ctx is None:
            ctx = RequestContext(text=text, original_text=original_text or text)
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[ctx.id] = future
        try:
            await bus.emit("RAW_INPUT", ctx)
            return await asyncio.wait_for(future, timeout=30.0)
        finally:
            self._pending.pop(ctx.id, None)


def get_request_bridge() -> RequestBridge:
    global _request_bridge
    if _request_bridge is None:
        _request_bridge = RequestBridge()
    return _request_bridge


async def submit_request(
    text: str,
    *,
    original_text: Optional[str] = None,
    ctx: Optional[RequestContext] = None,
) -> RequestContext:
    """Submit chat text through the pipeline and wait for RESPONSE_READY."""
    return await get_request_bridge().submit(text, original_text=original_text, ctx=ctx)


class ChatApp:
    """Terminal chat front-end.


    Also intercepts in-band slash commands (e.g. /debug, /h, /compress)
    and routes them via application/commands/command_router.py.


    Sends user input as RAW_INPUT, waits for a single RESPONSE_READY via a
    Future, then fires RESPONSE_SENT.

    Streaming is intentionally removed for now.
    """

    def __init__(self) -> None:
        self._bridge = get_request_bridge()
        self._loop: asyncio.AbstractEventLoop
        self._history: list[Dict] = []
        self._ctxs: Dict[str, RequestContext] = {}
        self._streaming_ids: set[str] = set()

    async def _on_stream_chunk(self, payload) -> None:
        """Handle incremental stream chunks for an inflight request.

        Expects payload to be a dict with keys: 'id', 'chunk', 'done'.
        Appends chunk text to the stored RequestContext and prints it.
        """
        try:
            if not isinstance(payload, dict):
                return

            rid = payload.get("id")
            if rid is None:
                return

            ctx = self._ctxs.get(rid)
            if not ctx:
                return

            chunk = payload.get("chunk", "") or ""
            done = bool(payload.get("done", False))

            if getattr(ctx, "response", None) is None:
                ctx.response = ""

            if rid not in self._streaming_ids:
                self._streaming_ids.add(rid)
                print(f"\n✨ Kitsu: ", end="", flush=True)

            ctx.response += chunk

            if chunk:
                print(chunk, end="", flush=True)

            if done:
                print()
                self._streaming_ids.discard(rid)
        except Exception:
            logger.exception("_on_stream_chunk failed")

    # ── History Display ───────────────────────────────────────────────────

    def _display_history(self, ctx: RequestContext, score: float) -> None:
        """Display conversation history with confidence score."""
        from .terminal_ui import terminal_print

        history_entry = {
            "user": ctx.text,
            "kitsu": ctx.response or "(no response)",
            "confidence": score,
            "mode": ctx.mode,
            "timestamp": getattr(ctx, "response_timestamp_ns", None),
        }

        self._history.append(history_entry)

        terminal_print(f"\n📋 User: {ctx.text}")
        terminal_print(f"   Kitsu: {ctx.response} [confidence: {score:.1f}]")
        terminal_print()

    # ── Main loop ─────────────────────────────────────────────────────────

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()

        ensure_pipeline_modules_loaded()

        if not bus.is_running():
            await bus.start()

        await self._bridge.ensure_registered()

        if not _SPLASH_AVAILABLE:
            print("\n🦊 Kitsu AI — type a message, 'exit' to quit.\n")

        from .core.subscriptions import register

        register("RESPONSE_STREAM", self._on_stream_chunk)

        try:
            while True:
                try:
                    print("[user] ", end="", flush=True)

                    raw = await self._loop.run_in_executor(None, sys.stdin.readline)
                    raw = raw.rstrip("\n")
                except (EOFError, KeyboardInterrupt):
                    break

                if not raw.strip():
                    continue

                lowered = raw.strip().lower()
                if lowered in ("exit", "quit", "q"):
                    print("Goodbye! 🦊")
                    break

                if lowered in ("history", "h"):
                    self._show_history()
                    continue

                await self._handle(raw)
        finally:
            if bus.is_running():
                await bus.stop()

    def _show_history(self) -> None:
        """Display conversation history."""
        if not self._history:
            print("📭 No conversation history yet.\n")
            return

        print("\n📚 Conversation History:")
        print("-" * 60)
        for i, entry in enumerate(self._history[-10:], 1):
            ts = entry["timestamp"][:16] if entry.get("timestamp") else ""
            print(f"{i:2d}. [{entry['mode'].upper()}] {ts}")
            print(f"   👤  {entry['user']}")
            print(f"   🦊  {entry['kitsu']} [confidence: {entry['confidence']:.1f}]")
            print()
        print()

    async def _handle(self, raw: str) -> None:
        text = raw.strip()
        if text.startswith('/'):
            # In-band command: route via CommandRouter and do not send RAW_INPUT
            try:
                from .commands.command_router import CommandRouter

                # CommandRouter expects a desktop_controller-like object.
                # We try to grab the engine/controller off the running pipeline if present.
                desktop_controller = None
                engine = getattr(self, 'engine', None)
                if engine is not None:
                    desktop_controller = engine
                router = CommandRouter(desktop_controller=desktop_controller)  # type: ignore[arg-type]

                result = await router.route(text)
                output = result.get('output', '')
                if output:
                    print(f"\n{output}")
                return
            except Exception as e:
                print(f"\n❌ Command routing failed: {e}")
                return

        ctx = RequestContext(text=text, original_text=raw)
        self._ctxs[ctx.id] = ctx

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("RAW_INPUT emitted id=%s text=%r", ctx.id, ctx.text)

        try:
            result_ctx = await self._bridge.submit(text, original_text=raw, ctx=ctx)
        except asyncio.TimeoutError:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "TIMEOUT waiting for response for id=%s text=%r",
                    ctx.id,
                    ctx.text,
                )
            result_ctx = ctx

        from .modules.judge import judge

        score = 0.0
        if getattr(result_ctx, "response", None):
            j = judge(result_ctx.response, result_ctx.text, result_ctx.vibe, result_ctx.mode)
            score = j.confidence(result_ctx.mode)

        if logger.isEnabledFor(logging.DEBUG):
            owner = getattr(result_ctx, "response_owner", "")
            trace = getattr(result_ctx, "trace", [])
            trace_tail = trace[-6:] if trace else []
            logger.debug("owner=%r trace_tail=%r", owner, trace_tail)

        self._display_history(result_ctx, score)

        await bus.emit("RESPONSE_SENT", {"ctx": result_ctx, "judge_score": score})

        self._ctxs.pop(ctx.id, None)


# ── Entry point ───────────────────────────────────────────────────────────────

async def _main() -> None:
    await ChatApp().run()


if __name__ == "__main__":
    try:
        from .runtime_error_hooks import install_runtime_error_hooks

        install_runtime_error_hooks()
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)

