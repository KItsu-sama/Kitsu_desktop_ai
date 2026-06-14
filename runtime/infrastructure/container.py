"""
runtime/infrastructure/container.py

Production-grade Dependency Injection Container for the Kitsu Runtime.

Features:
- Deterministic circular dependency tracing
- Singleton / Scoped / Transient lifetimes
- Async-safe resolution tracking via ContextVar
- Runtime freeze locking
- Dependency graph validation
- Optional dependency support
- Async factory support
- Disposal lifecycle management
- Scope isolation
- Constructor introspection with type resolution
- Captive dependency validation
- Sync/async resolution boundary enforcement
"""

from __future__ import annotations

import inspect
import logging
import sys
from contextvars import ContextVar
from enum import Enum
from types import UnionType
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
    ForwardRef,
)

logger = logging.getLogger(__name__)


# ============================================================
# Resolution Context
# ============================================================

_resolution_stack: ContextVar[List[Type]] = ContextVar(
    "_resolution_stack",
    default=[],
)


# ============================================================
# Lifetimes
# ============================================================


class ServiceLifetime(Enum):
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


# ============================================================
# Dependency Specification
# ============================================================


class DependencySpec:
    def __init__(self, dependency_type: Type, optional: bool = False):
        self.dependency_type = dependency_type
        self.optional = optional


# ============================================================
# Service Descriptor
# ============================================================


class ServiceDescriptor:
    def __init__(
        self,
        interface: Type,
        implementation: Type,
        lifetime: ServiceLifetime,
        dependencies: Dict[str, DependencySpec],
        factory: Optional[Callable[..., Any]] = None,
        instance: Optional[Any] = None,
    ):
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.dependencies = dependencies
        self.factory = factory
        self.instance = instance


# ============================================================
# Exceptions
# ============================================================


class DIContainerError(Exception):
    pass


class CircularDependencyError(DIContainerError):
    pass


class ServiceNotRegisteredError(DIContainerError):
    pass


class LifetimeViolationError(DIContainerError):
    pass


class FrozenContainerError(DIContainerError):
    pass


class AsyncResolutionError(DIContainerError):
    pass


# ============================================================
# Scope
# ============================================================


class DIScope:
    """Scoped resolution context."""

    def __init__(self, container: DIContainer):
        self._container = container
        self._scoped_instances: Dict[Type, Any] = {}
        self._disposed = False

    def get(self, interface: Type) -> Any:
        return self._container._resolve(interface, self)

    async def get_async(self, interface: Type) -> Any:
        return await self._container._resolve_async(interface, self)

    async def dispose(self) -> None:
        if self._disposed:
            return

        for instance in reversed(list(self._scoped_instances.values())):
            await self._container._dispose_instance(instance)

        self._scoped_instances.clear()
        self._disposed = True


# ============================================================
# Main Container
# ============================================================


class DIContainer:
    """Production-grade dependency injection container."""

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._frozen: bool = False

    # ========================================================
    # Registration
    # ========================================================

    def register_singleton(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._register(
            interface,
            implementation or interface,
            ServiceLifetime.SINGLETON,
            factory,
        )

    def register_scoped(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._register(
            interface,
            implementation or interface,
            ServiceLifetime.SCOPED,
            factory,
        )

    def register_transient(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._register(
            interface,
            implementation or interface,
            ServiceLifetime.TRANSIENT,
            factory,
        )

    def register_instance(self, interface: Type, instance: Any) -> None:
        self._assert_not_frozen()

        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=type(instance),
            lifetime=ServiceLifetime.SINGLETON,
            dependencies={},
            instance=instance,
        )

        self._services[interface] = descriptor
        self._singletons[interface] = instance

        logger.debug("Registered instance: %s", getattr(interface, "__name__", str(interface)))

    def _register(
        self,
        interface: Type,
        implementation: Type,
        lifetime: ServiceLifetime,
        factory: Optional[Callable[..., Any]],
    ) -> None:
        self._assert_not_frozen()

        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime,
            dependencies=self._get_dependencies(implementation),
            factory=factory,
        )

        self._services[interface] = descriptor

        logger.debug(
            "Registered %s: %s -> %s",
            lifetime.value,
            getattr(interface, "__name__", str(interface)),
            getattr(implementation, "__name__", str(implementation)),
        )

    # ========================================================
    # Freeze
    # ========================================================

    def freeze(self) -> None:
        if not self._frozen:
            self._frozen = True
            logger.info("DIContainer frozen successfully.")

    def _assert_not_frozen(self) -> None:
        if self._frozen:
            raise FrozenContainerError("Container is frozen and cannot be modified.")

    # ========================================================
    # Scope Management
    # ========================================================

    def create_scope(self) -> DIScope:
        return DIScope(self)

    # ========================================================
    # Public Resolution API
    # ========================================================

    def get(self, interface: Type) -> Any:
        return self._resolve(interface, None)

    async def get_async(self, interface: Type) -> Any:
        return await self._resolve_async(interface, None)

    def get_optional(self, interface: Type) -> Optional[Any]:
        if interface not in self._services:
            return None
        return self.get(interface)

    async def get_optional_async(self, interface: Type) -> Optional[Any]:
        if interface not in self._services:
            return None
        return await self.get_async(interface)

    # ========================================================
    # Internal Resolution
    # ========================================================

    def _resolve(self, interface: Type, scope: Optional[DIScope]) -> Any:
        descriptor = self._require_descriptor(interface)

        stack = list(_resolution_stack.get())
        if interface in stack:
            cycle = " -> ".join([x.__name__ for x in stack] + [interface.__name__])
            raise CircularDependencyError(cycle)

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if interface in self._singletons:
                return self._singletons[interface]

        if descriptor.lifetime == ServiceLifetime.SCOPED:
            if scope is None:
                raise DIContainerError(
                    f"Scoped service '{interface.__name__}' requires a scope."
                )
            if interface in scope._scoped_instances:
                return scope._scoped_instances[interface]

        if self._is_async_service(descriptor):
            raise AsyncResolutionError(
                f"Service '{interface.__name__}' is asynchronous. Use get_async()."
            )

        stack.append(interface)
        token = _resolution_stack.set(stack)
        try:
            instance = self._create_instance_sync(descriptor, scope)
            self._store_instance(interface, descriptor, instance, scope)
            return instance
        finally:
            _resolution_stack.reset(token)

    async def _resolve_async(self, interface: Type, scope: Optional[DIScope]) -> Any:
        descriptor = self._require_descriptor(interface)

        stack = list(_resolution_stack.get())
        if interface in stack:
            cycle = " -> ".join([x.__name__ for x in stack] + [interface.__name__])
            raise CircularDependencyError(cycle)

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if interface in self._singletons:
                return self._singletons[interface]

        if descriptor.lifetime == ServiceLifetime.SCOPED:
            if scope is None:
                raise DIContainerError(
                    f"Scoped service '{interface.__name__}' requires a scope."
                )
            if interface in scope._scoped_instances:
                return scope._scoped_instances[interface]

        stack.append(interface)
        token = _resolution_stack.set(stack)
        try:
            instance = await self._create_instance_async(descriptor, scope)
            self._store_instance(interface, descriptor, instance, scope)
            return instance
        finally:
            _resolution_stack.reset(token)

    # ========================================================
    # Instance Storage
    # ========================================================

    def _store_instance(
        self,
        interface: Type,
        descriptor: ServiceDescriptor,
        instance: Any,
        scope: Optional[DIScope],
    ) -> None:
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            self._singletons[interface] = instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            assert scope is not None
            scope._scoped_instances[interface] = instance

    # ========================================================
    # Sync Construction
    # ========================================================

    def _create_instance_sync(self, descriptor: ServiceDescriptor, scope: Optional[DIScope]) -> Any:
        if descriptor.instance is not None:
            return descriptor.instance

        if descriptor.factory:
            result = descriptor.factory(self)
            self._validate_factory_result(descriptor.interface, result)
            return result

        kwargs: Dict[str, Any] = {}
        for name, dep in descriptor.dependencies.items():
            if dep.optional:
                kwargs[name] = self.get_optional(dep.dependency_type)
            else:
                kwargs[name] = self._resolve(dep.dependency_type, scope)

        return descriptor.implementation(**kwargs)

    # ========================================================
    # Async Construction
    # ========================================================

    async def _create_instance_async(self, descriptor: ServiceDescriptor, scope: Optional[DIScope]) -> Any:
        if descriptor.instance is not None:
            return descriptor.instance

        if descriptor.factory:
            if inspect.iscoroutinefunction(descriptor.factory):
                result = await descriptor.factory(self)
            else:
                result = descriptor.factory(self)
            self._validate_factory_result(descriptor.interface, result)
            return result

        kwargs: Dict[str, Any] = {}
        for name, dep in descriptor.dependencies.items():
            if dep.optional:
                kwargs[name] = await self.get_optional_async(dep.dependency_type)
            else:
                kwargs[name] = await self._resolve_async(dep.dependency_type, scope)

        implementation = descriptor.implementation
        create_method = getattr(implementation, "create", None)
        if create_method and inspect.iscoroutinefunction(create_method):
            return await create_method(**kwargs)

        return implementation(**kwargs)

    # ========================================================
    # Validation
    # ========================================================

    def build_graph(self) -> None:
        logger.info("Validating dependency graph...")

        errors: List[str] = []

        for interface, descriptor in self._services.items():
            for param_name, dep in descriptor.dependencies.items():
                dep_type = dep.dependency_type
                if dep.optional:
                    continue

                if dep_type not in self._services:
                    errors.append(
                        f"Missing dependency: {interface.__name__} requires {dep_type.__name__} for parameter '{param_name}'"
                    )
                    continue

                dep_descriptor = self._services[dep_type]

                if (
                    descriptor.lifetime == ServiceLifetime.SINGLETON
                    and dep_descriptor.lifetime == ServiceLifetime.TRANSIENT
                ):
                    errors.append(
                        f"Captive dependency violation: Singleton '{interface.__name__}' depends on transient '{dep_type.__name__}'"
                    )

                if (
                    not self._is_async_service(descriptor)
                    and self._is_async_service(dep_descriptor)
                ):
                    errors.append(
                        f"Sync/Async violation: Sync service '{interface.__name__}' depends on async service '{dep_type.__name__}'"
                    )

        try:
            self._validate_cycles()
        except CircularDependencyError as e:
            errors.append(str(e))

        if errors:
            raise DIContainerError(
                "Dependency graph validation failed:\n\n" + "\n".join(errors)
            )

        logger.info(
            "Dependency graph validated successfully. %d services verified.",
            len(self._services),
        )

    def _validate_cycles(self) -> None:
        visited = set()
        stack: List[Type] = []

        def dfs(interface: Type) -> None:
            if interface in stack:
                cycle = " -> ".join([x.__name__ for x in stack] + [interface.__name__])
                raise CircularDependencyError(cycle)

            if interface in visited:
                return

            visited.add(interface)
            stack.append(interface)

            descriptor = self._services.get(interface)
            if descriptor:
                for dep in descriptor.dependencies.values():
                    dep_type = dep.dependency_type
                    if dep_type in self._services:
                        dfs(dep_type)

            stack.pop()

        for interface in self._services:
            dfs(interface)

    # ========================================================
    # Disposal
    # ========================================================

    async def shutdown(self) -> None:
        logger.info("Shutting down DIContainer...")
        for instance in reversed(list(self._singletons.values())):
            await self._dispose_instance(instance)
        self._singletons.clear()

    async def _dispose_instance(self, instance: Any) -> None:
        try:
            if hasattr(instance, "dispose"):
                result = instance.dispose()
                if inspect.isawaitable(result):
                    await result
            elif hasattr(instance, "close"):
                result = instance.close()
                if inspect.isawaitable(result):
                    await result
            elif hasattr(instance, "shutdown"):
                result = instance.shutdown()
                if inspect.isawaitable(result):
                    await result
            elif hasattr(instance, "__aexit__"):
                await instance.__aexit__(None, None, None)
        except Exception:
            logger.exception("Failed to dispose instance: %s", type(instance).__name__)

    # ========================================================
    # Dependency Introspection
    # ========================================================

    def _get_dependencies(self, implementation: Type) -> Dict[str, DependencySpec]:
        dependencies: Dict[str, DependencySpec] = {}

        if (
            not hasattr(implementation, "__init__")
            or implementation.__init__ is object.__init__
        ):
            return dependencies

        try:
            module = sys.modules.get(implementation.__module__)
            global_ns = getattr(module, "__dict__", None)

            signature = inspect.signature(implementation.__init__)
            type_hints = inspect.get_annotations(
                implementation.__init__,
                globals=global_ns,
                eval_str=True,
            )

            for param_name, param in signature.parameters.items():
                if param_name == "self":
                    continue

                if param.kind in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ):
                    continue

                annotation = type_hints.get(param_name, param.annotation)
                if annotation == inspect.Parameter.empty:
                    continue

                dep_type, optional = self._unwrap_type(annotation)
                if dep_type:
                    dependencies[param_name] = DependencySpec(
                        dependency_type=dep_type,
                        optional=optional,
                    )
        except Exception:
            logger.exception(
                "Failed dependency extraction for %s",
                implementation.__name__,
            )

        return dependencies

    def _unwrap_type(self, annotation: Any) -> tuple[Optional[Type], bool]:
        origin = get_origin(annotation)

        if origin in (Union, UnionType):
            args = get_args(annotation)
            non_none = [
                arg
                for arg in args
                if arg is not type(None)
                and not isinstance(arg, ForwardRef)
            ]
            optional = len(non_none) != len(args)
            if non_none:
                return non_none[0], optional
            return None, optional

        if isinstance(annotation, ForwardRef):
            return None, False

        return annotation, False

    # ========================================================
    # Helpers
    # ========================================================

    def _require_descriptor(self, interface: Type) -> ServiceDescriptor:
        descriptor = self._services.get(interface)
        if descriptor is None:
            raise ServiceNotRegisteredError(
                f"Service '{interface.__name__}' is not registered."
            )
        return descriptor

    def _validate_factory_result(self, interface: Type, result: Any) -> None:
        if result is None:
            raise DIContainerError(f"Factory for '{interface.__name__}' returned None.")
        if not isinstance(result, interface):
            raise DIContainerError(
                f"Factory for '{interface.__name__}' returned invalid type: {type(result).__name__}"
            )

    def _is_async_service(self, descriptor: ServiceDescriptor) -> bool:
        if descriptor.factory and inspect.iscoroutinefunction(descriptor.factory):
            return True
        create_method = getattr(descriptor.implementation, "create", None)
        if create_method and inspect.iscoroutinefunction(create_method):
            return True
        return False

    # ========================================================
    # Diagnostics
    # ========================================================

    def is_registered(self, interface: Type) -> bool:
        return interface in self._services

    def get_registered_services(self) -> Dict[str, Any]:
        return {k.__name__: v for k, v in self._services.items()}

    def dump_graph(self) -> Dict[str, Any]:
        output: Dict[str, Any] = {}
        for interface, descriptor in self._services.items():
            output[interface.__name__] = {
                "implementation": descriptor.implementation.__name__,
                "lifetime": descriptor.lifetime.value,
                "dependencies": {
                    name: dep.dependency_type.__name__
                    for name, dep in descriptor.dependencies.items()
                },
            }
        return output

    # ========================================================
    # Testing Utilities
    # ========================================================

    def clear(self) -> None:
        self._services.clear()
        self._singletons.clear()
        self._frozen = False


# ============================================================
# Global container accessor (expected by imports)
# ============================================================

_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Return the global DIContainer instance.

    Several runtime modules import this symbol.
    """

    global _container
    if _container is None:
        _container = DIContainer()
    return _container

