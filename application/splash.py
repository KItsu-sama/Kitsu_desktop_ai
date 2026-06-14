"""
application/splash.py

Unified Kitsu Splash Screen with both ASCII art styles and rich terminal support.
Combines simple text-based splash with enhanced rich console capabilities.
"""

import logging
from typing import Optional

from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)


class Splash:
    """Unified splash screen manager supporting both simple ASCII and rich terminal displays.

    Features:
    - Two ASCII art styles (simple and detailed)
    - Rich console support with colored panels
    - Backward compatibility: provides SplashScreen alias
    """

    SIMPLE_ASCII_ART = r"""
╭────────────────────────────────────────────────────────── 🦊 KITSU AI ──────────────────────────────────────────────────────────╮
│                                                                                  │
│ Event-Driven Architecture                                                                                                                                    │
│ • InputMux (Sanity Layer) → EventBus → AI Pipeline                                                                                                           │
│ • Multi-tier processing: FastBrain → SLM → LLM                                                                                                               │
│ • Judge validation and behavior gating                                                                                                                        │
│                                                                                                                                                            │
│ Type /help for commands or start chatting below!                                                                                                             │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""

    DETAILED_ASCII_ART = r"""

=============================||=============================                                                     
|               ░\                        /░               |                                                     
|             /░/ ░\                    /░ \░\             |                                                     
|           /░/    \░\                /░/    \░\           |                                                     
|          ░/        \░\            /░/        \░          |                                                     
|        /░░          \░\          /░/          ░░\        |                                                     
|       /░░            \░\        /░/            ░░\       |                                                     
|       ░░     /░░░░\   |░░\____/░░|   /░░░░\     ░░       |                                                     
|       ░░    |░░░░░░░ /░░/░░||░░\░░\ ░░░░░░░|    ░░       |                                                     
|       ░░   /░░░░░░░░░░░░░_=┘└=_░░░░░░░░░░░░░\   ░░       |                                                     
|       \░░  |░░░/░░░░░░░//      \\░░░░░░░░\░░|  ░░/       |                                                     
|        \░░/░░░░░░__░░░||        ||░░░__░░░░░░\░░/        |                                                     
|         \░░░░░░/1010\_░\\      //░_/0010\░░░░░░/         |                                                     
|         /░░\░░░░\0101_\░░¯=┐┌=¯░░/_0010/░░░░/░░\         |                                                     
|         ░░_\¯\\_░░░░░░¯\░░░||░░░/¯░░░░░░_//¯/_░░         |                                                     
|       /░░/10\   ¯\░░░░░░░░░||░░░░░░░░░/¯   /01\░░\       |                                                     
|       ░░░\010\     ¯\░░░░░░||░░░░░░/¯     /010/░░░       |                                                     
|      ░░\░░¯001¯\_     \░░░░||░░░░/     _/¯011¯░░/░░      |                                                     
|      ░░11\░░░¯\10=¯ = _ \░░||░░/ _ = ¯=01/¯░░░/01░░      |                                                     
|      \░\1101\░░░░░░░░░░░'░░||░░'░░░░░░░░░░░/0100/░/      |                                                     
|       \░░\001░░░░_101\░░░░░||░░░░░/110_░░░░010/░░/       |                                                     
|         \_░░░░░_/101/░░░/░░||░░\░░░\010\_░░░░░_/         |                                                     
|            ¯\\_░░░░░░░░/|░░||░░|\░░░░░░░__//¯            |                                                     
|                ¯\\_░░░░\ ¯¯  ¯¯ /░░░░░//¯                |                                                     
|                     \░░░░░░¯¯░░░░░░░/                    |                                                     
|                      \░░░░░||░░░░░/                      |                                                     
|                        ¯¯==--==¯¯                        |                                                     
=============================||=============================                                                          
"""

    def __init__(self, console: Optional[Console] = None, art_style: str = "detailed"):
        self.console = console or Console()
        self.art_style = art_style
        self._ascii_art = self._get_ascii_art(art_style)

    def _get_ascii_art(self, style: str) -> str:
        if style == "simple":
            return self.SIMPLE_ASCII_ART
        return self.DETAILED_ASCII_ART

    def switch_art_style(self, style: str) -> None:
        if style not in ["simple", "detailed"]:
            raise ValueError("Style must be 'simple' or 'detailed'")
        self.art_style = style
        self._ascii_art = self._get_ascii_art(style)
        logger.info("Switched to %s ASCII art style", style)

    def display_splash(
        self,
        mode: str = "text",
        model: str = "kitsu:character",
        use_rich: bool = True,
    ) -> None:
        if use_rich:
            try:
                self._display_rich_splash(mode, model)
            except UnicodeEncodeError:
                try:
                    self._display_text_splash(mode, model)
                except UnicodeEncodeError:
                    print(self._create_panel_text(mode, model))
        else:
            try:
                self._display_text_splash(mode, model)
            except UnicodeEncodeError:
                print(self._create_panel_text(mode, model))

    def _display_text_splash(self, mode: str, model: str) -> None:
        print(self._ascii_art)
        print(f"\n🎯 Mode: {mode}")
        print(f"🧠 Model: {model}")
        print("\n💡 Type your message below and press Enter to chat.")
        print("💡 Type 'exit' or 'quit' to stop.\n")

    def _display_rich_splash(self, mode: str, model: str) -> None:
        self.console.print(self._ascii_art, justify="center", style="bright_cyan")
        panel_text = self._create_panel_text(mode, model)
        self.console.print(
            Panel(
                panel_text,
                title="🦊 KITSU AI - Desktop VTuber Assistant",
                border_style="magenta",
            )
        )

    def _create_panel_text(self, mode: str, model: str) -> str:
        if self.art_style == "simple":
            return (
                "[bold cyan]Event-Driven Architecture[/bold cyan]\n"
                "[dim]• InputMux (Sanity Layer) → EventBus → AI Pipeline[/dim]\n"
                "[dim]• Multi-tier processing: FastBrain → SLM → LLM[/dim]\n"
                "[dim]• Judge validation and behavior gating[/dim]\n\n"
                "[cyan]Type[/cyan] [bold yellow]/help[/bold yellow] for commands or start chatting below!\n\n"
                "[cyan]Mode:[/cyan] [bold yellow]{mode}[/bold yellow]\n"
                "[cyan]Model:[/cyan] [bold yellow]{model}[/bold yellow]"
            ).format(mode=mode, model=model)

        return (
            "[bold magenta]With Emotion + Personality Systems[/bold magenta]\n\n"
            "[cyan]Type[/cyan] [bold yellow]/help[/bold yellow] for a full list of commands.\n"
            "[cyan]Type[/cyan] [bold yellow]/mood -h[/bold yellow] or [bold yellow]/style -h[/bold yellow] for command-specific help.\n"
            "[cyan]Tip[/cyan]: Most commands support -h / --help.\n\n"
            "[cyan]Mode:[/cyan] [bold yellow]{mode}[/bold yellow]\n"
            "[cyan]Model:[/cyan] [bold yellow]{model}[/bold yellow]"
        ).format(mode=mode, model=model)

    def display_ascii_art_only(self, use_rich: bool = True) -> None:
        if use_rich:
            self.console.print(self._ascii_art, justify="center", style="bright_cyan")
        else:
            print(self._ascii_art)

    def display_help_panel(self, mode: str = "text", model: str = "kitsu:character") -> None:
        panel_text = self._create_panel_text(mode, model)
        self.console.print(
            Panel(
                panel_text,
                title="🦊 KITSU AI - Desktop VTuber Assistant",
                border_style="magenta",
            )
        )


def display_kitsu_error_box(title: str, message: str, details: Optional[str] = None) -> None:
    """Print a friendly red error box using rich.

    If `details` contains a traceback, it will be boxed in a second panel.
    """

    console = Console()
    try:
        details_text = details or ""
        has_trace = "Traceback" in details_text or "most recent call last" in details_text

        header_lines = [
            "i think there is a flaw with my code",
            "",
            f"[bold red]{message}[/bold red]",
        ]

        if details_text and has_trace:
            console.print(
                Panel(
                    "\n".join(header_lines),
                    title=title,
                    border_style="red",
                    style="red",
                )
            )
            console.print(
                Panel(
                    details_text,
                    title="Traceback (most recent call last):",
                    border_style="red",
                    style="red",
                )
            )
            return

        if details_text:
            header_lines.append("")
            header_lines.append(f"[dim]{details_text}[/dim]")

        console.print(
            Panel(
                "\n".join(header_lines),
                title=title,
                border_style="red",
                style="red",
            )
        )
    except Exception:
        print("i think there is a flaw with my code")
        print(f"[ERROR] {title}: {message}")
        if details:
            print(details)


# Backward compatibility alias
SplashScreen = Splash

