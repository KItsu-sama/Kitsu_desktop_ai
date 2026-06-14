#!/usr/bin/env python3
"""r.py — Kitsu Desktop AI Entry Point

This file should be a pure entry point.
Responsibilities:
  - sys.path anchor
  - CLI arg parsing
  - configure logging once
  - delegate all runtime phases to application.launcher.ModernLauncher

No first-run logic here; no handler setup here beyond calling configure_logging.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# rich
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import logging

# Fix: Standardize on PROJECT_ROOT as the base anchor for absolute tracking
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Setup unbuffered output and UTF-8 encoding safely
try:
    if hasattr(sys.stdin, "reconfigure"):
        # mypy/pyright may not know about TextIO.reconfigure; safe at runtime.
        sys.stdin.reconfigure(encoding="utf-8", errors="ignore")  # type: ignore[attr-defined]
    else:
        import io

        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="ignore")
except Exception:
    pass


os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

LOGO = r""" 
=============================||=============================
                ░\                        /░
             /░/  ░\                    /░  \░\
           /░/     \░░\              /░░/     \░\
           ░/        \░░\          /░░/        \░
         /░/          \░░\        /░░/          \░\
        /░|            \░░\      /░░/            |░\
        ░░     /====\    ░░\____/░░    /====\     ░░
        ░░    |░░░░░░░ /░░/░░||░░\░░\ ░░░░░░░|    ░░
        ░░   /░░░░░░░░░░░░░_=┘└=_░░░░░░░░░░░░░\   ░░
        \░░  |░░░/░░░░░░░//      \\░░░░░░░░\░░|  ░░/
         \░░/░░░░░░__░░░||        ||░░░__░░░░░░\░░/
          \░░░░░░/1010\_░\\      //░_/0010\░░░░░░/
          /░░\░░░░\0101_\░░¯=┐┌=¯░░/_0010/░░░░/░░\
          ░░_\¯\\_░░░░░░¯\░░░||░░░/¯░░░░░░_//¯/_░░
        /░░/10\   ¯\░░░░░░░░░||░░░░░░░░░/¯   /01\░░\
        ░░░\010\     ¯\░░░░░░||░░░░░░/¯     /010/░░░
       ░░\░░¯001¯\_     \░░░░||░░░░/     _/¯011¯░░/░░
       ░|11\░░░░¯\0=¯ = _ \░░||░░/ _ = ¯=1/¯░░░░/01|░
       \░░0101\░░░░░░░░░░░'░░||░░'░░░░░░░░░░░/0100░░/
        \░░\0010░░░_101\░░░░░||░░░░░/110_░░░1010/░░/
          \_░░░░░_/101/░░░/░░||░░\░░░\010\_░░░░░_/
             ¯\\_░░░░░░░░/|░░||░░|\░░░░░░░__//¯
                 ¯\\_░░░░\ ¯¯  ¯¯ /░░░░░//¯
                      \░░░░░░¯¯░░░░░░░/
                       \░░░░░||░░░░░/ 
                         ¯¯==--==¯¯
=============================||=============================
"""

__version__ = "2.1.3"


def parse_args() -> dict:
    parser = argparse.ArgumentParser(
        prog="kitsu",
        description="Kitsu Desktop AI - Local AI Assistant Runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python r.py --logo                    # Show logo
  python r.py --debug                   # Debug mode
  python r.py --safe                    # Safe mode (laptop friendly)
  python r.py --profile high            # Custom profile
  python r.py --status                  # Health check
  python r.py --version                 # Show version
        """,
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--logo", action="store_true", help="Display Kitsu logo and exit")
    parser.add_argument("--safe", action="store_true", help="Force safe-mode profile")
    parser.add_argument("--profile", type=str, help="Override hardware profile")
    parser.add_argument("--version", action="version", version=f"Kitsu {__version__}")
    parser.add_argument("--status", action="store_true", help="Show health dashboard")

    return vars(parser.parse_args())


async def main() -> int:
    args = parse_args()

    # Early Exit Flags (Prevents accidental side effects like creating files)
    if args["logo"]:
        print(LOGO)
        return 0

    # Configure logging (entrypoint-only responsibility)
    from infrastructure.logging.logger import configure_logging

    configure_logging(debug=bool(args["debug"]))
    logger = logging.getLogger(__name__)

    # Status check (build minimal wiring needed for HealthMonitor)
    if args["status"]:
        try:
            from runtime.infrastructure.container import get_container
            from runtime.communication.bus import MessageBus
            from runtime.infrastructure.clocks import ClockService
            from runtime.legacy.orchestrator import Orchestrator
            from runtime.systems.health import HealthMonitor

            container = get_container()

            # Minimal wiring required to instantiate HealthMonitor
            container.register_singleton(MessageBus, MessageBus)
            container.register_singleton(ClockService, ClockService)
            container.register_singleton(Orchestrator, Orchestrator)

            event_bus = container.get(MessageBus)
            orchestrator = container.get(Orchestrator)
            clock_service = container.get(ClockService)

            health = HealthMonitor(
                event_bus=event_bus,
                orchestrator=orchestrator,
                clock_service=clock_service,
                container=container,
            )

            await health.start()
            status = health.get_status()
            console = Console()

            table = Table(title="Kitsu System Health")

            table.add_column("Component")
            table.add_column("Status")
            table.add_column("Detail")

            table.add_row(
                "AI Tier",
                "[green]OK[/green]",
                status["ai"]["tier"]
            )

            table.add_row(
                "CPU",
                "[yellow]ACTIVE[/yellow]",
                f"{status['system']['cpu_percent']:.0f}%"
            )

            console.print(
                Panel(table, title="KITSU STATUS")
            )
            return 0


        except Exception as e:
            logger.error(f"❌ Health status failed: {e}", exc_info=True)
            return 1


    try:
        from application.launcher import Launcher
    except ImportError as e:
        logger.error(f"❌ Failed to import Launcher from application.launcher: {e}")
        return 1

    try:
        launcher = Launcher(safe_mode=bool(args.get("safe", False)))
        success = await launcher.start()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"❌ Launcher failed: {e}", exc_info=bool(args.get("debug", False)))
        return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

