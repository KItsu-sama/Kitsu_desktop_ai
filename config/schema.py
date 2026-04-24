from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Type, TypeVar

logger = logging.getLogger('kitsu.config.schema')
T = TypeVar('T')


class ConfigValidationError(ValueError):
    """Base exception for all config validation errors."""
    pass


class SchemaError(ConfigValidationError):
    """Raised when config fails schema validation."""


# Required top-level keys in defaults.yaml
_REQUIRED_TOP_LEVEL = {
    "flags", "profile", "idle", "fast_brain", "router", "logging", "paths"
}

# All known flag names — must match CapabilityFlags fields exactly
_KNOWN_FLAGS = {
    "use_fast_brain",
    "use_emotion",
    "use_2d",
    "use_3d",
    "use_slm",
    "use_llm",
    "use_voice",
    "use_shimeji",
    "use_system_control",
}

# Flags that must always be True
_IMMUTABLE_TRUE = {"use_fast_brain", "use_emotion"}


@dataclass
class ProfileConfig:
    name: str
    tier: str
    description: str
    flags: Dict[str, Any]
    startup_modules: Dict[str, list[str]]
    ui_mode: str
    model_downloads: list[Dict[str, Any]]


@dataclass
class CharacterConfig:
    name: str
    identity: Dict[str, Any]
    voice: Dict[str, Any]


def _load_yaml(path: Path) -> Any:
    """Load YAML file with error handling."""
    try:
        import yaml
    except ImportError as exc:
        raise ImportError('PyYAML is required to load YAML config files') from exc
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise ConfigValidationError(f'Failed to parse YAML at {path}: {exc}') from exc


def load_and_validate(path: Path, schema_type: Type[T]) -> T:
    """Load YAML and validate against specified schema type."""
    document = _load_yaml(path)
    if schema_type is dict:
        return document
    if schema_type is ProfileConfig:
        return _validate_profile_config(document)
    if schema_type is CharacterConfig:
        return _validate_character_config(document)
    raise TypeError(f'Unsupported schema type: {schema_type}')


def validate_defaults(data: dict[str, Any]) -> None:
    """
    Validate the full defaults.yaml structure. Raises SchemaError on failure.
    Called by app/launcher.py at startup before flags are set.
    """
    missing = _REQUIRED_TOP_LEVEL - set(data.keys())
    if missing:
        raise SchemaError(f"defaults.yaml missing required keys: {sorted(missing)}")

    _validate_flags_block(data["flags"], source="defaults.yaml")

    idle = data.get("idle", {})
    _require_keys(idle, {"idle_threshold_seconds", "sleep_threshold_seconds"}, "idle")

    fb = data.get("fast_brain", {})
    _require_keys(
        fb,
        {"spam_window_seconds", "spam_threshold_count", "confidence_promote_threshold"},
        "fast_brain",
    )

    router = data.get("router", {})
    _require_keys(router, {"confidence_slm_threshold", "confidence_llm_threshold"}, "router")


def validate_profile(data: dict[str, Any], profile_name: str) -> None:
    """Validate a profile override YAML. Only 'flags' and 'idle' keys are allowed."""
    allowed = {"flags", "idle"}
    unknown = set(data.keys()) - allowed
    if unknown:
        raise SchemaError(
            f"Profile '{profile_name}' contains unexpected keys: {sorted(unknown)}. "
            f"Profiles may only override: {sorted(allowed)}"
        )

    if "flags" in data:
        _validate_flags_block(data["flags"], source=f"profile '{profile_name}'")


def _validate_profile_config(document: Any) -> ProfileConfig:
    """Validate and parse profile YAML into ProfileConfig dataclass."""
    if not isinstance(document, dict):
        raise ConfigValidationError('Profile YAML must be a mapping')
    
    unknown = set(document.keys()) - {
        'name', 'tier', 'description', 'flags', 'startup_modules', 'ui_mode', 'model_downloads'
    }
    if unknown:
        logger.warning('Unknown profile fields in %s: %s', document.get('name', 'unknown'), unknown)
    
    # Validate flags block if present
    if 'flags' in document:
        _validate_flags_block(document['flags'], source=f"profile '{document.get('name', 'unknown')}'")
    
    return ProfileConfig(
        name=str(document.get('name', 'unknown')),
        tier=str(document.get('tier', 'unknown')),
        description=str(document.get('description', '')),
        flags=dict(document.get('flags', {})),
        startup_modules=dict(document.get('startup_modules', {})),
        ui_mode=str(document.get('ui_mode', 'text_only')),
        model_downloads=list(document.get('model_downloads', [])),
    )


def _validate_character_config(document: Any) -> CharacterConfig:
    """Validate and parse character YAML into CharacterConfig dataclass."""
    if not isinstance(document, dict):
        raise ConfigValidationError('Character YAML must be a mapping')
    
    unknown = set(document.keys()) - {'name', 'identity', 'voice'}
    if unknown:
        logger.warning('Unknown character fields: %s', unknown)
    
    return CharacterConfig(
        name=str(document.get('name', 'unknown')),
        identity=dict(document.get('identity', {})),
        voice=dict(document.get('voice', {})),
    )


def _validate_flags_block(flags: dict[str, Any], source: str) -> None:
    """Validate flags dictionary against known flags and immutables."""
    unknown = set(flags.keys()) - _KNOWN_FLAGS
    if unknown:
        raise SchemaError(f"{source} contains unknown flags: {sorted(unknown)}")

    for flag in _IMMUTABLE_TRUE:
        if flag in flags and flags[flag] is not True:
            raise SchemaError(
                f"{source} sets {flag}=False — this flag cannot be disabled."
            )

    for name, value in flags.items():
        if not isinstance(value, bool):
            raise SchemaError(
                f"{source}: flag '{name}' must be a boolean, got {type(value).__name__}"
            )


def _require_keys(block: dict[str, Any], keys: set[str], block_name: str) -> None:
    """Ensure all required keys exist in a config block."""
    missing = keys - set(block.keys())
    if missing:
        raise SchemaError(f"Config block '{block_name}' missing keys: {sorted(missing)}")


# Convenience functions
def load_profile_config(path: Path) -> ProfileConfig:
    """Load and validate profile config."""
    return load_and_validate(path, ProfileConfig)


def load_character_config(path: Path) -> CharacterConfig:
    """Load and validate character config."""
    return load_and_validate(path, CharacterConfig)


def load_defaults(path: Path) -> dict[str, Any]:
    """Load and validate defaults.yaml."""
    data = load_and_validate(path, dict)
    validate_defaults(data)
    return data