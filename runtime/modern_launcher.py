"""
runtime/modern_launcher.py

Modern launcher using the 4-layer architecture with proper startup phases.

ServiceContainer -> ModuleRegistry -> LifecycleManager -> RuntimeOrchestrator
"""

import asyncio
import logging
from typing import Optional

from runtime.runtime_orchestrator import RuntimeOrchestrator, get_runtime_orchestrator
from runtime.profiles import select_profile
from shared.capability_flags import CapabilityFlags
from runtime.runtime_config import RuntimeConfig

log = logging.getLogger(__name__)


class ModernLauncher:
    """
    Modern launcher with proper 4-layer architecture.
    
    Implements deterministic startup phases:
    PHASE 0 — Core Services
    PHASE 1 — Communication  
    PHASE 2 — Runtime Control
    PHASE 3 — Monitoring
    PHASE 4 — Cognition
    PHASE 5 — Shell Systems
    """
    
    def __init__(self):
        self.orchestrator: Optional[RuntimeOrchestrator] = None
        self.startup_time: Optional[float] = None
    
    async def launch(
        self,
        profile_override: Optional[str] = None,
        safe_mode: bool = False,
        runtime_config: Optional[RuntimeConfig] = None
    ) -> bool:
        """
        Launch the Kitsu system using modern architecture.
        
        Args:
            profile_override: Hardware profile override
            safe_mode: Force safe mode startup
            runtime_config: Runtime configuration
            
        Returns:
            True if launch successful, False otherwise
        """
        self.startup_time = asyncio.get_event_loop().time()
        
        try:
            log.info("=== Kitsu Modern Launcher Starting ===")
            
            # Step 1: Initialize Runtime Orchestrator
            self.orchestrator = get_runtime_orchestrator()
            
            # Step 2: Select hardware profile and capabilities
            profile = select_profile(profile_override=profile_override, safe_mode=safe_mode)
            log.info(f"Selected hardware profile: {profile.name}")
            
            flags = CapabilityFlags.from_profile(profile.profile_definition.flags)
            diagnostics = flags.validate()
            for diagnostic in diagnostics:
                log.warning(diagnostic)
            
            # Step 3: Register modules based on capabilities
            await self._register_modules_by_capabilities(flags)
            
            # Step 4: Execute startup sequence
            success = await self.orchestrator.startup()
            
            if success:
                startup_duration = asyncio.get_event_loop().time() - self.startup_time
                log.info(f"=== Kitsu Startup Complete in {startup_duration:.2f}s ===")
                
                # Lock capability flags after successful startup
                flags.lock()
                log.info("Capability flags locked")
                
                return True
            else:
                log.error("=== Kitsu Startup Failed ===")
                return False
                
        except Exception as e:
            log.error(f"Launch failed with exception: {e}", exc_info=True)
            return False
    
    async def _create_module_instance_with_di(self, module_id: str) -> bool:
        """Create module instance using dependency injection."""
        module_info = self.orchestrator.module_registry.get_module_info(module_id)
        if not module_info:
            return False
        
        try:
            # Use container to resolve dependencies automatically
            instance = self.orchestrator.container.get(module_info.module_class)
            module_info.instance = instance
            module_info.status = ModuleStatus.REGISTERED
            
            log.info(f"Created instance for module {module_id} with DI")
            return True
            
        except Exception as e:
            log.error(f"Failed to create instance for {module_id}: {e}")
            module_info.status = ModuleStatus.FAILED
            return False
    
    async def _register_modules_by_capabilities(self, flags: CapabilityFlags):
        """Register modules based on capability flags."""
        module_registry = self.orchestrator.module_registry
        
        # Core monitoring modules (always registered)
        # These will be created with DI, so no string dependencies needed
        module_registry.register_module(
            "core.health",
            self._create_health_monitor_class(),
            dependencies=[]
        )
        
        module_registry.register_module(
            "core.performance_manager", 
            self._create_performance_manager_class(),
            dependencies=[]
        )
        
        # AI modules based on capabilities
        if flags.use_fast_brain:
            from domain.ai.fast_brain.provider import FastBrainProvider
            module_registry.register_module("ai.fast_brain", FastBrainProvider)
        
        if flags.use_slm:
            from domain.ai.slm.provider import SLMProvider
            module_registry.register_module("ai.slm", SLMProvider)
        
        if flags.use_llm:
            from domain.ai.llm.provider import LLMProvider
            module_registry.register_module("ai.llm", LLMProvider)
        
        # Personality system
        if flags.use_emotion:
            module_registry.register_module(
                "domain.personality.emotion_engine",
                self._create_emotion_engine_class()
            )
            module_registry.register_module(
                "domain.personality.memory_manager",
                self._create_memory_manager_class()
            )
            module_registry.register_module(
                "domain.personality.emotion_controller",
                self._create_emotion_controller_class(),
                dependencies=[]
            )
        
        # Avatar system
        if flags.use_2d or flags.use_3d:
            from interfaces.desktop.avatar.controller import AvatarController
            module_registry.register_module("interfaces.avatar", AvatarController)
        
        log.info(f"Registered modules based on capabilities: {len(module_registry.get_all_modules())} total")
    
    def _create_health_monitor_class(self):
        """Create a health monitor class that can be instantiated with DI."""
        from runtime.health import HealthMonitor
        return HealthMonitor
    
    def _create_performance_manager_class(self):
        """Create a performance manager class that can be instantiated with DI."""
        from runtime.performance_manager import PerformanceManager
        return PerformanceManager
    
    def _create_emotion_engine_class(self):
        """Create an emotion engine class that can be instantiated with DI."""
        from domain.personality.emotion_engine import EmotionEngine
        return EmotionEngine
    
    def _create_memory_manager_class(self):
        """Create a memory manager class that can be instantiated with DI."""
        from domain.personality.memory_manager import MemoryManager
        return MemoryManager
    
    def _create_emotion_controller_class(self):
        """Create an emotion controller class that can be instantiated with DI."""
        from domain.personality.emotion_controller import EmotionController
        return EmotionController
    
    async def shutdown(self) -> bool:
        """Graceful shutdown of the system."""
        if not self.orchestrator:
            return True
        
        try:
            log.info("=== Kitsu Shutdown Starting ===")
            
            success = await self.orchestrator.shutdown()
            
            if success:
                log.info("=== Kitsu Shutdown Complete ===")
            else:
                log.warning("=== Kitsu Shutdown Had Issues ===")
            
            return success
            
        except Exception as e:
            log.error(f"Shutdown failed: {e}", exc_info=True)
            return False
    
    async def get_system_status(self):
        """Get current system status."""
        if not self.orchestrator:
            return {"status": "not_running"}
        
        return await self.orchestrator.get_system_status()


# Global launcher instance
_launcher: Optional[ModernLauncher] = None


def get_modern_launcher() -> ModernLauncher:
    """Get the global modern launcher instance."""
    global _launcher
    if _launcher is None:
        _launcher = ModernLauncher()
    return _launcher


async def launch_kitsu(
    profile_override: Optional[str] = None,
    safe_mode: bool = False,
    runtime_config: Optional[RuntimeConfig] = None
) -> bool:
    """
    Launch Kitsu using the modern architecture.
    
    This is the main entry point for the new system.
    """
    launcher = get_modern_launcher()
    return await launcher.launch(
        profile_override=profile_override,
        safe_mode=safe_mode,
        runtime_config=runtime_config
    )


async def shutdown_kitsu() -> bool:
    """Shutdown Kitsu gracefully."""
    launcher = get_modern_launcher()
    return await launcher.shutdown()
