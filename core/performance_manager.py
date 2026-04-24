from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.contracts import ModuleContract
from core.events import EventBus, EventType, EventPayload
from core.clocks import ClockService
from core.bus import MessageBus, BusTimeout

logger = logging.getLogger('kitsu.core.performance_manager')


class PerformanceManager(ModuleContract):
    module_id = 'core.performance_manager'
    required_flags = []

    def __init__(self, event_bus: EventBus, message_bus: MessageBus, clock_service: ClockService) -> None:
        self.event_bus = event_bus
        self.message_bus = message_bus
        self.clock_service = clock_service
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        self._task = self.clock_service.schedule_recurring(10000, self._check_pressure)
        return True

    async def stop(self) -> bool:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        return True

    async def health_check(self) -> 'HealthStatus':
        from core.health import HealthStatus
        return HealthStatus(module_id=self.module_id, ok=True, latency_ms=0.0)

    async def _check_pressure(self) -> None:
        try:
            import psutil
            memory = psutil.virtual_memory()
            ram_pct = memory.percent  # This is the used memory percentage
            cpu_pct = psutil.cpu_percent(interval=None)
        except ImportError:
            logger.debug('psutil is unavailable for performance polling')
            return

        if ram_pct > 85 or cpu_pct > 90:
            self.event_bus.publish(
                EventPayload(
                    event_type=EventType.PERFORMANCE_PRESSURE,
                    source='core.performance_manager',
                    data={'ram_pct': ram_pct, 'cpu_pct': cpu_pct}
                )
            )
            try:
                await self.message_bus.request('model_manager.unload', {'reason': 'pressure'})
            except BusTimeout:
                logger.warning('Unload request timed out')
