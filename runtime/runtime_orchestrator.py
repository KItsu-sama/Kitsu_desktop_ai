"""
runtime/runtime_orchestrator.py

Central runtime orchestrator that coordinates all systems.

Implements the 4-layer architecture:
ServiceContainer -> ModuleRegistry -> LifecycleManager -> RuntimeOrchestrator
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Set, Type
from dataclasses import dataclass
from enum import Enum

from runtime.container import DIContainer, get_container
from runtime.module_registry import UnifiedModuleRegistry, ModuleStatus, get_module_registry
from runtime.lifecycle import LifecycleManager, create_lifecycle_manager
from runtime.events import EventBus, EventType, EventPayload

log = logging.getLogger(__name__)


class StartupPhase(Enum):
    """Startup phases for deterministic initialization."""
    CORE_SERVICES = "core_services"          # clock_service, logger, config, container
    COMMUNICATION = "communication"          # event_bus, message_bus
    RUNTIME_CONTROL = "runtime_control"    # orchestrator, module_registry, lifecycle_manager
    MONITORING = "monitoring"               # health_monitor, performance_manager, resource_controller
    COGNITION = "cognition"                 # memory, emotion, judge, router, reflex, slm, llm
    SHELL_SYSTEMS = "shell_systems"         # desktop_pet, wallpaper, cursor, voice, live2d


@dataclass
class PhaseConfig:
    """Configuration for a startup phase."""
    phase: StartupPhase
    services: List[str]
    modules: List[str]
    dependencies: List[StartupPhase]
    timeout_seconds: float = 30.0
    critical: bool = True  # If True, startup fails if this phase fails


class RuntimeOrchestrator:
    """
    Central runtime orchestrator.
    
    Coordinates:
    - Dependency injection container
    - Module registry and lifecycle
    - Startup phases and dependency resolution
    - Health monitoring and failure recovery
    """
    
    def __init__(self):
        self.container: DIContainer = get_container()
        self.module_registry: UnifiedModuleRegistry = get_module_registry()
        self.lifecycle_manager: Optional[LifecycleManager] = None
        self.event_bus: Optional[EventBus] = None
        
        # Startup state
        self.current_phase: Optional[StartupPhase] = None
        self.completed_phases: Set[StartupPhase] = set()
        self.failed_phases: Set[StartupPhase] = set()
        self.startup_time: Optional[float] = None
        
        # Phase configurations
        self.phase_configs: Dict[StartupPhase, PhaseConfig] = {}
        self._setup_phase_configs()
        
        # Runtime state
        self._running = False
        self._shutdown_requested = False
        
        log.info("RuntimeOrchestrator initialized")
    
    def _setup_phase_configs(self):
        """Setup startup phase configurations."""
        self.phase_configs[StartupPhase.CORE_SERVICES] = PhaseConfig(
            phase=StartupPhase.CORE_SERVICES,
            services=["clock_service", "logger", "config"],
            modules=[],
            dependencies=[],
            timeout_seconds=10.0,
            critical=True
        )
        
        self.phase_configs[StartupPhase.COMMUNICATION] = PhaseConfig(
            phase=StartupPhase.COMMUNICATION,
            services=["event_bus", "message_bus"],
            modules=[],
            dependencies=[StartupPhase.CORE_SERVICES],
            timeout_seconds=15.0,
            critical=True
        )
        
        self.phase_configs[StartupPhase.RUNTIME_CONTROL] = PhaseConfig(
            phase=StartupPhase.RUNTIME_CONTROL,
            services=["orchestrator", "module_registry", "lifecycle_manager"],
            modules=[],
            dependencies=[StartupPhase.COMMUNICATION],
            timeout_seconds=20.0,
            critical=True
        )
        
        self.phase_configs[StartupPhase.MONITORING] = PhaseConfig(
            phase=StartupPhase.MONITORING,
            services=["health_monitor", "performance_manager", "resource_controller"],
            modules=["core.health", "core.performance_manager"],
            dependencies=[StartupPhase.RUNTIME_CONTROL],
            timeout_seconds=30.0,
            critical=False
        )
        
        self.phase_configs[StartupPhase.COGNITION] = PhaseConfig(
            phase=StartupPhase.COGNITION,
            services=["memory", "emotion", "judge", "router", "reflex", "slm", "llm"],
            modules=[
                "domain.personality.emotion_engine",
                "domain.personality.memory_manager", 
                "domain.personality.emotion_controller",
                "ai.model_manager"
            ],
            dependencies=[StartupPhase.MONITORING],
            timeout_seconds=45.0,
            critical=False
        )
        
        self.phase_configs[StartupPhase.SHELL_SYSTEMS] = PhaseConfig(
            phase=StartupPhase.SHELL_SYSTEMS,
            services=["desktop_pet", "wallpaper", "cursor", "voice", "live2d"],
            modules=[],
            dependencies=[StartupPhase.COGNITION],
            timeout_seconds=30.0,
            critical=False
        )
    
    async def initialize(self) -> bool:
        """Initialize the runtime orchestrator."""
        try:
            self.startup_time = time.time()
            
            # Register core services in container
            await self._register_core_services()
            
            # Build dependency graph
            self.container.build_graph()
            
            # Validate dependencies
            validation_result = await self._validate_dependencies()
            if not validation_result.valid:
                log.error(f"Dependency validation failed: {validation_result.errors}")
                return False
            
            log.info("RuntimeOrchestrator initialized successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to initialize RuntimeOrchestrator: {e}")
            return False
    
    async def _register_core_services(self):
        """Register core services in the DI container."""
        # Create and register event bus first
        if not self.container.is_registered(EventBus):
            event_bus = EventBus()
            self.container.register_instance(EventBus, event_bus)
            self.event_bus = event_bus
        
        # Register orchestrator itself
        self.container.register_instance(RuntimeOrchestrator, self)
        
        # Register module registry
        if not self.container.is_registered(UnifiedModuleRegistry):
            self.container.register_instance(UnifiedModuleRegistry, self.module_registry)
        
        # Create lifecycle manager
        if not self.container.is_registered(LifecycleManager):
            self.lifecycle_manager = create_lifecycle_manager(self.event_bus)
            self.container.register_instance(LifecycleManager, self.lifecycle_manager)
    
    async def _validate_dependencies(self) -> 'ValidationResult':
        """Validate all dependencies before startup."""
        errors = []
        warnings = []
        
        # Check service dependencies
        for phase_config in self.phase_configs.values():
            for service_name in phase_config.services:
                if not self._is_service_available(service_name):
                    errors.append(f"Service {service_name} not available for phase {phase_config.phase.value}")
        
        # Check module dependencies
        for module_id, module_info in self.module_registry.get_all_modules().items():
            for dep in module_info.dependencies:
                if dep not in self.module_registry.get_all_modules():
                    errors.append(f"Module {module_id} depends on unknown module {dep}")
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies()
        if circular_deps:
            errors.extend([f"Circular dependency: {cycle}" for cycle in circular_deps])
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _is_service_available(self, service_name: str) -> bool:
        """Check if a service is available in the container."""
        # This is a simplified check - in reality would need to map service names to types
        return True  # Placeholder
    
    def _detect_circular_dependencies(self) -> List[str]:
        """Detect circular dependencies in modules."""
        # Simplified circular dependency detection
        return []  # Placeholder
    
    async def startup(self) -> bool:
        """Execute full startup sequence."""
        if self._running:
            log.warning("Runtime already running")
            return True
        
        try:
            log.info("Starting runtime orchestrator...")
            
            # Initialize if not already done
            if not await self.initialize():
                return False
            
            # Execute startup phases in order
            for phase in StartupPhase:
                if not await self._execute_phase(phase):
                    if self.phase_configs[phase].critical:
                        log.error(f"Critical phase {phase.value} failed, aborting startup")
                        return False
                    else:
                        log.warning(f"Non-critical phase {phase.value} failed, continuing")
                        self.failed_phases.add(phase)
                        continue
                
                self.completed_phases.add(phase)
                log.info(f"Completed phase: {phase.value}")
            
            # Start lifecycle manager
            if self.lifecycle_manager:
                await self.lifecycle_manager.start()
            
            # Start monitoring systems
            await self._start_monitoring()
            
            self._running = True
            startup_duration = time.time() - (self.startup_time or time.time())
            log.info(f"Runtime orchestrator startup complete in {startup_duration:.2f}s")
            
            return True
            
        except Exception as e:
            log.error(f"Startup failed: {e}")
            return False
    
    async def _execute_phase(self, phase: StartupPhase) -> bool:
        """Execute a single startup phase."""
        self.current_phase = phase
        phase_config = self.phase_configs[phase]
        
        log.info(f"Executing phase: {phase.value}")
        
        try:
            # Check dependencies
            for dep_phase in phase_config.dependencies:
                if dep_phase not in self.completed_phases:
                    log.error(f"Dependency phase {dep_phase.value} not completed for {phase.value}")
                    return False
            
            # Start services
            for service_name in phase_config.services:
                if not await self._start_service(service_name):
                    log.error(f"Failed to start service {service_name}")
                    return False
            
            # Start modules
            for module_id in phase_config.modules:
                if not await self._start_module_with_di(module_id):
                    log.error(f"Failed to start module {module_id}")
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"Phase {phase.value} failed: {e}")
            return False
    
    async def _start_service(self, service_name: str) -> bool:
        """Start a service using dependency injection."""
        try:
            # Services would be resolved from container and started
            log.debug(f"Starting service: {service_name}")
            return True
        except Exception as e:
            log.error(f"Failed to start service {service_name}: {e}")
            return False
    
    async def _start_module_with_di(self, module_id: str) -> bool:
        """Start a module with dependency injection."""
        try:
            module_info = self.module_registry.get_module_info(module_id)
            if not module_info:
                log.error(f"Module {module_id} not registered")
                return False
            
            # Create instance with dependency injection
            if not await self._create_module_instance_with_di(module_id):
                return False
            
            # Start the module
            return await self.module_registry.start_module(module_id)
            
        except Exception as e:
            log.error(f"Failed to start module {module_id} with DI: {e}")
            return False
    
    async def _create_module_instance_with_di(self, module_id: str) -> bool:
        """Create module instance using dependency injection."""
        module_info = self.module_registry.get_module_info(module_id)
        if not module_info:
            return False
        
        try:
            # Resolve constructor dependencies
            kwargs = {}
            for dep_name in module_info.dependencies:
                dep_instance = self.module_registry.get_module(dep_name)
                if dep_instance:
                    kwargs[dep_name] = dep_instance
                else:
                    # Try to resolve from container
                    dep_instance = self.container.create_instance_safe(dep_name)
                    if dep_instance:
                        kwargs[dep_name] = dep_instance
            
            # Create instance
            instance = module_info.module_class(**kwargs)
            module_info.instance = instance
            module_info.status = ModuleStatus.REGISTERED
            
            log.info(f"Created instance for module {module_id} with DI")
            return True
            
        except Exception as e:
            log.error(f"Failed to create instance for {module_id}: {e}")
            module_info.status = ModuleStatus.FAILED
            return False
    
    async def _start_monitoring(self):
        """Start monitoring systems."""
        try:
            from domain.contracts.lifecycle import Monitorable
            from domain.core.failure_recovery import FAILURE_RECOVERY_SYSTEM
            from domain.inference.resource_controller import RESOURCE_CONTROLLER
            
            # Start failure recovery system
            if isinstance(FAILURE_RECOVERY_SYSTEM, Monitorable):
                await FAILURE_RECOVERY_SYSTEM.start_monitoring()
            
            # Start resource controller monitoring
            if isinstance(RESOURCE_CONTROLLER, Monitorable):
                await RESOURCE_CONTROLLER.start_monitoring()
            
            log.info("Monitoring systems started")
            
        except Exception as e:
            log.error(f"Failed to start monitoring: {e}")
    
    async def _stop_monitoring(self):
        """Stop monitoring systems."""
        try:
            from domain.contracts.lifecycle import Monitorable
            from domain.core.failure_recovery import FAILURE_RECOVERY_SYSTEM
            from domain.inference.resource_controller import RESOURCE_CONTROLLER
            
            # Stop failure recovery system
            if isinstance(FAILURE_RECOVERY_SYSTEM, Monitorable):
                FAILURE_RECOVERY_SYSTEM.stop_monitoring()
            
            # Stop resource controller monitoring
            if isinstance(RESOURCE_CONTROLLER, Monitorable):
                await RESOURCE_CONTROLLER.stop_monitoring()
            
            log.info("Monitoring systems stopped")
            
        except Exception as e:
            log.error(f"Failed to stop monitoring: {e}")
    
    async def shutdown(self) -> bool:
        """Graceful shutdown of all systems."""
        if not self._running:
            return True
        
        log.info("Shutting down runtime orchestrator...")
        self._shutdown_requested = True
        
        try:
            # Stop monitoring systems
            await self._stop_monitoring()
            
            # Stop all modules in reverse order
            await self.module_registry.stop_all()
            
            # Stop lifecycle manager
            if self.lifecycle_manager:
                await self.lifecycle_manager.stop()
            
            self._running = False
            log.info("Runtime orchestrator shutdown complete")
            return True
            
        except Exception as e:
            log.error(f"Shutdown failed: {e}")
            return False
    
    async def _stop_monitoring(self):
        """Stop monitoring systems."""
        try:
            from domain.core.failure_recovery import FAILURE_RECOVERY_SYSTEM
            FAILURE_RECOVERY_SYSTEM.stop_monitoring()
            
            from domain.inference.resource_controller import RESOURCE_CONTROLLER
            await RESOURCE_CONTROLLER.stop_monitoring()
            
            log.info("Monitoring systems stopped")
            
        except Exception as e:
            log.error(f"Failed to stop monitoring: {e}")
    
    def is_running(self) -> bool:
        """Check if runtime is running."""
        return self._running
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "runtime": {
                "running": self._running,
                "current_phase": self.current_phase.value if self.current_phase else None,
                "completed_phases": [p.value for p in self.completed_phases],
                "failed_phases": [p.value for p in self.failed_phases],
                "startup_time": self.startup_time
            },
            "modules": await self.module_registry.health_check(),
            "container": {
                "registered_services": len(self.container.get_registered_services())
            }
        }


@dataclass
class ValidationResult:
    """Result of dependency validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


# Global orchestrator instance
_orchestrator: Optional[RuntimeOrchestrator] = None


def get_runtime_orchestrator() -> RuntimeOrchestrator:
    """Get the global runtime orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RuntimeOrchestrator()
    return _orchestrator


def set_runtime_orchestrator(orchestrator: RuntimeOrchestrator) -> None:
    """Set the global runtime orchestrator (for testing)."""
    global _orchestrator
    _orchestrator = orchestrator
