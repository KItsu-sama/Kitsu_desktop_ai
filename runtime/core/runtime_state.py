"""
runtime/core/runtime_state.py

Runtime Health State Management

Tracks the overall health and operational state of the Kitsu runtime.
States are deterministic and transition based on lifecycle events.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Optional

logger = logging.getLogger(__name__)


class RuntimeState(Enum):
    """
    Runtime health state enum.
    
    Transitions:
    - BOOTING → RUNNING (success) or FAILED (bootstrap error)
    - RUNNING → DEGRADED (optional module failure)
    - RUNNING/DEGRADED → SHUTTING_DOWN (shutdown signal)
    - SHUTTING_DOWN → STOPPED (clean shutdown)
    - RUNNING/DEGRADED → SAFE_MODE (critical error recovery)
    - RUNNING/DEGRADED/SAFE_MODE → FAILED (unrecoverable error)
    """
    BOOTING = "booting"
    RUNNING = "running"
    DEGRADED = "degraded"
    SAFE_MODE = "safe_mode"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    FAILED = "failed"
    
    def __str__(self) -> str:
        return self.value


class RuntimeStateStore:
    """
    Singleton state store for runtime health tracking.
    
    Maintains current state, transition history, and optional persistence.
    Thread-safe with RLock for state mutations.
    """
    
    _instance: Optional[RuntimeStateStore] = None
    _lock = RLock()
    
    def __init__(self, persist: bool = True, state_file: Optional[Path] = None):
        self.persist = persist
        self.state_file = state_file or Path("data/runtime/runtime_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._state = RuntimeState.BOOTING
        self._state_lock = RLock()
        self._history: list[dict] = []
        self._crash_history: list[dict] = []
        self._consecutive_crashes = 0
        self._last_crash_time: Optional[datetime] = None
        self._safe_mode_forced = False
        
        self._load_persisted_state()
    
    @classmethod
    def get_singleton(cls, persist: bool = True) -> RuntimeStateStore:
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(persist=persist)
        return cls._instance
    
    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton (for testing)."""
        with cls._lock:
            cls._instance = None
    
    def set_state(
        self, 
        state: RuntimeState, 
        reason: Optional[str] = None,
        exception: Optional[Exception] = None
    ) -> None:
        """
        Set runtime state with optional reason and exception.
        
        Args:
            state: New runtime state
            reason: Human-readable reason for state change
            exception: Associated exception if any
        """
        with self._state_lock:
            old_state = self._state
            self._state = state
            
            # Record transition
            transition = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "from": str(old_state),
                "to": str(state),
                "reason": reason,
                "exception": str(exception) if exception else None,
            }
            self._history.append(transition)
            
            # Log state change
            if exception:
                logger.warning(
                    f"State transition: {old_state} → {state} ({reason})",
                    exc_info=exception
                )
            else:
                logger.info(f"State transition: {old_state} → {state}" + 
                           (f" ({reason})" if reason else ""))
            
            # Handle crash recording
            if state == RuntimeState.FAILED:
                self._record_crash(reason, exception)
            
            # Persist state if enabled
            if self.persist:
                self._persist_state()
    
    def get_state(self) -> RuntimeState:
        """Get current runtime state."""
        with self._state_lock:
            return self._state
    
    def record_crash(
        self, 
        phase: str, 
        exception: Exception,
        traceback_str: Optional[str] = None
    ) -> None:
        """
        Record a crash event.
        
        Args:
            phase: Startup phase when crash occurred
            exception: Exception that caused crash
            traceback_str: Optional traceback string
        """
        crash_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "phase": phase,
            "exception": str(exception),
            "exception_type": type(exception).__name__,
            "traceback": traceback_str,
        }
        
        with self._state_lock:
            self._crash_history.append(crash_entry)
            self._consecutive_crashes += 1
            self._last_crash_time = datetime.utcnow()
            
            if self.persist:
                self._persist_crashes()
    
    def _record_crash(
        self,
        reason: Optional[str] = None,
        exception: Optional[Exception] = None
    ) -> None:
        """Internal: record crash from set_state."""
        import traceback
        tb_str = traceback.format_exc() if exception else None
        
        self.record_crash(
            phase=reason or "unknown",
            exception=exception or Exception("Unknown failure"),
            traceback_str=tb_str
        )
    
    def mark_crash_recovered(self) -> None:
        """Mark the system as recovered from crash."""
        with self._state_lock:
            self._consecutive_crashes = 0
            if self.persist:
                self._persist_state()
    
    def get_crash_count(self) -> int:
        """Get current consecutive crash count."""
        with self._state_lock:
            return self._consecutive_crashes
    
    def get_last_crash_time(self) -> Optional[datetime]:
        """Get timestamp of last crash."""
        with self._state_lock:
            return self._last_crash_time
    
    def should_force_safe_mode(self, threshold: int = 2) -> bool:
        """
        Check if safe mode should be forced.
        
        Args:
            threshold: Consecutive crash count threshold
        """
        with self._state_lock:
            return self._consecutive_crashes >= threshold
    
    def set_safe_mode_forced(self, forced: bool = True) -> None:
        """Mark safe mode as forced."""
        with self._state_lock:
            self._safe_mode_forced = forced
            if self.persist:
                self._persist_state()
    
    def is_safe_mode_forced(self) -> bool:
        """Check if safe mode is currently forced."""
        with self._state_lock:
            return self._safe_mode_forced
    
    def get_state_summary(self) -> dict:
        """Get summary of current state and history."""
        with self._state_lock:
            return {
                "current_state": str(self._state),
                "safe_mode_forced": self._safe_mode_forced,
                "consecutive_crashes": self._consecutive_crashes,
                "last_crash_time": self._last_crash_time.isoformat() if self._last_crash_time else None,
                "transition_history": self._history[-10:],  # Last 10 transitions
                "crash_count_total": len(self._crash_history),
            }
    
    def _persist_state(self) -> None:
        """Persist current state to JSON file."""
        try:
            data = {
                "current_state": str(self._state),
                "safe_mode_forced": self._safe_mode_forced,
                "consecutive_crashes": self._consecutive_crashes,
                "last_crash_time": self._last_crash_time.isoformat() if self._last_crash_time else None,
                "transition_history": self._history,
            }
            self.state_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to persist runtime state: {e}")
    
    def _persist_crashes(self) -> None:
        """Persist crash history to separate file."""
        try:
            crash_file = self.state_file.parent / "crash_history.json"
            crash_file.write_text(json.dumps(self._crash_history, indent=2))
        except Exception as e:
            logger.error(f"Failed to persist crash history: {e}")
    
    def _load_persisted_state(self) -> None:
        """Load previously persisted state from file."""
        if not self.state_file.exists():
            return
        
        try:
            data = json.loads(self.state_file.read_text())
            self._state = RuntimeState(data.get("current_state", "booting"))
            self._safe_mode_forced = data.get("safe_mode_forced", False)
            self._consecutive_crashes = data.get("consecutive_crashes", 0)
            
            last_crash_str = data.get("last_crash_time")
            if last_crash_str:
                self._last_crash_time = datetime.fromisoformat(last_crash_str.replace("Z", "+00:00"))
            
            self._history = data.get("transition_history", [])
            
            logger.debug(f"Loaded persisted runtime state: {self._state}")
        except Exception as e:
            logger.warning(f"Failed to load persisted state: {e}")
