"""
RULE: MODULAR SKILLS.
- Contains self-contained abilities like 'quiz_solver' or 'voice'.
- Features should be easy to toggle on/off for the "Strip System."
- Can depend on Domain and Shared.

ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- QuizEngine (educational assistance)
- BrowserController (web integration)
- CommunityManager (user content)
- PluginAPI (feature development)

What can import this?
- runtime/ (for feature loading)
- app/ (for command integration)
- interfaces/ (for UI integration)

What imports it?
- runtime/core/runtime_orchestrator.py
- app/commands/command_router.py
- interfaces/ (feature UI)

Is it active or deprecated?
- ACTIVE: All feature systems
- DEPRECATED: None

Is it runtime-critical?
- NON-CRITICAL: All features are optional
- SEMI-CRITICAL: BrowserController (web features)
- Failure here = core system runs without features
"""

__version__ = "0.0.1"

import importlib.util
from typing import Dict, List, Any, Optional

# Feature dependency mappings
_FEATURE_DEPENDENCIES: Dict[str, List[str]] = {
    "quiz_solver": ["selenium", "requests"],
    "browser_integration": ["selenium", "webdriver_manager"],
    "community_features": ["requests", "aiohttp"],
}


def _check_module_exists(module_name: str) -> bool:
    """Check if a Python module is installed."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError):
        return False


def _check_dependency(feature_name: str) -> bool:
    """Internal dependency checker for feature availability."""
    required_modules = _FEATURE_DEPENDENCIES.get(feature_name, [])
    return all(_check_module_exists(module) for module in required_modules)


def _feature_available(feature_name: str) -> bool:
    """Check if the feature package is present and its dependencies are met."""
    if importlib.util.find_spec(f"plugins.{feature_name}") is None:
        return False
    return _check_dependency(feature_name)

# Feature exports (conditional based on availability)
_available_features: Dict[str, Any] = {}

if _feature_available("quiz_solver"):
    try:
        from .quiz_solver.quiz_engine import QuizEngine
        _available_features["quiz_solver"] = QuizEngine
    except ImportError:
        pass

if _feature_available("browser_integration"):
    try:
        from .browser_integration.browser_controller import BrowserController
        _available_features["browser_integration"] = BrowserController
    except ImportError:
        pass

if _feature_available("community_features"):
    try:
        from .community_features.community_manager import CommunityManager
        _available_features["community_features"] = CommunityManager
    except ImportError:
        pass


def get_available_features() -> List[str]:
    """Returns a list of features that have their dependencies met."""
    return list(_available_features.keys())


def get_feature(feature_name: str) -> Optional[Any]:
    """Get a feature class by name if available."""
    return _available_features.get(feature_name)


def check_dependency(feature_name: str) -> bool:
    """Check if a feature's dependencies are met."""
    return _check_dependency(feature_name)


def get_strip_system_status() -> Dict[str, Any]:
    """Check which features can run in stripped-down mode."""
    available = get_available_features()

    if len(available) == 0:
        strip_level = "minimal"
    elif len(available) <= 2:
        strip_level = "basic"
    else:
        strip_level = "full"

    return {
        "strip_level": strip_level,
        "available_features": available,
        "missing_dependencies": [f for f in list(_FEATURE_DEPENDENCIES.keys()) if f not in available],
        "can_run_core": True,
    }

# Global strip system check
_strip_status = get_strip_system_status()
is_compatible = len(_available_features) > 0

__all__ = [
    "get_available_features",
    "get_feature",
    "check_dependency",
    "get_strip_system_status",
    "is_compatible",
] + list(_available_features.keys())