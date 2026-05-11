"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- BehaviorEngine (attention & behavior)
- DesktopController (desktop integration)
- HealthMonitor (system health)
- IdleManager (idle state management)
- SystemMonitor (resource monitoring)

What can import this?
- runtime/core/ (for orchestration)
- runtime/launchers/ (for startup)
- domain/ (for coordination)

What imports it?
- runtime/core/runtime_orchestrator.py
- runtime/launchers/modern_launcher.py
- domain/ (behavior coordination)

Is it active or deprecated?
- ACTIVE: All systems are active
- NO DEPRECATED: Core runtime systems

Is it runtime-critical?
- CRITICAL: BehaviorEngine, HealthMonitor
- SEMI-CRITICAL: DesktopController, IdleManager, SystemMonitor
- Failure here = degraded behavior but system continues
"""
