"""
domain/state/behavior_state_machine.py

State machine layer for Kitsu's behavior states.

Provides structured behavior states that control:
- Animation FPS and model size
- Voice usage and reaction frequency  
- Desktop activity and latency budgets
- CPU efficiency vs "alive" feeling balance
"""

import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


class BehaviorState(Enum):
    """Core behavior states for Kitsu."""
    ACTIVE = "active"          # Fully responsive, high resource usage
    IDLE = "idle"              # Low activity, waiting for input
    SLEEPY = "sleepy"          # Very low activity, minimal responses
    FOCUSED = "focused"        # Concentrated on task, reduced interruptions
    PLAYFUL = "playful"        # High animation, more expressive
    OVERLOADED = "overloaded"  # System stressed, minimal features
    LOW_POWER = "low_power"    # Battery saving mode


class StateTransition(Enum):
    """Types of state transitions."""
    IMMEDIATE = "immediate"    # Change state immediately
    GRADUAL = "gradual"        # Smooth transition over time
    CONDITIONAL = "conditional" # Change only if conditions met


@dataclass
class StateConfig:
    """Configuration for a behavior state."""
    # Animation settings
    animation_fps: float = 30.0
    model_quality: float = 1.0  # 0.0 (chibi) - 1.0 (full 3D)
    animation_priority: float = 0.5
    
    # Voice settings
    voice_enabled: bool = True
    voice_frequency: float = 0.5  # How often to speak
    voice_volume: float = 0.8
    
    # Reaction settings
    reaction_speed: float = 0.5  # 0.0 (slow) - 1.0 (instant)
    interruptible: bool = True
    reaction_frequency: float = 0.5
    
    # Resource settings
    cpu_budget: float = 0.5  # 0.0 (minimal) - 1.0 (maximum)
    memory_budget: float = 0.5
    network_usage: float = 0.5
    
    # Behavior settings
    desktop_activity: float = 0.5  # Interaction with desktop
    popup_frequency: float = 0.5
    idle_actions: bool = True
    auto_responses: bool = True
    
    # Latency budgets (seconds)
    response_latency: float = 1.0
    animation_latency: float = 0.1
    voice_latency: float = 0.5


@dataclass
class StateTransitionRule:
    """Rule for state transitions."""
    from_state: BehaviorState
    to_state: BehaviorState
    condition: Callable[[], bool]
    transition_type: StateTransition = StateTransition.IMMEDIATE
    priority: int = 0  # Higher priority rules checked first


@dataclass
class StateHistory:
    """History of state changes."""
    timestamp: float
    from_state: BehaviorState
    to_state: BehaviorState
    trigger: str
    transition_time: float


class BehaviorStateMachine:
    """
    Manages Kitsu's behavior state machine.
    
    Features:
    - Seven behavior states with different resource profiles
    - Smooth transitions and conditional rules
    - Resource-aware state selection
    - History tracking and analytics
    """
    
    def __init__(self):
        self.current_state = BehaviorState.ACTIVE
        self.previous_state = BehaviorState.ACTIVE
        self.state_history: List[StateHistory] = []
        self.transition_start_time: Optional[float] = None
        self.transitioning_to: Optional[BehaviorState] = None
        self.transition_progress: float = 0.0
        
        # State configurations
        self.state_configs: Dict[BehaviorState, StateConfig] = {}
        self._setup_state_configs()
        
        # Transition rules
        self.transition_rules: List[StateTransitionRule] = []
        self._setup_transition_rules()
        
        # State change callbacks
        self.state_callbacks: Dict[BehaviorState, List[Callable]] = {}
        
        # System state tracking
        self.system_load = 0.5
        self.battery_level = 1.0
        self.user_activity = 1.0
        self.attention_level = 0.5
        
        log.info(f"BehaviorStateMachine initialized in {self.current_state.value} state")
    
    def _setup_state_configs(self):
        """Setup configurations for each behavior state."""
        # ACTIVE: Full responsiveness
        self.state_configs[BehaviorState.ACTIVE] = StateConfig(
            animation_fps=30.0,
            model_quality=1.0,
            animation_priority=0.8,
            voice_enabled=True,
            voice_frequency=0.7,
            voice_volume=0.9,
            reaction_speed=0.9,
            interruptible=True,
            reaction_frequency=0.8,
            cpu_budget=0.8,
            memory_budget=0.7,
            network_usage=0.6,
            desktop_activity=0.7,
            popup_frequency=0.5,
            idle_actions=False,
            auto_responses=True,
            response_latency=0.5,
            animation_latency=0.03,
            voice_latency=0.2
        )
        
        # IDLE: Low activity, responsive
        self.state_configs[BehaviorState.IDLE] = StateConfig(
            animation_fps=15.0,
            model_quality=0.6,
            animation_priority=0.3,
            voice_enabled=True,
            voice_frequency=0.3,
            voice_volume=0.6,
            reaction_speed=0.5,
            interruptible=True,
            reaction_frequency=0.4,
            cpu_budget=0.3,
            memory_budget=0.3,
            network_usage=0.2,
            desktop_activity=0.2,
            popup_frequency=0.1,
            idle_actions=True,
            auto_responses=False,
            response_latency=2.0,
            animation_latency=0.1,
            voice_latency=0.8
        )
        
        # SLEEPY: Very low activity
        self.state_configs[BehaviorState.SLEEPY] = StateConfig(
            animation_fps=5.0,
            model_quality=0.3,
            animation_priority=0.1,
            voice_enabled=False,
            voice_frequency=0.0,
            voice_volume=0.0,
            reaction_speed=0.1,
            interruptible=False,
            reaction_frequency=0.1,
            cpu_budget=0.1,
            memory_budget=0.2,
            network_usage=0.0,
            desktop_activity=0.0,
            popup_frequency=0.0,
            idle_actions=False,
            auto_responses=False,
            response_latency=5.0,
            animation_latency=0.5,
            voice_latency=0.0
        )
        
        # FOCUSED: Task-oriented
        self.state_configs[BehaviorState.FOCUSED] = StateConfig(
            animation_fps=20.0,
            model_quality=0.8,
            animation_priority=0.4,
            voice_enabled=True,
            voice_frequency=0.4,
            voice_volume=0.7,
            reaction_speed=0.7,
            interruptible=False,
            reaction_frequency=0.3,
            cpu_budget=0.6,
            memory_budget=0.6,
            network_usage=0.5,
            desktop_activity=0.3,
            popup_frequency=0.0,
            idle_actions=False,
            auto_responses=True,
            response_latency=0.8,
            animation_latency=0.05,
            voice_latency=0.4
        )
        
        # PLAYFUL: High animation, expressive
        self.state_configs[BehaviorState.PLAYFUL] = StateConfig(
            animation_fps=45.0,
            model_quality=1.0,
            animation_priority=1.0,
            voice_enabled=True,
            voice_frequency=0.9,
            voice_volume=1.0,
            reaction_speed=1.0,
            interruptible=True,
            reaction_frequency=1.0,
            cpu_budget=0.9,
            memory_budget=0.8,
            network_usage=0.4,
            desktop_activity=0.8,
            popup_frequency=0.7,
            idle_actions=True,
            auto_responses=True,
            response_latency=0.3,
            animation_latency=0.02,
            voice_latency=0.1
        )
        
        # OVERLOADED: System stressed
        self.state_configs[BehaviorState.OVERLOADED] = StateConfig(
            animation_fps=10.0,
            model_quality=0.2,
            animation_priority=0.1,
            voice_enabled=False,
            voice_frequency=0.0,
            voice_volume=0.0,
            reaction_speed=0.2,
            interruptible=False,
            reaction_frequency=0.1,
            cpu_budget=0.2,
            memory_budget=0.3,
            network_usage=0.1,
            desktop_activity=0.0,
            popup_frequency=0.0,
            idle_actions=False,
            auto_responses=False,
            response_latency=3.0,
            animation_latency=0.3,
            voice_latency=0.0
        )
        
        # LOW_POWER: Battery saving
        self.state_configs[BehaviorState.LOW_POWER] = StateConfig(
            animation_fps=8.0,
            model_quality=0.4,
            animation_priority=0.2,
            voice_enabled=True,
            voice_frequency=0.2,
            voice_volume=0.5,
            reaction_speed=0.3,
            interruptible=False,
            reaction_frequency=0.2,
            cpu_budget=0.2,
            memory_budget=0.2,
            network_usage=0.1,
            desktop_activity=0.1,
            popup_frequency=0.0,
            idle_actions=True,
            auto_responses=False,
            response_latency=4.0,
            animation_latency=0.2,
            voice_latency=1.0
        )
    
    def _setup_transition_rules(self):
        """Setup state transition rules."""
        # High system load -> OVERLOADED
        self.transition_rules.append(StateTransitionRule(
            from_state=BehaviorState.ACTIVE,
            to_state=BehaviorState.OVERLOADED,
            condition=lambda: self.system_load > 0.8,
            transition_type=StateTransition.IMMEDIATE,
            priority=10
        ))
        
        # Low battery -> LOW_POWER
        self.transition_rules.append(StateTransitionRule(
            from_state=BehaviorState.ACTIVE,
            to_state=BehaviorState.LOW_POWER,
            condition=lambda: self.battery_level < 0.2,
            transition_type=StateTransition.GRADUAL,
            priority=9
        ))
        
        # User inactive -> IDLE
        self.transition_rules.append(StateTransitionRule(
            from_state=BehaviorState.ACTIVE,
            to_state=BehaviorState.IDLE,
            condition=lambda: self.user_activity < 0.3,
            transition_type=StateTransition.GRADUAL,
            priority=5
        ))
        
        # High attention + playful mood -> PLAYFUL
        self.transition_rules.append(StateTransitionRule(
            from_state=BehaviorState.ACTIVE,
            to_state=BehaviorState.PLAYFUL,
            condition=lambda: self.attention_level > 0.7 and self.user_activity > 0.6,
            transition_type=StateTransition.IMMEDIATE,
            priority=3
        ))
        
        # Focused task -> FOCUSED
        self.transition_rules.append(StateTransitionRule(
            from_state=BehaviorState.ACTIVE,
            to_state=BehaviorState.FOCUSED,
            condition=lambda: self.attention_level > 0.6 and self.user_activity > 0.8,
            transition_type=StateTransition.IMMEDIATE,
            priority=4
        ))
        
        # Very inactive -> SLEEPY
        self.transition_rules.append(StateTransitionRule(
            from_state=BehaviorState.IDLE,
            to_state=BehaviorState.SLEEPY,
            condition=lambda: self.user_activity < 0.1,
            transition_type=StateTransition.GRADUAL,
            priority=6
        ))
        
        # Recovery transitions
        for state in [BehaviorState.OVERLOADED, BehaviorState.LOW_POWER, BehaviorState.SLEEPY]:
            self.transition_rules.append(StateTransitionRule(
                from_state=state,
                to_state=BehaviorState.ACTIVE,
                condition=lambda: (self.system_load < 0.5 and 
                                 self.battery_level > 0.5 and 
                                 self.user_activity > 0.4),
                transition_type=StateTransition.GRADUAL,
                priority=2
            ))
    
    def register_state_callback(self, state: BehaviorState, callback: Callable) -> None:
        """Register callback for state changes."""
        if state not in self.state_callbacks:
            self.state_callbacks[state] = []
        self.state_callbacks[state].append(callback)
    
    def update_system_state(
        self,
        system_load: float,
        battery_level: float = 1.0,
        user_activity: float = 1.0,
        attention_level: float = 0.5
    ) -> None:
        """Update system state metrics."""
        self.system_load = max(0.0, min(1.0, system_load))
        self.battery_level = max(0.0, min(1.0, battery_level))
        self.user_activity = max(0.0, min(1.0, user_activity))
        self.attention_level = max(0.0, min(1.0, attention_level))
    
    def check_transitions(self) -> None:
        """Check and execute state transitions."""
        if self.transitioning_to:
            # Currently transitioning - update progress
            self._update_transition()
            return
        
        # Check transition rules
        applicable_rules = [
            rule for rule in self.transition_rules
            if rule.from_state == self.current_state and rule.condition()
        ]
        
        if applicable_rules:
            # Sort by priority (highest first)
            applicable_rules.sort(key=lambda r: r.priority, reverse=True)
            best_rule = applicable_rules[0]
            
            self._start_transition(best_rule.to_state, best_rule.transition_type, "automatic")
    
    def _start_transition(
        self,
        target_state: BehaviorState,
        transition_type: StateTransition,
        trigger: str
    ) -> None:
        """Start transition to new state."""
        if target_state == self.current_state:
            return
        
        log.info(f"Starting transition: {self.current_state.value} -> {target_state.value} ({transition_type.value})")
        
        self.transitioning_to = target_state
        self.transition_start_time = time.time()
        
        if transition_type == StateTransition.IMMEDIATE:
            self._complete_transition(trigger)
        else:  # GRADUAL
            self.transition_progress = 0.0
    
    def _update_transition(self) -> None:
        """Update gradual transition progress."""
        if not self.transitioning_to or not self.transition_start_time:
            return
        
        # 2-second transition for gradual changes
        transition_duration = 2.0
        elapsed = time.time() - self.transition_start_time
        self.transition_progress = min(1.0, elapsed / transition_duration)
        
        if self.transition_progress >= 1.0:
            self._complete_transition("gradual_complete")
    
    def _complete_transition(self, trigger: str) -> None:
        """Complete state transition."""
        if not self.transitioning_to:
            return
        
        old_state = self.current_state
        self.previous_state = self.current_state
        self.current_state = self.transitioning_to
        
        transition_time = time.time() - (self.transition_start_time or time.time())
        
        # Record in history
        self.state_history.append(StateHistory(
            timestamp=time.time(),
            from_state=old_state,
            to_state=self.current_state,
            trigger=trigger,
            transition_time=transition_time
        ))
        
        # Keep history manageable
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-50:]
        
        # Reset transition state
        self.transitioning_to = None
        self.transition_start_time = None
        self.transition_progress = 0.0
        
        log.info(f"State transition complete: {old_state.value} -> {self.current_state.value}")
        
        # Trigger callbacks
        if self.current_state in self.state_callbacks:
            for callback in self.state_callbacks[self.current_state]:
                try:
                    callback(old_state, self.current_state)
                except Exception as e:
                    log.error(f"State callback error: {e}")
    
    def force_state(self, state: BehaviorState, trigger: str = "manual") -> None:
        """Force immediate state change."""
        self._start_transition(state, StateTransition.IMMEDIATE, trigger)
    
    def get_current_config(self) -> StateConfig:
        """Get current state configuration (blended during transitions)."""
        if not self.transitioning_to:
            return self.state_configs[self.current_state]
        
        # Blend configs during gradual transition
        current_config = self.state_configs[self.current_state]
        target_config = self.state_configs[self.transitioning_to]
        
        # Simple linear interpolation
        def blend(current, target, progress):
            return current + (target - current) * progress
        
        return StateConfig(
            animation_fps=blend(current_config.animation_fps, target_config.animation_fps, self.transition_progress),
            model_quality=blend(current_config.model_quality, target_config.model_quality, self.transition_progress),
            animation_priority=blend(current_config.animation_priority, target_config.animation_priority, self.transition_progress),
            voice_enabled=target_config.voice_enabled if self.transition_progress > 0.5 else current_config.voice_enabled,
            voice_frequency=blend(current_config.voice_frequency, target_config.voice_frequency, self.transition_progress),
            voice_volume=blend(current_config.voice_volume, target_config.voice_volume, self.transition_progress),
            reaction_speed=blend(current_config.reaction_speed, target_config.reaction_speed, self.transition_progress),
            interruptible=target_config.interruptible if self.transition_progress > 0.5 else current_config.interruptible,
            reaction_frequency=blend(current_config.reaction_frequency, target_config.reaction_frequency, self.transition_progress),
            cpu_budget=blend(current_config.cpu_budget, target_config.cpu_budget, self.transition_progress),
            memory_budget=blend(current_config.memory_budget, target_config.memory_budget, self.transition_progress),
            network_usage=blend(current_config.network_usage, target_config.network_usage, self.transition_progress),
            desktop_activity=blend(current_config.desktop_activity, target_config.desktop_activity, self.transition_progress),
            popup_frequency=blend(current_config.popup_frequency, target_config.popup_frequency, self.transition_progress),
            idle_actions=target_config.idle_actions if self.transition_progress > 0.5 else current_config.idle_actions,
            auto_responses=target_config.auto_responses if self.transition_progress > 0.5 else current_config.auto_responses,
            response_latency=blend(current_config.response_latency, target_config.response_latency, self.transition_progress),
            animation_latency=blend(current_config.animation_latency, target_config.animation_latency, self.transition_progress),
            voice_latency=blend(current_config.voice_latency, target_config.voice_latency, self.transition_progress)
        )
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state machine status."""
        config = self.get_current_config()
        
        return {
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value,
            "transitioning_to": self.transitioning_to.value if self.transitioning_to else None,
            "transition_progress": self.transition_progress,
            "system_metrics": {
                "system_load": self.system_load,
                "battery_level": self.battery_level,
                "user_activity": self.user_activity,
                "attention_level": self.attention_level
            },
            "current_config": {
                "animation_fps": config.animation_fps,
                "model_quality": config.model_quality,
                "voice_enabled": config.voice_enabled,
                "reaction_speed": config.reaction_speed,
                "cpu_budget": config.cpu_budget,
                "response_latency": config.response_latency
            },
            "state_history_count": len(self.state_history),
            "last_transition": self.state_history[-1].to_dict() if self.state_history else None
        }
    
    def tick(self) -> None:
        """Regular tick to update state machine."""
        self.check_transitions()


# Global instance
BEHAVIOR_STATE_MACHINE = BehaviorStateMachine()
