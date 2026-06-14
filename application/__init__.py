"""
# application/__init__.py

RULE: APPLICATION COORDINATION LAYER.
- Handles command routing, user management, and application initialization.
- Bridge between entry point (r.py) and runtime orchestrator.
- Manages CLI commands, user profiles, and application state.

ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- CommandRouter (CLI command handling)
- UserManager (user profile and preferences)
- ApplicationAdapter (main app initialization)
- SplashScreen (startup UI)

What can import this?
- r.py (entry point only)
- scripts/ (setup wizards, first-run)
- runtime/ (for application initialization)

What imports it?
- r.py (main entry point)
- runtime/launchers/modern_launcher.py (ModernLauncher)
- scripts/first_run.py (setup scripts)

Is it active or deprecated?
- ACTIVE: All application layer systems
- NO DEPRECATED: Core application never deprecated

Is it runtime-critical?
- CRITICAL: CommandRouter, ApplicationAdapter
- SEMI-CRITICAL: UserManager (profile loading)
- NON-CRITICAL: SplashScreen (UI only)
- Failure here = cannot initialize application or route commands
"""

__version__ = "0.0.1"

# Application exports
try:
    from .launcher import main as app_main
    from .user_manager import UserManager
    from .main import ApplicationAdapter
except ImportError:
    pass

__all__ = [
    "app_main",
    "UserManager",
    "ApplicationAdapter",
]
