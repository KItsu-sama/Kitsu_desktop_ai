"""
domain/contracts/lifecycle.py

Standardized lifecycle interfaces and contracts for all modules.

Provides consistent interfaces for:
- Module lifecycle (start/stop)
- Monitoring capabilities  
- Module state management
"""

from __future__ import annotations
from typing import Protocol, runtime_checkable
from enum import Enum


class ModuleState(Enum):
    """Standard module states for all runtime modules."""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


@runtime_checkable
class RuntimeModule(Protocol):
    """Protocol for all runtime modules."""
    
    module_id: str
    required_flags: list[str]
    
    async def start(self) -> bool:
        """Start the module."""
        ...
    
    async def stop(self) -> bool:
        """Stop the module."""
        ...
    
    async def health_check(self) -> dict:
        """Check module health."""
        ...
    
    def get_state(self) -> ModuleState:
        """Get current module state."""
        ...


@runtime_checkable
class Monitorable(Protocol):
    """Protocol for modules that support monitoring."""
    
    async def start_monitoring(self) -> None:
        """Start monitoring activities."""
        ...
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring activities."""
        ...
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        ...


@runtime_checkable
class ResourceAware(Protocol):
    """Protocol for modules that are resource-aware."""
    
    async def handle_resource_pressure(self, resource_type: str, level: float) -> None:
        """Handle resource pressure events."""
        ...
    
    async def handle_tier_change(self, tier: str) -> None:
        """Handle tier change events."""
        ...


@runtime_checkable
class Failurable(Protocol):
    """Protocol for modules that support failure recovery."""
    
    async def handle_failure(self, error: Exception, context: dict) -> bool:
        """Handle module failure. Return True if recovered."""
        ...
    
    async def attempt_recovery(self) -> bool:
        """Attempt automatic recovery."""
        ...
    
    def get_failure_count(self) -> int:
        """Get number of failures."""
        ...


class BaseModule:
    """Base class for all modules with common lifecycle management."""
    
    def __init__(self, module_id: str, required_flags: list[str] = None):
        self.module_id = module_id
        self.required_flags = required_flags or []
        self._state = ModuleState.CREATED
        self._failure_count = 0
        self._last_error: Exception = None
    
    async def start(self) -> bool:
        """Default start implementation."""
        if self._state not in [ModuleState.CREATED, ModuleState.STOPPED]:
            return False
        
        self._state = ModuleState.INITIALIZING
        
        try:
            # Call subclass implementation
            result = await self._on_start()
            if result:
                self._state = ModuleState.RUNNING
            else:
                self._state = ModuleState.FAILED
            return result
        except Exception as e:
            self._handle_error(e)
            self._state = ModuleState.FAILED
            return False
    
    async def stop(self) -> bool:
        """Default stop implementation."""
        if self._state not in [ModuleState.RUNNING, ModuleState.DEGRADED]:
            return True
        
        self._state = ModuleState.STOPPING
        
        try:
            # Call subclass implementation
            result = await self._on_stop()
            self._state = ModuleState.STOPPED
            return result
        except Exception as e:
            self._handle_error(e)
            self._state = ModuleState.FAILED
            return False
    
    async def health_check(self) -> dict:
        """Default health check implementation."""
        try:
            if self._state in [ModuleState.FAILED]:
                return {
                    "ok": False,
                    "state": self._state.value,
                    "error": str(self._last_error) if self._last_error else "Unknown error",
                    "failure_count": self._failure_count
                }
            
            # Call subclass implementation
            health = await self._on_health_check()
            health["state"] = self._state.value
            health["failure_count"] = self._failure_count
            return health
        except Exception as e:
            return {
                "ok": False,
                "state": self._state.value,
                "error": str(e),
                "failure_count": self._failure_count
            }
    
    def get_state(self) -> ModuleState:
        """Get current module state."""
        return self._state
    
    def get_failure_count(self) -> int:
        """Get number of failures."""
        return self._failure_count
    
    def _handle_error(self, error: Exception):
        """Handle error and update failure count."""
        self._last_error = error
        self._failure_count += 1
    
    # Subclass hooks
    async def _on_start(self) -> bool:
        """Hook for subclass start implementation."""
        return True
    
    async def _on_stop(self) -> bool:
        """Hook for subclass stop implementation."""
        return True
    
    async def _on_health_check(self) -> dict:
        """Hook for subclass health check implementation."""
        return {"ok": True, "latency_ms": 0.0}


class ModuleStateManager:
    """Manages state transitions for modules."""
    
    def __init__(self, module: BaseModule):
        self.module = module
        self._state_history: list[tuple[ModuleState, float]] = []
    
    def can_transition_to(self, target_state: ModuleState) -> bool:
        """Check if transition to target state is allowed."""
        current_state = self.module.get_state()
        
        # Define valid transitions
        valid_transitions = {
            ModuleState.CREATED: [ModuleState.INITIALIZING],
            ModuleState.INITIALIZING: [ModuleState.RUNNING, ModuleState.FAILED],
            ModuleState.RUNNING: [ModuleState.DEGRADED, ModuleState.STOPPING],
            ModuleState.DEGRADED: [ModuleState.RUNNING, ModuleState.STOPPING, ModuleState.FAILED],
            ModuleState.FAILED: [ModuleState.INITIALIZING, ModuleState.STOPPED],
            ModuleState.STOPPING: [ModuleState.STOPPED, ModuleState.FAILED],
            ModuleState.STOPPED: [ModuleState.INITIALIZING]
        }
        
        return target_state in valid_transitions.get(current_state, [])
    
    def transition_to(self, target_state: ModuleState) -> bool:
        """Transition to target state if allowed."""
        if not self.can_transition_to(target_state):
            return False
        
        old_state = self.module.get_state()
        # State change would happen here in actual implementation
        # For now, just record the transition
        self._state_history.append((target_state, __import__('time').time()))
        
        return True
    
    def get_state_history(self) -> list[tuple[ModuleState, float]]:
        """Get history of state transitions."""
        return self._state_history.copy()
