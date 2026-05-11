"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- PersonalityConfig (personality configuration)
- triggers.json (emotion triggers)
- ul_templates.json (micro-interaction templates)

What can import this?
- domain/personality/ (personality system)
- runtime/ (personality integration)
- interfaces/ (avatar expression)

What imports it?
- domain/personality/emotion_engine.py
- runtime/core/runtime_orchestrator.py
- interfaces/desktop/avatar/controller.py

Is it active or deprecated?
- ACTIVE: All personality systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: PersonalityConfig
- SEMI-CRITICAL: triggers.json, ul_templates.json
- Failure here = no personality configuration
"""
