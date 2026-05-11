"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- RuntimeOrchestrator (main coordinator)
- ModuleRegistry (module management)
- LifecycleManager (startup/shutdown)
- ServiceContainer (dependency injection)

What can import this?
- runtime/launchers/ (for startup)
- runtime/legacy/ (for compatibility)
- domain/ (for coordination)

What imports it?
- runtime/launchers/modern_launcher.py
- runtime/launchers/legacy_compat.py
- runtime/ (for core coordination)

Is it active or deprecated?
- ACTIVE: Modern 4-layer architecture
- NO DEPRECATED: Core architecture never deprecated

Is it runtime-critical?
- CRITICAL: Core runtime execution
- All components are runtime-critical
- Failure here = system failure
"""
