from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from core.contracts import SystemGateway, SystemAdapterContract

logger = logging.getLogger('kitsu.system.gateway')
PERMISSIONS_PATH = Path('data/config/permissions.json')
DEFAULT_PERMISSIONS = {
    'browser_hooks': False,
    'system_control': False,
    'file_access': False,
    'safe_mode': True,
    'can_train': False,
    'can_modify_memory': True,
    'allow_file_scan': False,
    'allow_system_power': False,
    'allow_browser_inject': False,
    'require_confirmation_for_destructive': True,
}

ACTION_SCOPE_MAP: dict[str, str] = {
    'shutdown': 'allow_system_power',
    'restart': 'allow_system_power',
    'sleep': 'allow_system_power',
    'open_file': 'file_access',
    'scan_files': 'allow_file_scan',
    'browser_inject': 'allow_browser_inject',
    'train': 'can_train',
    'modify_memory': 'can_modify_memory',
    'system_control': 'system_control',
}


class PermissionedSystemGateway(SystemGateway):
    """System gateway that enforces permission settings from disk."""

    def __init__(self, permissions_path: Path = PERMISSIONS_PATH) -> None:
        self.permissions_path = permissions_path
        self.permissions = self._load_permissions()

    def _load_permissions(self) -> Dict[str, Any]:
        if not self.permissions_path.exists():
            logger.warning('Permissions config missing: %s', self.permissions_path)
            return DEFAULT_PERMISSIONS.copy()

        try:
            return json.loads(self.permissions_path.read_text(encoding='utf-8'))
        except Exception as exc:
            logger.warning('Failed to load permissions config: %s', exc)
            return DEFAULT_PERMISSIONS.copy()

    def reload_permissions(self) -> None:
        self.permissions = self._load_permissions()

    def is_permitted(self, action: str) -> bool:
        scope = ACTION_SCOPE_MAP.get(action, 'system_control')
        return bool(self.permissions.get(scope, False))

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_permitted(action):
            return self._response(False, None, f'Action not permitted: {action}')

        if action in ('shutdown', 'restart', 'sleep'):
            return self._response(True, {'action': action}, None)
        if action == 'open_file':
            return self._response(True, {'path': params.get('path')}, None)
        if action == 'scan_files':
            return self._response(True, {'scanned': min(params.get('max_files', 0), 100)}, None)
        if action == 'browser_inject':
            return self._response(True, {'target': params.get('target')}, None)
        if action == 'train':
            return self._response(True, {'queued': True}, None)
        if action == 'modify_memory':
            return self._response(True, {'updated': True}, None)

        return self._response(False, None, f'Unsupported action: {action}')

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(action, payload)

    def _response(self, success: bool, result: Any = None, error: str | None = None) -> Dict[str, Any]:
        return {
            'success': success,
            'result': result,
            'error': error,
        }
