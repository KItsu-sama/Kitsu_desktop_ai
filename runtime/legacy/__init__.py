"""
runtime.legacy

Compatibility shims to preserve legacy import paths while using the
current runtime implementations. These shims provide minimal wrappers
so modules that import `runtime.legacy.*` continue to work.
"""

from .orchestrator import Orchestrator, get_orchestrator
from .application import Application

__all__ = ["Orchestrator", "get_orchestrator", "Application"]
