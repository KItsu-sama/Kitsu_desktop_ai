"""
shared/utils/logger.py

Utility functions for debug output management.
"""

import logging
from typing import Optional

# Global debug output state
_debug_enabled: bool = False

def _try_delegate_to_handler(enabled: bool | None = None) -> bool:
    """Delegate debug toggle/query to the console handler's real flag.

    Important: importing the handler module may trigger heavy imports.
    We keep this lightweight by only trying to import the specific
    module that defines the handler flag, and we swallow failures.

    Returns:
        - if enabled is None: the delegated value (True/False) when possible
        - if enabled is not None: True when delegation succeeded
        - False otherwise
    """
    if enabled is None:
        # Query only; do not import candidates that may be heavy.
        try:
            mod = __import__("infrastructure.logging.logger", fromlist=["is_debug_output_enabled", "_debug_output_enabled"])
            if hasattr(mod, "is_debug_output_enabled"):
                return bool(mod.is_debug_output_enabled())  # type: ignore[attr-defined]
            if hasattr(mod, "_debug_output_enabled"):
                return bool(getattr(mod, "_debug_output_enabled"))

        except Exception:
            return False

    # Toggle: best-effort.
    try:
        mod = __import__("infrastructure.logging.logger", fromlist=["set_debug_output"])
        if hasattr(mod, "set_debug_output"):
            mod.set_debug_output(enabled)  # type: ignore[attr-defined]
            return True

    except Exception:
        return False

    return False



def set_debug_output(enabled: bool) -> None:
    """Enable or disable debug output.

    Important: keep this flag consistent with the console handler.
    """
    global _debug_enabled
    delegated = _try_delegate_to_handler(enabled=enabled)
    _debug_enabled = enabled

    # If we managed to delegate, also update root logger level for
    # any loggers that depend on it.
    root_logger = logging.getLogger()
    if enabled:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    if not delegated:
        # Still keep internal state updated.
        return


def is_debug_output_enabled() -> bool:
    """Check if debug output is currently enabled.

    Priority:
      1) handler module flag (if readable)
      2) local cached flag

    We cannot reliably distinguish "handler flag is False" from
    "handler flag import failed" in every environment, so the handler
    value is only used when we also have matching local state.
    """
    delegated_value = _try_delegate_to_handler(enabled=None)

    # If local state was toggled this process, trust local.
    if _debug_enabled:
        return True

    # If local state is off, prefer delegated (but allow fallback).
    return bool(delegated_value)



def get_debug_logger(name: str) -> logging.Logger:
    """
    Get a logger with appropriate debug level set.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if _debug_enabled:
        logger.setLevel(logging.DEBUG)
    return logger
