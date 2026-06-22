"""application/health_gateway.py

HTTP gateway used by `r.py --serve/--status`.

This module exists to keep `r.py` as a thin entrypoint.

Endpoints:
- GET  /        : small homepage (useful for HF iframe embedding)
- GET  /health  : JSON health
- GET  /status  : JSON health (same as /health)
- GET  /chat    : chat proxy (GET ?text=... for HF probes; needs LLM_BASE_URL)
- POST /chat    : chat proxy (JSON {"text": "..."}; needs LLM_BASE_URL)

The JSON output is based on the legacy logic that used to live in `r.py`,
with a few compatibility patches applied in `_build_status()`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Tuple
from urllib.parse import parse_qs, urlparse

from application.gateway_chat import complete_chat

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _is_safe_mode() -> bool:
    return os.environ.get("KITSU_SAFE_MODE", "0") in {"1", "true", "True", "TRUE"} or os.environ.get(
        "kitsu_SAFE_MODE", "0"
    ) in {"1", "true", "True", "TRUE"}


_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Kitsu AI — Health Gateway</title>
  <style>
    body { font-family: monospace; background: #0d0d0d; color: #e0e0e0;
           display: flex; flex-direction: column; align-items: center;
           justify-content: center; min-height: 100vh; margin: 0; }
    pre  { color: #7fffb2; font-size: 0.72rem; line-height: 1.2; }
    h2   { color: #ff9f43; margin: 0.5rem 0 0; }
    p    { color: #aaa; font-size: 0.85rem; }
    a    { color: #7fffb2; }
    .badge { background: #1a1a2e; border: 1px solid #7fffb2; border-radius: 6px;
             padding: 0.4rem 1rem; margin-top: 1rem; font-size: 0.8rem; }
  </style>
</head>
<body>
  <pre>
  /\\_/\\
 ( o.o )
  > ^ <   Kitsu AI
  </pre>
  <h2>🦊 Kitsu Desktop AI — Gateway</h2>
  <p>Running in <strong>safe / gateway mode</strong>. Inference handled by external endpoint.</p>
  <div class="badge">
    <a href="/health">/health</a> &nbsp;·&nbsp;
    <a href="/status">/status</a> &nbsp;·&nbsp;
    <a href="/chat">/chat (POST)</a>
  </div>
  <p style="margin-top:1.5rem;font-size:0.75rem;color:#555;">
    Kitsu v{version} &nbsp;|&nbsp; HF Space gateway
  </p>
</body>
</html>
""".strip()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class _LightweightHealthStub:
    """Minimal health reporter for pure gateway / safe-mode deployments."""

    async def start(self) -> None:
        return

    async def stop(self) -> None:
        return

    def get_status(self) -> dict:
        import psutil

        mem = psutil.virtual_memory()
        return {
            "status": "gateway",
            "mode": "safe_gateway",
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory": {
                    "used_gb": round((mem.total - mem.available) / 1e9, 1),
                    "total_gb": round(mem.total / 1e9, 1),
                    "percent": round(mem.percent, 1),
                    "note": "host_or_container_memory",
                },
                "gpu_percent": 0,
            },
            "ai": {
                "tier": "SAFE",
                "vram_used_gb": 0.0,
                "personality": {
                    "emotion": "ready",
                    "mood": "calm",
                    "intensity": 0.5,
                },
                "llm_endpoint": os.environ.get("LLM_BASE_URL", "not_configured"),
            },
            "modules": {
                "running": 0,
                "failed": 0,
                "total": 0,
                "details": {},
                "note": "gateway_mode_no_modules_loaded",
            },
            "timestamp": time.time(),
        }


class HealthHTTPRequestHandler(BaseHTTPRequestHandler):
    handler_name = "application.health_gateway"

    def __init__(self, health_monitor: Any, version: str, *args: Any, **kwargs: Any):
        self.health_monitor = health_monitor
        self._version = version
        super().__init__(*args, **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        logging.getLogger("http.server").debug(fmt, *args)

    def _normalize_path(self, raw_path: str) -> str:
        return raw_path.split("?")[0].rstrip("/") or "/"

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Kitsu-Handler", self.handler_name)
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _build_status(self) -> dict[str, Any]:

        try:
            raw = self.health_monitor.get_status()
        except Exception as e:
            raw = {"error": str(e)}

        # Patch 1: timestamp must be Unix epoch
        raw["timestamp"] = time.time()

        # Patch 2: tier fallback
        ai = raw.get("ai", {})
        if not isinstance(ai, dict):
            ai = {}
        if ai.get("tier") in (None, "", "UNKNOWN"):
            ai["tier"] = "SAFE" if _is_safe_mode() else "OFFLINE"
        raw["ai"] = ai

        # Patch 3: memory context label
        sys_info = raw.get("system", {})
        if isinstance(sys_info, dict):
            mem = sys_info.get("memory", {})
            if isinstance(mem, dict) and mem.get("total_gb", 0) > 30:
                mem["note"] = "host_hypervisor_memory_not_container"
            sys_info["memory"] = mem
        raw["system"] = sys_info

        # Patch 4: safe gateway override
        modules = raw.get("modules", {})
        current_status = raw.get("status", "unknown")
        if (
            current_status == "degraded"
            and _is_safe_mode()
            and isinstance(modules, dict)
            and modules.get("total", 0) == 0
        ):
            raw["status"] = "gateway"
            raw["mode"] = "safe_gateway"

        raw["version"] = self._version
        return raw

    def _extract_chat_text_from_query(self) -> str | None:
        query = parse_qs(urlparse(self.path).query)
        for key in ("text", "message", "prompt"):
            values = query.get(key)
            if values and str(values[0]).strip():
                return str(values[0]).strip()
        return None

    def _read_json_body(self, path: str) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(
                400,
                {"error": "Invalid JSON body", "debug": {"handler": self.handler_name, "route": path}},
            )
            return None
        if not isinstance(payload, dict):
            self._send_json(
                400,
                {"error": "JSON body must be an object", "debug": {"handler": self.handler_name, "route": path}},
            )
            return None
        return payload

    def _extract_chat_text_from_payload(self, payload: dict[str, Any]) -> str | None:
        for key in ("text", "message", "prompt"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _handle_chat(self, text: str | None, *, method: str, path: str) -> None:
        if not text:
            self._send_json(
                400,
                {
                    "error": "Missing chat text",
                    "hint": 'Use POST /chat with {"text": "..."} or GET /chat?text=...',
                    "debug": {"handler": self.handler_name, "route": path, "method": method},
                },
            )
            return

        status_code, payload = complete_chat(text)
        if status_code >= 400:
            payload.setdefault(
                "debug",
                {"handler": self.handler_name, "route": path, "method": method},
            )
        self._send_json(status_code, payload)

    def do_OPTIONS(self) -> None:
        # HF Spaces and some clients may issue CORS preflight requests.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("X-Kitsu-Handler", self.handler_name)
        self.end_headers()

    def do_GET(self) -> None:
        path = self._normalize_path(self.path)

        if path == "/":
            html = _INDEX_HTML.replace("{version}", self._version)
            self._send_html(200, html)
            return

        # HF Space / some clients may probe chat via GET with ?text=...
        if path == "/chat":
            self._handle_chat(self._extract_chat_text_from_query(), method="GET", path=path)
            return

        if path in ("/health", "/status"):
            self._send_json(200, self._build_status())
            return

        self.send_error(404, "Not Found")


    def do_POST(self) -> None:
        path = self._normalize_path(self.path)
        logger.info("POST %s from %s", path, self.client_address)

        if path == "/chat":
            payload = self._read_json_body(path)
            if payload is None:
                return
            text = self._extract_chat_text_from_payload(payload)
            if text is None:
                self._send_json(
                    400,
                    {
                        "error": "JSON body must include 'text', 'message', or 'prompt'",
                        "debug": {"handler": self.handler_name, "route": path, "method": "POST"},
                    },
                )
                return
            self._handle_chat(text, method="POST", path=path)
            return

        self.send_error(404, "Not Found")


def _start_http_service(health: Any, version: str, port: int) -> Tuple[HTTPServer, threading.Thread]:
    def handler_factory(*args: Any, **kwargs: Any):
        return HealthHTTPRequestHandler(health, version, *args, **kwargs)

    server = ThreadingHTTPServer(("0.0.0.0", port), handler_factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


async def run_gateway(args: dict, *, version: str) -> int:
    """Run gateway for `--serve/--status`. Returns process exit code."""

    # Lazy import heavy runtime bits
    try:
        from runtime.infrastructure.container import get_container
        from runtime.communication.bus import MessageBus
        from runtime.infrastructure.clocks import ClockService
        from runtime.legacy.orchestrator import Orchestrator
        from runtime.systems.health import HealthMonitor

        container = get_container()
        container.register_singleton(MessageBus, MessageBus)
        container.register_singleton(ClockService, ClockService)
        container.register_singleton(Orchestrator, Orchestrator)

        event_bus = container.get(MessageBus)
        orchestrator = container.get(Orchestrator)
        clock_service = container.get(ClockService)

        health: Any = HealthMonitor(
            event_bus=event_bus,
            orchestrator=orchestrator,
            clock_service=clock_service,
            container=container,
        )
    except Exception as e:
        logger.warning("Full HealthMonitor unavailable (%s); using lightweight stub", e)
        health = _LightweightHealthStub()

    try:
        await health.start()

        if args.get("status"):
            start_ts = time.perf_counter()


            # Build status with same patching logic as HTTP handler
            handler = HealthHTTPRequestHandler.__new__(HealthHTTPRequestHandler)
            handler.health_monitor = health
            handler._version = version
            status = handler._build_status()

            if args.get("deep"):
                deep: dict[str, Any] = {}



                # Backend probe
                try:
                    from runtime.infrastructure.container import get_container as _gc

                    rc = _gc().get("domain.inference.resource_controller")  # type: ignore
                    deep["backend"] = {
                        "tier": rc.get_current_tier().value.upper() if hasattr(rc, "get_current_tier") else None,
                        "usage": rc.get_resource_usage() if hasattr(rc, "get_resource_usage") else {},
                    }
                except Exception as exc:
                    deep["backend"] = {"error": str(exc)}

                # Storage probe
                try:
                    storage_checks: dict[str, Any] = {}
                    for sub in ["models", "runtime", "logs", "memory", "profiles", "config"]:
                        p = (PROJECT_ROOT / "data") / sub
                        storage_checks[sub] = {"exists": p.exists(), "is_dir": p.is_dir()}
                        if p.exists() and p.is_dir():
                            storage_checks[sub]["readable"] = os.access(p, os.R_OK)
                    deep["storage"] = storage_checks
                except Exception as exc:
                    deep["storage"] = {"error": str(exc)}

                status["deep"] = deep

            # Output
            from rich.console import Console

            console = Console()
            if args.get("json"):
                console.print(json.dumps(status, ensure_ascii=False, indent=2))
                elapsed_ms = (time.perf_counter() - start_ts) * 1000
                console.print(f"Completed --status in {elapsed_ms:.0f}ms")
                return 0

            from rich.table import Table
            from rich.panel import Panel

            table = Table(title="Kitsu System Health")
            table.add_column("Component")
            table.add_column("Status")
            table.add_column("Detail")

            global_status = status.get("status", "UNKNOWN")
            status_color = {
                "healthy": "[green]OK[/green]",
                "gateway": "[cyan]GATEWAY[/cyan]",
                "degraded": "[yellow]DEGRADED[/yellow]",
            }.get(global_status, "[red]CRITICAL[/red]")
            table.add_row("Overall", status_color, str(global_status).upper())

            tier = status.get("ai", {}).get("tier", "UNKNOWN")
            tier_color = "[green]OK[/green]" if tier not in ("UNKNOWN", "OFFLINE") else "[yellow]UNKNOWN[/yellow]"
            table.add_row("AI Tier", tier_color, str(tier))

            cpu = status.get("system", {}).get("cpu_percent")
            table.add_row("CPU", "[yellow]ACTIVE[/yellow]", f"{cpu:.0f}%" if isinstance(cpu, (int, float)) else "N/A")

            if args.get("verbose"):
                sys_info = status.get("system", {})
                mem = sys_info.get("memory", {}) if isinstance(sys_info.get("memory"), dict) else {}
                table.add_row(
                    "Memory",
                    "[cyan]RAM[/cyan]",
                    f"{mem.get('used_gb','?')}/{mem.get('total_gb','?')}GB ({mem.get('percent','?'):.0f}%){' (' + mem.get('note','') + ')' if mem.get('note') else ''}" if mem else "N/A",
                )

                modules = status.get("modules", {})
                if isinstance(modules, dict):
                    table.add_row(
                        "Modules",
                        "[magenta]MODULES[/magenta]",
                        f"{modules.get('running','?')}/{modules.get('total','?')} running, {modules.get('failed','?')} failed",
                    )

                mode = status.get("mode", "")
                if mode:
                    table.add_row("Mode", "[blue]MODE[/blue]", str(mode))

            console.print(Panel(table, title="KITSU STATUS"))
            elapsed_ms = (time.perf_counter() - start_ts) * 1000
            console.print(f"Completed --status in {elapsed_ms:.0f}ms")
            return 0

        if args.get("serve"):
            server, thread = _start_http_service(health, version=version, port=int(args["port"]))
            logger.info("HTTP health server running on port %s", args["port"])
            print(f"Kitsu HTTP health server listening on 0.0.0.0:{args['port']}")

            try:
                await _wait_indefinitely()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=1)

            return 0

        return 0

    finally:
        try:
            await health.stop()
        except Exception:
            pass


async def _wait_indefinitely() -> None:
    stop_event = asyncio.Event()
    await stop_event.wait()

