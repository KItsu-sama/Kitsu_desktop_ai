"""
system/kill_switch.py

Emergency kill switch for dangerous automation actions.
Provides hotkey and programmatic emergency stop functionality.
"""

from __future__ import annotations
import asyncio
import logging
import signal
import threading
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger('kitsu.system.kill_switch')


class KillSwitch:
    """Emergency stop system for dangerous automation actions."""
    
    def __init__(self):
        self._armed = False
        self._triggered = False
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[], None]] = []
        self._hotkey_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def arm(self) -> None:
        """Arm the kill switch. Must be called before any dangerous automation."""
        with self._lock:
            if self._armed:
                return
            
            self._armed = True
            self._triggered = False
            self._start_hotkey_listener()
            log.info("Kill switch ARMED - Press Ctrl+C or F12 to emergency stop")
    
    def disarm(self) -> None:
        """Disarm the kill switch."""
        with self._lock:
            if not self._armed:
                return
            
            self._armed = False
            self._stop_hotkey_listener()
            log.info("Kill switch DISARMED")
    
    def is_armed(self) -> bool:
        """Check if kill switch is currently armed."""
        with self._lock:
            return self._armed
    
    def is_triggered(self) -> bool:
        """Check if kill switch has been triggered."""
        with self._lock:
            return self._triggered
    
    def add_callback(self, callback: Callable[[], None]) -> None:
        """Add callback to be executed when kill switch is triggered."""
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove callback from kill switch."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def trigger(self, reason: str = "Manual trigger") -> None:
        """Manually trigger the kill switch."""
        with self._lock:
            if not self._armed or self._triggered:
                return
            
            self._triggered = True
            log.warning(f"KILL SWITCH TRIGGERED - {reason}")
        
        # Execute callbacks outside of lock
        self._execute_callbacks()
    
    def reset(self) -> None:
        """Reset the kill switch after triggering (requires re-arming)."""
        with self._lock:
            if not self._triggered:
                return
            
            self._triggered = False
            log.info("Kill switch reset - call arm() to re-enable")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle SIGINT/SIGTERM signals."""
        signal_name = signal.Signals(signum).name
        self.trigger(f"Signal {signal_name}")
    
    def _start_hotkey_listener(self) -> None:
        """Start hotkey listener thread."""
        if self._hotkey_thread and self._hotkey_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._hotkey_thread = threading.Thread(target=self._hotkey_listener, daemon=True)
        self._hotkey_thread.start()
    
    def _stop_hotkey_listener(self) -> None:
        """Stop hotkey listener thread."""
        self._stop_event.set()
        if self._hotkey_thread and self._hotkey_thread.is_alive():
            self._hotkey_thread.join(timeout=1.0)
    
    def _hotkey_listener(self) -> None:
        """Listen for emergency hotkey (F12)."""
        try:
            import keyboard
            
            while not self._stop_event.is_set() and self._armed:
                if keyboard.is_pressed('F12'):
                    self.trigger("F12 hotkey")
                    break
                self._stop_event.wait(0.1)  # Check every 100ms
                
        except ImportError:
            # keyboard module not available, skip hotkey support
            log.debug("keyboard module not available, hotkey support disabled")
        except Exception as e:
            log.warning(f"Hotkey listener error: {e}")
    
    def _execute_callbacks(self) -> None:
        """Execute all registered callbacks."""
        callbacks = self._callbacks.copy()
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                log.error(f"Kill switch callback error: {e}")


# Context manager for automatic arming/disarming
class AutoKillSwitch:
    """Context manager that automatically arms/disarms kill switch."""
    
    def __init__(self, kill_switch: KillSwitch, reason: str = "Automation action"):
        self.kill_switch = kill_switch
        self.reason = reason
    
    def __enter__(self) -> KillSwitch:
        self.kill_switch.arm()
        return self.kill_switch
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.kill_switch.disarm()
        if exc_type == KeyboardInterrupt:
            self.kill_switch.trigger("Keyboard interrupt in context")


# Global instance
_global_kill_switch: Optional[KillSwitch] = None


def get_kill_switch() -> KillSwitch:
    """Get global kill switch instance."""
    global _global_kill_switch
    if _global_kill_switch is None:
        _global_kill_switch = KillSwitch()
    return _global_kill_switch


def initialize_kill_switch() -> KillSwitch:
    """Initialize global kill switch."""
    global _global_kill_switch
    if _global_kill_switch is not None:
        raise RuntimeError("Kill switch already initialized.")
    
    _global_kill_switch = KillSwitch()
    return _global_kill_switch


def reset_kill_switch() -> None:
    """Reset global kill switch (for testing)."""
    global _global_kill_switch
    if _global_kill_switch:
        _global_kill_switch.disarm()
    _global_kill_switch = None