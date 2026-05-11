"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- first_run.py (initial setup)
- setup_wizard.py (interactive configuration)
- quick_start.py (fast initialization)
- fast_brain_trainer.py (AI training)

What can import this?
- runtime/launchers/ (for setup)
- app/ (for configuration)
- None (scripts are standalone)

What imports it?
- runtime/launchers/launcher.py
- runtime/launchers/bootstrap.py
- r.py (entry point)

Is it active or deprecated?
- ACTIVE: All scripts are active
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: first_run.py (initial setup)
- SEMI-CRITICAL: setup_wizard.py, quick_start.py
- NON-CRITICAL: fast_brain_trainer.py (training only)
- Failure here = no initial setup or configuration
"""
