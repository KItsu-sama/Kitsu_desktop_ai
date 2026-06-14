"""
runtime/core/crash_manager.py

Crash History and Recovery Management

Handles crash logging, recovery tracking, and crash-driven safe-mode forcing.
Replaces legacy crash.log and last_crash.json logic with centralized state management.
"""

from __future__ import annotations

import json
import logging
import traceback as tb
from datetime import datetime
from pathlib import Path
from typing import Optional

from .runtime_state import RuntimeState, RuntimeStateStore

logger = logging.getLogger(__name__)

CRASH_THRESHOLD = 2
CRASH_LOG_DIR = Path("data/runtime/logs/crashes")
CRASH_HISTORY_FILE = Path("data/runtime/crash_history.json")


def init_crash_logging() -> None:
    """Initialize crash logging directories."""
    CRASH_LOG_DIR.mkdir(parents=True, exist_ok=True)


def record_crash(
    phase: str,
    exception: Exception,
    boot_attempt: int = 1,
) -> None:
    """
    Record a crash with full details.
    
    Args:
        phase: Startup phase when crash occurred
        exception: Exception that triggered crash
        boot_attempt: Which boot attempt this crash occurred on
    """
    init_crash_logging()
    state_store = RuntimeStateStore.get_singleton()
    
    # Get traceback
    tb_str = "".join(tb.format_exception(type(exception), exception, exception.__traceback__))
    
    # Record in state store
    state_store.record_crash(phase=phase, exception=exception, traceback_str=tb_str)
    
    # Write individual crash log file
    crash_timestamp = datetime.utcnow().isoformat().replace(":", "-").split(".")[0]
    crash_file = CRASH_LOG_DIR / f"crash_{crash_timestamp}_{phase}.log"
    
    try:
        crash_log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "phase": phase,
            "boot_attempt": boot_attempt,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": tb_str,
            "crash_count": state_store.get_crash_count(),
        }
        crash_file.write_text(json.dumps(crash_log, indent=2))
        logger.error(f"Crash logged to {crash_file}")
    except Exception as e:
        logger.error(f"Failed to write crash log file: {e}")


def check_should_force_safe_mode(threshold: int = CRASH_THRESHOLD) -> bool:
    """
    Check if safe mode should be forced due to crash history.
    
    Args:
        threshold: Consecutive crash count to trigger safe mode
        
    Returns:
        True if safe mode should be forced
    """
    state_store = RuntimeStateStore.get_singleton()
    
    # Check environment variable override
    import os
    if os.environ.get("KITSU_SAFE_MODE", "").lower() in ("1", "true", "yes"):
        logger.info("Safe mode forced via KITSU_SAFE_MODE environment variable")
        state_store.set_safe_mode_forced(True)
        return True
    
    # Check crash threshold
    if state_store.should_force_safe_mode(threshold):
        logger.warning(f"Safe mode forced: {state_store.get_crash_count()} consecutive crashes >= {threshold}")
        state_store.set_safe_mode_forced(True)
        return True
    
    return False


def mark_boot_successful() -> None:
    """
    Mark current boot as successful, resetting crash counter.
    Call this once the system is fully initialized and stable.
    """
    state_store = RuntimeStateStore.get_singleton()
    state_store.mark_crash_recovered()
    logger.info("Boot successful - crash counter reset")


def get_crash_summary() -> dict:
    """Get summary of crash history."""
    state_store = RuntimeStateStore.get_singleton()
    return {
        "consecutive_crashes": state_store.get_crash_count(),
        "last_crash_time": state_store.get_last_crash_time().isoformat() if state_store.get_last_crash_time() else None,
        "safe_mode_forced": state_store.is_safe_mode_forced(),
    }


def reset_crash_history() -> None:
    """Reset crash history (for testing or manual intervention)."""
    state_store = RuntimeStateStore.get_singleton()
    state_store.mark_crash_recovered()
    state_store.set_safe_mode_forced(False)
    logger.info("Crash history reset")
