"""application.runtime_error_hooks

Installs runtime/code exception hooks to render a Rich red 2-box UI.

The UI is implemented in application.error_ui.render_code_flaw_ui.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from typing import Any

from .error_ui import render_code_flaw_ui

logger = logging.getLogger("runtime_error_hooks")


def _render_exception(exc: BaseException) -> None:
    try:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        render_code_flaw_ui(error=exc, tb=tb)
    except Exception:
        logger.exception("Failed to render code flaw UI")


def install_runtime_error_hooks() -> None:
    """Install sys.excepthook + asyncio exception handler."""

    def _sync_excepthook(exc_type, exc, tb):
        if isinstance(exc, BaseException):
            _render_exception(exc)
        else:
            try:
                _render_exception(RuntimeError(str(exc)))
            except Exception:
                pass

    try:
        sys.excepthook = _sync_excepthook  # type: ignore[assignment]
    except Exception:
        logger.exception("Failed to set sys.excepthook")

    def _async_exception_handler(_loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exc = context.get("exception")
        if isinstance(exc, BaseException):
            _render_exception(exc)
            return

        msg = context.get("message") or "Asyncio exception"
        try:
            _render_exception(RuntimeError(str(msg)))
        except Exception:
            pass

    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(_async_exception_handler)
    except RuntimeError:
        # No running loop yet; handler will be set when one exists.
        pass
    except Exception:
        logger.exception("Failed to set asyncio exception handler")


