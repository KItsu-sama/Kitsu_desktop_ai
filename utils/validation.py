"""
utils/validation.py

Input validation utilities for Kitsu.
Provides safe validation for user input and other data.
"""

import re
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Input validation patterns
MAX_INPUT_LENGTH = 10000
ALLOWED_COMMANDS = {'help', 'status', 'quit', 'exit', 'q'}

def validate_user_input(user_input: str) -> Dict[str, Any]:
    """
    Validate user input for safety and length.
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Dict with validation results
    """
    if not isinstance(user_input, str):
        return {
            'valid': False,
            'error': 'Input must be a string',
            'sanitized': ''
        }
    
    # Remove leading/trailing whitespace
    sanitized = user_input.strip()
    
    # Check empty input
    if not sanitized:
        return {
            'valid': False,
            'error': 'Empty input',
            'sanitized': ''
        }
    
    # Check length
    if len(sanitized) > MAX_INPUT_LENGTH:
        logger.warning(f"Input too long: {len(sanitized)} chars (max: {MAX_INPUT_LENGTH})")
        return {
            'valid': False,
            'error': f'Input too long (max {MAX_INPUT_LENGTH} characters)',
            'sanitized': ''
        }
    
    # Check for potentially dangerous patterns
    dangerous_patterns = [
        r'<script.*?>.*?</script>',  # Script tags
        r'javascript:',             # JavaScript URLs
        r'data:',                   # Data URLs
        r'\x00',                   # Null bytes
        r'[\r\n]{3,}',            # Excessive newlines
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE | re.DOTALL):
            logger.warning(f"Potentially dangerous input pattern detected: {pattern}")
            return {
                'valid': False,
                'error': 'Input contains potentially dangerous content',
                'sanitized': ''
            }
    
    # Basic sanitization - normalize whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    return {
        'valid': True,
        'error': None,
        'sanitized': sanitized
    }

def validate_command(command: str) -> Dict[str, Any]:
    """
    Validate and normalize command input.
    
    Args:
        command: Command string
        
    Returns:
        Dict with validation results
    """
    if not isinstance(command, str):
        return {
            'valid': False,
            'error': 'Command must be a string',
            'command': None
        }
    
    # Normalize command
    normalized = command.lower().strip()
    
    # Check if it's a valid command
    if normalized in ALLOWED_COMMANDS:
        return {
            'valid': True,
            'error': None,
            'command': normalized
        }
    
    return {
        'valid': False,
        'error': f'Unknown command: {command}',
        'command': None
    }

def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Basic text sanitization.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return ''
    
    # Remove null bytes and control characters except newlines/tabs
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Apply length limit
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()
