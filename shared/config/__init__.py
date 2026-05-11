"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- ConfigLoader (configuration loading)
- UnifiedConfig (config merging)
- defaults.yaml (default configuration)

What can import this?
- ALL folders (shared configuration)
- No restrictions (global access)

What imports it?
- runtime/ (configuration loading)
- app/ (configuration management)
- domain/ (configuration access)

Is it active or deprecated?
- ACTIVE: All configuration systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: ConfigLoader, UnifiedConfig
- Failure here = no configuration loading
"""
