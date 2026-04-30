"""
ui/adapters.py

UI component adapters implementing core interfaces.
This allows core modules to depend on interfaces rather than
concrete UI implementations, fixing dependency inversion.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from domain.contracts.interfaces import (
    ICommandRouter, ITerminalInterface, IAvatarController,
    InterfaceResponse, register_interface, InterfaceType
)


class CommandRouterAdapter(ICommandRouter):
    """Adapter for ui.commands.command_router.CommandRouter."""
    
    def __init__(self, command_router):
        self._command_router = command_router
    
    async def route(self, command: str) -> Dict[str, Any]:
        """Route command to appropriate handler."""
        try:
            result = await self._command_router.route(command)
            return {
                'success': True,
                'data': result,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
    
    def register_command(self, name: str, handler: callable) -> None:
        """Register a new command handler."""
        if hasattr(self._command_router, 'register_command'):
            self._command_router.register_command(name, handler)


class TerminalInterfaceAdapter(ITerminalInterface):
    """Adapter for ui.terminal.interface.TerminalInterface."""
    
    def __init__(self, terminal_interface):
        self._terminal_interface = terminal_interface
    
    def set_mode(self, mode: str) -> None:
        """Set interface mode (text/voice)."""
        if hasattr(self._terminal_interface, 'set_mode'):
            self._terminal_interface.set_mode(mode)
    
    def set_model(self, model: str) -> None:
        """Set AI model."""
        if hasattr(self._terminal_interface, 'set_model'):
            self._terminal_interface.set_model(model)
    
    async def run_text_mode(self, orchestrator) -> None:
        """Run in text mode."""
        if hasattr(self._terminal_interface, 'run_text_mode'):
            await self._terminal_interface.run_text_mode(orchestrator)
    
    async def run_voice_mode(self, orchestrator) -> None:
        """Run in voice mode."""
        if hasattr(self._terminal_interface, 'run_voice_mode'):
            await self._terminal_interface.run_voice_mode(orchestrator)


class AvatarControllerAdapter(IAvatarController):
    """Adapter for ui.avatar.controller.AvatarController."""
    
    def __init__(self, avatar_controller):
        self._avatar_controller = avatar_controller
    
    async def set_expression(self, mood: str, style: str, state: str) -> bool:
        """Set avatar expression based on emotional state."""
        try:
            if hasattr(self._avatar_controller, 'set_expression'):
                await self._avatar_controller.set_expression(mood, style, state)
                return True
            return False
        except Exception:
            return False
    
    def is_visible(self) -> bool:
        """Check if avatar is currently visible."""
        if hasattr(self._avatar_controller, 'is_visible'):
            return self._avatar_controller.is_visible()
        return False
    
    async def show(self) -> bool:
        """Show avatar."""
        try:
            if hasattr(self._avatar_controller, 'show'):
                await self._avatar_controller.show()
                return True
            return False
        except Exception:
            return False
    
    async def hide(self) -> bool:
        """Hide avatar."""
        try:
            if hasattr(self._avatar_controller, 'hide'):
                await self._avatar_controller.hide()
                return True
            return False
        except Exception:
            return False


def register_ui_adapters():
    """Register all UI adapters with the interface registry."""
    try:
        # Register command router
        from interfaces.desktop.commands.command_router import CommandRouter
        # Note: This will be registered when the router is created
        
        # Register terminal interface
        from interfaces.desktop.terminal.interface import TerminalInterface
        terminal = TerminalInterface()
        adapter = TerminalInterfaceAdapter(terminal)
        register_interface(InterfaceType.UI, adapter)
        
        # Register avatar controller
        from interfaces.desktop.avatar.controller import AvatarController
        avatar = AvatarController()
        avatar_adapter = AvatarControllerAdapter(avatar)
        register_interface(InterfaceType.UI, avatar_adapter)
        
    except ImportError as e:
        # UI components not available, that's okay for headless mode
        pass


# Auto-register when module is imported
register_ui_adapters()
