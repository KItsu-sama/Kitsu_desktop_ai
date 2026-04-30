from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger('kitsu.app.runtime_config')

SYSTEM_CONFIG_PATH = Path('data/config/system_config.json')


@dataclass
class RuntimeConfig:
    defaults: dict[str, Any]
    system_config: dict[str, Any]
    profile_name: str
    profile_path: Path
    profile_definition: Any
    overrides: dict[str, Any]
    safe_mode: bool = False
    debug: bool = False
    merged: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.merged = self._build_merged_config()

    def _build_merged_config(self) -> dict[str, Any]:
        merged = {}
        merged.update(self.defaults.get('runtime', {}))
        merged.update(self.system_config.get('runtime', {}))
        if self.profile_definition and hasattr(self.profile_definition, 'flags'):
            merged['flags'] = self.profile_definition.flags
        merged.update(self.overrides.get('runtime', {}) if isinstance(self.overrides.get('runtime'), dict) else {})
        return merged

    @property
    def first_run_complete(self) -> bool:
        if self.system_config.get('completed_setup') is True:
            return True
        return Path('data/runtime/.first_run_complete').exists()

    @property
    def persistent_model_lock(self) -> str | None:
        if self.system_config.get('model_lock') == 'lock':
            return self.system_config.get('model')
        return None

    @property
    def active_model(self) -> str | None:
        model_override = self.overrides.get('model')
        if isinstance(model_override, dict):
            action = model_override.get('action')
            value = model_override.get('value')
            if action == 'temporary':
                return value
            if action == 'lock':
                return self.system_config.get('model') or value
            if action == 'reset':
                return self.defaults.get('runtime', {}).get('model')
        if self.persistent_model_lock:
            return self.persistent_model_lock
        return self.system_config.get('model') or self.defaults.get('runtime', {}).get('model')

    def copy(self) -> 'RuntimeConfig':
        return RuntimeConfig(
            defaults=self.defaults.copy(),
            system_config=self.system_config.copy(),
            profile_name=self.profile_name,
            profile_path=self.profile_path,
            profile_definition=self.profile_definition,
            overrides=self.overrides.copy(),
            safe_mode=self.safe_mode,
            debug=self.debug,
        )


def load_system_config() -> dict[str, Any]:
    if not SYSTEM_CONFIG_PATH.exists():
        logger.debug('System config file not found: %s', SYSTEM_CONFIG_PATH)
        return {}
    try:
        return json.loads(SYSTEM_CONFIG_PATH.read_text(encoding='utf-8'))
    except Exception as exc:
        logger.warning('Failed to parse system config: %s', exc)
        return {}


def save_system_config(config: dict[str, Any]) -> bool:
    try:
        SYSTEM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SYSTEM_CONFIG_PATH, 'w', encoding='utf-8') as handle:
            json.dump(config, handle, indent=2)
        return True
    except Exception as exc:
        logger.exception('Failed to write system config: %s', exc)
        return False
