"""
personality/energy.py

Energy and idle decay system for personality vectors.

Implements time-based decay of personality dimensions to simulate
natural energy depletion and recovery cycles.

Key Features:
- Configurable decay rates per dimension
- Idle time detection and sleep mode triggers
- Energy recovery on wake events
- Natural energy cycles and fatigue simulation
"""

import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

from .vector import PersonalityVector, create_neutral_vector

log = logging.getLogger(__name__)


@dataclass
class EnergyState:
    """Tracks current energy state and decay information."""
    
    # Current energy levels
    current_vector: PersonalityVector = field(default_factory=create_neutral_vector)
    
    # Decay tracking
    last_activity: float = field(default_factory=time.time)
    total_idle_time: float = 0.0
    
    # Sleep state
    is_sleeping: bool = False
    sleep_start_time: Optional[float] = None
    
    # Energy thresholds
    low_energy_threshold: float = 0.2
    sleep_energy_threshold: float = 0.1
    wake_energy_boost: float = 0.3
    
    # Fatigue tracking
    fatigue_level: float = 0.0  # Accumulated fatigue
    max_fatigue: float = 1.0


class EnergySystem:
    """
    Manages energy decay and recovery for personality vectors.
    
    Simulates natural energy cycles including fatigue, sleep, and recovery.
    Prevents perpetual high-energy states and adds realism to personality evolution.
    """
    
    def __init__(self):
        """Initialize energy system."""
        # Decay rates per dimension (per second of idle time)
        self.idle_decay_rates = {
            'energy': 0.02,          # Energy depletes during inactivity
            'chaos': 0.01,           # Chaos reduces as system stabilizes
            'expressiveness': 0.01,    # Expressiveness fades when tired
            'verbosity': 0.015,        # Less talkative when low energy
            'affection': 0.005,       # Affection slowly decreases when tired
            'playfulness': 0.02,       # Playfulness requires energy
            'edge': 0.008,            # Edge/sass requires energy
            'mystery': 0.003,         # Mystery slowly decreases
            'focus': 0.01,            # Focus depletes with fatigue
            'warmth': 0.004           # Warmth slowly decreases when tired
        }
        
        # Recovery rates per dimension (when active)
        self.recovery_rates = {
            'energy': 0.05,           # Energy recovers when active
            'chaos': 0.03,            # Chaos can increase with stimulation
            'expressiveness': 0.04,     # Expressiveness recovers
            'verbosity': 0.03,         # Verbosity returns
            'affection': 0.02,         # Affection recovers
            'playfulness': 0.06,        # Playfulness recovers quickly
            'edge': 0.025,             # Edge returns with energy
            'mystery': 0.01,           # Mystery slowly returns
            'focus': 0.04,             # Focus improves with rest
            'warmth': 0.03             # Warmth returns
        }
        
        # Sleep recovery rates (enhanced recovery during sleep)
        self.sleep_recovery_rates = {
            'energy': 0.08,           # Faster energy recovery during sleep
            'chaos': 0.01,            # Chaos continues to decrease
            'expressiveness': 0.02,     # Slow expressiveness recovery
            'verbosity': 0.015,        # Slow verbosity recovery
            'affection': 0.025,         # Moderate affection recovery
            'playfulness': 0.04,        # Playfulness recovers
            'edge': 0.015,             # Slow edge recovery
            'mystery': 0.02,           # Mystery returns during rest
            'focus': 0.06,             # Focus improves significantly
            'warmth': 0.04             # Warmth returns
        }
        
        # Energy state
        self.state = EnergyState()
        
        # Configuration
        self.sleep_threshold_seconds = 300  # 5 minutes of inactivity
        self.max_idle_time = 1800          # 30 minutes before forced sleep
        
        log.debug("EnergySystem initialized")
    
    def update_activity(self):
        """Update activity timestamp and trigger wake if sleeping."""
        current_time = time.time()
        
        if self.state.is_sleeping:
            # Wake from sleep
            self._wake_up(current_time)
        else:
            # Update last activity
            self.state.last_activity = current_time
            self.state.total_idle_time = 0.0
        
        log.debug("Activity updated")
    
    def apply_decay(self, current_vector: PersonalityVector) -> PersonalityVector:
        """
        Apply time-based decay to personality vector.
        
        Args:
            current_vector: Current personality vector
            
        Returns:
            Personality vector with decay applied
        """
        current_time = time.time()
        idle_time = current_time - self.state.last_activity
        
        # Update total idle time
        self.state.total_idle_time += idle_time
        
        # Check for sleep conditions
        if self._should_enter_sleep(current_vector, idle_time):
            self._enter_sleep(current_time)
            return self._apply_sleep_decay(current_vector)
        
        # Apply normal idle decay
        if idle_time > 1.0:  # Only decay after 1 second of inactivity
            decayed_vector = self._apply_idle_decay(current_vector, idle_time)
        else:
            decayed_vector = current_vector.copy()
        
        # Update fatigue
        self._update_fatigue(idle_time)
        
        # Store current vector
        self.state.current_vector = decayed_vector.copy()
        self.state.last_activity = current_time
        
        return decayed_vector
    
    def _apply_idle_decay(self, vector: PersonalityVector, idle_time: float) -> PersonalityVector:
        """
        Apply idle decay to personality vector.
        
        Args:
            vector: Current personality vector
            idle_time: Time since last activity
            
        Returns:
            Decayed personality vector
        """
        result_values = {}
        
        for dimension in vector.__dataclass_fields__.keys():
            current_val = getattr(vector, dimension)
            decay_rate = self.idle_decay_rates.get(dimension, 0.01)
            
            # Apply exponential decay
            decay_factor = max(0.0, 1.0 - (decay_rate * idle_time))
            new_val = current_val * decay_factor
            
            # Apply fatigue modifier
            fatigue_modifier = 1.0 - (self.state.fatigue_level * 0.3)
            new_val *= fatigue_modifier
            
            result_values[dimension] = max(0.0, new_val)
        
        return PersonalityVector(**result_values)
    
    def _apply_sleep_decay(self, vector: PersonalityVector) -> PersonalityVector:
        """
        Apply sleep-specific decay and recovery.
        
        During sleep, some dimensions decay while others recover.
        
        Args:
            vector: Current personality vector
            
        Returns:
            Sleep-adjusted personality vector
        """
        result_values = {}
        
        for dimension in vector.__dataclass_fields__.keys():
            current_val = getattr(vector, dimension)
            
            # Use sleep recovery rates (some dimensions recover during sleep)
            if dimension in ['energy', 'focus', 'warmth', 'affection']:
                # These recover during sleep
                recovery_rate = self.sleep_recovery_rates.get(dimension, 0.02)
                new_val = min(1.0, current_val + recovery_rate)
            else:
                # These continue to decay slowly during sleep
                decay_rate = self.sleep_recovery_rates.get(dimension, 0.005)
                new_val = max(0.0, current_val - decay_rate)
            
            result_values[dimension] = new_val
        
        return PersonalityVector(**result_values)
    
    def _should_enter_sleep(self, vector: PersonalityVector, idle_time: float) -> bool:
        """
        Check if system should enter sleep mode.
        
        Args:
            vector: Current personality vector
            idle_time: Time since last activity
            
        Returns:
            True if should enter sleep
        """
        # Already sleeping
        if self.state.is_sleeping:
            return False
        
        # Energy-based sleep trigger
        if vector.energy <= self.state.sleep_energy_threshold:
            return True
        
        # Time-based sleep trigger
        if idle_time >= self.max_idle_time:
            return True
        
        # Fatigue-based sleep trigger
        if self.state.fatigue_level >= 0.8:
            return True
        
        return False
    
    def _enter_sleep(self, current_time: float):
        """Enter sleep mode."""
        self.state.is_sleeping = True
        self.state.sleep_start_time = current_time
        log.info("Entering sleep mode due to inactivity/low energy")
    
    def _wake_up(self, current_time: float):
        """Wake from sleep mode."""
        if not self.state.is_sleeping:
            return
        
        # Calculate sleep duration
        sleep_duration = current_time - (self.state.sleep_start_time or current_time)
        
        # Apply wake energy boost
        self.state.current_vector.energy = min(1.0, 
            self.state.current_vector.energy + self.state.wake_energy_boost)
        
        # Reduce fatigue from sleep
        self.state.fatigue_level = max(0.0, 
            self.state.fatigue_level - (sleep_duration * 0.001))
        
        # Update state
        self.state.is_sleeping = False
        self.state.sleep_start_time = None
        self.state.last_activity = current_time
        self.state.total_idle_time = 0.0
        
        log.info(f"Woke from sleep after {sleep_duration:.1f}s, "
                f"energy boost to {self.state.current_vector.energy:.2f}")
    
    def _update_fatigue(self, idle_time: float):
        """
        Update fatigue level based on activity and time.
        
        Args:
            idle_time: Time since last activity
        """
        if idle_time > 0:
            # Fatigue increases during inactivity
            fatigue_increase = idle_time * 0.0001  # Very slow accumulation
            self.state.fatigue_level = min(self.state.max_fatigue,
                self.state.fatigue_level + fatigue_increase)
        else:
            # Fatigue decreases with activity
            fatigue_decrease = 0.01
            self.state.fatigue_level = max(0.0,
                self.state.fatigue_level - fatigue_decrease)
    
    def boost_energy(self, amount: float = 0.2):
        """
        Apply immediate energy boost.
        
        Args:
            amount: Energy boost amount (0.0 - 1.0)
        """
        self.state.current_vector.energy = min(1.0,
            self.state.current_vector.energy + amount)
        
        # Wake up if sleeping
        if self.state.is_sleeping:
            self._wake_up(time.time())
        
        log.debug(f"Energy boosted by {amount:.2f} to {self.state.current_vector.energy:.2f}")
    
    def force_sleep(self):
        """Force entry into sleep mode."""
        if not self.state.is_sleeping:
            self._enter_sleep(time.time())
    
    def force_wake(self):
        """Force wake from sleep mode."""
        if self.state.is_sleeping:
            self._wake_up(time.time())
    
    def get_energy_status(self) -> Dict[str, any]:
        """
        Get current energy system status.
        
        Returns:
            Dictionary with energy status information
        """
        current_time = time.time()
        idle_time = current_time - self.state.last_activity
        
        return {
            'energy_level': self.state.current_vector.energy,
            'is_sleeping': self.state.is_sleeping,
            'idle_time': idle_time,
            'total_idle_time': self.state.total_idle_time,
            'fatigue_level': self.state.fatigue_level,
            'sleep_threshold': self.state.sleep_energy_threshold,
            'time_until_sleep': max(0, self.sleep_threshold_seconds - idle_time),
            'current_vector': self.state.current_vector.copy()
        }
    
    def set_decay_rates(self, dimension: str, idle_rate: float, 
                      recovery_rate: float, sleep_rate: float = None):
        """
        Set custom decay rates for a dimension.
        
        Args:
            dimension: Dimension name
            idle_rate: Decay rate during idle
            recovery_rate: Recovery rate during activity
            sleep_rate: Recovery rate during sleep (optional)
        """
        if dimension in self.idle_decay_rates:
            self.idle_decay_rates[dimension] = max(0.0, idle_rate)
            self.recovery_rates[dimension] = max(0.0, recovery_rate)
            
            if sleep_rate is not None:
                self.sleep_recovery_rates[dimension] = max(0.0, sleep_rate)
            
            log.debug(f"Updated decay rates for {dimension}")
        else:
            log.warning(f"Unknown dimension: {dimension}")
    
    def reset_fatigue(self):
        """Reset fatigue level to zero."""
        self.state.fatigue_level = 0.0
        log.debug("Fatigue level reset")


# Convenience functions for standalone usage
def apply_idle_decay(vector: PersonalityVector, idle_time: float) -> PersonalityVector:
    """
    Apply basic idle decay to personality vector.
    
    Args:
        vector: PersonalityVector to decay
        idle_time: Time in seconds since last activity
        
    Returns:
        Decayed PersonalityVector
    """
    system = EnergySystem()
    return system._apply_idle_decay(vector, idle_time)


def get_energy_status(vector: PersonalityVector) -> Dict[str, any]:
    """
    Get energy status for a personality vector.
    
    Args:
        vector: PersonalityVector to check
        
    Returns:
        Energy status dictionary
    """
    system = EnergySystem()
    system.state.current_vector = vector
    return system.get_energy_status()
