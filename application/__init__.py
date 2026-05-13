"""
RULE: ORCHESTRATION & PIPELINES.
- Coordinates between Domain and Infra.
- Handles the main chat loop and the "Strip System" logic.
- Does not perform low-level system tasks; it tells Infra to do them.

ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- UserManager (user profile management)
- CommandRouter (CLI command handling)
- Adapters (system integration)

What can import this?
- runtime/ (for application coordination)
- interfaces/ (for UI integration)
- features/ (for feature coordination)

What imports it?
- runtime/ (orchestrator coordination)
- interfaces/ (desktop/web integration)
- features/ (plugin system)

Is it active or deprecated?
- ACTIVE: All application systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: CommandRouter, UserManager
- SEMI-CRITICAL: Adapters
- Failure here = no application coordination
"""

__version__ = "0.0.1"

# Application layer exports
from .user_manager import UserManager
from .commands.command_router import CommandRouter

__all__ = [
    "UserManager",
    "CommandRouter"
]
