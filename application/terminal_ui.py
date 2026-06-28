"""application.terminal_ui

Single terminal output gateway for Rich-based UI rendering.

Goals:
- All Rich imports live in this file.
- All user-facing terminal prints/prompts should route through this module.
- Provides safe plain-text fallbacks when Rich is unavailable.

This module is intentionally dependency-light: only stdlib + optional rich.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence


try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box

    _RICH_AVAILABLE = True
except Exception:  # pragma: no cover
    Console = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    Prompt = None  # type: ignore[assignment]
    Confirm = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]
    box = None  # type: ignore[assignment]
    _RICH_AVAILABLE = False


@dataclass(frozen=True)
class TerminalCapabilities:
    supports_rich: bool


_CAPS = TerminalCapabilities(supports_rich=_RICH_AVAILABLE)


def capabilities() -> TerminalCapabilities:
    """Return terminal UI capabilities."""

    return _CAPS


def _get_console() -> Optional[Any]:
    if not _RICH_AVAILABLE or Console is None:
        return None
    try:
        return Console()
    except Exception:  # pragma: no cover
        return None


def terminal_print(text: str = "", *, style: Optional[str] = None, end: str = "\n") -> None:
    """Print a line to terminal.

    When Rich is available, uses Console.print so rich markup can be rendered.
    Otherwise falls back to built-in print.
    """

    if _RICH_AVAILABLE is not None and Console is not None:
        console = _get_console()
        if console is not None:
            console.print(text, style=style, end=end)
            return

    # Plain fallback
    print(text, end=end)


def terminal_print_panel(
    title: str,
    body: str,
    *,
    border_style: str = "magenta",
    style: Optional[str] = None,
) -> None:

    """Print a rich panel (or plain text fallback)."""

    if _RICH_AVAILABLE is not None and Panel is not None and box is not None:
        console = _get_console()
        if console is not None:
            console.print(
                Panel(
                    body,
                    title=title,
                    border_style=border_style,
                    style=(style if style is not None else ""),
                    box=box.DOUBLE_EDGE,
                )
            )
            return


    # Plain fallback
    terminal_print(f"[{title}] {body}")


def terminal_print_error(title: str, message: str, details: Optional[str] = None) -> None:

    """Print an error box."""

    if details:



        # Make it deterministic and readable in plain mode.
        details_block = details
        full = f"{message}\n\n{details_block}"
    else:
        full = message

    if _RICH_AVAILABLE and Panel is not None and box is not None:
        console = _get_console()
        if console is not None:
            header = f"[bold red]{message}[/bold red]"
            if details:
                console.print(Panel(f"\n{header}", title=title, border_style="red", style="red", box=box.DOUBLE_EDGE))
                console.print(Panel(details, title="Traceback", border_style="red", style="red", box=box.DOUBLE_EDGE))
            else:
                console.print(Panel(header, title=title, border_style="red", style="red", box=box.DOUBLE_EDGE))
            return

    terminal_print_panel(title=title, body=full, border_style="red")


def terminal_print_table(
    title: str,
    rows: Sequence[tuple[str, str, str]],
) -> None:
    """Print a table with 3 columns: Component/Status/Detail."""

    if _RICH_AVAILABLE:
        console = _get_console()
        if console is not None and Table is not None:
            t = Table(title=title)
            t.add_column("Component")
            t.add_column("Status")
            t.add_column("Detail")
            for comp, status, detail in rows:
                t.add_row(comp, status, detail)
            console.print(t)
            return

    # Plain fallback
    terminal_print(title)
    for comp, status, detail in rows:
        terminal_print(f"- {comp}: {status} | {detail}")


def terminal_print_json(obj: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
    """Print machine-readable JSON via terminal."""

    import json

    txt = json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent)
    terminal_print(txt)


def terminal_ask_yes_no(
    prompt: str,
    *,
    default: bool = False,
    help_text: Optional[str] = None,
) -> bool:
    """Ask yes/no in terminal.

    If Rich is available, uses Confirm.ask.
    If help_text is provided and Rich is used, we fall back to plain mode
    because the existing code uses a custom [h] handler.
    """

    if _RICH_AVAILABLE and Confirm is not None and help_text is None:
        try:
            return bool(Confirm.ask(prompt, default=default))
        except Exception:
            pass

    # Plain fallback with optional 'h'
    default_str = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} ({default_str}) ").strip()
        if raw.lower() == "h" and help_text:
            terminal_print(help_text)
            continue
        if not raw:
            return default
        if raw.lower() in {"y", "yes"}:
            return True
        if raw.lower() in {"n", "no"}:
            return False
        terminal_print("Please enter Y or N (or 'h' for help).")


def terminal_ask_question(
    prompt: str,
    *,
    default: str = "",
    options: Optional[list[str]] = None,
) -> str:
    """Ask a free-form question or constrained options."""

    if _RICH_AVAILABLE and Prompt is not None and options:
        try:
            choices = options
            ans = Prompt.ask(prompt, choices=choices, default=default)
            return str(ans)
        except Exception:
            pass

    if _RICH_AVAILABLE and Prompt is not None and not options:
        try:
            ans = Prompt.ask(prompt, default=default)
            return str(ans)
        except Exception:
            pass

    # Plain fallback
    opts_suffix = f" ({'/'.join(options[:3])}{'...' if len(options or []) > 3 else ''})" if options else ""
    full_prompt = f"{prompt}{opts_suffix} [{default}]: " if default else f"{prompt}{opts_suffix}: "
    while True:
        raw = input(full_prompt).strip()
        if not raw:
            raw = default
        if options and raw not in options:
            terminal_print(f"Invalid option. Choose from: {', '.join(options)}")
            continue
        return raw


# ----------------------------------------------------------------------------
# Splash helpers
# ----------------------------------------------------------------------------


SIMPLE_ASCII_ART = r"""
╭────────────────────────────────────────────────────────── 🦊 KITSU AI ──────────────────────────────────────────────────────────╮
│                                                                                  │
│ Event-Driven Architecture                                                                                                                                    │
│ • InputMux (Sanity Layer) → EventBus → AI Pipeline                                                                                                           │
│ • Multi-tier processing: FastBrain → SLM → LLM                                                                                                               │
│ • Judge validation and behavior gating                                                                                                                        │
│                                                                                                                                                            │
│ Type /help for commands or start chatting below!                                                                                                             │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""


DETAILED_ASCII_ART = r"""

=============================||=============================                                                     
|               ░\                        /░               |
|            /░/  ░\                    /░  \░\            |
|          /░/     \░░\              /░░/     \░\          |
|          ░/        \░░\          /░░/        \░          |
|        /░/          \░░\        /░░/          \░\        |
|       /░|            \░░\      /░░/            |░\       |
|       ░░     /====\    ░░\____/░░    /====\     ░░       |
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
|      ░|11\░░░░¯\0=¯ = _ \░░||░░/ _ = ¯=1/¯░░░░/01|░      |
|      \░░0101\░░░░░░░░░░░'░░||░░'░░░░░░░░░░░/0100░░/      |
|       \░░\0010░░░_101\░░░░░||░░░░░/110_░░░1010/░░/       |
|         \_░░░░░_/101/░░░/░░||░░\░░░\010\_░░░░░_/         |
|            ¯\\_░░░░░░░░/|░░||░░|\░░░░░░░░_//¯            |
|                ¯\\_░░░░\ ¯¯  ¯¯ /░░░░░//¯                |
|                     \░░░░░░¯¯░░░░░░░/                    |
|                      \░░░░░||░░░░░/                      |
|                        ¯¯==--==¯¯                        |               
=============================||=============================                                                     
"""


def display_splash(mode: str = "text", model: str = "kitsu:character", *, use_rich: bool = True) -> None:
    """Display the Kitsu splash header.

    This is a thin wrapper and should be used by all entry points.
    """

    if use_rich and _RICH_AVAILABLE and Panel is not None and box is not None:
        console = _get_console()
        if console is not None:
            console.print(DETAILED_ASCII_ART, justify="center", style="bright_cyan")
            panel_text = (
                "[bold magenta]With Emotion + Personality Systems[/bold magenta]\n\n"
                "[cyan]Type[/cyan] [bold yellow]/help[/bold yellow] for a full list of commands.\n"
                f"[cyan]Mode:[/cyan] [bold yellow]{mode}[/bold yellow]\n"
                f"[cyan]Model:[/cyan] [bold yellow]{model}[/bold yellow]"
            )
            console.print(Panel(panel_text, title="🦊 KITSU AI - Desktop VTuber Assistant", border_style="magenta", box=box.DOUBLE_EDGE))
            return

    # Plain fallback
    print(DETAILED_ASCII_ART)
    print(f"\n🎯 Mode: {mode}")
    print(f"🧠 Model: {model}")
    print("\n💡 Type your message below and press Enter to chat.")
    print("💡 Type 'exit' or 'quit' to stop.\n")

