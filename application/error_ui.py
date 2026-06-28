"""application.error_ui

Renders runtime/code errors as a Rich UI in application.terminal_ui style.

This is separated to keep terminal_ui focused, while allowing a single
import point from exception handlers.
"""

from __future__ import annotations

import traceback
from typing import Optional

from .terminal_ui import _RICH_AVAILABLE, terminal_print, terminal_print_panel


def render_code_flaw_ui(
    *,
    error_title: str = "I think there is a flaw with my code",
    runtime_log_title: str = "Recent runtime error log",
    error: BaseException,
    tb: Optional[str] = None,
) -> None:
    """Show the required 2-box red UI."""

    if tb is None:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    # Box 1: flaw code part
    err_line = f"{type(error).__name__}: {error}".strip()

    file_line = ""
    code_line = ""

    # Extract the first traceback location and the following source excerpt line.
    # This should look like:
    #   File "path", line 123, in func
    #     <source code line>
    if tb:
        tb_lines = tb.strip().splitlines()
        for i, line in enumerate(tb_lines):
            if line.lstrip().startswith("File ") and ", line " in line:
                file_line = line.strip()
                if i + 1 < len(tb_lines):
                    code_line = tb_lines[i + 1].rstrip()
                break

    msg1_parts = [error_title, "", err_line]
    if file_line:
        msg1_parts.extend(["", file_line])
    if code_line:
        msg1_parts.extend(["", code_line])

    msg1 = "\n".join(msg1_parts)

    # Box 2: recent runtime error log
    msg2 = tb.strip() if tb else str(error)

    if _RICH_AVAILABLE:
        terminal_print_panel(title=error_title, body=msg1, border_style="red")
        terminal_print_panel(title=runtime_log_title, body=msg2, border_style="red")
    else:
        terminal_print_panel(title=error_title, body=msg1, border_style="red")
        terminal_print_panel(title=runtime_log_title, body=msg2, border_style="red")

