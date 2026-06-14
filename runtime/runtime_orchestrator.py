"""
runtime/runtime_orchestrator.py

Compatibility shim for the modern runtime orchestrator.

This module exists to preserve legacy import paths while the implementation
lives under runtime/core/runtime_orchestrator.py.
"""

from .core.runtime_orchestrator import RuntimeOrchestrator, get_runtime_orchestrator

__all__ = ["RuntimeOrchestrator", "get_runtime_orchestrator"]
