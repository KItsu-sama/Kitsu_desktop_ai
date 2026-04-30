"""
src/interfaces.py

Interface definitions for dependency inversion and module communication.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class InterfaceType(Enum):
    """Types of interfaces available in the system."""
    AVATAR = "avatar"
    PERSONALITY = "personality"
    COMMAND_ROUTER = "command_router"
    TERMINAL = "terminal"


class InterfaceResponse:
    """Standard response format for interface calls."""
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error


class IAvatarController(ABC):
    """Interface for avatar control and expression management."""
    
    @abstractmethod
    async def set_expression(self, expression: str, intensity: float = 1.0) -> bool:
        """Set facial expression."""
        pass
    
    @abstractmethod
    async def set_emotion(self, emotion: str) -> bool:
        """Set emotional state."""
        pass
    
    @abstractmethod
    async def get_available_expressions(self) -> List[str]:
        """Get list of available expressions."""
        pass


class IPersonalityEngine(ABC):
    """Interface for personality and emotion processing."""
    
    @abstractmethod
    async def process_emotion(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """Process emotion trigger and return response."""
        pass
    
    @abstractmethod
    async def get_current_state(self) -> Dict[str, Any]:
        """Get current emotional state."""
        pass


class ICommandRouter(ABC):
    """Interface for command routing and processing."""
    
    @abstractmethod
    async def route_command(self, command: str, context: Dict[str, Any]) -> InterfaceResponse:
        """Route command to appropriate handler."""
        pass
    
    @abstractmethod
    async def register_handler(self, command_type: str, handler) -> bool:
        """Register a command handler."""
        pass


class ITerminalInterface(ABC):
    """Interface for terminal and CLI interactions."""
    
    @abstractmethod
    async def process_input(self, input_text: str) -> InterfaceResponse:
        """Process terminal input."""
        pass
    
    @abstractmethod
    async def run_voice_mode(self, orchestrator) -> bool:
        """Run in voice interaction mode."""
        pass


# Interface registry
_interface_registry: Dict[InterfaceType, List[type]] = {
    InterfaceType.AVATAR: [],
    InterfaceType.PERSONALITY: [],
    InterfaceType.COMMAND_ROUTER: [],
    InterfaceType.TERMINAL: [],
}


def register_interface(interface_type: InterfaceType, implementation_class: type) -> None:
    """Register an interface implementation."""
    _interface_registry[interface_type].append(implementation_class)


def get_interface(interface_type: InterfaceType) -> Optional[type]:
    """Get the first available interface implementation of a type."""
    implementations = _interface_registry.get(interface_type, [])
    return implementations[0] if implementations else None


def get_all_interfaces(interface_type: InterfaceType) -> List[type]:
    """Get all interface implementations of a type."""
    return _interface_registry.get(interface_type, []).copy()