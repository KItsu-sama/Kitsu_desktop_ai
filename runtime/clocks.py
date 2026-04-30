from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger('kitsu.core.clocks')

TickCallback = Callable[[], Awaitable[None]]
TimeProvider = Callable[[], float]


class ClockService:
    module_id = 'core.clocks'
    required_flags: list[str] = []

    def __init__(self, time_provider: Optional[TimeProvider] = None) -> None:
        self._time_provider = time_provider or time.monotonic
        self._tasks: list[asyncio.Task[Any]] = []

    async def start(self) -> bool:
        return True

    async def stop(self) -> bool:
        await self.shutdown()
        return True

    async def health_check(self) -> 'HealthStatus':
        from runtime.health import HealthStatus
        return HealthStatus(module_id=self.module_id, ok=True, latency_ms=0.0)

    def monotonic(self) -> float:
        return self._time_provider()

    def schedule_recurring(self, interval_ms: int, callback: TickCallback) -> asyncio.Task[Any]:
        task = asyncio.create_task(self._run_loop(interval_ms / 1000.0, callback), name=f'clock-{interval_ms}')
        self._tasks.append(task)
        return task

    async def _run_loop(self, interval_s: float, callback: TickCallback) -> None:
        while True:
            start = self.monotonic()
            try:
                await callback()
            except Exception:
                logger.exception('Scheduled callback failed')
            await asyncio.sleep(max(0.0, interval_s - (self.monotonic() - start)))

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()


def debounce(delay_ms: int, callback: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    timer: asyncio.Task[Any] | None = None

    async def wrapper(*args: Any, **kwargs: Any) -> None:
        nonlocal timer
        if timer is not None:
            timer.cancel()
        async def delayed() -> None:
            await asyncio.sleep(delay_ms / 1000.0)
            await callback(*args, **kwargs)
        timer = asyncio.create_task(delayed())

    return wrapper


def throttle(interval_ms: int, callback: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    last_run = 0.0

    async def wrapper(*args: Any, **kwargs: Any) -> None:
        nonlocal last_run
        now = time.monotonic()
        if now - last_run < interval_ms / 1000.0:
            return
        last_run = now
        await callback(*args, **kwargs)

    return wrapper
