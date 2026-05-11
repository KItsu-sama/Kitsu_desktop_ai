"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- RuntimeConfig (configuration management)
- Profiles (hardware profiles)
- CapabilityGateway (capability flags)

What can import this?
- runtime/launchers/ (for startup config)
- runtime/core/ (for orchestration)
- domain/ (for capability checks)

What imports it?
- runtime/launchers/modern_launcher.py
- runtime/launchers/legacy_compat.py
- runtime/core/runtime_orchestrator.py

Is it active or deprecated?
- ACTIVE: All config systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: RuntimeConfig, Profiles
- SEMI-CRITICAL: CapabilityGateway
- Failure here = no startup or default config
"""
