"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- FileSecurity (safe file operations)
- Validation (config validation)

What can import this?
- ALL folders (shared security)
- No restrictions (global access)

What imports it?
- runtime/ (file operations)
- app/ (configuration validation)
- interfaces/ (security checks)

Is it active or deprecated?
- ACTIVE: All security systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: FileSecurity
- SEMI-CRITICAL: Validation
- Failure here = no secure file operations
"""
