"""
interfaces/desktop/terminal/banner.py

Banner components for terminal display.

Provides reusable banner components extracted from legacy runtime.
"""

import logging
from typing import Optional
from rich.console import Console
from rich.panel import Panel

log = logging.getLogger(__name__)


class Banner:
    """
    Reusable banner components for terminal display.
    
    Extracted from legacy/runtime/app.py panel display functionality.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def display_info_banner(
        self, 
        title: str, 
        content: str, 
        style: str = "blue",
        border_style: str = "blue"
    ) -> None:
        """
        Display an informational banner.
        
        Args:
            title: Banner title
            content: Banner content
            style: Text style
            border_style: Border style
        """
        self.console.print(Panel(
            content,
            title=title,
            border_style=border_style
        ))
    
    def display_success_banner(self, title: str, content: str) -> None:
        """Display a success-themed banner."""
        self.display_info_banner(title, content, "green", "green")
    
    def display_warning_banner(self, title: str, content: str) -> None:
        """Display a warning-themed banner."""
        self.display_info_banner(title, content, "yellow", "yellow")
    
    def display_error_banner(self, title: str, content: str) -> None:
        """Display an error-themed banner."""
        self.display_info_banner(title, content, "red", "red")
    
    def display_system_info(self, mode: str, model: str, additional_info: Optional[dict] = None) -> None:
        """
        Display system information banner.
        
        Args:
            mode: Application mode
            model: Model name
            additional_info: Additional system information
        """
        content = f"[cyan]Mode:[/cyan] [bold yellow]{mode}[/bold yellow]\n"
        content += f"[cyan]Model:[/cyan] [bold yellow]{model}[/bold yellow]"
        
        if additional_info:
            for key, value in additional_info.items():
                content += f"\n[cyan]{key.title()}:[/cyan] [bold yellow]{value}[/bold yellow]"
        
        self.display_info_banner(
            "🦊 KITSU AI - System Information",
            content,
            "cyan",
            "magenta"
        )
