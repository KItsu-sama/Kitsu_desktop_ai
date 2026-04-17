from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.profiles import HardwareProfile, select_profile
from app.runtime_config import RuntimeConfig
from config.capability_flags import CapabilityFlags
from core.bus import MessageBus
from core.clocks import ClockService
from core.health import HealthMonitor
from core.orchestrator import Orchestrator
from core.performance_manager import PerformanceManager
from core.contracts import ModuleContract
from personality.emotion_engine import EmotionEngine
from personality.engine import PersonalityEngine
from core.contracts import NullSystemGateway
from system.gateway import PermissionedSystemGateway

logger = logging.getLogger('kitsu.app.bootstrap')

_container: AppContainer | None = None
_container_params: dict[str, Any] | None = None


class BootstrapError(RuntimeError):
    """Raised when the application fails to bootstrap."""


@dataclass
class AppContainer:
    event_bus: MessageBus
    message_bus: MessageBus
    flags: CapabilityFlags
    profile: HardwareProfile
    runtime_config: Optional[RuntimeConfig]
    gateway: Any
    personality_engine: Any
    orchestrator: Orchestrator
    health_monitor: HealthMonitor
    performance_manager: PerformanceManager
    clock_service: ClockService
    model_manager: Any


class ModelManagerShell(ModuleContract):
    module_id = 'ai.model_manager'
    required_flags = []

    def __init__(self) -> None:
        self.started = False

    async def start(self) -> bool:
        self.started = True
        return True

    async def stop(self) -> bool:
        self.started = False
        return True

    async def health_check(self):
        from core.health import HealthStatus

        return HealthStatus(module_id=self.module_id, ok=True, latency_ms=0.0)


def build_app_container(
    profile_override: str | None = None,
    safe_mode: bool = False,
    runtime_config: Optional[RuntimeConfig] = None,
    force_rebuild: bool = False,
) -> AppContainer:
    """Build and wire all runtime singletons."""
    global _container, _container_params
    params = {
        'profile_override': profile_override,
        'safe_mode': safe_mode,
        'debug': runtime_config.debug if runtime_config else False,
    }

    if _container is not None and not force_rebuild:
        if _container_params == params:
            return _container
        logger.warning('Rebuilding app container for new bootstrap configuration')
        _container = None
        _container_params = None

    try:
        profile = select_profile(profile_override=profile_override, safe_mode=safe_mode)
        flags = CapabilityFlags.from_profile(profile.profile_definition.flags)
        diagnostics = flags.validate()
        for diagnostic in diagnostics:
            logger.warning(diagnostic)

        event_bus = MessageBus()
        message_bus = MessageBus()
        clock_service = ClockService()
        orchestrator = Orchestrator(event_bus=event_bus)
        health_monitor = HealthMonitor(event_bus=event_bus, orchestrator=orchestrator, clock_service=clock_service)
        performance_manager = PerformanceManager(event_bus=event_bus, message_bus=message_bus, clock_service=clock_service)
        model_manager = ModelManagerShell()

        gateway = PermissionedSystemGateway() if flags.use_system_control else NullSystemGateway()
        orchestrator.gateway = gateway

        personality_engine = None
        if flags.use_emotion:
            emotion_engine = EmotionEngine()
            personality_engine = PersonalityEngine(emotion_engine=emotion_engine)
            orchestrator.personality = personality_engine

        registered_modules: list[ModuleContract] = [
            event_bus,
            message_bus,
            clock_service,
            orchestrator,
            health_monitor,
            performance_manager,
            model_manager,
        ]

        for module in registered_modules:
            orchestrator.register(module)
            logger.info('Registered module %s', module.module_id)

        flags.lock()
        logger.info('Capability flags locked')

        _container = AppContainer(
            event_bus=event_bus,
            message_bus=message_bus,
            flags=flags,
            profile=profile,
            runtime_config=runtime_config,
            gateway=gateway,
            personality_engine=personality_engine,
            orchestrator=orchestrator,
            health_monitor=health_monitor,
            performance_manager=performance_manager,
            clock_service=clock_service,
            model_manager=model_manager,
        )
        _container_params = params
        logger.info('Bootstrap completed with profile %s', profile.name)
        return _container
    except Exception as exc:
        raise BootstrapError(str(exc)) from exc
