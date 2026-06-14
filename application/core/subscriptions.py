"""
application/core/subscriptions.py -

Utilities for registering EventBus subscriptions safely.

Many modules register handlers at import time. Since EventBus.subscribe is
an async coroutine, we must schedule it instead of calling it directly.

This module provides a small helper that does that without requiring each
caller to manage event loop details.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from .event_bus import bus

logger = logging.getLogger(__name__)


def register(event: str, handler: Callable, priority: int = 0) -> None:
    """Register an EventBus handler.

    Safe at import time: schedules the async `bus.subscribe(...)` coroutine.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(bus.subscribe(event, handler, priority=priority))
        return
    except RuntimeError:
        # No running loop yet (import-time).
        # Defer actual registration until the bus is running.
        try:
            pending = getattr(bus, "pending_subscriptions", None)
            if pending is None:
                setattr(bus, "pending_subscriptions", [])
                pending = getattr(bus, "pending_subscriptions")

            pending.append((event, handler, priority))

        except Exception:
            logger.exception("Failed to defer subscription for %s -> %r", event, handler)


