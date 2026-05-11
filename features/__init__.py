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

# Feature exports (conditional based on availability)
_available_features = {}

# Try to import quiz_solver
if _check_dependency("quiz_solver"):
    try:
        from .quiz_solver.quiz_engine import QuizEngine
        _available_features["quiz_solver"] = QuizEngine
    except ImportError:
        pass

# Try to import browser_integration
if _check_dependency("browser_integration"):
    try:
        from .browser_integration.browser_controller import BrowserController
        _available_features["browser_integration"] = BrowserController
    except ImportError:
        pass

# Try to import community_features
if _check_dependency("community_features"):
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
    if feature_name == "quiz_solver":
        return _check_module_exists("selenium") or _check_module_exists("requests")
    elif feature_name == "browser_integration":
        return _check_module_exists("selenium") and _check_module_exists("webdriver_manager")
    elif feature_name == "community_features":
        return _check_module_exists("requests") and _check_module_exists("aiohttp")
    return False

def _check_dependency(feature_name: str) -> bool:
    """Internal dependency checker for feature availability."""
    return check_dependency(feature_name)

def _check_module_exists(module_name: str) -> bool:
    """Check if a Python module is installed."""
    try:
        importlib.util.find_spec(module_name)
        return True
    except (ImportError, ModuleNotFoundError):
        return False

# Strip system presence check
def get_strip_system_status() -> Dict[str, Any]:
    """Check which features can run in stripped-down mode."""
    available = get_available_features()
    
    # Determine strip system level
    if len(available) == 0:
        strip_level = "minimal"  # Only core personality system
    elif len(available) <= 2:
        strip_level = "basic"    # Essential features only
    else:
        strip_level = "full"     # All features available
    
    return {
        "strip_level": strip_level,
        "available_features": available,
        "missing_dependencies": [f for f in ["quiz_solver", "browser_integration", "community_features"] if f not in available],
        "can_run_core": True  # Core system always runs
    }

# Global strip system check
_strip_status = get_strip_system_status()
is_compatible = len(_available_features) > 0

# Dynamic exports based on availability
__all__ = [
    "get_available_features",
    "get_feature", 
    "check_dependency",
    "get_strip_system_status",
    "is_compatible"
] + list(_available_features.keys())