"""
config/capability_flags.py

All capability flags for Kitsu.

Rules:
- Flags are set ONCE by launcher.py before lock_flags() is called.
- After lock_flags(), any write raises RuntimeError.
- No module outside app/bootstrap.py and app/launcher.py may call set_flag().
- Call sites never check 'if USE_SLM:' — they use null implementations instead.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field, fields
from typing import Any, Dict

logger = logging.getLogger('kitsu.config.capability_flags')


class CapabilityFlagsLockedError(RuntimeError):
    """Raised when trying to modify flags after they are locked."""


@dataclass
class CapabilityFlags:
    # --- Always-on (cannot be disabled) ---
    use_fast_brain: bool = True
    use_emotion: bool = True

    # --- Avatar ---
    use_2d: bool = False
    use_3d: bool = False

    # --- AI stack ---
    use_slm: bool = True
    use_llm: bool = False

    # --- Input/output ---
    use_voice: bool = False

    # --- Desktop ---
    use_shimeji: bool = False
    use_system_control: bool = False

    _locked: bool = field(default=False, init=False, repr=False)

    def __setattr__(self, key: str, value: Any) -> None:
        """Override setattr to enforce locking."""
        if self._locked and key != '_locked':
            raise CapabilityFlagsLockedError(
                f"Capability flags are locked. Cannot set '{key}' after startup."
            )
        super().__setattr__(key, value)

    def set_flag(self, name: str, value: bool) -> None:
        """Set a single flag by name. Must be called before lock."""
        if not hasattr(self, name):
            raise ValueError(f"Unknown capability flag: '{name}'")
        setattr(self, name, value)

    def lock(self) -> None:
        """Called once by launcher.py after all flags are set. Irreversible."""
        self._locked = True

    def flags_are_locked(self) -> bool:
        """Check if flags are locked."""
        return self._locked

    @classmethod
    def from_profile(cls, profile_data: Dict[str, Any]) -> 'CapabilityFlags':
        """Apply a dict of flag overrides from a profile YAML. Must be called before lock."""
        flags = cls()
        for name, value in profile_data.get('flags', {}).items():
            flags.set_flag(name, bool(value))
        return flags

    def apply_profile(self, overrides: Dict[str, Any]) -> None:
        """Apply flag overrides directly to this instance. Must be called before lock."""
        for name, value in overrides.items():
            self.set_flag(name, bool(value))

    def as_dict(self) -> Dict[str, bool]:
        """Return all flags as a dictionary."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def validate(self) -> list[str]:
        """Return a list of validation error strings, empty if valid."""
        errors: list[str] = []
        
        # Dependency validations
        if self.use_3d and not self.use_2d:
            errors.append("use_3d requires use_2d to also be enabled.")
        if self.use_llm and not self.use_slm:
            errors.append("use_llm requires use_slm to also be enabled.")
        if self.use_voice and not (self.use_slm or self.use_fast_brain):
            errors.append("use_voice requires at least use_slm or use_fast_brain.")
        
        # Always-on validations
        if not self.use_fast_brain:
            errors.append("use_fast_brain cannot be disabled.")
        if not self.use_emotion:
            errors.append("use_emotion cannot be disabled.")
        
        return errors


# Module-level singleton — created once, locked by launcher.
FLAGS = CapabilityFlags()