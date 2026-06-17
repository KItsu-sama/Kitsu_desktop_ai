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
import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn

# rich
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

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
  python r.py --serve                   # Run HTTP health server on port 7860
  python r.py --version                 # Show version
        """,
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--logo", action="store_true", help="Display Kitsu logo and exit")
    parser.add_argument("--safe", action="store_true", help="Force safe-mode profile")
    parser.add_argument("--profile", type=str, help="Override hardware profile")
    parser.add_argument("--status", action="store_true", help="Show health dashboard")
    parser.add_argument(
        "--json",
        action="store_true",
        help="When used with --status, print machine-readable JSON",
    )
    parser.add_argument("--verbose", action="store_true", help="When used with --status, print extra details")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="When used with --status, perform extra backend/storage checks",
    )
    parser.add_argument("--serve", action="store_true", help="Run HTTP health server on port 7860")
    parser.add_argument("--port", type=int, default=7860, help="Port for --serve")
    parser.add_argument("--version", action="version", version=f"Kitsu {__version__}")


    return vars(parser.parse_args())


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class HealthHTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, health_monitor, *args, **kwargs):
        self.health_monitor = health_monitor
        super().__init__(*args, **kwargs)

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/health", "/status"):
            status = self.health_monitor.get_status()
            self._send_json(200, status)
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        if self.path == "/chat":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            if not isinstance(payload, dict) or "text" not in payload:
                self._send_json(400, {"error": "JSON body must include 'text'"})
                return

            self._send_json(501, {"error": "Chat endpoint not implemented in this lightweight service"})
            return

        self.send_error(404, "Not Found")


def _start_http_service(health: object, port: int) -> tuple[HTTPServer, threading.Thread]:
    handler_factory = lambda *args, **kwargs: HealthHTTPRequestHandler(health, *args, **kwargs)
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


async def _wait_indefinitely() -> None:
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass


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

    if args.get("profile"):
        os.environ.setdefault("kitsu_PROFILE", args["profile"])
        os.environ.setdefault("KITSU_PROFILE", args["profile"])
        logger.info("Using profile override from CLI: %s", args["profile"])

    if args.get("safe"):
        os.environ.setdefault("KITSU_SAFE_MODE", "1")
        os.environ.setdefault("kitsu_SAFE_MODE", "1")
        logger.info("Safe mode CLI request enabled")

    # Health server and status modes
    if args["serve"] or args["status"]:
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

            if args["status"]:
                # Status execution timing (for quick CLI feedback)
                import time

                start_ts = time.perf_counter()
                try:
                    status = health.get_status()

                    # Deep checks: extend status with best-effort backend/storage probes
                    if args.get("deep"):
                        deep: dict = {}

                        # Backend: attempt to read resource/tier controller usage more explicitly
                        try:
                            rc = container.get('domain.inference.resource_controller')  # type: ignore[arg-type]
                            usage = rc.get_resource_usage() if hasattr(rc, 'get_resource_usage') else {}
                            deep['backend'] = {
                                'tier': rc.get_current_tier().value.upper() if hasattr(rc, 'get_current_tier') else None,
                                'usage': usage,
                            }
                        except Exception as e:
                            deep.setdefault('backend', {})['error'] = str(e)

                        # Storage: verify key data directories are present + readable
                        try:
                            data_root = PROJECT_ROOT / 'data'
                            storage_checks = {}
                            for sub in ['models', 'runtime', 'logs', 'memory', 'profiles', 'config']:
                                p = data_root / sub
                                storage_checks[sub] = {
                                    'exists': p.exists(),
                                    'is_dir': p.is_dir(),
                                }
                                if p.exists() and p.is_dir():
                                    storage_checks[sub]['readable'] = os.access(p, os.R_OK)
                            deep['storage'] = storage_checks
                        except Exception as e:
                            deep.setdefault('storage', {})['error'] = str(e)

                        status['deep'] = deep

                    console = Console()

                    if args.get("json"):
                        # Ensure timestamp is JSON serializable (may already be float)
                        console.print(json.dumps(status, ensure_ascii=False, indent=2))
                        elapsed_ms = (time.perf_counter() - start_ts) * 1000
                        console.print(f"⏱️ Completed --status in {elapsed_ms:.0f}ms")
                        await health.stop()
                        return 0

                    table = Table(title="Kitsu System Health")
                    table.add_column("Component")
                    table.add_column("Status")
                    table.add_column("Detail")

                    # Overall health summary (if present)
                    global_status = status.get('status', 'UNKNOWN')
                    table.add_row(
                        "Overall",
                        "[green]OK[/green]" if global_status == 'healthy' else "[yellow]DEGRADED[/yellow]" if global_status == 'degraded' else "[red]CRITICAL[/red]",
                        str(global_status).upper(),
                    )

                    table.add_row(
                        "AI Tier",
                        "[green]OK[/green]" if status.get('ai', {}).get('tier') not in (None, '', 'UNKNOWN') else "[yellow]UNKNOWN[/yellow]",
                        str(status.get("ai", {}).get("tier"))
                    )
                    table.add_row(
                        "CPU",
                        "[yellow]ACTIVE[/yellow]",
                        f"{status['system']['cpu_percent']:.0f}%" if 'system' in status and 'cpu_percent' in status['system'] else "N/A"
                    )

                    if args.get("verbose"):
                        sys_info = status.get('system', {})
                        mem = sys_info.get('memory', {}) if isinstance(sys_info.get('memory'), dict) else {}
                        table.add_row(
                            "Memory",
                            "[cyan]RAM[/cyan]",
                            f"{mem.get('used_gb','?')}/{mem.get('total_gb','?')}GB ({mem.get('percent','?'):.0f}%)" if mem else "N/A"
                        )
                        table.add_row(
                            "GPU",
                            "[cyan]GPU[/cyan]",
                            f"{sys_info.get('gpu_percent',0):.0f}%" if isinstance(sys_info.get('gpu_percent'), (int,float)) else "N/A"
                        )
                        modules = status.get('modules', {})
                        if isinstance(modules, dict):
                            table.add_row(
                                "Modules",
                                "[magenta]MODULES[/magenta]",
                                f"{modules.get('running','?')}/{modules.get('total','?')} running, {modules.get('failed','?')} failed"
                            )

                        # Show failing module details (best effort)
                        details = modules.get('details', {}) if isinstance(modules, dict) else {}
                        if isinstance(details, dict):
                            failed_details = [
                                (mid, d.get('detail'))
                                for mid, d in details.items()
                                if not d.get('ok', True)
                            ]
                            if failed_details:
                                sample = failed_details[:5]
                                table.add_row(
                                    "Failures",
                                    "[red]#{len(failed_details)}[/red]",
                                    "; ".join([f"{mid}: {det}" for mid, det in sample])
                                )

                    console.print(Panel(table, title="KITSU STATUS"))

                    elapsed_ms = (time.perf_counter() - start_ts) * 1000
                    console.print(f"⏱️ Completed --status in {elapsed_ms:.0f}ms")
                    await health.stop()
                    return 0

                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start_ts) * 1000
                    logger.error(f"❌ Status failed: {e}", exc_info=True)
                    Console().print(f"❌ Status failed after {elapsed_ms:.0f}ms: {e}")
                    try:
                        await health.stop()
                    except Exception:
                        pass
                    return 1


            server, thread = _start_http_service(health, port=args["port"])
            logger.info("HTTP health server running on port %s", args["port"])
            print(f"🚀 Kitsu HTTP health server listening on 0.0.0.0:{args['port']}")

            try:
                await _wait_indefinitely()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=1)
                await health.stop()

            return 0

        except Exception as e:
            logger.error(f"❌ Health server failed: {e}", exc_info=True)
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

