"""
utils/file_security.py

Simple file security utilities for Kitsu.
Provides path validation and permission checking for file operations.
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Allowed base directories for file operations
ALLOWED_BASE_DIRS = [
    Path.cwd(),  # Current working directory
    Path.home() / ".kitsu",  # User config directory
    Path("data"),  # Data directory relative to cwd
    Path("logs"),  # Logs directory relative to cwd
]

def is_path_allowed(path: Path) -> bool:
    """Check if a path is within allowed directories."""
    try:
        resolved_path = path.resolve()
        for base_dir in ALLOWED_BASE_DIRS:
            try:
                base_resolved = base_dir.resolve()
                if resolved_path.is_relative_to(base_resolved):
                    return True
            except (ValueError, OSError):
                # Path doesn't exist or can't be resolved
                continue
        return False
    except (ValueError, OSError):
        return False

def safe_file_write(path, content, encoding='utf-8', append=False) -> bool:
    """Safely write content to a file with permission checks."""
    try:
        # Convert string to Path if needed
        path = Path(path) if isinstance(path, str) else path
        
        # Check if path is allowed
        if not is_path_allowed(path):
            logger.error("Path not allowed for write operation: %s", path)
            return False
        
        # Ensure parent directory exists and is allowed
        parent = path.parent
        if not parent.exists():
            if not is_path_allowed(parent):
                logger.error("Parent directory not allowed: %s", parent)
                return False
            parent.mkdir(parents=True, exist_ok=True)
        
        # Write file safely
        if append and path.exists():
            with path.open('a', encoding=encoding) as f:
                f.write(content)
        else:
            path.write_text(content, encoding=encoding)
        return True
        
    except (OSError, PermissionError) as e:
        logger.error("Failed to write file %s: %s", path, e)
        return False
    except Exception as e:
        logger.error("Unexpected error writing file %s: %s", path, e)
        return False

def safe_file_read(path, encoding='utf-8') -> Optional[str]:
    """Safely read content from a file with permission checks."""
    try:
        # Convert string to Path if needed
        path = Path(path) if isinstance(path, str) else path
        
        # Check if path is allowed
        if not is_path_allowed(path):
            logger.error("Path not allowed for read operation: %s", path)
            return None
        
        if not path.exists():
            return None
        
        return path.read_text(encoding=encoding)
        
    except (OSError, PermissionError) as e:
        logger.error("Failed to read file %s: %s", path, e)
        return None
    except Exception as e:
        logger.error("Unexpected error reading file %s: %s", path, e)
        return None
