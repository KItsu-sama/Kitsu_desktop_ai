"""
runtime/legacy_compat.py

Legacy compatibility layer for modern architecture.

Provides adapters and compatibility shims to bridge legacy modules
with the modern 4-layer architecture (ServiceContainer → ModuleRegistry → LifecycleManager → RuntimeOrchestrator).

This allows gradual migration while maintaining backward compatibility.
"""

import asyncio
import logging
from typing import Any, Optional, Dict, List

from domain.contracts.lifecycle import RuntimeModule, ModuleState
from runtime.container import DIContainer
from runtime.runtime_orchestrator import RuntimeOrchestrator

log = logging.getLogger(__name__)


class LegacyModuleAdapter:
    """
    Adapter for legacy modules to conform to modern RuntimeModule interface.
    
    Provides standardized lifecycle methods for modules that don't implement
    the modern RuntimeModule protocol.
    """
    
    def __init__(self, module: Any, module_id: str):
        self.module = module
        self.module_id = module_id
        self._state = ModuleState.CREATED
    
    async def start(self) -> bool:
        """Start the legacy module with compatibility methods."""
        if self._state not in [ModuleState.CREATED, ModuleState.STOPPED]:
            return False
        
        self._state = ModuleState.INITIALIZING
        
        try:
            # Try modern start method
            if hasattr(self.module, 'start'):
                result = await self.module.start()
                self._state = ModuleState.RUNNING if result else ModuleState.FAILED
                return result
            
            # Try legacy initialize method
            elif hasattr(self.module, 'initialize'):
                result = await self.module.initialize()
                self._state = ModuleState.RUNNING if result else ModuleState.FAILED
                return result
            
            # Try synchronous initialize
            elif hasattr(self.module, 'initialize'):
                result = self.module.initialize()
                self._state = ModuleState.RUNNING if result else ModuleState.FAILED
                return bool(result)
            
            # No initialization needed - mark as running
            else:
                self._state = ModuleState.RUNNING
                log.info(f"Legacy module {self.module_id} marked as running (no init method)")
                return True
                
        except Exception as e:
            log.error(f"Failed to start legacy module {self.module_id}: {e}")
            self._state = ModuleState.FAILED
            return False
    
    async def stop(self) -> bool:
        """Stop the legacy module with compatibility methods."""
        if self._state not in [ModuleState.RUNNING, ModuleState.DEGRADED]:
            return True
        
        self._state = ModuleState.STOPPING
        
        try:
            # Try modern stop method
            if hasattr(self.module, 'stop'):
                result = await self.module.stop()
                self._state = ModuleState.STOPPED if result else ModuleState.FAILED
                return result
            
            # Try legacy cleanup method
            elif hasattr(self.module, 'cleanup'):
                result = await self.module.cleanup()
                self._state = ModuleState.STOPPED if result else ModuleState.FAILED
                return result
            
            # Try synchronous cleanup
            elif hasattr(self.module, 'cleanup'):
                result = self.module.cleanup()
                self._state = ModuleState.STOPPED if result else ModuleState.FAILED
                return bool(result)
            
            # No cleanup needed - mark as stopped
            else:
                self._state = ModuleState.STOPPED
                log.info(f"Legacy module {self.module_id} marked as stopped (no cleanup method)")
                return True
                
        except Exception as e:
            log.error(f"Failed to stop legacy module {self.module_id}: {e}")
            self._state = ModuleState.FAILED
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check with compatibility methods."""
        try:
            # Try modern health check
            if hasattr(self.module, 'health_check'):
                return await self.module.health_check()
            
            # Try synchronous health check
            elif hasattr(self.module, 'health_check'):
                return self.module.health_check()
            
            # Default health check based on state
            else:
                return {
                    "ok": self._state in [ModuleState.RUNNING, ModuleState.DEGRADED],
                    "state": self._state.value,
                    "latency_ms": 0.0,
                    "module_type": "legacy"
                }
                
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "state": self._state.value,
                "module_type": "legacy"
            }
    
    def get_state(self) -> ModuleState:
        """Get current module state."""
        return self._state
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped module."""
        return getattr(self.module, name)


class LegacyCompatibilityOrchestrator:
    """
    Compatibility orchestrator that bridges legacy launcher with modern architecture.
    
    Provides the same interface as RuntimeOrchestrator but uses modern
    architecture internally while maintaining legacy compatibility.
    """
    
    def __init__(self):
        self.modern_orchestrator: Optional[RuntimeOrchestrator] = None
        self.legacy_adapters: Dict[str, LegacyModuleAdapter] = {}
        self._running = False
    
    async def initialize(self, profile_override: Optional[str] = None, safe_mode: bool = False):
        """Initialize the modern orchestrator with legacy compatibility."""
        try:
            # Initialize modern orchestrator
            from runtime.runtime_orchestrator import get_runtime_orchestrator
            self.modern_orchestrator = get_runtime_orchestrator()
            
            # Start modern orchestrator
            success = await self.modern_orchestrator.startup()
            if success:
                self._running = True
                log.info("Legacy compatibility orchestrator initialized successfully")
                return True
            else:
                log.error("Failed to initialize modern orchestrator")
                return False
                
        except Exception as e:
            log.error(f"Failed to initialize legacy compatibility orchestrator: {e}")
            return False
    
    async def start_legacy_module(self, module_id: str, module_class: type, **kwargs) -> bool:
        """Start a legacy module with compatibility adapter."""
        try:
            # Create module instance using DI container
            if self.modern_orchestrator:
                instance = self.modern_orchestrator.container.get(module_class)
            else:
                instance = module_class(**kwargs)
            
            # Wrap in compatibility adapter
            adapter = LegacyModuleAdapter(instance, module_id)
            self.legacy_adapters[module_id] = adapter
            
            # Start the adapter
            success = await adapter.start()
            if success:
                log.info(f"Legacy module {module_id} started via compatibility adapter")
            else:
                log.error(f"Failed to start legacy module {module_id}")
            
            return success
            
        except Exception as e:
            log.error(f"Failed to start legacy module {module_id}: {e}")
            return False
    
    async def stop_legacy_module(self, module_id: str) -> bool:
        """Stop a legacy module via compatibility adapter."""
        adapter = self.legacy_adapters.get(module_id)
        if not adapter:
            log.warning(f"Legacy module {module_id} not found in adapters")
            return False
        
        return await adapter.stop()
    
    async def shutdown(self) -> bool:
        """Shutdown all systems."""
        if not self._running:
            return True
        
        try:
            # Stop all legacy adapters
            for module_id in list(self.legacy_adapters.keys()):
                await self.stop_legacy_module(module_id)
            
            # Shutdown modern orchestrator
            if self.modern_orchestrator:
                await self.modern_orchestrator.shutdown()
            
            self._running = False
            log.info("Legacy compatibility orchestrator shutdown complete")
            return True
            
        except Exception as e:
            log.error(f"Failed to shutdown legacy compatibility orchestrator: {e}")
            return False
    
    def get_module(self, module_id: str) -> Optional[Any]:
        """Get legacy module instance."""
        adapter = self.legacy_adapters.get(module_id)
        return adapter.module if adapter else None
    
    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running


# Global compatibility orchestrator instance
_compat_orchestrator: Optional[LegacyCompatibilityOrchestrator] = None


def get_legacy_orchestrator() -> LegacyCompatibilityOrchestrator:
    """Get the global legacy compatibility orchestrator."""
    global _compat_orchestrator
    if _compat_orchestrator is None:
        _compat_orchestrator = LegacyCompatibilityOrchestrator()
    return _compat_orchestrator


async def bootstrap_legacy_compat(
    profile_override: Optional[str] = None,
    safe_mode: bool = False
) -> bool:
    """
    Bootstrap legacy compatibility layer with modern architecture.
    
    This is the main entry point for legacy systems to use the modern architecture.
    """
    orchestrator = get_legacy_orchestrator()
    return await orchestrator.initialize(profile_override, safe_mode)
