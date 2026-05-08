"""
Domain capabilities module.

Provides capability sandbox system for Kitsu's safety.
"""

from .capability_manager import (
    CapabilityManager,
    Capability,
    PermissionLevel,
    PermissionContext,
    AuditEntry,
    CapabilityRule,
    CAPABILITY_MANAGER
)

__all__ = [
    'CapabilityManager',
    'Capability', 
    'PermissionLevel',
    'PermissionContext',
    'AuditEntry',
    'CapabilityRule',
    'CAPABILITY_MANAGER'
]
