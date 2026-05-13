"""
RULE: EXTERNAL IMPLEMENTATIONS.
- Contains the "heavy lifting": LLM connectors, TTS engines, and File System access.
- All hardware-specific code (CPU/GPU detection) lives here.
- Wraps external APIs so the rest of the project stays clean.

ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- LLMFallback (LLM integration)
- BackgroundManager (task management)
- PreferenceStore (data persistence)
- Logger (logging infrastructure)
- Hardware detection (system requirements)

What can import this?
- runtime/ (for infrastructure services)
- domain/ (for external integrations)
- interfaces/ (for hardware access)

What imports it?
- runtime/core/runtime_orchestrator.py
- runtime/infrastructure/container.py
- domain/ai/ (LLM providers)

Is it active or deprecated?
- ACTIVE: All infrastructure systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: Logger, BackgroundManager
- SEMI-CRITICAL: LLMFallback, PreferenceStore
- NON-CRITICAL: Hardware detection (startup only)
- Failure here = no external integrations or logging
"""

__version__ = "0.0.1"

import platform
import psutil
from typing import Dict, Any

# Infrastructure exports
from .llm.llm_fallback_generator import LLMFallback
from .system.background_tasks import create_background_manager
from .storage.preferences import PreferenceStore
from .logging.logger import setup_logger, get_logger

# Hardware compatibility checks
def check_hardware_requirements() -> Dict[str, Any]:
    """Check if system meets minimum hardware requirements."""
    
    # Basic requirements
    cpu_cores = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    # Set compatibility flags
    is_compatible = {
        "llm_local": cpu_cores >= 4 and memory_gb >= 8,  # For local LLM inference
        "3d_rendering": memory_gb >= 16,  # For 3D avatar rendering
        "voice_synthesis": True,  # Voice synthesis works on most systems
        "full_features": cpu_cores >= 8 and memory_gb >= 16
    }
    
    return {
        "system_info": {
            "cpu_cores": cpu_cores,
            "memory_gb": round(memory_gb, 1),
            "platform": platform.system()
        },
        "compatibility": is_compatible,
        "recommended_mode": "full" if is_compatible["full_features"] else "basic"
    }

# Global compatibility check
_hardware_check = check_hardware_requirements()
is_compatible = _hardware_check["compatibility"]["full_features"]

__all__ = [
    "LLMFallback",
    "create_background_manager",
    "PreferenceStore",
    "setup_logger",
    "get_logger",
    "check_hardware_requirements",
    "is_compatible"
]
