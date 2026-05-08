"""
core/module_registry.py

Unified module registry to consolidate legacy and modern module systems.
This fixes the dual architecture problem by providing a single entry point
for all module registration and management.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass
from enum import Enum

from domain.contracts.contracts import ModuleContract
from runtime.events import EventBus, EventType, EventPayload
from runtime.container import get_container

logger = logging.getLogger(__name__)


class ModuleType(Enum):
    """Types of modules in the unified system."""
    LEGACY = "legacy"
    MODERN = "modern"
    HYBRID = "hybrid"


class ModuleStatus(Enum):
    """Module status states."""
    INITIALIZING = "initializing"
    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ModuleInfo:
    """Information about a registered module."""
    module_id: str
    module_type: ModuleType
    module_class: Type
    instance: Optional[Any] = None
    status: ModuleStatus = ModuleStatus.INITIALIZING
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}


class UnifiedModuleRegistry:
    """
    Unified registry for both legacy and modern modules.
    
    Provides a single interface for:
    - Module registration
    - Dependency resolution
    - Lifecycle management
    - Health monitoring
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self._modules: Dict[str, ModuleInfo] = {}
        self._legacy_providers: Dict[str, Any] = {}
        self._startup_order: List[str] = []
        self._shutdown_order: List[str] = []
    
    def register_legacy_provider(self, name: str, provider: Any) -> None:
        """Register a legacy AI provider."""
        self._legacy_providers[name] = provider
        logger.info(f"Registered legacy provider: {name}")
    
    def register_module(
        self, 
        module_id: str, 
        module_class: Type,
        module_type: ModuleType = ModuleType.MODERN,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a module with the unified registry."""
        if module_id in self._modules:
            logger.warning(f"Module {module_id} already registered, replacing")
        
        module_info = ModuleInfo(
            module_id=module_id,
            module_type=module_type,
            module_class=module_class,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self._modules[module_id] = module_info
        self._calculate_dependency_order()
        
        logger.info(f"Registered {module_type.value} module: {module_id}")
        
        # Emit registration event
        if self.event_bus:
            self.event_bus.emit(
                EventType.MODULE_REGISTERED,
                EventPayload(
                    source='module_registry',
                    data={
                        'module_id': module_id,
                        'module_type': module_type.value,
                        'dependencies': dependencies
                    }
                )
            )
    
    def get_module(self, module_id: str) -> Optional[Any]:
        """Get module instance by ID."""
        if module_id in self._modules:
            return self._modules[module_id].instance
        elif module_id in self._legacy_providers:
            return self._legacy_providers[module_id]
        return None
    
    def get_module_info(self, module_id: str) -> Optional[ModuleInfo]:
        """Get module information by ID."""
        return self._modules.get(module_id)
    
    def get_all_modules(self) -> Dict[str, ModuleInfo]:
        """Get all registered modules."""
        return dict(self._modules)
    
    def get_modules_by_type(self, module_type: ModuleType) -> List[ModuleInfo]:
        """Get all modules of a specific type."""
        return [info for info in self._modules.values() if info.module_type == module_type]
    
    async def create_instance(self, module_id: str, **kwargs) -> bool:
        """Create an instance of a registered module."""
        if module_id not in self._modules:
            logger.error(f"Module {module_id} not registered")
            return False
        
        module_info = self._modules[module_id]
        
        try:
            # Check dependencies
            for dep in module_info.dependencies:
                if dep not in self._modules or self._modules[dep].instance is None:
                    logger.error(f"Dependency {dep} not available for {module_id}")
                    return False
            
            # Try to create instance using DI container first
            try:
                container = get_container()
                instance = container.get(module_info.module_class)
                logger.debug(f"Created instance for {module_id} using DI container")
            except Exception:
                # Fallback to direct instantiation with kwargs
                instance = module_info.module_class(**kwargs)
                logger.debug(f"Created instance for {module_id} using direct instantiation")
            
            module_info.instance = instance
            module_info.status = ModuleStatus.REGISTERED
            
            logger.info(f"Created instance for module: {module_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create instance for {module_id}: {e}")
            module_info.status = ModuleStatus.FAILED
            return False
    
    async def start_module(self, module_id: str) -> bool:
        """Start a module instance."""
        module_info = self._modules.get(module_id)
        if not module_info:
            logger.error(f"Module {module_id} not registered")
            return False
        
        if module_info.status not in [ModuleStatus.REGISTERED, ModuleStatus.STOPPED]:
            logger.warning(f"Module {module_id} not in startable state: {module_info.status.value}")
            return False
        
        try:
            module_info.status = ModuleStatus.STARTING
            
            # Start dependencies first
            for dep in module_info.dependencies:
                if not await self.start_module(dep):
                    logger.error(f"Failed to start dependency {dep} for {module_id}")
                    module_info.status = ModuleStatus.FAILED
                    return False
            
            # Start the module
            if hasattr(module_info.instance, 'start'):
                result = await module_info.instance.start()
                if result:
                    module_info.status = ModuleStatus.RUNNING
                    logger.info(f"Started module: {module_id}")
                    
                    # Emit start event
                    if self.event_bus:
                        self.event_bus.emit(
                            EventType.MODULE_STARTED,
                            EventPayload(
                                source='module_registry',
                                data={'module_id': module_id}
                            )
                        )
                    return True
                else:
                    module_info.status = ModuleStatus.FAILED
                    return False
            else:
                # Legacy provider - just mark as running
                module_info.status = ModuleStatus.RUNNING
                logger.info(f"Legacy provider marked as running: {module_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start module {module_id}: {e}")
            module_info.status = ModuleStatus.FAILED
            return False
    
    async def stop_module(self, module_id: str) -> bool:
        """Stop a module instance."""
        module_info = self._modules.get(module_id)
        if not module_info:
            logger.error(f"Module {module_id} not registered")
            return False
        
        # Check if module is in a stoppable state
        stoppable_states = [ModuleStatus.RUNNING, ModuleStatus.DEGRADED, ModuleStatus.FAILED]
        if module_info.status not in stoppable_states:
            logger.debug(f"Module {module_id} not in stoppable state: {module_info.status.value}")
            return True
        
        try:
            module_info.status = ModuleStatus.STOPPING
            
            # Stop dependents first
            dependents = [
                mid for mid, info in self._modules.items() 
                if module_id in info.dependencies
            ]
            for dependent in dependents:
                await self.stop_module(dependent)
            
            # Stop module
            if hasattr(module_info.instance, 'stop'):
                result = await module_info.instance.stop()
                module_info.status = ModuleStatus.STOPPED if result else ModuleStatus.FAILED
                logger.info(f"Stopped module: {module_id} (success: {result})")
                return result
            else:
                # Legacy provider - just mark as stopped
                module_info.status = ModuleStatus.STOPPED
                logger.info(f"Legacy provider marked as stopped: {module_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to stop module {module_id}: {e}")
            module_info.status = ModuleStatus.FAILED
            return False
    
    async def start_all(self) -> bool:
        """Start all modules in dependency order."""
        logger.info("Starting all modules...")
        
        for module_id in self._startup_order:
            if not await self.start_module(module_id):
                logger.error(f"Failed to start module {module_id}, aborting startup")
                return False
        
        logger.info("All modules started successfully")
        return True
    
    async def stop_all(self) -> bool:
        """Stop all modules in reverse dependency order."""
        logger.info("Stopping all modules...")
        
        for module_id in reversed(self._shutdown_order):
            await self.stop_module(module_id)
        
        logger.info("All modules stopped")
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all modules."""
        results = {}
        
        for module_id, module_info in self._modules.items():
            if module_info.instance and hasattr(module_info.instance, 'health_check'):
                try:
                    health = await module_info.instance.health_check()
                    results[module_id] = {
                        'status': module_info.status.value,
                        'health': health,
                        'type': module_info.module_type.value
                    }
                except Exception as e:
                    results[module_id] = {
                        'status': ModuleStatus.FAILED.value,
                        'error': str(e),
                        'type': module_info.module_type.value
                    }
            else:
                results[module_id] = {
                    'status': module_info.status.value,
                    'type': module_info.module_type.value
                }
        
        return results
    
    def _calculate_dependency_order(self) -> None:
        """Calculate startup and shutdown order based on dependencies."""
        # Simple topological sort for startup order
        visited = set()
        temp_visited = set()
        
        def visit(module_id: str):
            if module_id in temp_visited:
                raise ValueError(f"Circular dependency detected: {module_id}")
            if module_id in visited:
                return
            
            temp_visited.add(module_id)
            
            if module_id in self._modules:
                for dep in self._modules[module_id].dependencies:
                    visit(dep)
            
            temp_visited.remove(module_id)
            visited.add(module_id)
            
            if module_id not in self._startup_order:
                self._startup_order.append(module_id)
        
        # Visit all modules
        for module_id in self._modules:
            if module_id not in visited:
                visit(module_id)
        
        # Shutdown order is reverse of startup order
        self._shutdown_order = list(reversed(self._startup_order))


# Global registry instance
_registry: Optional[UnifiedModuleRegistry] = None


def get_module_registry() -> UnifiedModuleRegistry:
    """Get the global module registry."""
    global _registry
    if _registry is None:
        _registry = UnifiedModuleRegistry()
    return _registry


def set_module_registry(registry: UnifiedModuleRegistry) -> None:
    """Set the global module registry (for testing)."""
    global _registry
    _registry = registry
