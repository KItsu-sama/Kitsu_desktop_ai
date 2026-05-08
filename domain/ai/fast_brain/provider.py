"""
ai/fast_brain/provider.py
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Optional, Tuple, Callable, Dict, Any

from domain.contracts.contracts import AIProviderContract
from .markov import markov_chain, add_conversation
from .cache_store import conversation_cache, get_cached_response, check_spam, get_spam_response

logger = logging.getLogger(__name__)


def random_fact() -> str:
    """Return a random fun fact."""
    facts = [
        "Octopuses have three hearts and blue blood!",
        "Honey never spoils - archaeologists have found 3000-year-old honey that's still edible!",
        "A group of flamingos is called a 'flamboyance'!",
        "Bananas are berries, but strawberries aren't!",
        "There are more stars in the universe than grains of sand on all Earth's beaches!",
    ]
    return random.choice(facts)


def surprise_me() -> str:
    """Return a surprise response."""
    surprises = [
        "✨ Did you know I can learn from our conversations?",
        "🌟 Sometimes the best responses are the unexpected ones!",
        "💕 I'm always here to chat and help!",
        "🎭 Want to hear something interesting? Ask me for a random fact!",
        "🌈 Every conversation is unique, just like you!",
    ]
    return random.choice(surprises)


AMBIENT_PATTERNS: Dict[str, str | Callable] = {
    "hello": "Hey! What's up?",
    "hi": "Heyyy~",
    "hey": "Yeah?",
    "what time is it": lambda: f"It's {datetime.now().strftime('%H:%M')}",
    "good morning": "Morning! Did you sleep okay?",
    "good night": "Night night~ don't let the bugs bite",
    "how are you": "Running fine, mostly.",
    "tell me a random fact": random_fact,
    "surprise me": surprise_me,
}


class FastBrainProvider(AIProviderContract):
    """FastBrain AI provider for ultra-fast pattern responses."""

    def __init__(self):
        self._initialized = False
        self.markov_model = markov_chain
        self.cache_store = conversation_cache

    async def initialize(self) -> bool:
        logger.info("FastBrain provider initializing with pattern matching and Markov model")
        self._initialized = True
        return True

    def is_available(self) -> bool:
        """Sync availability check."""
        return self._initialized

    def handle(self, text: str, vibe: list) -> Tuple[str, float] | None:
        """
        Handle input with pattern matching and Markov generation.
        
        Args:
            text: Input text to process
            vibe: List of vibe/context tags (currently unused)
            
        Returns:
            Tuple of (response, confidence) or None if no match
        """
        normalized = text.lower().strip().rstrip("?!.")
        
        # Check cache first for exact matches
        cached_response = get_cached_response(text)
        if cached_response:
            return cached_response, 0.98
        
        # Check for spam/repeated input
        if check_spam(text):
            spam_response = get_spam_response(text)
            return spam_response, 0.90
        
        # Try ambient patterns
        if normalized in AMBIENT_PATTERNS:
            response = AMBIENT_PATTERNS[normalized]
            result = response() if callable(response) else response
            return result, 0.95
        
        # Try Markov model if trained
        if self.markov_model and self.markov_model.has_high_confidence(text):
            markov_response = self.markov_model.generate_response(text)
            if markov_response:
                return markov_response, 0.7
        
        return None  # Miss - escalate to SLM

    def query(self, text: str) -> Optional[str]:
        """Query FastBrain. Returns None if no pattern matches."""
        if not self.is_available():
            return None
        
        result = self.handle(text, [])
        if result:
            response, confidence = result
            # Cache the response for future use
            self.cache_store.add_exchange(text, response, {"confidence": confidence})
            # Train Markov model with this interaction
            add_conversation(text, response)
            return response
        
        return None

    async def infer(self, prompt: str, context=None) -> Optional[str]:
        """Async infer — delegates to sync query."""
        return self.query(prompt)

    def train(self, input_text: str, response_text: str) -> None:
        """Synchronous train method."""
        # Add to cache
        self.cache_store.add_exchange(input_text, response_text, {"training": True})
        # Train Markov model
        add_conversation(input_text, response_text)
        logger.debug("FastBrain training: %s -> %s", input_text, response_text)

    async def train_async(self, input_text: str, response_text: str) -> None:
        """Async train method - delegates to sync version."""
        self.train(input_text, response_text)

    async def shutdown(self) -> None:
        self._initialized = False
        logger.info("FastBrain shutdown")