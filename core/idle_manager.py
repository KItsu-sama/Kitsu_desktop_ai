"""
core/idle_manager.py

Idle behavior coordination extracted from legacy system.

Manages idle time tracking, sleep mode detection, and check-in behaviors.
Integrates with modern EmotionEngine and event bus architecture.
"""

import asyncio
import time
import logging
from typing import Optional, Callable, Dict, Any
from enum import Enum
from dataclasses import dataclass

from core.contracts import ModuleContract
from core.bus import bus
from core.events import EventType, EventPayload

log = logging.getLogger(__name__)


class IdleState(Enum):
    """Idle state enumeration."""
    ACTIVE = "active"           # User is active
    IDLE = "idle"              # Idle but not sleeping
    CHECK_IN = "check_in"      # 5 min idle - check-in triggered
    SLEEP = "sleep"            # 10 min idle - sleep mode


@dataclass
class IdleConfig:
    """Configuration for idle behavior thresholds."""
    check_in_threshold: float = 300.0    # 5 minutes
    sleep_threshold: float = 600.0       # 10 minutes
    active_threshold: float = 60.0       # 1 minute
    check_interval: float = 10.0         # Check every 10 seconds


class IdleManager(ModuleContract):
    """
    Manages idle behavior coordination with modern architecture.
    
    Features:
    - Tracks idle time since last interaction
    - Triggers check-in at configurable threshold
    - Triggers sleep mode at configurable threshold
    - Emits events instead of direct callbacks
    - Integrates with EmotionEngine for personality-aware responses
    """
    
    module_id = 'core.idle_manager'
    required_flags = ['use_emotion']
    
    def __init__(self, config: Optional[IdleConfig] = None):
        """
        Initialize idle manager with configuration.
        
        Args:
            config: Idle behavior configuration, uses defaults if None
        """
        self.config = config or IdleConfig()
        
        # State tracking
        self.last_interaction_time: float = time.time()
        self.current_state: IdleState = IdleState.ACTIVE
        self.check_in_triggered: bool = False
        self.sleep_triggered: bool = False
        
        # Background task management
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        
        log.debug(f"IdleManager initialized with thresholds: "
                 f"check_in={self.config.check_in_threshold}s, "
                 f"sleep={self.config.sleep_threshold}s")
    
    # =========================================================================
    # ModuleContract Implementation
    # =========================================================================
    
    async def start(self) -> bool:
        """Start idle monitoring loop."""
        if self._running:
            log.warning("IdleManager already running")
            return False
        
        try:
            self._running = True
            self._task = asyncio.create_task(self._run())
            
            # Subscribe to interaction events
            bus.subscribe(EventType.USER_INTERACTION, self._on_user_interaction)
            
            log.info("IdleManager started")
            return True
        except Exception as e:
            log.error(f"Failed to start IdleManager: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop idle monitoring loop."""
        try:
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            
            log.info("IdleManager stopped")
            return True
        except Exception as e:
            log.error(f"Error stopping IdleManager: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check idle manager health."""
        return {
            'ok': self._running,
            'latency_ms': 0.0,
            'current_state': self.current_state.value,
            'idle_time': self.get_idle_time(),
            'check_in_triggered': self.check_in_triggered,
            'sleep_triggered': self.sleep_triggered
        }
    
    # =========================================================================
    # Interaction Tracking
    # =========================================================================
    
    def record_interaction(self) -> None:
        """
        Record user interaction.
        
        Resets idle timer and wakes from sleep if needed.
        Emits appropriate events for state changes.
        """
        now = time.time()
        was_sleeping = self.current_state == IdleState.SLEEP
        old_state = self.current_state
        
        self.last_interaction_time = now
        
        # Reset flags and state
        if self.current_state != IdleState.ACTIVE:
            log.debug("User interaction detected - resetting idle state")
            self.check_in_triggered = False
            self.sleep_triggered = False
            self.current_state = IdleState.ACTIVE
            
            # Emit interaction event
            bus.publish(EventPayload(
                event_type=EventType.USER_INTERACTION,
                source='idle_manager',
                data={'timestamp': now, 'previous_state': old_state.value}
            ))
            
            # Emit wake event if was sleeping
            if was_sleeping:
                bus.publish(EventPayload(
                    event_type=EventType.IDLE_WAKE,
                    source='idle_manager',
                    data={'timestamp': now}
                ))
                log.debug("Wake event emitted")
    
    def _on_user_interaction(self, event: EventPayload) -> None:
        """Handle user interaction events from bus."""
        self.record_interaction()
    
    def get_idle_time(self) -> float:
        """
        Get seconds since last interaction.
        
        Returns:
            Idle time in seconds
        """
        return time.time() - self.last_interaction_time
    
    def is_idle(self) -> bool:
        """
        Check if currently idle.
        
        Returns:
            True if idle (not active)
        """
        return self.current_state != IdleState.ACTIVE
    
    def is_sleeping(self) -> bool:
        """
        Check if in sleep mode.
        
        Returns:
            True if in sleep mode
        """
        return self.current_state == IdleState.SLEEP
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    async def _update_state(self) -> None:
        """
        Update idle state based on idle time.
        
        Emits events when thresholds are crossed.
        """
        idle_time = self.get_idle_time()
        old_state = self.current_state
        
        # Sleep mode
        if idle_time >= self.config.sleep_threshold:
            if not self.sleep_triggered:
                self.sleep_triggered = True
                self.current_state = IdleState.SLEEP
                log.debug(f"Sleep mode triggered (idle: {idle_time:.1f}s)")
                
                bus.publish(EventPayload(
                    event_type=EventType.IDLE_SLEEP,
                    source='idle_manager',
                    data={
                        'idle_time': idle_time,
                        'threshold': self.config.sleep_threshold
                    }
                ))
        
        # Check-in
        elif idle_time >= self.config.check_in_threshold:
            if not self.check_in_triggered:
                self.check_in_triggered = True
                self.current_state = IdleState.CHECK_IN
                log.debug(f"Check-in triggered (idle: {idle_time:.1f}s)")
                
                bus.publish(EventPayload(
                    event_type=EventType.IDLE_CHECK_IN,
                    source='idle_manager',
                    data={
                        'idle_time': idle_time,
                        'threshold': self.config.check_in_threshold
                    }
                ))
        
        # Idle state
        elif idle_time > self.config.active_threshold:
            if self.current_state == IdleState.ACTIVE:
                self.current_state = IdleState.IDLE
                log.debug(f"Entered idle state (idle: {idle_time:.1f}s)")
                
                bus.publish(EventPayload(
                    event_type=EventType.IDLE_START,
                    source='idle_manager',
                    data={'idle_time': idle_time}
                ))
        
        # Active state
        else:
            if self.current_state != IdleState.ACTIVE:
                self.current_state = IdleState.ACTIVE
                self.check_in_triggered = False
                self.sleep_triggered = False
                log.debug("Returned to active state")
                
                bus.publish(EventPayload(
                    event_type=EventType.IDLE_END,
                    source='idle_manager',
                    data={'timestamp': time.time()}
                ))
    
    # =========================================================================
    # Background Loop
    # =========================================================================
    
    async def _run(self) -> None:
        """Background loop for idle monitoring."""
        while self._running:
            try:
                await self._update_state()
                await asyncio.sleep(self.config.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"IdleManager loop error: {e}")
                await asyncio.sleep(self.config.check_interval)
    
    # =========================================================================
    # State Export and Control
    # =========================================================================
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current idle state.
        
        Returns:
            Dict with idle state information
        """
        return {
            "state": self.current_state.value,
            "idle_time": self.get_idle_time(),
            "check_in_triggered": self.check_in_triggered,
            "sleep_triggered": self.sleep_triggered,
            "check_in_threshold": self.config.check_in_threshold,
            "sleep_threshold": self.config.sleep_threshold,
            "active_threshold": self.config.active_threshold
        }
    
    def force_sleep(self) -> None:
        """
        Force sleep mode (for testing or manual control).
        
        NOTE: This bypasses normal idle detection.
        """
        if self.current_state != IdleState.SLEEP:
            old_state = self.current_state
            self.current_state = IdleState.SLEEP
            self.sleep_triggered = True
            log.info("Sleep mode forced")
            
            bus.publish(EventPayload(
                event_type=EventType.IDLE_SLEEP_FORCED,
                source='idle_manager',
                data={'previous_state': old_state.value}
            ))
    
    def force_wake(self) -> None:
        """
        Force wake from sleep (for testing or manual control).
        
        NOTE: This bypasses normal idle detection.
        """
        if self.current_state == IdleState.SLEEP:
            self.current_state = IdleState.ACTIVE
            self.sleep_triggered = False
            self.check_in_triggered = False
            self.last_interaction_time = time.time()
            log.info("Wake forced")
            
            bus.publish(EventPayload(
                event_type=EventType.IDLE_WAKE_FORCED,
                source='idle_manager',
                data={'timestamp': time.time()}
            ))
    
    def update_config(self, **kwargs) -> None:
        """
        Update configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                log.debug(f"Updated idle config: {key} = {value}")
            else:
                log.warning(f"Unknown config parameter: {key}")


# Global instance for easy access
idle_manager: Optional[IdleManager] = None


def get_idle_manager() -> Optional[IdleManager]:
    """Get the global idle manager instance."""
    return idle_manager


def create_idle_manager(config: Optional[IdleConfig] = None) -> IdleManager:
    """
    Create and register the global idle manager.
    
    Args:
        config: Optional configuration for idle behavior
        
    Returns:
        Configured IdleManager instance
    """
    global idle_manager
    idle_manager = IdleManager(config)
    return idle_manager
