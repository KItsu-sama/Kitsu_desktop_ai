"""
shared/utils/logger.py

Utility functions for debug output management.
"""

import logging
from typing import Optional

# Global debug output state
_debug_enabled: bool = False

def set_debug_output(enabled: bool) -> None:
    """
    Enable or disable debug output.
    
    Args:
        enabled: Whether debug output should be enabled
    """
    global _debug_enabled
    _debug_enabled = enabled
    
    # Update logging level for root logger
    root_logger = logging.getLogger()
    if enabled:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

def is_debug_output_enabled() -> bool:
    """
    Check if debug output is currently enabled.
    
    Returns:
        True if debug output is enabled, False otherwise
    """
    return _debug_enabled

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
