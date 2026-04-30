"""
RULE: ORCHESTRATION & PIPELINES.
- Coordinates between Domain and Infra.
- Handles the main chat loop and the "Strip System" logic.
- Does not perform low-level system tasks; it tells Infra to do them.
"""

__version__ = "0.0.1"

# Application layer exports
from .user_manager import UserManager
from .adapters import AdapterManager
from .commands.command_router import CommandRouter

__all__ = [
    "UserManager",
    "AdapterManager", 
    "CommandRouter"
]
