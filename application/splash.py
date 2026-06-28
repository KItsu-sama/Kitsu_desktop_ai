"""application.splash

Splash wrapper.

All terminal output (including Rich rendering) must be centralized in
`application.terminal_ui`.

This module intentionally contains no Rich imports.
"""

from __future__ import annotations

from application.terminal_ui import display_splash as _display_splash
from application.terminal_ui import terminal_print_error


class Splash:
    """Compatibility wrapper around terminal_ui splash display."""

    def __init__(self, *args, **kwargs) -> None:  # kept for backward compatibility
        self._args = args
        self._kwargs = kwargs

    def display_splash(self, mode: str = "text", model: str = "kitsu:character", use_rich: bool = True) -> None:
        _display_splash(mode=mode, model=model, use_rich=use_rich)


# Backward compatibility alias(s)
SplashScreen = Splash


__all__ = [
    "Splash",
    "SplashScreen",
    "terminal_print_error",
]

