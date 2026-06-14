"""
runtime/legacy/application.py

Minimal legacy `Application` shim to satisfy bootstrap registration.
This provides the basic async `start`/`stop` API used by older codepaths.
"""

from __future__ import annotations
import logging

logger = logging.getLogger("kitsu.runtime.legacy.application")


class Application:
    """Minimal Application shim for legacy compatibility."""

    def __init__(self, *args, **kwargs):
        self.started = False

    async def start(self) -> bool:
        self.started = True
        logger.info("Legacy Application shim started")
        return True

    async def stop(self) -> bool:
        self.started = False
        logger.info("Legacy Application shim stopped")
        return True


__all__ = ["Application"]
