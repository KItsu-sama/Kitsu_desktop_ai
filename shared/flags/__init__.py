"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- CapabilityFlags (feature flags)
- Budgets (resource budgets)
- Tiers (hardware tiers)

What can import this?
- ALL folders (shared flags)
- No restrictions (global access)

What imports it?
- runtime/ (capability management)
- app/ (feature detection)
- domain/ (capability checks)

Is it active or deprecated?
- ACTIVE: All flag systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: CapabilityFlags
- SEMI-CRITICAL: Budgets, Tiers
- Failure here = no feature management
"""
