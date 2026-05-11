"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- KitsuIdentity (self-model and personality)

What can import this?
- runtime/core/ (for orchestration)
- domain/personality/ (for personality integration)
- interfaces/desktop/ (for avatar integration)

What imports it?
- runtime/core/runtime_orchestrator.py
- domain/personality/emotion_engine.py
- interfaces/desktop/avatar/controller.py

Is it active or deprecated?
- ACTIVE: Core identity system
- NO DEPRECATED: Identity never deprecated

Is it runtime-critical?
- CRITICAL: Core personality and identity
- Failure here = no personality, but system may continue
"""
