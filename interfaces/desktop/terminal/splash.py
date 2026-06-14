"""interfaces/desktop/terminal/splash.py

Deprecated location kept for backward compatibility.

The unified splash implementation was moved to:
- application/splash.py

Importers using the old path can continue to work.
"""

from application.splash import Splash as SplashScreen

__all__ = ["SplashScreen"]

