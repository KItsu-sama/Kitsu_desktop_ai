"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- ClockService (time management)
- Container (dependency injection)
- Engine (AI coordination)
- PerformanceManager (resource management)
- StripController (LED control)

What can import this?
- runtime/core/ (for DI container)
- runtime/launchers/ (for bootstrap)
- domain/ (for infrastructure services)

What imports it?
- runtime/core/runtime_orchestrator.py
- runtime/launchers/bootstrap.py
- domain/ (service coordination)

Is it active or deprecated?
- ACTIVE: All infrastructure systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: Container, ClockService
- SEMI-CRITICAL: Engine, PerformanceManager
- NON-CRITICAL: StripController
- Failure here = no dependency injection or time management
"""
