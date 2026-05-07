from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict

from domain.contracts.contracts import ModuleContract
from runtime.events import EventBus, EventType, EventPayload
from runtime.orchestrator import Orchestrator
from runtime.clocks import ClockService

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
                    # Debug log the health status
                    if isinstance(status, dict):
                        logger.debug('Health status for %s: ok=%s, details=%s', module_id, status.get('ok', True), {k:v for k,v in status.items() if k != 'ok'})
                    else:
                        logger.debug('Health status for %s: ok=%s, detail=%s', module_id, getattr(status, 'ok', True), getattr(status, 'detail', None))
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
                # Get meaningful reason for failure
                if isinstance(status, dict):
                    # Handle dictionary-based health status
                    if not status.get('ok', True):
                        reason = status.get('detail', 'Health check returned false')
                        # If no detail, try to infer from available data
                        if reason == 'Health check returned false':
                            if status.get('healthy_modules', 0) < status.get('module_count', 1):
                                failed_count = status.get('failed_modules', 0)
                                reason = f'{failed_count} module(s) failed'
                            elif 'legacy_subsystems' in status:
                                failed_legacy = [name for name, healthy in status['legacy_subsystems'].items() if not healthy]
                                if failed_legacy:
                                    reason = f'Legacy subsystems failed: {", ".join(failed_legacy)}'
                            else:
                                reason = 'System health check failed'
                    else:
                        reason = 'Health status inconsistent'
                else:
                    # Handle HealthStatus objects
                    reason = getattr(status, 'detail', 'Health check returned false')
                
                logger.warning('Health degradation detected for %s — reason: %s', module_id, reason)
                self.event_bus.publish(
                    EventPayload(
                        event_type=EventType.HEALTH_CHECK_FAILED,
                        source='core.health',
                        data={'module_id': module_id, 'detail': reason}
                    )
                )

    def get_summary(self) -> Dict[str, HealthStatus]:
        return {module_id: history[-1] for module_id, history in self._history.items() if history}

    def get_status(self) -> Dict[str, any]:
        """Get comprehensive system status for dashboard."""
        summary = self.get_summary()
        
        # Count running vs failed modules
        running = sum(1 for status in summary.values() if getattr(status, 'ok', True))
        total = len(summary)
        
        # Mock data for now - would integrate with actual modules
        status_data = {
            "personality": getattr(self, '_personality_status', 'playful/happy (0.8)'),
            "ai_tier": getattr(self, '_ai_tier_status', 'SLM (4GB VRAM used)'),
            "memory_usage": getattr(self, '_memory_status', '6.2/16GB (39%)'),
            "modules": f"{running}/{total} running",
            "resources": getattr(self, '_resource_status', 'CPU: 23% │ GPU: 67%'),
            "module_details": {
                module_id: {
                    "ok": getattr(status, 'ok', True),
                    "detail": getattr(status, 'detail', None),
                    "latency_ms": getattr(status, 'latency_ms', 0.0)
                }
                for module_id, status in summary.items()
            }
        }
        
        return status_data
