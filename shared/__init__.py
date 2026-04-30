"""
RULE: GLOBAL CONSTANTS & UTILS.
- Contains cross-cutting concerns: Types, Config schemas, and Helper functions.
- Every other folder is allowed to import from here.
"""

__version__ = "0.0.1"

# Shared exports
from .config_loader import ConfigLoader
from .unified_config import UnifiedConfig
from .session_logger import SessionLogger
from .capability_flags import CapabilityFlags

# Utility exports
from .utils.layout_mapper import LayoutMapper
from .utils.metrics import metrics

__all__ = [
    "ConfigLoader",
    "UnifiedConfig",
    "SessionLogger",
    "CapabilityFlags",
    "LayoutMapper",
    "metrics"
]