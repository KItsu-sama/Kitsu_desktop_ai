"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- Launcher (original startup)
- Orchestrator (original event loop)
- Application (legacy lifecycle)
- Main (alternative entry point)

What can import this?
- runtime/launchers/legacy_compat.py (for compatibility)
- runtime/ (for fallback)

What imports it?
- runtime/launchers/legacy_compat.py
- runtime/ (for fallback scenarios)

Is it active or deprecated?
- DEPRECATED: All components superseded
- MAINTENANCE: Kept for compatibility only
- PLANNED REMOVAL: After modern architecture proven

Is it runtime-critical?
- NON-CRITICAL: Legacy only
- SEMI-CRITICAL: Fallback scenarios
- Failure here = use modern architecture instead
"""
