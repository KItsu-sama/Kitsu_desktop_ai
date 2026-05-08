"""
Domain attention module.

Provides attention engine for dynamic prioritization.
"""

from .attention_manager import (
    AttentionManager,
    AttentionEvent,
    AttentionType,
    UrgencyLevel,
    AttentionState,
    ATTENTION_MANAGER
)

__all__ = [
    'AttentionManager',
    'AttentionEvent',
    'AttentionType', 
    'UrgencyLevel',
    'AttentionState',
    'ATTENTION_MANAGER'
]
