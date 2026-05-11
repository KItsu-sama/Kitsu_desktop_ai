"""
domain/core/kitsu_orchestrator.py

Central orchestrator that integrates all critical systems.

This is the "clean shell architecture" that coordinates:
- Capability sandbox system
- Attention engine
- State machine layer
- Resource-aware inference controller
- Tool grounding system
- Energy budget system

Ensures Kitsu feels alive while remaining safe and efficient.
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

# Import all the systems we just created
from domain.capabilities import CAPABILITY_MANAGER, Capability, PermissionLevel
from domain.attention import ATTENTION_MANAGER, AttentionType, UrgencyLevel
from domain.state import BEHAVIOR_STATE_MACHINE, BehaviorState
from domain.inference import RESOURCE_CONTROLLER, InferenceTier, RenderTier
from domain.grounding import TOOL_GROUNDING_SYSTEM, GroundingType
from shared.flags.budgets import BUDGET_MANAGER, BudgetType

log = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    """Overall system status."""
    healthy: bool = True
    safety_level: str = "normal"  # normal, elevated, critical
    performance_mode: str = "balanced"  # minimal, balanced, performance
    active_capabilities: List[str] = None
    current_state: str = "active"
    energy_factor: float = 1.0
    attention_score: float = 0.0
    
    def __post_init__(self):
        if self.active_capabilities is None:
            self.active_capabilities = []


class KitsuOrchestrator:
    """
    Central orchestrator for Kitsu's critical systems.
    
    This is the brain that coordinates all subsystems to ensure:
    - Safety through capability sandboxing
    - Intelligence through attention and grounding
    - Efficiency through resource management
    - Life-like behavior through state machines
    """
    
    def __init__(self):
        self.running = False
        self.tick_interval = 0.1  # 100ms tick rate
        self.last_tick = 0.0
        
        # System status
        self.status = SystemStatus()
        
        # Event callbacks
        self.status_callbacks: List[Callable[[SystemStatus], None]] = []
        
        # Performance tracking
        self.tick_times: List[float] = []
        self.max_tick_history = 100
        
        # Integration setup
        self._setup_system_integration()
        
        log.info("KitsuOrchestrator initialized - all critical systems integrated")
    
    def _setup_system_integration(self):
        """Setup integration between all systems."""
        
        # Attention -> State Machine integration
        ATTENTION_MANAGER.register_callback(
            AttentionType.EMOTIONAL_TRIGGER,
            self._on_emotional_trigger
        )
        
        ATTENTION_MANAGER.register_callback(
            AttentionType.USER_INPUT,
            self._on_user_input
        )
        
        # Resource Controller -> State Machine integration
        RESOURCE_CONTROLLER.register_inference_callback(
            self._on_inference_tier_change
        )
        
        RESOURCE_CONTROLLER.register_render_callback(
            self._on_render_tier_change
        )
        
        # Budget Manager -> Resource Controller integration
        BUDGET_MANAGER.register_callback(
            BudgetType.ENERGY,
            self._on_energy_budget_change
        )
        
        BUDGET_MANAGER.register_callback(
            BudgetType.CPU,
            self._on_cpu_budget_change
        )
        
        # State Machine -> Budget Manager integration
        BEHAVIOR_STATE_MACHINE.register_state_callback(
            BehaviorState.LOW_POWER,
            self._on_low_power_state
        )
        
        BEHAVIOR_STATE_MACHINE.register_state_callback(
            BehaviorState.OVERLOADED,
            self._on_overloaded_state
        )
        
        # Set up capability permission prompt callback
        CAPABILITY_MANAGER.set_prompt_callback(self._on_permission_request)
    
    def _on_emotional_trigger(self, event) -> None:
        """Handle emotional attention events."""
        # Update state machine with emotional context
        BEHAVIOR_STATE_MACHINE.update_system_state(
            system_load=RESOURCE_CONTROLLER.metrics.cpu_percent,
            user_activity=ATTENTION_MANAGER.user_activity,
            attention_level=ATTENTION_MANAGER.get_attention_score()
        )
    
    def _on_user_input(self, event) -> None:
        """Handle user input attention events."""
        # Ground user input to prevent hallucinations
        request_id = f"user_input_{int(time.time())}"
        grounding_results = TOOL_GROUNDING_SYSTEM.ground_request(
            request_id=request_id,
            query=event.metadata.get("input_type", "unknown"),
            source="user_input"
        )
        
        # Update attention based on grounding success
        if grounding_results and any(r.status.value == "verified" for r in grounding_results):
            ATTENTION_MANAGER.add_event(
                AttentionType.USER_INPUT,
                urgency=UrgencyLevel.NORMAL,
                novelty=0.3,
                emotional_weight=0.8,
                source="grounded_input"
            )
    
    def _on_inference_tier_change(self, old_tier: InferenceTier, new_tier: InferenceTier) -> None:
        """Handle inference tier changes."""
        log.info(f"Inference tier changed: {old_tier.value} -> {new_tier.value}")
        
        # Update budget limits based on tier
        if new_tier == InferenceTier.LLM:
            BUDGET_MANAGER.limits[BudgetType.CPU].max_value = 80.0
            BUDGET_MANAGER.limits[BudgetType.MEMORY].max_value = 70.0
        elif new_tier == InferenceTier.SLM:
            BUDGET_MANAGER.limits[BudgetType.CPU].max_value = 60.0
            BUDGET_MANAGER.limits[BudgetType.MEMORY].max_value = 50.0
        else:  # REFLEX
            BUDGET_MANAGER.limits[BudgetType.CPU].max_value = 30.0
            BUDGET_MANAGER.limits[BudgetType.MEMORY].max_value = 30.0
    
    def _on_render_tier_change(self, old_tier: RenderTier, new_tier: RenderTier) -> None:
        """Handle render tier changes."""
        log.info(f"Render tier changed: {old_tier.value} -> {new_tier.value}")
        
        # Update animation budget based on tier
        if new_tier == RenderTier.FULL_3D:
            BUDGET_MANAGER.limits[BudgetType.ANIMATION].max_value = 60.0
        elif new_tier == RenderTier.PARTIAL_3D:
            BUDGET_MANAGER.limits[BudgetType.ANIMATION].max_value = 45.0
        elif new_tier == RenderTier.CHIBI_2D:
            BUDGET_MANAGER.limits[BudgetType.ANIMATION].max_value = 30.0
        else:  # MINIMAL
            BUDGET_MANAGER.limits[BudgetType.ANIMATION].max_value = 15.0
    
    def _on_energy_budget_change(self, budget_type: BudgetType, state) -> None:
        """Handle energy budget changes."""
        energy_factor = BUDGET_MANAGER.get_energy_factor()
        
        # Update resource controller based on energy
        if energy_factor < 0.5:
            # Force lower tiers to save energy
            if RESOURCE_CONTROLLER.current_inference_tier == InferenceTier.LLM:
                RESOURCE_CONTROLLER.force_inference_tier(InferenceTier.SLM)
            if RESOURCE_CONTROLLER.current_render_tier == RenderTier.FULL_3D:
                RESOURCE_CONTROLLER.force_render_tier(RenderTier.CHIBI_2D)
        
        # Update state machine with battery info
        BEHAVIOR_STATE_MACHINE.update_system_state(
            system_load=RESOURCE_CONTROLLER.metrics.cpu_percent,
            battery_level=BUDGET_MANAGER.energy_budget.battery_level,
            user_activity=ATTENTION_MANAGER.user_activity
        )
    
    def _on_cpu_budget_change(self, budget_type: BudgetType, state) -> None:
        """Handle CPU budget changes."""
        if state.status.value == "critical":
            # Force state to overloaded if CPU critical
            BEHAVIOR_STATE_MACHINE.force_state(BehaviorState.OVERLOADED, "cpu_critical")
    
    def _on_low_power_state(self, old_state: BehaviorState, new_state: BehaviorState) -> None:
        """Handle transition to low power state."""
        log.info("Entered low power state - enabling energy saving")
        
        # Enable power saving across all systems
        BUDGET_MANAGER.energy_budget.power_saving_mode = True
        
        # Force minimal resource usage
        RESOURCE_CONTROLLER.force_inference_tier(InferenceTier.REFLEX)
        RESOURCE_CONTROLLER.force_render_tier(RenderTier.MINIMAL)
    
    def _on_overloaded_state(self, old_state: BehaviorState, new_state: BehaviorState) -> None:
        """Handle transition to overloaded state."""
        log.info("Entered overloaded state - reducing activity")
        
        # Disable non-essential capabilities
        high_risk_caps = [
            Capability.DESKTOP_AUTOMATION,
            Capability.CONTROL_BROWSER,
            Capability.EXECUTE_PROGRAMS
        ]
        
        for cap in high_risk_caps:
            CAPABILITY_MANAGER.deny_capability(cap)
    
    def _on_permission_request(self, context) -> bool:
        """Handle capability permission requests."""
        # Check current system state before granting permissions
        if BEHAVIOR_STATE_MACHINE.current_state in [BehaviorState.OVERLOADED, BehaviorState.SLEEPY]:
            log.warning(f"Denying permission {context.capability.value} - system in {BEHAVIOR_STATE_MACHINE.current_state.value}")
            return False
        
        # Check energy budget
        if BUDGET_MANAGER.energy_budget.should_reduce_activity():
            if context.capability in [Capability.DESKTOP_AUTOMATION, Capability.CONTROL_BROWSER]:
                log.warning(f"Denying permission {context.capability.value} - energy saving mode")
                return False
        
        # Check attention level
        if ATTENTION_MANAGER.get_attention_score() < 0.3:
            # Low attention - only allow low-risk operations
            low_risk_caps = [Capability.READ_FILES, Capability.WEB_SEARCH]
            if context.capability not in low_risk_caps:
                log.warning(f"Denying permission {context.capability.value} - low attention")
                return False
        
        # Default to allow with user confirmation
        log.info(f"Requesting permission for {context.capability.value}: {context.reason}")
        return True  # In a real implementation, this would prompt the user
    
    async def start(self) -> None:
        """Start the orchestrator."""
        if self.running:
            log.warning("Orchestrator already running")
            return
        
        self.running = True
        log.info("KitsuOrchestrator started")
        
        # Start the main tick loop
        await self._tick_loop()
    
    async def stop(self) -> None:
        """Stop the orchestrator."""
        self.running = False
        log.info("KitsuOrchestrator stopped")
    
    async def _tick_loop(self) -> None:
        """Main tick loop."""
        while self.running:
            tick_start = time.time()
            
            try:
                await self._tick()
            except Exception as e:
                log.error(f"Error in orchestrator tick: {e}")
            
            # Track performance
            tick_time = time.time() - tick_start
            self.tick_times.append(tick_time)
            if len(self.tick_times) > self.max_tick_history:
                self.tick_times = self.tick_times[-self.max_tick_history//2:]
            
            # Sleep until next tick
            sleep_time = max(0, self.tick_interval - tick_time)
            await asyncio.sleep(sleep_time)
    
    async def _tick(self) -> None:
        """Single tick of the orchestrator."""
        # Update all systems
        RESOURCE_CONTROLLER.update_metrics()
        RESOURCE_CONTROLLER.update_tiers()
        
        BEHAVIOR_STATE_MACHINE.update_system_state(
            system_load=RESOURCE_CONTROLLER.metrics.cpu_percent,
            battery_level=BUDGET_MANAGER.energy_budget.battery_level,
            user_activity=ATTENTION_MANAGER.user_activity,
            attention_level=ATTENTION_MANAGER.get_attention_score()
        )
        
        BEHAVIOR_STATE_MACHINE.check_transitions()
        
        ATTENTION_MANAGER.tick()
        BUDGET_MANAGER.tick()
        
        # Update system status
        self._update_system_status()
        
        # Trigger status callbacks
        for callback in self.status_callbacks:
            try:
                callback(self.status)
            except Exception as e:
                log.error(f"Status callback error: {e}")
    
    def _update_system_status(self) -> None:
        """Update overall system status."""
        # Determine health
        cpu_status = BUDGET_MANAGER.get_budget_status(BudgetType.CPU)
        memory_status = BUDGET_MANAGER.get_budget_status(BudgetType.MEMORY)
        
        self.status.healthy = (
            cpu_status.status.value != "critical" and
            memory_status.status.value != "critical" and
            BEHAVIOR_STATE_MACHINE.current_state != BehaviorState.OVERLOADED
        )
        
        # Determine safety level
        critical_issues = []
        if cpu_status.status.value == "critical":
            critical_issues.append("cpu")
        if memory_status.status.value == "critical":
            critical_issues.append("memory")
        if BUDGET_MANAGER.energy_budget.battery_level < 10:
            critical_issues.append("battery")
        
        if critical_issues:
            self.status.safety_level = "critical"
        elif BEHAVIOR_STATE_MACHINE.current_state in [BehaviorState.OVERLOADED, BehaviorState.LOW_POWER]:
            self.status.safety_level = "elevated"
        else:
            self.status.safety_level = "normal"
        
        # Determine performance mode
        energy_factor = BUDGET_MANAGER.get_energy_factor()
        if energy_factor < 0.3:
            self.status.performance_mode = "minimal"
        elif energy_factor < 0.7:
            self.status.performance_mode = "balanced"
        else:
            self.status.performance_mode = "performance"
        
        # Update other status fields
        self.status.current_state = BEHAVIOR_STATE_MACHINE.current_state.value
        self.status.energy_factor = energy_factor
        self.status.attention_score = ATTENTION_MANAGER.get_attention_score()
        
        # Update active capabilities
        self.status.active_capabilities = [
            cap.value for cap, level in CAPABILITY_MANAGER.permissions.items()
            if level in [PermissionLevel.GRANTED, PermissionLevel.TEMPORARY]
        ]
    
    def register_status_callback(self, callback: Callable[[SystemStatus], None]) -> None:
        """Register callback for system status changes."""
        self.status_callbacks.append(callback)
    
    def get_system_status(self) -> SystemStatus:
        """Get current system status."""
        return self.status
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status from all systems."""
        return {
            "orchestrator": {
                "healthy": self.status.healthy,
                "safety_level": self.status.safety_level,
                "performance_mode": self.status.performance_mode,
                "tick_interval": self.tick_interval,
                "avg_tick_time": sum(self.tick_times) / len(self.tick_times) if self.tick_times else 0.0
            },
            "capabilities": CAPABILITY_MANAGER.get_permission_status(),
            "attention": ATTENTION_MANAGER.get_state_summary(),
            "state_machine": BEHAVIOR_STATE_MACHINE.get_state_summary(),
            "resources": RESOURCE_CONTROLLER.get_system_status(),
            "grounding": TOOL_GROUNDING_SYSTEM.get_statistics(),
            "budgets": BUDGET_MANAGER.get_budget_summary()
        }
    
    def process_user_request(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request through all systems.
        
        Args:
            request: User request text
            context: Additional context
            
        Returns:
            Response with grounding and system state
        """
        # Trigger attention event
        ATTENTION_MANAGER.trigger_user_input(request, novelty=0.6)
        
        # Ground the request to prevent hallucinations
        request_id = f"user_req_{int(time.time())}"
        grounding_results = TOOL_GROUNDING_SYSTEM.ground_request(
            request_id=request_id,
            query=request,
            parameters=context or {},
            source="user_request"
        )
        
        # Generate grounded response (placeholder - would integrate with LLM)
        grounded_response = TOOL_GROUNDING_SYSTEM.generate_grounded_response(
            original_query=request,
            model_response="This is a placeholder response.",
            grounding_results=grounding_results
        )
        
        return {
            "request": request,
            "response": grounded_response.grounded_response,
            "confidence": grounded_response.confidence,
            "sources": grounded_response.sources,
            "system_state": self.get_system_status(),
            "grounding_results": [
                {
                    "status": r.status.value,
                    "execution_time": r.execution_time,
                    "data": r.data
                }
                for r in grounding_results
            ]
        }


# Global orchestrator instance
KITSU_ORCHESTRATOR = KitsuOrchestrator()
