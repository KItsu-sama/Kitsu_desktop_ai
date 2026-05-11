"""
RULE: RUNTIME STATE & EXECUTION.
- Contains runtime state management and execution contexts.

ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- RuntimeOrchestrator (main coordinator)
- ServiceContainer (dependency injection)
- ModuleRegistry (module management)
- LifecycleManager (startup/shutdown)

What can import this?
- r.py (entry point only)
- domain/ (for runtime coordination)
- interfaces/ (for runtime integration)
- app/ (for application layer)

What imports it?
- r.py (main entry point)
- domain/ (runtime coordination)
- interfaces/ (desktop/web integration)

Is it active or deprecated?
- ACTIVE: Modern 4-layer architecture
- DEPRECATED: Legacy components (moved to legacy/)

Is it runtime-critical?
- CRITICAL: Core runtime execution
- All components are runtime-critical
- Failure here = system failure
"""

__version__ = "0.0.1"

# Runtime exports
from .legacy.orchestrator import Orchestrator
from .legacy.launcher import main
from .core.lifecycle import LifecycleManager
from .systems.system_monitor import SystemMonitor

# Runtime configuration
from .config.runtime_config import RuntimeConfig

__all__ = [
    "Orchestrator",
    "main",
    "LifecycleManager",
    "SystemMonitor",
    "RuntimeConfig"
]