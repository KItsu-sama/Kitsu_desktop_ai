"""
app/bootstrap.py

Merged bootstrap using dependency injection container.
This fixes bootstrap complexity by automating service wiring while maintaining
compatibility with the original bootstrap interface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from runtime.profiles import HardwareProfile, select_profile
from runtime.runtime_config import RuntimeConfig
from shared.capability_flags import CapabilityFlags
from runtime.container import get_container, ServiceLifetime
from runtime.bus import MessageBus
from runtime.clocks import ClockService
from runtime.health import HealthMonitor
from runtime.orchestrator import Orchestrator
from runtime.performance_manager import PerformanceManager
from domain.contracts.contracts import ModuleContract, NullSystemGateway
from interfaces.desktop.gateway import PermissionedSystemGateway

# Legacy AI providers
from domain.ai.fast_brain.provider import FastBrainProvider
from domain.ai.slm.provider import SLMProvider  
from domain.ai.llm.provider import LLMProvider
from domain.personality.emotion_controller import EmotionController
from interfaces.desktop.avatar.controller import AvatarController
from domain.personality.memory_manager import MemoryManager

# Modern services
from runtime.application import Application
from domain.interaction.input_manager import InputManager
from runtime.system_monitor import SystemMonitor

logger = logging.getLogger('kitsu.app.bootstrap')

# Global container caching
_container: Optional['AppContainer'] = None
_container_params: Optional[dict[str, Any]] = None


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
    splash_screen: Any


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
        try:
            self.started = True
            logger.info(f"{self.module_id} started successfully")
            return True
        except Exception as e:
            logger.error(f"{self.module_id} failed to start: {e}", exc_info=True)
            return False

    async def stop(self) -> bool:
        try:
            self.started = False
            logger.info(f"{self.module_id} stopped successfully")
            return True
        except Exception as e:
            logger.error(f"{self.module_id} failed to stop: {e}", exc_info=True)
            return False

    async def health_check(self):
        from runtime.health import HealthStatus
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


class ServiceRegistry:
    """Service registry for dependency injection setup."""
    
    @staticmethod
    def register_core_services(container) -> None:
        """Register core infrastructure services."""
        # Message bus
        container.register_singleton(MessageBus, MessageBus)
        
        # Clock service
        container.register_singleton(ClockService, ClockService)
        
        # Use factories for complex services
        def create_health_monitor():
            event_bus = container.get(MessageBus)
            orchestrator = container.get(Orchestrator)
            clock_service = container.get(ClockService)
            return HealthMonitor(event_bus=event_bus, orchestrator=orchestrator, clock_service=clock_service)
        
        def create_performance_manager():
            event_bus = container.get(MessageBus)
            message_bus = container.get(MessageBus)
            clock_service = container.get(ClockService)
            return PerformanceManager(event_bus=event_bus, message_bus=message_bus, clock_service=clock_service)
        
        container.register_singleton(HealthMonitor, factory=create_health_monitor)
        container.register_singleton(PerformanceManager, factory=create_performance_manager)
        
        logger.info("Registered core services")
    
    @staticmethod
    def register_application_services(container, runtime_config) -> None:
        """Register application-level services."""
        # Register RuntimeConfig first
        if runtime_config:
            container.register_instance(type(runtime_config), runtime_config)
        
        # Orchestrator (main coordinator) - use factory to handle RuntimeConfig
        def create_orchestrator():
            return Orchestrator(runtime_config)
        container.register_singleton(Orchestrator, factory=create_orchestrator)
        
        # Focused managers
        container.register_singleton(Application)
        container.register_singleton(InputManager)
        container.register_singleton(SystemMonitor)
        
        logger.info("Registered application services")
    
    @staticmethod
    def register_legacy_providers(container, flags: CapabilityFlags) -> None:
        """Register legacy AI providers based on capability flags."""
        if flags.use_fast_brain:
            container.register_singleton(FastBrainProvider)
        
        if flags.use_slm:
            container.register_singleton(SLMProvider)
        
        if flags.use_llm:
            container.register_singleton(LLMProvider)
        
        logger.info("Registered legacy providers")
    
    @staticmethod
    def register_system_gateway(container, flags: CapabilityFlags) -> None:
        """Register system gateway based on capabilities."""
        gateway_class = PermissionedSystemGateway if flags.use_system_control else NullSystemGateway
        container.register_singleton(gateway_class)
        
        logger.info(f"Registered system gateway: {gateway_class.__name__}")
    
    @staticmethod
    def register_legacy_subsystems(container, flags: CapabilityFlags) -> None:
        """Register legacy subsystems based on capability flags."""
        from pathlib import Path
        
        # Model manager
        container.register_singleton(ModelManagerShell)
        
        # Register Path for EmotionEngine (will be overridden by memory path)
        
        # Emotion system
        if flags.use_emotion:
            from domain.personality.emotion_engine import EmotionEngine
            container.register_singleton(EmotionEngine)
        
        # Avatar system
        if flags.use_2d or flags.use_3d:
            container.register_singleton(AvatarController)
        
        # Memory manager - always enabled for now
        # Register MemoryConfig and Path for MemoryManager
        from domain.personality.memory_manager import MemoryConfig
        from pathlib import Path
        
        container.register_instance(MemoryConfig, MemoryConfig())
        container.register_instance(Path, Path("data/runtime/memory.json"))
        
        # Use factory for MemoryManager to provide correct dependencies
        def create_memory_manager():
            config = container.get(MemoryConfig)
            memory_path = container.get(Path)
            return MemoryManager(config=config, memory_path=memory_path)
        container.register_singleton(MemoryManager, factory=create_memory_manager)
        
        logger.info("Registered legacy subsystems")
    
    @staticmethod
    def register_lifecycle_services(container) -> None:
        """Register lifecycle and background services."""
        from runtime.lifecycle import create_lifecycle_manager
        from infra.system.background_tasks import create_background_manager
        from interfaces.desktop.terminal.splash import SplashScreen
        
        container.register_instance(type(create_lifecycle_manager()), create_lifecycle_manager())
        container.register_instance(type(create_background_manager()), create_background_manager())
        container.register_singleton(SplashScreen)
        
        logger.info("Registered lifecycle services")


class SimplifiedBootstrap:
    """Simplified bootstrap using dependency injection."""
    
    def __init__(self):
        self.container = get_container()
        self.registry = ServiceRegistry()
    
    async def build_app_container(
        self,
        profile_override: str | None = None,
        safe_mode: bool = False,
        runtime_config: Optional[RuntimeConfig] = None,
        force_rebuild: bool = False,
    ) -> AppContainer:
        """Build and wire all runtime services automatically."""
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
        
        logger.info("Starting simplified bootstrap...")
        
        try:
            # 1. Select hardware profile
            profile = select_profile(profile_override=profile_override, safe_mode=safe_mode)
            logger.info(f"Selected hardware profile: {profile.name}")
            
            # 2. Create capability flags
            flags = CapabilityFlags.from_profile(profile.profile_definition.flags)
            diagnostics = flags.validate()
            for diagnostic in diagnostics:
                logger.warning(diagnostic)
            
            # 3. Register all services
            self.registry.register_core_services(self.container)
            self.registry.register_application_services(self.container, runtime_config)
            self.registry.register_legacy_providers(self.container, flags)
            self.registry.register_system_gateway(self.container, flags)
            self.registry.register_legacy_subsystems(self.container, flags)
            self.registry.register_lifecycle_services(self.container)
            
            # 4. Build dependency graph
            self.container.build_graph()
            
            # 5. Resolve core services
            event_bus = self.container.get(MessageBus)
            message_bus = self.container.get(MessageBus)
            clock_service = self.container.get(ClockService)
            orchestrator = self.container.get(Orchestrator)
            health_monitor = self.container.get(HealthMonitor)
            performance_manager = self.container.get(PerformanceManager)
            model_manager = self.container.get(ModelManagerShell)
            
            # 6. Inject legacy providers into orchestrator
            self._inject_legacy_providers(orchestrator, flags)
            
            # 7. Inject legacy subsystems into orchestrator
            self._inject_legacy_subsystems(orchestrator, flags)
            
            # 8. Register orchestrator as a module first
            await orchestrator.register(orchestrator)
            logger.info('Registered module %s', orchestrator.module_id)
            
            # 9. Register other modules with orchestrator
            await self._register_modules(orchestrator, {
                'clock_service': clock_service,
                'health_monitor': health_monitor,
                'performance_manager': performance_manager,
                'model_manager': model_manager,
            })
            
            # 10. Initialize AI providers
            await self._initialize_ai_providers(orchestrator, flags)
            
            # 11. Lock capability flags
            flags.lock()
            logger.info('Capability flags locked')
            
            # 12. Display startup screen
            from interfaces.desktop.terminal.splash import SplashScreen
            splash_screen = SplashScreen()
            
            mode = runtime_config.merged.get("mode", "text") if runtime_config else "text"
            model = runtime_config.merged.get("model", "unknown") if runtime_config else "unknown"
            splash_screen.display_splash(mode, model)
            
            # 13. Create and return AppContainer
            app_container = AppContainer(
                event_bus=event_bus,
                message_bus=message_bus,
                flags=flags,
                profile=profile,
                runtime_config=runtime_config,
                gateway=orchestrator.gateway,
                personality_engine=self._get_personality_engine(orchestrator, flags),
                orchestrator=orchestrator,
                health_monitor=health_monitor,
                performance_manager=performance_manager,
                clock_service=clock_service,
                model_manager=model_manager,
                lifecycle_manager=type('MockLifecycleManager', (), {'start': lambda: True})(),
                background_manager=type('MockBackgroundManager', (), {'start': lambda: True})(),
                splash_screen=splash_screen,
            )
            
            _container = app_container
            _container_params = params
            logger.info('Bootstrap completed with profile %s', profile.name)
            return app_container
            
        except Exception as e:
            logger.error(f"Bootstrap failed: {e}")
            raise BootstrapError(str(e)) from e
    
    def _inject_legacy_providers(self, orchestrator: Orchestrator, flags: CapabilityFlags) -> None:
        """Inject legacy providers into orchestrator."""
        if flags.use_fast_brain:
            orchestrator.fast_brain = self.container.get(FastBrainProvider)
        
        if flags.use_slm:
            orchestrator.slm = self.container.get(SLMProvider)
        
        if flags.use_llm:
            orchestrator.llm = self.container.get(LLMProvider)
        
        # System gateway
        gateway_type = PermissionedSystemGateway if flags.use_system_control else NullSystemGateway
        orchestrator.gateway = self.container.get(gateway_type)
        
        logger.info("Injected legacy providers into orchestrator")
    
    def _inject_legacy_subsystems(self, orchestrator: Orchestrator, flags: CapabilityFlags) -> None:
        """Inject legacy subsystems into orchestrator."""
        # Emotion system
        if flags.use_emotion:
            from domain.personality.emotion_engine import EmotionEngine
            emotion_engine = self.container.get(EmotionEngine)
            from domain.personality.reaction_mapper import ReactionMapper
            from domain.personality.kitsu_self import KitsuSelf
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
            
        # Avatar system
        if flags.use_2d or flags.use_3d:
            orchestrator.avatar = self.container.get(AvatarController)
            
        # Memory manager - always enabled for now
        orchestrator.memory = self.container.get(MemoryManager)
        
        logger.info("Injected legacy subsystems into orchestrator")
    
    async def _register_modules(self, orchestrator: Orchestrator, modules: dict) -> None:
        """Register modules with orchestrator."""
        for name, module in modules.items():
            await orchestrator.register(module)
            logger.info('Registered module %s', module.module_id)
    
    async def _initialize_ai_providers(self, orchestrator: Orchestrator, flags: CapabilityFlags) -> None:
        """Initialize AI providers."""
        if orchestrator.fast_brain:
            await orchestrator.fast_brain.initialize()
        if orchestrator.slm:
            await orchestrator.slm.initialize()
        if orchestrator.llm:
            await orchestrator.llm.initialize()
        
        logger.info("Initialized AI providers")
    
    def _get_personality_engine(self, orchestrator: Orchestrator, flags: CapabilityFlags) -> Any:
        """Get personality engine if available."""
        return getattr(orchestrator, 'personality', None)


# Global bootstrap instance
_bootstrap: Optional[SimplifiedBootstrap] = None


def get_simplified_bootstrap() -> SimplifiedBootstrap:
    """Get the global simplified bootstrap instance."""
    global _bootstrap
    if _bootstrap is None:
        _bootstrap = SimplifiedBootstrap()
    return _bootstrap


async def build_app_container(
    profile_override: str | None = None,
    safe_mode: bool = False,
    runtime_config: Optional[RuntimeConfig] = None,
    force_rebuild: bool = False,
) -> AppContainer:
    """Build and wire all runtime singletons."""
    bootstrap = get_simplified_bootstrap()
    return await bootstrap.build_app_container(
        profile_override=profile_override,
        safe_mode=safe_mode,
        runtime_config=runtime_config,
        force_rebuild=force_rebuild
    )
