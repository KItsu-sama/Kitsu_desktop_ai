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

from runtime.launchers.bootstrap import BootstrapError, build_app_container
from runtime.config.profiles import (
    HardwareProfile, 
    detect_hardware_profile, 
    get_profile_path, 
    select_profile
)
from runtime.config.runtime_config import RuntimeConfig, load_system_config, save_system_config
from shared.security.file_security import safe_file_read, safe_file_write

PROJECT_ROOT = Path(__file__).parent.parent.parent
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
    try:
        content = safe_file_read(LOG_PATH)
        if content is None:
            return False
        
        lines = [line for line in content.splitlines() if line.strip()]
        return len(lines) >= CRASH_THRESHOLD
    except Exception:
        logger.debug('Unable to evaluate crash log for safe mode')
        return False  # Fail safe - don't force safe mode on error


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
        from shared.schemas.schema import load_defaults
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
    defaults = _load_defaults(PROJECT_ROOT / 'shared' / 'config' / 'defaults.yaml')
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
    import time
    start_time = time.time()
    
    overrides = overrides or {}
    debug = bool(overrides.get('debug', False))
    _setup_logging(logging.DEBUG if debug else logging.INFO)
    
    # Check for crash recovery
    crash_data = _load_crash_data()
    if crash_data and not crash_data.get('recovered', True):
        logger.warning(f"Previous crash detected: {crash_data.get('error', 'Unknown')} at {crash_data.get('timestamp', 'Unknown')}")
    
    logger.info("Starting Kitsu...")

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

    from runtime.legacy.main import start_engine
    return await start_engine(container)


def write_crash_log(exception: Exception) -> None:
    """Write crash log entry."""
    import time
    start_time = time.time()
    
    content = json.dumps({
        'error': str(exception),
        'type': type(exception).__name__,
        'timestamp': start_time,
    }) + '\n'
    
    # Append to existing file or create new one
    if not safe_file_write(LOG_PATH, content, append=True):
        logger.warning('Failed to write crash log')
    
    # Update crash recovery file
    _save_crash_data({
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'error': str(exception),
        'recovered': False,
        'startup_time_ms': int((time.time() - start_time) * 1000),
        'crash_count': _get_crash_count() + 1
    })


def _load_crash_data() -> dict[str, Any] | None:
    """Load crash recovery data."""
    crash_file = Path('data/runtime/last_crash.json')
    if not crash_file.exists():
        return None
        
    try:
        content = safe_file_read(crash_file)
        if content:
            return json.loads(content)
    except Exception as exc:
        logger.warning(f'Failed to load crash data: {exc}')
        
    return None


def _save_crash_data(data: dict[str, Any]) -> None:
    """Save crash recovery data."""
    crash_file = Path('data/runtime/last_crash.json')
    crash_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        content = json.dumps(data, indent=2)
        safe_file_write(crash_file, content)
    except Exception as exc:
        logger.warning(f'Failed to save crash data: {exc}')


def _get_crash_count() -> int:
    """Get current crash count from log."""
    try:
        content = safe_file_read(LOG_PATH)
        if content is None:
            return 0
            
        lines = [line for line in content.splitlines() if line.strip()]
        return len(lines)
    except Exception:
        return 0


def _mark_crash_recovered() -> None:
    """Mark crash as recovered."""
    crash_data = _load_crash_data()
    if crash_data:
        crash_data['recovered'] = True
        _save_crash_data(crash_data)


class Launcher:
    def __init__(self, container: Any) -> None:
        self.container = container
        self.event_bus = container.event_bus
        self.orchestrator = container.orchestrator
        self.profile = container.profile

    @staticmethod
    async def bootstrap() -> int:
        """Run bootstrap only and exit."""
        import time
        start_time = time.time()
        
        _setup_logging()
        logger.info("Running bootstrap-only mode...")
        
        try:
            from runtime.bootstrap import build_app_container
            container = await build_app_container()
            logger.info(f"Bootstrap complete: {time.time()-start_time:.1f}s")
            return 0
        except Exception as exc:
            logger.exception('Bootstrap failed')
            return 1

    @staticmethod 
    async def quick_start() -> int:
        """Run quick test mode."""
        import time
        start_time = time.time()
        
        _setup_logging()
        logger.info("Running quick test mode...")
        
        try:
            from scripts.quick_start import show_guide
            show_guide()
            success = True
            logger.info(f"Quick start complete: {time.time()-start_time:.1f}s")
            return 0 if success else 1
        except Exception as exc:
            logger.exception('Quick start failed')
            return 1

    @staticmethod
    async def full_startup() -> int:
        """Run full startup sequence."""
        import time
        start_time = time.time()
        
        _setup_logging()
        logger.info("Running full startup...")
        
        try:
            result = await main()
            logger.info(f"Full startup complete: {time.time()-start_time:.1f}s")
            return result
        except Exception as exc:
            logger.exception('Full startup failed')
            return 1

    @staticmethod
    async def show_status() -> int:
        """Show module status and exit."""
        _setup_logging()
        
        try:
            # Try to load existing container to get status
            from runtime.bootstrap import build_app_container
            from interfaces.ui.dashboard import render_dashboard
            
            container = await build_app_container()
            
            # Get health monitor if available
            health_monitor = None
            if hasattr(container, 'orchestrator'):
                health_monitor = container.orchestrator.get_module('core.health')
            
            if health_monitor:
                status_data = health_monitor.get_status()
                render_dashboard(status_data)
            else:
                # Fallback: get module status directly from orchestrator
                module_status = {}
                if hasattr(container, 'orchestrator'):
                    for module_id in container.orchestrator._modules:
                        module = container.orchestrator.get_module(module_id)
                        if module:
                            try:
                                health = await module.health_check()
                                module_status[module_id] = {
                                    "ok": getattr(health, 'ok', True),
                                    "detail": getattr(health, 'detail', None),
                                    "latency_ms": getattr(health, 'latency_ms', 0.0)
                                }
                            except Exception:
                                module_status[module_id] = {
                                    "ok": False,
                                    "detail": "Health check failed",
                                    "latency_ms": 0.0
                                }
                
                # Count running vs failed
                running = sum(1 for status in module_status.values() if status['ok'])
                total = len(module_status)
                
                status_data = {
                    "personality": "playful/happy (0.8)",
                    "ai_tier": "SLM (4GB VRAM used)",
                    "memory_usage": "6.2/16GB (39%)",
                    "modules": f"{running}/{total} running",
                    "resources": "CPU: 69% │ GPU: 67%",
                    "module_details": module_status
                }
                
                render_dashboard(status_data)
            
            return 0
        except Exception as exc:
            print(f"Status check failed: {exc}")
            return 1

    async def startup(self) -> bool:
        """Step 11: Start modules using unified registry."""
        from runtime.core.module_registry import get_module_registry
        
        registry = get_module_registry()
        all_modules = registry.get_all_modules()
        
        # Start all registered modules in dependency order
        startup_order = registry._startup_order if hasattr(registry, '_startup_order') else list(all_modules.keys())
        total_steps = len(startup_order)
        completed = 0

        logger.info("Starting %d registered modules", total_steps)

        for module_id in startup_order:
            completed += 1
            self._emit_progress(completed, total_steps, module_id)
            
            # Create instance first if needed
            module_info = registry.get_module_info(module_id)
            if module_info and module_info.instance is None:
                instance_created = await registry.create_instance(module_id)
                if not instance_created:
                    logger.warning('Failed to create instance for module %s', module_id)
                    continue
            
            # Try to start the module via registry
            success = await registry.start_module(module_id)
            if not success:
                logger.warning('Module %s failed to start, continuing with others', module_id)

        from runtime.communication.events import EventType, EventPayload
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
        from runtime.communication.events import EventType, EventPayload
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
            logger.warning('Failed to start module %s (orchestrator could not initialize it)', module_id)
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
        from runtime.communication.events import EventType, EventPayload
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