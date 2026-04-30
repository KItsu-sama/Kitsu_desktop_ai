# ui/terminal/__init__.py
"""
Terminal UI components for Kitsu Desktop AI.

Provides Rich-based terminal interface components including
splash screens, banners, and interactive elements.
"""

from .splash import SplashScreen
from .banner import Banner
from .interface import TerminalInterface

__all__ = ['SplashScreen', 'Banner', 'TerminalInterface']
