"""
ARCHITECTURE OWNERSHIP:
=====================

- Launcher (4-layer architecture)
- LegacyCompat (bridge layer)
- Bootstrap (container setup)
- KitsuLauncher (alternative entry)

What can import this?
- r.py (main entry point only)
- runtime/ (for startup coordination)

What imports it?
- r.py (main entry point)
- runtime/ (startup coordination)

- ACTIVE: Launcher, LegacyCompat
- DEPRECATED: Bootstrap (legacy)
- MAINTENANCE: KitsuLauncher

Is it runtime-critical?
- CRITICAL: Startup sequence
- SEMI-CRITICAL: Bootstrap can fallback
- Failure here = no startup
"""
