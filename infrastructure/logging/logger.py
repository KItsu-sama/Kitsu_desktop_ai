"""
infastrucher/logging/logger.py
Logger setup for Kitsu with color support and proper level handling
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# Global debug output flag
_debug_output_enabled = False


class ColoredFormatter(logging.Formatter):
    """
    Formatter with color support for different log levels
    
    Colors:
    - DEBUG: White (37)
    - INFO: Cyan (36)
    - WARNING: Yellow (33)
    - ERROR: Red (31)
    """
    
    COLORS = {
        logging.DEBUG: '\033[37m',      # White
        logging.INFO: '\033[36m',       # Cyan
        logging.WARNING: '\033[33m',    # Yellow
        logging.ERROR: '\033[31m',      # Red
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Only apply colors to console output (not file)
        if hasattr(record, '_is_console') and record._is_console:
            color = self.COLORS.get(record.levelno, '')
            if color:
                record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        return super().format(record)


class DebugAwareHandler(logging.StreamHandler):
    """Stream handler that respects debug output toggle"""
    
    def emit(self, record):
        # For console stderr, filter DEBUG if debug output disabled
        if self.stream == sys.stderr and record.levelno == logging.DEBUG:
            if not _debug_output_enabled:
                return
        
        # Suppress verbose INFO messages when not in debug mode
        if self.stream == sys.stderr and record.levelno == logging.INFO:
            if not _debug_output_enabled:
                # Filter out common verbose INFO messages
                verbose_messages = [
                    "Debug mode disabled - hiding DEBUG logs",
                    " Kitsu Launcher starting...",
                    "Building runtime configuration...",
                    "Runtime config built:",
                    "Platform:",
                    "Mode:",
                    "Model:",
                    "Initializing KitsuEngine...",
                    "Initializing DesktopController...",
                    "Signal handlers registered",
                    "Running in text mode",
                    " DesktopController ready!"
                ]
                if any(msg in record.getMessage() for msg in verbose_messages):
                    return
        
        record._is_console = (self.stream == sys.stderr)
        super().emit(record)


def setup_logger(
    name: str = "kitsu",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup logger with proper level separation and color support
    
    - Console (stderr): INFO level with colors + DEBUG if enabled
    - File (kitsu.log): DEBUG level with all messages
    
    Args:
        name: Logger name for the returned logger handle
        log_file: Optional log file path (defaults to "data/logs/kitsu.log")
        
    Returns:
        Configured logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Logger accepts all, handlers filter
    
    # Remove existing handlers from the root logger so we don't duplicate output
    root_logger.handlers.clear()
    
    # Set default log file
    if log_file is None:
        log_file = "data/logs/kitsu.log"
    
    # =========================================================================
    # Console Handler (stderr) — INFO level with colors
    # =========================================================================
    console_handler = DebugAwareHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)  # DEBUG level, but filtered by handler
    
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # =========================================================================
    # File Handler (kitsu.log) — DEBUG level (all messages)
    # =========================================================================
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """Get existing logger by name"""
    return logging.getLogger(name)


def configure_logging(debug: bool = False, name: str = "kitsu", log_file: Optional[str] = None) -> logging.Logger:
    """Entry-point-friendly logging configuration."""
    set_debug_output(enabled=debug)
    return setup_logger(name=name, log_file=log_file)







def set_debug_output(enabled: bool):

    """

    Enable or disable debug output to console
    
    Args:
        enabled: True to show DEBUG logs, False to hide them
    """
    global _debug_output_enabled
    _debug_output_enabled = enabled


def is_debug_output_enabled() -> bool:
    """Check if debug output is currently enabled"""
    return _debug_output_enabled


# usage;
"""
# launcher.py (unchanged)
from shared.logging.logger import setup
setup(level=logging.DEBUG, log_dir="logs")

# New code
from shared.logging.logger import setup_logger, get_logger, set_debug_output
logger = setup_logger("kitsu.app.profiles")
set_debug_output(True)
logger = get_logger("kitsu")
"""