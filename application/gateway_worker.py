"""Single async worker thread for the HTTP gateway chat pipeline."""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class GatewayWorker:
    """Single async worker thread that the HTTP gateway offloads chat requests to."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._pipeline_initialized = False

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="gateway-worker")
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            raise RuntimeError("GatewayWorker failed to start within 5 seconds")

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    def _ensure_pipeline_initialized(self) -> None:
        if self._pipeline_initialized or self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(
            _init_gateway_pipeline(),
            self._loop,
        )
        future.result(timeout=30.0)
        self._pipeline_initialized = True

    def submit(self, coro) -> Any:
        """Submit a coroutine from any thread; block until done. Returns result or raises."""
        if self._loop is None:
            raise RuntimeError("GatewayWorker not started")
        self._ensure_pipeline_initialized()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=35.0)


async def _init_gateway_pipeline() -> None:
    from application.core.event_bus import bus
    from application.main import ensure_pipeline_modules_loaded, get_request_bridge

    ensure_pipeline_modules_loaded()
    if not bus.is_running():
        await bus.start()
    await get_request_bridge().ensure_registered()


_worker = GatewayWorker()


def get_worker() -> GatewayWorker:
    return _worker
