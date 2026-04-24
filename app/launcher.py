"""
app/launcher.py - SOLE ENTRY POINT FOR KITSU

NEVER run main.py directly. launcher.py handles ALL startup phases.

CRITICAL STARTUP (1-7 → clean exit):
1. Logging + CLI args
2. First-run check/setup  
3. Config schema validation
4. Load defaults.yaml
5. Profile overlay
6. Hardware detection
7. Capability flags → LOCK

BOOTSTRAP (8-9 → degraded mode):
8. Build RuntimeConfig  
9. bootstrap.py → app container

ORCHESTRATION (10-12 → graceful shutdown):
10. Launcher.startup() → modules
11. KitsuEngine startup  
12. orchestrator.run()
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from app.bootstrap import BootstrapError, build_app_container
from app.profiles import (
    HardwareProfile, 
    detect_hardware_profile, 
    get_profile_path, 
    select_profile
)
from app.runtime_config import RuntimeConfig, load_system_config, save_system_config
from utils.file_security import safe_file_read, safe_file_write

PROJECT_ROOT = Path(__file__).parent.parent
LOG_PATH = Path('data/runtime/crash.log')
FIRST_RUN_FLAG = Path('data/runtime/.first_run_complete')
CRASH_THRESHOLD = 2

logger = logging.getLogger('kitsu.app.launcher')


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for profile selection and safe mode."""
    parser = argparse.ArgumentParser(description='Kitsu Phase 0 launcher')
    parser.add_argument('--profile', help='Profile override name or YAML path')
    parser.add_argument('--safe', action='store_true', help='Force ultra low safe-mode profile')
    parser.add_argument('--first-run', action='store_true', help='Run first-run setup and exit')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args(argv)


def _setup_logging(level: int = logging.INFO) -> None:
    """Step 1: Initialize logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _mark_first_run_complete() -> bool:
    """Mark first-run setup as complete."""
    content = json.dumps({'completed': True})
    return safe_file_write(FIRST_RUN_FLAG, content)


def _should_force_safe_mode() -> bool:
    """Check if safe mode should be forced due to crash history."""
    content = safe_file_read(LOG_PATH)
    if content is None:
        return False
    
    try:
        lines = [line for line in content.splitlines() if line.strip()]
        return len(lines) >= CRASH_THRESHOLD
    except Exception:
        logger.debug('Unable to evaluate crash log for safe mode')
        return False


def _maybe_run_first_run() -> bool:
    """Step 2: Handle first-run setup if needed."""
    if FIRST_RUN_FLAG.exists():
        logger.info("First-run already completed.")
        return True

    logger.info('First-run setup required before startup')
    from scripts.first_run import run_first_run
    success = run_first_run()
    if success:
        return _mark_first_run_complete()
    return False


def _load_yaml(path: Path) -> dict:
    """Load YAML file safely."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _fatal(message: str) -> None:
    """Critical startup failure - clean exit."""
    logger.critical("STARTUP FAILED: %s", message)
    sys.exit(1)


def _load_defaults(path: Path) -> dict[str, Any]:
    try:
        from config.schema import load_defaults
        return load_defaults(path)
    except Exception as exc:
        _fatal(f'Failed to load defaults: {exc}')


def _load_system_config() -> dict[str, Any]:
    return load_system_config()


def _persist_locked_model(model_name: str | None) -> None:
    system_config = _load_system_config()
    if model_name:
        system_config['model'] = model_name
        system_config['model_lock'] = 'lock'
        system_config['locked_at'] = datetime.utcnow().isoformat() + 'Z'
    else:
        system_config.pop('model_lock', None)
        system_config.pop('locked_at', None)
        system_config.pop('model', None)
    if not save_system_config(system_config):
        logger.warning('Failed to persist locked model to system config')


def _build_runtime_config(profile_name: str, overrides: dict[str, Any], safe_mode: bool) -> RuntimeConfig:
    defaults = _load_defaults(PROJECT_ROOT / 'config' / 'defaults.yaml')
    system_config = _load_system_config()

    model_override = overrides.get('model')
    if isinstance(model_override, dict):
        action = model_override.get('action')
        if action == 'lock':
            _persist_locked_model(model_override.get('value', ''))
            system_config = _load_system_config()
        elif action == 'reset':
            _persist_locked_model(None)
            system_config = _load_system_config()

    if overrides.get('debug') and not overrides.get('profile'):
        profile_name = 'full'

    profile = select_profile(profile_override=profile_name, safe_mode=safe_mode)

    return RuntimeConfig(
        defaults=defaults,
        system_config=system_config,
        profile_name=profile.name,
        profile_path=profile.profile_path,
        profile_definition=profile.profile_definition,
        overrides=overrides,
        safe_mode=safe_mode,
        debug=bool(overrides.get('debug', False)),
    )


async def main(overrides: Optional[dict[str, Any]] = None) -> int:
    overrides = overrides or {}
    debug = bool(overrides.get('debug', False))
    _setup_logging(logging.DEBUG if debug else logging.INFO)

    if overrides.get('logo'):
        print(overrides.get('logo_text', ''))
        return 0

    if overrides.get('first-run'):
        success = _maybe_run_first_run()
        return 0 if success else 1

    safe_mode = bool(overrides.get('safe', False)) or _should_force_safe_mode()
    if safe_mode:
        logger.warning('Launching in safe mode due to override or system history')

    profile_override = overrides.get('profile')
    profile_name = profile_override or detect_hardware_profile()
    runtime_config = _build_runtime_config(profile_name, overrides, safe_mode)

    if not runtime_config.first_run_complete:
        if not _maybe_run_first_run():
            _fatal('First-run setup failed')

    try:
        container = await build_app_container(
            profile_override=profile_name,
            safe_mode=safe_mode,
            runtime_config=runtime_config,
        )
    except BootstrapError as exc:
        logger.exception('Bootstrap failed')
        write_crash_log(exc)
        return 1
    except Exception as exc:
        logger.exception('Unexpected bootstrap failure')
        write_crash_log(exc)
        return 1

    from app.main import start_engine
    return await start_engine(container)


def write_crash_log(exception: Exception) -> None:
    """Write crash log entry."""
    content = json.dumps({
        'error': str(exception),
        'type': type(exception).__name__,
        'timestamp': 0.0,
    }) + '\n'
    
    # Append to existing file or create new one
    if not safe_file_write(LOG_PATH, content, append=True):
        logger.warning('Failed to write crash log')


class Launcher:
    def __init__(self, container: Any) -> None:
        self.container = container
        self.event_bus = container.event_bus
        self.orchestrator = container.orchestrator
        self.profile = container.profile

    async def startup(self) -> bool:
        """Step 11: Start modules according to profile."""
        profile_def = self.profile.profile_definition
        required = profile_def.startup_modules.get('required', [])
        optional = profile_def.startup_modules.get('optional', [])
        total_steps = len(required) + len(optional)
        completed = 0

        logger.info("Starting %d modules (%d required, %d optional)", 
                   total_steps, len(required), len(optional))

        # Start required modules
        for module_id in required:
            completed += 1
            self._emit_progress(completed, total_steps, module_id)
            if not await self._start_module(module_id, required=True):
                logger.error('Required module %s failed to start', module_id)
                return await self._enter_safe_mode()

        # Start optional modules
        for module_id in optional:
            completed += 1
            self._emit_progress(completed, total_steps, module_id)
            await self._start_module(module_id, required=False)

        from core.events import EventType, EventPayload
        self.event_bus.publish(
            EventPayload(
                event_type=EventType.APP_READY,
                source='launcher',
                data={}
            )
        )
        logger.info('Startup sequence complete')
        return True

    def _emit_progress(self, completed: int, total: int, current_module: str) -> None:
        from core.events import EventType, EventPayload
        self.event_bus.publish(
            EventPayload(
                event_type=EventType.LOADING_PROGRESS,
                source='launcher',
                data={
                    'completed': completed, 
                    'total': total, 
                    'module': current_module
                }
            )
        )

    async def _start_module(self, module_id: str, required: bool) -> bool:
        module = self.orchestrator.get_module(module_id)
        if module is None:
            if required:
                logger.error('Required module %s not registered', module_id)
                return False
            logger.warning('Optional module %s not registered', module_id)
            return True

        started = await self.orchestrator.start_module(module_id)
        if not started:
            logger.warning('Failed to start module %s', module_id)
            return not required

        try:
            health = await module.health_check()
            if not getattr(health, 'ok', True):
                logger.warning('Health check failed for %s: %s', 
                             module_id, getattr(health, 'detail', None))
                return not required
        except Exception:
            logger.exception('Health check exception for %s', module_id)
            return not required

        logger.debug('Module %s started successfully', module_id)
        return True

    async def _enter_safe_mode(self) -> bool:
        logger.warning('Entering safe mode due to startup failure')
        from core.events import EventType, EventPayload
        self.event_bus.publish(
            EventPayload(
                event_type=EventType.APP_SHUTDOWN,
                source='launcher',
                data={'reason': 'startup_failure'}
            )
        )
        return False


async def shutdown_container(container) -> None:
    """Step 13: Graceful shutdown."""
    try:
        await container.orchestrator.shutdown()
    except Exception:
        logger.exception('Error during orchestrator shutdown')


if __name__ == '__main__':
    sys.exit(main())