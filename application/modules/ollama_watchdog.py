"""application.modules.ollama_watchdog

Implements an Ollama restart state machine.

Design note (short):
- Goal: if the Ollama HTTP endpoint fails (connection refused, non-200,
  or repeated timeouts), attempt to restart Ollama once per cooldown.
- States:
    IDLE -> MONITORING -> RESTARTING -> COOLDOWN -> IDLE

State machine triggers:
- record_failure(kind) increments a failure counter.
- When failures in a sliding window exceed THRESHOLD => request_restart().

Async implementation:
- Single restart lock ensures only one restart attempt runs.
- restart queue coalesces multiple requests while COOLDOWN is active.
- Uses non-blocking asyncio.sleep for cooldown.

Note: actual restart backend is environment-dependent.
- We support two strategies:
    1) If running inside the Tauri/Desktop integration, a provided command
       hook can be implemented later.
    2) Fallback: try to stop/start via Windows process name (best-effort).
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Deque, Optional
from collections import deque

from .failure_categorizer import categorize_exception

logger = logging.getLogger("ollama.watchdog")


@dataclass
class OllamaWatchdogConfig:
    endpoint: str = "http://localhost:11434/api/generate"
    window_seconds: int = 90
    threshold_failures: int = 3
    cooldown_seconds: int = 180
    restart_attempts_max: int = 2

    # Process names for best-effort restart on Windows
    process_names: tuple[str, ...] = ("ollama.exe",)


class OllamaRestartStateMachine:
    IDLE = "IDLE"
    MONITORING = "MONITORING"
    RESTARTING = "RESTARTING"
    COOLDOWN = "COOLDOWN"

    def __init__(self, cfg: OllamaWatchdogConfig | None = None) -> None:
        self.cfg = cfg or OllamaWatchdogConfig()
        self.state = self.IDLE

        self._failure_times: Deque[float] = deque()
        self._restart_lock = asyncio.Lock()
        self._cooldown_until: float = 0.0

        self._restart_attempts = 0
        self._restart_task: Optional[asyncio.Task] = None

    def _now(self) -> float:
        return time.time()

    def _in_cooldown(self) -> bool:
        return self._now() < self._cooldown_until

    def record_failure(self, exc: BaseException) -> None:
        now = self._now()
        self._failure_times.append(now)

        # Drop old failures
        cutoff = now - self.cfg.window_seconds
        while self._failure_times and self._failure_times[0] < cutoff:
            self._failure_times.popleft()

        logger.warning("ollama watchdog failure recorded: %s", exc)

        if self._in_cooldown():
            logger.info("ollama watchdog in cooldown; ignoring restart request")
            return

        failures = len(self._failure_times)
        logger.info("ollama watchdog failures in window: %d (threshold=%d)", failures, self.cfg.threshold_failures)

        if failures >= self.cfg.threshold_failures:
            self.request_restart(exc)

    def request_restart(self, exc: BaseException) -> None:
        # Coalesce while a restart task exists
        if self._restart_task and not self._restart_task.done():
            logger.info("ollama watchdog restart already scheduled; coalescing")
            return

        loop = asyncio.get_event_loop()
        self._restart_task = loop.create_task(self._run_restart_flow(exc))

    async def _run_restart_flow(self, exc: BaseException) -> None:
        async with self._restart_lock:
            if self._in_cooldown():
                return

            if self._restart_attempts >= self.cfg.restart_attempts_max:
                logger.error("ollama watchdog max restart attempts reached; staying idle")
                self._failure_times.clear()
                self.state = self.IDLE
                return

            self.state = self.RESTARTING
            self._restart_attempts += 1

            category, summary, details = categorize_exception(exc, fallback="MODEL")
            logger.error(
                "Restarting Ollama due to category=%s summary=%s attempts=%d/%d",
                category,
                summary,
                self._restart_attempts,
                self.cfg.restart_attempts_max,
            )
            # details is potentially huge; avoid spamming. Keep in logs at debug.
            logger.debug("ollama restart trigger details:\n%s", details)

            try:
                await self._restart_ollama_best_effort()
            except Exception as e:
                logger.exception("ollama watchdog restart failed: %s", e)

            # enter cooldown no matter what
            self._cooldown_until = self._now() + self.cfg.cooldown_seconds
            self.state = self.COOLDOWN
            self._failure_times.clear()

            # Wait for cooldown to expire
            try:
                await asyncio.sleep(self.cfg.cooldown_seconds)
            except asyncio.CancelledError:
                raise
            finally:
                self.state = self.IDLE
                self._restart_task = None

    async def _restart_ollama_best_effort(self) -> None:
        """Best-effort restart for Windows.

        If you have a better integration (service manager, docker, etc), replace this.
        """
        # Optional: allow external hook via env var
        hook_cmd = os.environ.get("OLLAMA_RESTART_HOOK_CMD")
        if hook_cmd:
            logger.info("Using OLLAMA_RESTART_HOOK_CMD")
            p = subprocess.run(hook_cmd, shell=True, capture_output=True, text=True)
            logger.info("Restart hook exit=%s stdout=%s stderr=%s", p.returncode, p.stdout[-200:], p.stderr[-200:])
            await asyncio.sleep(2.0)
            return

        # Stop processes (best-effort)
        for name in self.cfg.process_names:
            try:
                subprocess.run(f"taskkill /F /IM {name}", shell=True, capture_output=True, text=True)
            except Exception:
                pass

        # Start ollama if installed / in PATH
        # Try common command.
        start_cmds = [
            "start /B ollama serve",
            "ollama serve",
        ]
        started = False
        for cmd in start_cmds:
            try:
                subprocess.Popen(cmd, shell=True)
                started = True
                break
            except Exception:
                continue

        logger.info("ollama restart best-effort started=%s", started)
        await asyncio.sleep(6.0)


watchdog = OllamaRestartStateMachine()

