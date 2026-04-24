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

# Legacy AI providers
from ai.fast_brain.provider import FastBrainProvider
from ai.slm.provider import SLMProvider  
from ai.llm.provider import LLMProvider
from personality.emotion_controller import EmotionController
from ui.avatar.controller import AvatarController
from memory.memory_manager import MemoryManager

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
    lifecycle_manager: Any
    background_manager: Any


class ModelManagerShell(ModuleContract):
    module_id = 'ai.model_manager'
    required_flags = []

    def __init__(self, message_bus=None) -> None:
        self.started = False
        self.message_bus = message_bus
        # Register message bus handler immediately to ensure it's available
        if message_bus:
            message_bus.register_handler('model_manager.unload', self._handle_unload)

    async def start(self) -> bool:
        self.started = True
        return True

    async def stop(self) -> bool:
        self.started = False
        return True

    async def health_check(self):
        from core.health import HealthStatus

        return HealthStatus(module_id=self.module_id, ok=True, latency_ms=0.0)
    
    async def _handle_unload(self, data: dict) -> dict:
        """Handle model unload requests from performance manager."""
        import logging
        logger = logging.getLogger('kitsu.ai.model_manager')
        
        reason = data.get('reason', 'unknown')
        logger.info(f"Model unload requested: {reason}")
        
        # In a real implementation, this would unload AI models
        # For now, just acknowledge the request
        return {'status': 'unloaded', 'reason': reason}


async def build_app_container(
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
    
    if force_rebuild or _container_params != params:
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
        orchestrator = Orchestrator(runtime_config)
        
        # Clear orchestrator state if rebuilding
        if force_rebuild:
            orchestrator._modules.clear()
            orchestrator._statuses.clear()
        
        health_monitor = HealthMonitor(event_bus=event_bus, orchestrator=orchestrator, clock_service=clock_service)
        performance_manager = PerformanceManager(event_bus=event_bus, message_bus=message_bus, clock_service=clock_service)
        model_manager = ModelManagerShell(message_bus=message_bus)
        
        # Create lifecycle and background task managers
        from core.lifecycle import create_lifecycle_manager
        from core.background_tasks import create_background_manager
        
        lifecycle_manager = create_lifecycle_manager(event_bus=event_bus)
        background_manager = create_background_manager(event_bus=event_bus)

        gateway = PermissionedSystemGateway() if flags.use_system_control else NullSystemGateway()
        orchestrator.gateway = gateway

        # Inject legacy AI providers
        if flags.use_fast_brain:
            orchestrator.fast_brain = FastBrainProvider()
        if flags.use_slm:
            orchestrator.slm = SLMProvider()
        if flags.use_llm:
            orchestrator.llm = LLMProvider()
        
        # Inject legacy subsystems
        if flags.use_emotion:
            emotion_engine = EmotionEngine()
            from personality.reaction_mapper import ReactionMapper
            from personality.kitsu_self import KitsuSelf
            kitsu_self = KitsuSelf(initial_state={})
            reaction_mapper = ReactionMapper()
            emotion_controller = EmotionController(
                emotion_engine=emotion_engine,
                kitsu_self=kitsu_self,
                reaction_mapper=reaction_mapper
            )
            # Set mock shared state to prevent errors
            mock_state = type('MockState', (), {'update_emotional_state': lambda self, *args, **kwargs: None})()
            emotion_engine.set_shared_state(mock_state)
            orchestrator.emotion = emotion_controller
            
        if flags.use_2d or flags.use_3d:
            orchestrator.avatar = AvatarController()
            
        # Memory manager - always enabled for now
        orchestrator.memory = MemoryManager()

        personality_engine = None
        if flags.use_emotion:
            personality_engine = PersonalityEngine(emotion_engine=emotion_engine)
            orchestrator.personality = personality_engine

        registered_modules: list[ModuleContract] = [
            clock_service,
            orchestrator,
            health_monitor,
            performance_manager,
            model_manager,
            lifecycle_manager,
            background_manager,
        ]

        for module in registered_modules:
            await orchestrator.register(module)
            logger.info('Registered module %s', module.module_id)

        # Initialize AI providers
        if orchestrator.fast_brain:
            await orchestrator.fast_brain.initialize()
        if orchestrator.slm:
            await orchestrator.slm.initialize()
        if orchestrator.llm:
            await orchestrator.llm.initialize()

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
            lifecycle_manager=lifecycle_manager,
            background_manager=background_manager,
        )
        _container_params = params
        logger.info('Bootstrap completed with profile %s', profile.name)
        return _container
    except Exception as exc:
        raise BootstrapError(str(exc)) from exc
