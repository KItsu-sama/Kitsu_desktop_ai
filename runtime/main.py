"""
app/main.py - CANONICAL KITU ENTRY POINT

Desktop launcher entry point for Kitsu.
DO NOT run this file directly - use r.py instead:
  python r.py
  python -m app.main



Startup Flow:
1. CLI parsing + logging
2. First-run check/setup  
3. Safe mode detection
4. Bootstrap container
5. kitsuLauncher.startup() → modules + engine
6. Fallback to ultra-low safe mode if needed
7. orchestrator event loop
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional
from argparse import Namespace

# Ensure project root is on sys.path when running directly
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from runtime.kitsu_launcher import kitsuLauncher  # or Launcher from previous merge
from runtime.launcher import main as launcher_main
from scripts.first_run import run_first_run

# Runtime paths
LOG_PATH = Path('data/runtime/crash.log')
FIRST_RUN_FLAG = Path('data/runtime/.first_run_complete')
CRASH_THRESHOLD = 2

logger = logging.getLogger('kitsu.app.main')


def parse_args(argv: Optional[list[str]] = None) -> Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Kitsu desktop AI companion")
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Force a specific hardware profile (ultra_low | balanced | full). "
             "Default: auto-detect.",
    )
    parser.add_argument(
        "--safe", 
        action="store_true", 
        help="Force ultra low safe-mode profile"
    )
    parser.add_argument(
        "--first-run", 
        action="store_true", 
        help="Run first-run setup and exit"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable DEBUG logging"
    )
    return parser.parse_args(argv)


def _setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _mark_first_run_complete() -> bool:
    try:
        FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
        FIRST_RUN_FLAG.write_text(json.dumps({'completed': True}), encoding='utf-8')
        return True
    except Exception:
        logger.exception('Failed to write first-run completion marker')
        return False


def _should_force_safe_mode() -> bool:
    if not LOG_PATH.exists():
        return False
    try:
        lines = [line for line in LOG_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]
        return len(lines) >= CRASH_THRESHOLD
    except Exception:
        logger.debug('Unable to evaluate crash log for safe mode')
        return False


def _maybe_run_first_run() -> bool:
    if FIRST_RUN_FLAG.exists():
        logger.info("First-run already completed")
        return True

    logger.info('Running first-run setup...')
    try:
        success = run_first_run()
        if success:
            return _mark_first_run_complete()
    except Exception as e:
        logger.error("First-run setup failed: %s", str(e))
        return False
    logger.error("First-run setup failed: unknown error")
    return False


def write_crash_log(exception: Exception) -> None:
    """Write crash log entry."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({
                'error': str(exception),
                'type': type(exception).__name__,
                'timestamp': asyncio.get_event_loop().time() if asyncio.get_event_loop() else None,
            }) + '\n')
    except Exception:
        logger.exception('Failed to write crash log')


async def shutdown_container(container: Any) -> None:
    """Graceful shutdown."""
    try:
        await container.orchestrator.shutdown()
    except Exception:
        logger.exception('Error during orchestrator shutdown')


async def start_engine(container: Any) -> int:
    """Core engine startup with safe mode fallback."""
    launcher = kitsuLauncher(container)
    
    try:
        logger.info("Starting Kitsu modules...")
        result = await launcher.startup()
        
        if not result and container.profile.tier != 'micro':  # safe mode check
            logger.warning('Primary startup failed (modules did not start) → falling back to ultra-low safe mode')
            
            # Shutdown current container
            try:
                await shutdown_container(container)
            except Exception:
                logger.exception('Error shutting down before safe mode')
            
            # Rebuild in safe mode
            try:
                logger.info("Rebuilding container in safe mode...")
                container = build_app_container(
                    profile_override=None, 
                    safe_mode=True, 
                    force_rebuild=True
                )
                launcher = kitsuLauncher(container)
                result = await launcher.startup()
            except (BootstrapError, Exception) as exc:
                logger.exception('Safe mode bootstrap failed')
                write_crash_log(exc)
                return 1
        
        if result:
            logger.info("✅ Kitsu startup complete - entering event loop")
            await container.orchestrator.run()
            return 0
        else:
            logger.error("❌ Final startup failure: safe mode startup failed or modules could not initialize")
            return 1
            
    except KeyboardInterrupt:
        logger.info('Shutdown requested by user')
        return 0
    except Exception as exc:
        logger.exception('Fatal engine error')
        write_crash_log(exc)
        return 1
    finally:
        if container:
            await shutdown_container(container)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    overrides = {
        'profile': args.profile,
        'safe': args.safe,
        'debug': args.debug,
        'first_run': args.first_run,
    }
    return asyncio.run(launcher_main(overrides))


if __name__ == "__main__":
    print(""" main must not be run directly""")
    raise SystemExit(main())
