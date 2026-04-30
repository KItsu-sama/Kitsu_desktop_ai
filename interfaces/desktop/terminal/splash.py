"""
Terminal splash screen components.

Extracted from legacy/runtime/app.py for reuse in the main application.
"""

import logging
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel

log = logging.getLogger(__name__)


class SplashScreen:
    """
    Manages terminal splash screen display with ASCII art and dynamic information.
    
    Extracted from legacy/runtime/app.py lines 58-108.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._ascii_art = self._get_ascii_art()
    
    def _get_ascii_art(self) -> str:
        """Get the Kitsu ASCII art."""
        return r"""


|               ░\                        /░                |
|             /░/ ░\                    /░ \░\              |
|           /░/    \░\                /░/    \░\            |
|          ░/        \░\            /░/        \░           |
|        /░░          \░\          /░/          ░░\         |
|       /░░            \░\        /░/            ░░\        |
|       ░░     /░░░░\   |░░\____/░░|   /░░░░\     ░░        |
|       ░░    |░░░░░░░ /░░/░░||░░\░░\ ░░░░░░░|    ░░        |
|       ░░   /░░░░░░░░░░░░░_=┘└=_░░░░░░░░░░░░░\   ░░        |
|       \░░  |░░░/░░░░░░░//      \\░░░░░░░░\░░|  ░░/        |
|        \░░/░░░░░░__░░░||        ||░░░__░░░░░░\░░/         |
|         \░░░░░░/1010\_░\\      //░_/0010\░░░░░░/          |
|         /░░\░░░░\0101_\░░¯=┐┌=¯░░/_0010/░░░░/░░\          |
|         ░░_\¯\\_░░░░░░¯\░░░||░░░/¯░░░░░░_//¯/_░░          |
|       /░/010\   ¯\░░░░░░░░░||░░░░░░░░░/¯   /010\░\        |
|       ░░░\010\     ¯\░░░░░░||░░░░░░/¯     /010/░░░        |
|      ░░\░░¯001¯\_     \░░░░||░░░░/     _/¯011¯░░/░░       |
|      ░░11\░░░¯\10=¯ = _ \░░||░░/ _ = ¯=01/¯░░░/01░░       |
|      \░░\101\░░░░░░░░░░░'░░||░░'░░░░░░░░░░░/010/░░/       |
|       \░░\001░░░░_101\░░░░░||░░░░░/110_░░░░010/░░/        |
|         \_░░░░░_/101/░░░/░░||░░\░░░\010\_░░░░░_/          |
|            ¯\\_░░░░░░░░/|░░||░░|\░░░░░░░__//¯             |
|                ¯\\_░░░░\ ¯¯  ¯¯ /░░░░░//¯                 |
|                     \░░░░░░¯¯░░░░░░░/                     |
|                      \░░░░░||░░░░░/                       |
|                        ¯¯==--==¯¯                         |


"""
    
    def display_splash(self, mode: str = "text", model: str = "unknown") -> None:
        """
        Display the complete splash screen with ASCII art and information panel.
        
        Args:
            mode: Application mode (text, voice, etc.)
            model: Model name being used
        """
        # Display ASCII art centered
        self.console.print(self._ascii_art, justify="center", style="bright_cyan")
        
        # Create information panel
        panel_text = self._create_panel_text(mode, model)
        
        # Display panel with title
        self.console.print(Panel(
            panel_text, 
            title="🦊 KITSU AI - Desktop VTuber Assistant", 
            border_style="magenta"
        ))
    
    def _create_panel_text(self, mode: str, model: str) -> str:
        """Create the panel text content."""
        return (
            "[bold magenta]With Emotion + Personality Systems[/bold magenta]\n\n"
            
            "[cyan]Type[/cyan] [bold yellow]/help[/bold yellow] for a full list of commands.\n"
            "[cyan]Type[/cyan] [bold yellow]/mood -h[/bold yellow] or [bold yellow]/style -h[/bold yellow] for command-specific help.\n"
            "[cyan]Tip[/cyan]: Most commands support -h / --help.\n\n"
            "[cyan]Mode:[/cyan] [bold yellow]{mode}[/bold yellow]\n"
            "[cyan]Model:[/cyan] [bold yellow]{model}[/bold yellow]"
        ).format(mode=mode, model=model)
    
    def display_ascii_art_only(self) -> None:
        """Display just the ASCII art without the information panel."""
        self.console.print(self._ascii_art, justify="center", style="bright_cyan")
    
    def display_help_panel(self, mode: str = "text", model: str = "unknown") -> None:
        """Display just the help information panel."""
        panel_text = self._create_panel_text(mode, model)
        self.console.print(Panel(
            panel_text,
            title="🦊 KITSU AI - Desktop VTuber Assistant",
            border_style="magenta"
        ))
