"""
Shared validation utilities.
"""

import re
from typing import Optional

def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text by removing potentially harmful characters and limiting length.
    
    Args:
        text: The text to sanitize
        max_length: Maximum allowed length (None for no limit)
    
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return str(text)
    
    # Remove control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Apply length limit if specified
    if max_length is not None and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized
