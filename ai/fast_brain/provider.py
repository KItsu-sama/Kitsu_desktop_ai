"""
ai/fast_brain/provider.py
"""

from __future__ import annotations

import logging
from typing import Optional

from core.contracts import AIProviderContract

logger = logging.getLogger(__name__)


class FastBrainProvider(AIProviderContract):
    """FastBrain AI provider for ultra-fast pattern responses."""

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> bool:
        logger.info("FastBrain provider not yet implemented — stub mode")
        self._initialized = True
        return True

    def is_available(self) -> bool:
        """Sync availability check."""
        return self._initialized

    def query(self, text: str) -> Optional[str]:
        """Query FastBrain. Returns None if no pattern matches."""
        if not self.is_available():
            return None

        text_lower = text.lower().strip()

        if any(g in text_lower for g in ['hello', 'hi', 'hey']):
            return "Hello! I'm Kitsu~"
        if any(q in text_lower for q in ['what', 'how', 'why', 'who']):
            return "Hmm, interesting question..."
        if any(c in text_lower for c in ['help', 'status']):
            return "I'm here and running!"

        return None

    async def infer(self, prompt: str, context=None) -> Optional[str]:
        """Async infer — delegates to sync query."""
        return self.query(prompt)

    def train(self, input_text: str, response_text: str) -> None:
        """Synchronous train method."""
        logger.debug("FastBrain training stub: %s -> %s", input_text, response_text)

    async def train_async(self, input_text: str, response_text: str) -> None:
        """Async train method - delegates to sync version."""
        self.train(input_text, response_text)

    async def shutdown(self) -> None:
        self._initialized = False
        logger.info("FastBrain shutdown")