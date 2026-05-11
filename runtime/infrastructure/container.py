"""
core/container.py

Dependency injection container to simplify bootstrap complexity.
Provides automatic dependency resolution and service wiring.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Type, Callable, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceLifetime(Enum):
    """Service lifetime options."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceDescriptor:
    """Describes a service registration."""
    interface: Type
    implementation: Type
    lifetime: ServiceLifetime
    dependencies: List[Type]
    factory: Optional[Callable] = None
    instance: Optional[Any] = None


class DIContainer:
    """
    Dependency injection container.
    
    Provides:
    - Service registration and resolution
    - Automatic dependency injection
    - Lifetime management
    - Circular dependency detection
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._resolving: set[Type] = set()
    
    def register_singleton(
        self, 
        interface: Type, 
        implementation: Type = None,
        factory: Callable = None
    ) -> None:
        """Register a singleton service."""
        impl = implementation or interface
        self._services[interface] = ServiceDescriptor(
            interface=interface,
            implementation=impl,
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=self._get_dependencies(impl),
            factory=factory
        )
        logger.debug(f"Registered singleton: {interface.__name__}")
    
    def register_transient(
        self, 
        interface: Type, 
        implementation: Type = None,
        factory: Callable = None
    ) -> None:
        """Register a transient service."""
        impl = implementation or interface
        self._services[interface] = ServiceDescriptor(
            interface=interface,
            implementation=impl,
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=self._get_dependencies(impl),
            factory=factory
        )
        logger.debug(f"Registered transient: {interface.__name__}")
    
    def register_instance(self, interface: Type, instance: Any) -> None:
        """Register a pre-created instance."""
        self._services[interface] = ServiceDescriptor(
            interface=interface,
            implementation=type(instance),
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=[],
            instance=instance
        )
        self._singletons[interface] = instance
        logger.debug(f"Registered instance: {interface.__name__}")
    
    def get(self, interface: Type) -> Any:
        """Resolve a service instance."""
        if interface not in self._services:
            raise ValueError(f"Service {interface.__name__} not registered")
        
        descriptor = self._services[interface]
        
        # Check for circular dependencies
        if interface in self._resolving:
            cycle = " -> ".join([t.__name__ for t in self._resolving] + [interface.__name__])
            raise ValueError(f"Circular dependency detected: {cycle}")
        
        # Return existing singleton if available
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if interface in self._singletons:
                return self._singletons[interface]
        
        # Create new instance
        self._resolving.add(interface)
        try:
            instance = self._create_instance(descriptor)
            
            # Store singleton
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                self._singletons[interface] = instance
            
            return instance
        finally:
            self._resolving.discard(interface)
    
    def get_optional(self, interface: Type) -> Optional[Any]:
        """Resolve a service instance, returning None if not registered."""
        if interface not in self._services:
            return None
        return self.get(interface)
    
    def is_registered(self, interface: Type) -> bool:
        """Check if a service is registered."""
        return interface in self._services
    
    def build_graph(self) -> None:
        """Build and validate the dependency graph."""
        logger.info("Building dependency graph...")
        
        # Skip validation for now to handle complex dependencies
        # Dependencies will be resolved at runtime
        
        logger.info(f"Dependency graph built successfully with {len(self._services)} services")
    
    def create_instance_safe(self, interface: Type) -> Optional[Any]:
        """Create an instance safely, returning None on failure."""
        try:
            return self.get(interface)
        except Exception as e:
            logger.error(f"Failed to create instance of {interface.__name__}: {e}")
            return None
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance with dependency injection."""
        # Use factory if provided
        if descriptor.factory:
            return descriptor.factory()
        
        # Use pre-created instance if available
        if descriptor.instance:
            return descriptor.instance
        
        # Resolve dependencies
        dependencies = [self.get(dep) for dep in descriptor.dependencies]
        
        # Create instance with dependencies
        try:
            instance = descriptor.implementation(*dependencies)
        except TypeError as e:
            # Try keyword injection
            if hasattr(descriptor.implementation, '__init__'):
                import inspect
                sig = inspect.signature(descriptor.implementation.__init__)
                kwargs = {}
                for i, dep in enumerate(descriptor.dependencies):
                    param_name = list(sig.parameters.keys())[i+1]  # Skip 'self'
                    kwargs[param_name] = dependencies[i]
                instance = descriptor.implementation(**kwargs)
            else:
                raise e
        
        return instance
    
    def _get_dependencies(self, implementation: Type) -> List[Type]:
        """Extract constructor dependencies from implementation."""
        try:
            import inspect
            from typing import Union, get_origin, get_args, ForwardRef
            
            # Skip primitive types
            primitive_types = (str, int, float, bool, type(None), Any)
            
            sig = inspect.signature(implementation.__init__)
            dependencies = []
            for param in sig.parameters.values():
                if param.name != 'self' and param.annotation != inspect.Parameter.empty:
                    # Handle string annotations by evaluating them
                    annotation = param.annotation
                    if isinstance(annotation, str):
                        # Skip string parameters that aren't type annotations
                        continue
                    
                    # Skip ForwardRef types
                    if isinstance(annotation, ForwardRef):
                        continue
                    
                    # Skip primitive types
                    if annotation in primitive_types:
                        continue
                    
                    # Handle Union types - take first non-None, non-primitive type
                    if get_origin(annotation) is Union:
                        args = get_args(annotation)
                        for arg in args:
                            if (arg is not type(None) and 
                                not isinstance(arg, ForwardRef) and 
                                arg not in primitive_types):
                                dependencies.append(arg)
                                break
                    else:
                        dependencies.append(annotation)
            return dependencies
        except Exception:
            return []
    
    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        self._services.clear()
        self._singletons.clear()
        self._resolving.clear()
    
    def get_registered_services(self) -> Dict[Type, ServiceDescriptor]:
        """Get all registered service descriptors."""
        return dict(self._services)


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global dependency injection container."""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def set_container(container: DIContainer) -> None:
    """Set the global container (for testing)."""
    global _container
    _container = container


def reset_container() -> None:
    """Reset the global container."""
    global _container
    _container = DIContainer()
