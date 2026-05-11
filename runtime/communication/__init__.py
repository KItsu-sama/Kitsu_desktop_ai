"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- MessageBus (event routing)
- EventBus (event system)
- PolicyRouter (intent classification)

What can import this?
- All runtime/ (for communication)
- domain/ (for event coordination)
- interfaces/ (for UI integration)

What imports it?
- runtime/core/ (orchestration)
- runtime/systems/ (subsystem communication)
- domain/ (personality events)

Is it active or deprecated?
- ACTIVE: All communication systems
- NO DEPRECATED: Core communication never deprecated

Is it runtime-critical?
- CRITICAL: MessageBus, EventBus
- SEMI-CRITICAL: PolicyRouter
- Failure here = no inter-system communication
"""
