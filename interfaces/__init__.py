"""
RULE: THE TOUCHPOINTS.
- Handles communication between the Python backend and the Tauri/Rust frontend.
- Contains CLI commands and bridge controllers.
"""

__version__ = "0.0.1"

import importlib.util
from typing import Dict, List, Any

# Interface exports
from .desktop.avatar.controller import AvatarController
from .desktop.gateway import PermissionedSystemGateway
from .desktop.terminal.interface import TerminalInterface

# Interface capability checks
def check_interface_capabilities() -> Dict[str, Any]:
    """Check which interface components are available and functional."""
    capabilities = {}
    
    # Check desktop interface availability
    capabilities["desktop"] = {
        "avatar": _check_module_exists("interfaces.desktop.avatar"),
        "shimeji": _check_module_exists("interfaces.desktop.shimeji"),
        "speech": _check_module_exists("interfaces.desktop.speech"),
        "terminal": True  # Terminal should always be available
    }
    
    # Check Tauri bridge availability
    capabilities["tauri_bridge"] = _check_module_exists("interfaces.tauri")
    
    # Determine overall interface status
    all_desktop_available = all(capabilities["desktop"].values())
    tauri_available = capabilities["tauri_bridge"]
    
    capabilities["overall"] = {
        "status": "full" if all_desktop_available and tauri_available else "degraded",
        "available_interfaces": [name for name, available in capabilities["desktop"].items() if available],
        "can_run_basic": capabilities["desktop"]["terminal"]  # Can always run basic terminal interface
    }
    
    return capabilities

def _check_module_exists(module_path: str) -> bool:
    """Check if a module exists and can be imported."""
    try:
        spec = importlib.util.find_spec(module_path)
        return spec is not None
    except (ImportError, ModuleNotFoundError):
        return False

# Global capability check
_interface_capabilities = check_interface_capabilities()
is_compatible = _interface_capabilities["overall"]["status"] == "full"

__all__ = [
    "AvatarController",
    "PermissionedSystemGateway",
    "TerminalInterface",
    "check_interface_capabilities",
    "is_compatible"
]
