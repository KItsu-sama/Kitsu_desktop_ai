from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict

from core.contracts import ModuleContract
from core.events import EventBus, EventType, EventPayload
from core.orchestrator import Orchestrator
from core.clocks import ClockService

logger = logging.getLogger('kitsu.core.health')


@dataclass
class HealthStatus:
    module_id: str
    ok: bool
    latency_ms: float
    detail: str | None = None


class HealthMonitor(ModuleContract):
    module_id = 'core.health'
    required_flags = []

    def __init__(self, event_bus: EventBus, orchestrator: Orchestrator, clock_service: ClockService) -> None:
        self.event_bus = event_bus
        self.orchestrator = orchestrator
        self.clock_service = clock_service
        self._history: Dict[str, list[HealthStatus]] = {}
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        self._task = self.clock_service.schedule_recurring(30000, self._run_health_cycle)
        return True

    async def stop(self) -> bool:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        return True

    async def health_check(self) -> HealthStatus:
        return HealthStatus(module_id=self.module_id, ok=True, latency_ms=0.0)

    async def _run_health_cycle(self) -> None:
        # Get health status from all registered modules
        summary = {}
        for module_id in self.orchestrator._modules:
            module = self.orchestrator.get_module(module_id)
            if module:
                try:
                    status = await module.health_check()
                    summary[module_id] = status
                except Exception as exc:
                    logger.exception('Health check failed for %s', module_id)
                    summary[module_id] = HealthStatus(module_id=module_id, ok=False, detail=str(exc))
        
        for module_id, status in summary.items():
            history = self._history.setdefault(module_id, [])
            history.append(status)
            if len(history) > 5:
                history.pop(0)
            failures = sum(1 for entry in history[-3:] if not (getattr(entry, 'ok', entry.get('ok', True) if isinstance(entry, dict) else True)))
            if failures >= 3:
                logger.warning('Health degradation detected for %s', module_id)
                self.event_bus.publish(
                    EventPayload(
                        event_type=EventType.HEALTH_CHECK_FAILED,
                        source='core.health',
                        data={'module_id': module_id, 'detail': getattr(status, 'detail', None)}
                    )
                )

    def get_summary(self) -> Dict[str, HealthStatus]:
        return {module_id: history[-1] for module_id, history in self._history.items() if history}
