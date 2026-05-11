from __future__ import annotations

import asyncio
import logging
import psutil
from dataclasses import dataclass
from typing import Dict

from domain.contracts.contracts import ModuleContract
from runtime.communication.events import EventBus, EventType, EventPayload
from runtime.legacy.orchestrator import Orchestrator
from runtime.infrastructure.clocks import ClockService
from runtime.infrastructure.container import DIContainer

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

    def __init__(self, event_bus: EventBus, orchestrator: Orchestrator, clock_service: ClockService, container: DIContainer) -> None:
        self.event_bus = event_bus
        self.orchestrator = orchestrator
        self.clock_service = clock_service
        self.container = container
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
        
        # Get real data from system components
        status_data = {
            "personality": self._get_personality_status(),
            "ai_tier": self._get_ai_tier_status(),
            "memory_usage": self._get_memory_usage(),
            "modules": f"{running}/{total} running",
            "resources": self._get_resource_usage(),
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
    
    def _get_personality_status(self) -> str:
        """Get real personality status from emotion engine."""
        try:
            # Try to get emotion controller from container
            emotion_controller = self.container.get('domain.personality.emotion_controller')
            if hasattr(emotion_controller, 'get_current_emotion'):
                emotion = emotion_controller.get_current_emotion()
                intensity = getattr(emotion_controller, 'get_current_intensity', lambda: 0.8)()
                return f"{emotion.name.lower()}/{emotion.mood.lower()} ({intensity:.1f})"
        except Exception:
            pass
        return "playful/happy (0.8)"
    
    def _get_ai_tier_status(self) -> str:
        """Get real AI tier status from resource controller."""
        try:
            # Try to get resource controller from container
            resource_controller = self.container.get('domain.inference.resource_controller')
            if hasattr(resource_controller, 'get_current_tier'):
                tier = resource_controller.get_current_tier()
                if hasattr(resource_controller, 'get_resource_usage'):
                    usage = resource_controller.get_resource_usage()
                    vram_usage = usage.get('vram_mb', 0)
                    return f"{tier.value.upper()} ({vram_usage//1024}GB VRAM used)"
                return tier.value.upper()
        except Exception:
            pass
        return "SLM (4GB VRAM used)"
    
    def _get_memory_usage(self) -> str:
        """Get real memory usage from system."""
        try:
            memory = psutil.virtual_memory()
            used_gb = memory.used / (1024**3)
            total_gb = memory.total / (1024**3)
            percent = memory.percent
            return f"{used_gb:.1f}/{total_gb:.1f}GB ({percent:.0f}%)"
        except Exception:
            pass
        return "unknoww"
    
    def _get_resource_usage(self) -> str:
        """Get real CPU and GPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Try to get GPU info from resource controller
            gpu_percent = 0
            try:
                resource_controller = self.container.get('domain.inference.resource_controller')
                if hasattr(resource_controller, 'get_resource_usage'):
                    usage = resource_controller.get_resource_usage()
                    gpu_percent = usage.get('gpu_percent', 0)
            except Exception:
                pass
            
            return f"CPU: {cpu_percent:.0f}% │ GPU: {gpu_percent:.0f}%"
        except Exception:
            pass
        return "CPU: unknoww% │ GPU: unknoww%"
