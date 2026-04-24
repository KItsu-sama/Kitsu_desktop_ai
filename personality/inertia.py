"""
personality/inertia.py

Emotional inertia system for smooth personality transitions.

Implements gradual, natural-feeling transitions between personality states
instead of abrupt jumps. Prevents personality whiplash and creates
more believable emotional evolution.

Key Features:
- Configurable inertia strength
- Directional inertia (resists change in specific dimensions)
- Momentum-based transitions
- No randomness - fully deterministic
- Smooth exponential decay toward target
"""

import logging
import time
import math
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field

from .vector import PersonalityVector, create_neutral_vector

log = logging.getLogger(__name__)


@dataclass
class InertiaState:
    """Tracks the current inertia state for smooth transitions."""
    
    # Current personality vector (what's actually displayed)
    current: PersonalityVector = field(default_factory=create_neutral_vector)
    
    # Target personality vector (what we're transitioning toward)
    target: PersonalityVector = field(default_factory=create_neutral_vector)
    
    # Velocity vector (rate of change in each dimension)
    velocity: PersonalityVector = field(default_factory=create_neutral_vector)
    
    # Timestamp of last update
    last_update: float = field(default_factory=time.time)
    
    # Whether transition is active
    transitioning: bool = False
    
    # Transition progress (0.0 = start, 1.0 = complete)
    progress: float = 0.0


class EmotionalInertia:
    """
    Manages smooth transitions between personality vectors using physics-based inertia.
    
    Instead of instant personality changes, applies gradual transitions that feel
    natural and prevent jarring emotional shifts.
    """
    
    def __init__(self, 
                 base_inertia: float = 0.3,
                 damping: float = 0.8,
                 max_velocity: float = 0.1):
        """
        Initialize emotional inertia system.
        
        Args:
            base_inertia: Base resistance to change (0.0 = none, 1.0 = maximum)
            damping: Velocity damping factor (0.0 = no damping, 1.0 = high damping)
            max_velocity: Maximum rate of change per dimension
        """
        self.base_inertia = max(0.0, min(1.0, base_inertia))
        self.damping = max(0.0, min(1.0, damping))
        self.max_velocity = max(0.001, max_velocity)
        
        # Dimension-specific inertia (can be adjusted for different behaviors)
        self.dimension_inertia = {
            'warmth': 0.3,        # Emotional warmth changes gradually
            'edge': 0.4,           # Edge/sass can change quicker
            'chaos': 0.5,          # Chaos changes slowly (stability)
            'energy': 0.2,          # Energy can change relatively quickly
            'affection': 0.3,       # Affection builds gradually
            'protectiveness': 0.4,   # Protective instincts change slowly
            'focus': 0.2,           # Focus can shift quickly
            'mystery': 0.5,         # Mystery changes very slowly
            'verbosity': 0.3,        # Verbosity changes moderately
            'expressiveness': 0.3     # Expressiveness changes moderately
        }
        
        # Current inertia state
        self.state = InertiaState()
        
        log.debug(f"EmotionalInertia initialized: base={self.base_inertia}, "
                 f"damping={self.damping}, max_vel={self.max_velocity}")
    
    def apply_inertia(self, target_vector: PersonalityVector, 
                    immediate: bool = False) -> PersonalityVector:
        """
        Apply inertia to a target personality vector.
        
        Args:
            target_vector: Desired target personality
            immediate: If True, skip transition and jump to target
            
        Returns:
            Current personality vector after inertia applied
        """
        current_time = time.time()
        dt = current_time - self.state.last_update
        
        # Update target
        self.state.target = target_vector.copy()
        
        if immediate:
            # Immediate transition (no inertia)
            self.state.current = target_vector.copy()
            self.state.velocity = create_neutral_vector()
            self.state.transitioning = False
            self.state.progress = 1.0
        else:
            # Smooth transition with inertia
            self._update_transition(dt)
        
        self.state.last_update = current_time
        
        return self.state.current.copy()
    
    def _update_transition(self, dt: float):
        """
        Update the ongoing transition based on physics simulation.
        
        Args:
            dt: Time delta since last update (seconds)
        """
        # Calculate distance to target
        distance = self.state.current.distance_to(self.state.target)
        
        if distance < 0.01:  # Very close to target
            # Transition complete
            self.state.current = self.state.target.copy()
            self.state.velocity = create_neutral_vector()
            self.state.transitioning = False
            self.state.progress = 1.0
            return
        
        # Mark as transitioning
        self.state.transitioning = True
        
        # Calculate forces for each dimension
        forces = self._calculate_forces()
        
        # Update velocity with forces and inertia
        self._update_velocity(forces, dt)
        
        # Update position with velocity
        self._update_position(dt)
        
        # Update progress
        initial_distance = self.state.current.distance_to(self.state.target)
        if initial_distance > 0:
            self.state.progress = 1.0 - (distance / initial_distance)
        else:
            self.state.progress = 1.0
    
    def _calculate_forces(self) -> PersonalityVector:
        """
        Calculate forces pulling toward target vector.
        
        Returns:
            Force vector for each dimension
        """
        force_values = {}
        
        for dim_name in self.state.current.__dataclass_fields__.keys():
            current_val = getattr(self.state.current, dim_name)
            target_val = getattr(self.state.target, dim_name)
            
            # Calculate force toward target
            force = target_val - current_val
            
            # Apply dimension-specific inertia
            inertia = self.dimension_inertia.get(dim_name, self.base_inertia)
            force *= (1.0 - inertia)
            
            # Apply base inertia
            force *= (1.0 - self.base_inertia)
            
            force_values[dim_name] = force
        
        return PersonalityVector(**force_values)
    
    def _update_velocity(self, forces: PersonalityVector, dt: float):
        """
        Update velocity based on forces and damping.
        
        Args:
            forces: Force vector
            dt: Time delta
        """
        velocity_values = {}
        
        for dim_name in self.state.velocity.__dataclass_fields__.keys():
            current_vel = getattr(self.state.velocity, dim_name)
            force = getattr(forces, dim_name)
            
            # Update velocity (F = ma, assuming m = 1)
            new_vel = current_vel + force * dt
            
            # Apply damping
            new_vel *= self.damping
            
            # Clamp to maximum velocity
            new_vel = max(-self.max_velocity, min(self.max_velocity, new_vel))
            
            velocity_values[dim_name] = new_vel
        
        self.state.velocity = PersonalityVector(**velocity_values)
    
    def _update_position(self, dt: float):
        """
        Update current position based on velocity.
        
        Args:
            dt: Time delta
        """
        position_values = {}
        
        for dim_name in self.state.current.__dataclass_fields__.keys():
            current_pos = getattr(self.state.current, dim_name)
            velocity = getattr(self.state.velocity, dim_name)
            
            # Update position
            new_pos = current_pos + velocity * dt
            
            # Clamp to valid range [0.0, 1.0]
            new_pos = max(0.0, min(1.0, new_pos))
            
            position_values[dim_name] = new_pos
        
        self.state.current = PersonalityVector(**position_values)
    
    def set_dimension_inertia(self, dimension: str, inertia: float):
        """
        Set inertia for a specific dimension.
        
        Args:
            dimension: Dimension name (e.g., 'warmth', 'edge')
            inertia: Inertia value (0.0 = none, 1.0 = maximum)
        """
        if dimension in self.dimension_inertia:
            self.dimension_inertia[dimension] = max(0.0, min(1.0, inertia))
            log.debug(f"Set {dimension} inertia to {inertia}")
        else:
            log.warning(f"Unknown dimension: {dimension}")
    
    def get_transition_info(self) -> Dict[str, any]:
        """
        Get information about current transition state.
        
        Returns:
            Dictionary with transition information
        """
        distance = self.state.current.distance_to(self.state.target)
        
        return {
            'transitioning': self.state.transitioning,
            'progress': self.state.progress,
            'distance_to_target': distance,
            'current': self.state.current.copy(),
            'target': self.state.target.copy(),
            'velocity': self.state.velocity.copy()
        }
    
    def is_transitioning(self) -> bool:
        """Check if a transition is currently active."""
        return self.state.transitioning
    
    def get_transition_progress(self) -> float:
        """Get current transition progress (0.0 to 1.0)."""
        return self.state.progress
    
    def force_transition(self, target_vector: PersonalityVector):
        """
        Force immediate transition to target vector.
        
        Args:
            target_vector: Target personality vector
        """
        self.state.current = target_vector.copy()
        self.state.target = target_vector.copy()
        self.state.velocity = create_neutral_vector()
        self.state.transitioning = False
        self.state.progress = 1.0
        
        log.debug("Forced immediate transition")
    
    def reset(self):
        """Reset inertia system to neutral state."""
        neutral = create_neutral_vector()
        self.state = InertiaState(
            current=neutral.copy(),
            target=neutral.copy(),
            velocity=neutral.copy(),
            last_update=time.time(),
            transitioning=False,
            progress=1.0
        )
        
        log.debug("EmotionalInertia reset to neutral")
    
    def estimate_transition_time(self, target_vector: PersonalityVector) -> float:
        """
        Estimate time required for transition to target.
        
        Args:
            target_vector: Target personality vector
            
        Returns:
            Estimated time in seconds
        """
        distance = self.state.current.distance_to(target_vector)
        
        if distance < 0.01:
            return 0.0
        
        # Rough estimate based on max velocity and damping
        effective_velocity = self.max_velocity * (1.0 - self.damping)
        
        if effective_velocity <= 0:
            return float('inf')
        
        return distance / effective_velocity


# Convenience functions for standalone usage
def apply_inertia(current: PersonalityVector, 
                 previous: PersonalityVector, 
                 inertia: float = 0.3) -> PersonalityVector:
    """
    Simple inertia application (blend previous into current).
    
    Args:
        current: Current personality vector
        previous: Previous personality vector
        inertia: Inertia factor (0.0 = no inertia, 1.0 = full inertia)
        
    Returns:
        Personality vector with inertia applied
    """
    return current.blend(previous, max(0.0, min(1.0, inertia)))


def smooth_transition(start: PersonalityVector, 
                   end: PersonalityVector, 
                   progress: float) -> PersonalityVector:
    """
    Smooth interpolation between two personality vectors.
    
    Args:
        start: Starting personality vector
        end: Ending personality vector
        progress: Progress (0.0 = start, 1.0 = end)
        
    Returns:
        Interpolated personality vector
    """
    return start.lerp(end, max(0.0, min(1.0, progress)))
