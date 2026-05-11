"""
RULE: GLOBAL CONSTANTS & UTILS.
- Contains cross-cutting concerns: Types, Config schemas, and Helper functions.
- Every other folder is allowed to import from here.

ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- config/ (configuration management)
- flags/ (feature flags and capability management)
- logging/ (logging utilities)
- security/ (security and validation)
- personality/ (personality configuration)
- models/ (AI model configuration)
- utils/ (general utilities)
- data/ (data structures and schemas)
- config_files/ (static configuration files)

What can import this?
- ALL folders (shared utilities)
- No restrictions (global access)

What imports it?
- runtime/ (configuration)
- domain/ (constants)
- app/ (utilities)
- interfaces/ (layout)
- features/ (flags)
- infra/ (logging)

Is it active or deprecated?
- ACTIVE: All shared systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: ConfigLoader, CapabilityFlags
- SEMI-CRITICAL: SessionLogger, UnifiedConfig
- NON-CRITICAL: LayoutMapper, Metrics
- Failure here = no configuration or utilities
"""

__version__ = "0.0.1"

# Configuration exports
from .config.config_loader import ConfigLoader
from .config.unified_config import UnifiedConfig

# Feature flags exports
from .flags.capability_flags import CapabilityFlags
from .flags.budgets import BudgetManager

# Logging exports
from .logging.session_logger import SessionLogger
from .logging.logger import get_debug_logger, set_debug_output

# Security exports
from .security.file_security import safe_file_read, safe_file_write
from .security.validation import sanitize_text

# Personality exports - moved to domain/personality/emotion_config.py

# Utility exports
from .utils.layout_mapper import LayoutMapper
from .utils.metrics import metrics
from .utils.tracing import span

__all__ = [
    # Configuration
    "ConfigLoader",
    "UnifiedConfig",
    # Feature flags
    "CapabilityFlags",
    "BudgetManager",
    # Logging
    "SessionLogger",
    "get_debug_logger",
    "set_debug_output",
    # Security
    "safe_file_read",
    "safe_file_write",
    "sanitize_text",
    # Utilities
    "LayoutMapper",
    "metrics",
    "span",
]