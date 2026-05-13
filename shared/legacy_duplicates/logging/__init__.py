"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- SessionLogger (session logging)
- Logger (general logging utilities)

What can import this?
- ALL folders (shared logging)
- No restrictions (global access)

What imports it?
- runtime/ (logging setup)
- infra/ (logging infrastructure)
- app/ (application logging)

Is it active or deprecated?
- ACTIVE: All logging systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: Logger
- SEMI-CRITICAL: SessionLogger
- Failure here = no logging capability
"""
