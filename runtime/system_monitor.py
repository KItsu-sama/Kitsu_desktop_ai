"""
core/system_monitor.py

System health monitoring and performance tracking.
Extracted from orchestrator.py to follow Single Responsibility Principle.

Responsibilities:
- Health check coordination
- Performance monitoring
- Module status tracking
- System metrics collection

Non-responsibilities:
- Application lifecycle (→ application.py)
- Input processing (→ input_manager.py)
- AI routing (→ orchestrator.py)
- Module management (→ orchestrator.py)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

from domain.contracts.contracts import ModuleContract
from runtime.events import EventBus, EventType, EventPayload

logger = logging.getLogger(__name__)


@dataclass
class SystemHealth:
    """System health snapshot."""
    ok: bool
    module_count: int
    healthy_modules: int
    failed_modules: int
    avg_latency_ms: float
    timestamp: float


@dataclass
class ModuleHealth:
    """Individual module health status."""
    module_id: str
    healthy: bool
    started: bool
    last_error: Optional[str]
    latency_ms: float
    last_check: float


class SystemMonitor:
    """
    Monitors system health and performance metrics.
    
    Coordinates health checks across all modules and provides
    unified system health reporting.
    """
    
    def __init__(self, orchestrator, event_bus: EventBus):
        self.orchestrator = orchestrator
        self.event_bus = event_bus
        self._monitoring: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._health_history: list[SystemHealth] = []
        self._max_history_size = 100
    
    async def start_monitoring(self, interval_seconds: float = 5.0) -> None:
        """Start continuous health monitoring."""
        if self._monitoring:
            logger.debug("Health monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
        logger.info("System health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System health monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: float) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                health = await self.collect_system_health()
                self._health_history.append(health)
                
                # Trim history if needed
                if len(self._health_history) > self._max_history_size:
                    self._health_history.pop(0)
                
                # Emit health event (use legacy bus publish for compatibility)
                try:
                    # Try new unified event system first
                    if hasattr(self.event_bus, 'publish'):
                        from runtime.unified_events import UnifiedEvent
                        health_event = UnifiedEvent(
                            event_type="health_check",
                            source="system_monitor",
                            data={
                                'health': health.__dict__,
                                'module_count': health.module_count,
                                'healthy_modules': health.healthy_modules,
                                'failed_modules': health.failed_modules,
                            }
                        )
                        self.event_bus.publish(health_event)
                    else:
                        # Fallback to legacy bus
                        self.event_bus.publish(EventPayload(
                            event_type=EventType.HEALTH_CHECK,
                            source='system_monitor',
                            data={
                                'health': health.__dict__,
                                'module_count': health.module_count,
                                'healthy_modules': health.healthy_modules,
                                'failed_modules': health.failed_modules,
                            }
                        ))
                except Exception as e:
                    logger.debug(f"Failed to emit health event: {e}")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def collect_system_health(self) -> SystemHealth:
        """Collect health status from all modules."""
        start_time = time.time()
        
        module_healths = []
        healthy_count = 0
        failed_count = 0
        
        # Check legacy subsystems
        legacy_status = await self._check_legacy_subsystems()
        for subsystem, status in legacy_status.items():
            module_health = ModuleHealth(
                module_id=f"legacy.{subsystem}",
                healthy=status,
                started=status,  # Assume started if healthy
                last_error=None if status else f"{subsystem} unavailable",
                latency_ms=0.0,
                last_check=time.time()
            )
            module_healths.append(module_health)
            if status:
                healthy_count += 1
            else:
                failed_count += 1
        
        # Check modern modules
        if hasattr(self.orchestrator, '_statuses'):
            for module_id, status in self.orchestrator._statuses.items():
                # Get actual health check if available
                module = self.orchestrator.get_module(module_id)
                latency_ms = 0.0
                
                if module and hasattr(module, 'health_check'):
                    try:
                        health_result = await module.health_check()
                        if isinstance(health_result, dict):
                            status.healthy = health_result.get('ok', True)
                            latency_ms = health_result.get('latency_ms', 0.0)
                        else:
                            status.healthy = bool(health_result)
                    except Exception as e:
                        logger.debug(f"Health check failed for {module_id}: {e}")
                        status.healthy = False
                        status.last_error = str(e)
                
                module_health = ModuleHealth(
                    module_id=module_id,
                    healthy=status.healthy,
                    started=status.started,
                    last_error=status.last_error,
                    latency_ms=latency_ms,
                    last_check=time.time()
                )
                module_healths.append(module_health)
                
                if status.healthy:
                    healthy_count += 1
                else:
                    failed_count += 1
        
        # Calculate average latency
        avg_latency = sum(m.latency_ms for m in module_healths) / len(module_healths) if module_healths else 0.0
        
        # System is healthy if all critical modules are healthy
        # Only require core.orchestrator as essential, legacy subsystems are optional
        critical_modules = ['core.orchestrator']
        critical_healthy = all(
            m.module_id in critical_modules and m.healthy 
            for m in module_healths 
            if m.module_id in critical_modules
        )
        
        # Allow system to be healthy if core modules are working, even if some optional legacy subsystems fail
        optional_failures = [m.module_id for m in module_healths if not m.healthy and m.module_id.startswith('legacy.')]
        system_ok = critical_healthy and (failed_count == 0 or all(f.startswith('legacy.') for f in optional_failures))
        
        return SystemHealth(
            ok=system_ok,
            module_count=len(module_healths),
            healthy_modules=healthy_count,
            failed_modules=failed_count,
            avg_latency_ms=avg_latency,
            timestamp=time.time()
        )
    
    async def _check_legacy_subsystems(self) -> Dict[str, bool]:
        """Check legacy subsystem health."""
        return {
            'fast_brain': getattr(self.orchestrator.fast_brain, 'is_available', lambda: False)() if self.orchestrator.fast_brain else False,
            'slm': await getattr(self.orchestrator.slm, 'is_available', lambda: False)() if self.orchestrator.slm else False,
            'llm': await getattr(self.orchestrator.llm, 'is_available', lambda: False)() if self.orchestrator.llm else False,
            'emotion': True if self.orchestrator.emotion else False,
            'avatar': (self.orchestrator.avatar.is_visible() if hasattr(self.orchestrator.avatar, 'is_visible') else False) if self.orchestrator.avatar else False,
        }
    
    async def get_module_health(self, module_id: str) -> Optional[ModuleHealth]:
        """Get health status for a specific module."""
        # Check legacy subsystems
        if module_id.startswith('legacy.'):
            subsystem = module_id.replace('legacy.', '')
            legacy_status = await self._check_legacy_subsystems()
            if subsystem in legacy_status:
                status = legacy_status[subsystem]
                return ModuleHealth(
                    module_id=module_id,
                    healthy=status,
                    started=status,
                    last_error=None if status else f"{subsystem} unavailable",
                    latency_ms=0.0,
                    last_check=time.time()
                )
        
        # Check modern modules
        if hasattr(self.orchestrator, '_statuses') and module_id in self.orchestrator._statuses:
            status = self.orchestrator._statuses[module_id]
            module = self.orchestrator.get_module(module_id)
            latency_ms = 0.0
            
            if module and hasattr(module, 'health_check'):
                try:
                    health_result = await module.health_check()
                    if isinstance(health_result, dict):
                        status.healthy = health_result.get('ok', True)
                        latency_ms = health_result.get('latency_ms', 0.0)
                    else:
                        status.healthy = bool(health_result)
                except Exception as e:
                    status.healthy = False
                    status.last_error = str(e)
            
            return ModuleHealth(
                module_id=module_id,
                healthy=status.healthy,
                started=status.started,
                last_error=status.last_error,
                latency_ms=latency_ms,
                last_check=time.time()
            )
        
        return None
    
    def get_health_history(self, limit: Optional[int] = None) -> list[SystemHealth]:
        """Get historical health data."""
        if limit:
            return self._health_history[-limit:]
        return self._health_history.copy()
    
    @property
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring
