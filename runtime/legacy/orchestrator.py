"""
runtime/legacy/orchestrator.py

Shim providing a legacy-compatible `Orchestrator` class.
This wraps the current `RuntimeOrchestrator` implementation while
accepting the legacy initializer signature (optional runtime_config).
"""

from __future__ import annotations

from runtime.core.runtime_orchestrator import RuntimeOrchestrator, get_runtime_orchestrator


class Orchestrator(RuntimeOrchestrator):
    """Legacy-compatible orchestrator wrapper.

    The legacy codebase constructed an `Orchestrator(runtime_config)`; the
    current `RuntimeOrchestrator` takes no args. This shim accepts the
    legacy signature and stores the runtime_config for compatibility.
    """

    def __init__(self, runtime_config=None):
        super().__init__()
        self.runtime_config = runtime_config


def get_orchestrator() -> RuntimeOrchestrator:
    return get_runtime_orchestrator()


__all__ = ["Orchestrator", "get_orchestrator"]
