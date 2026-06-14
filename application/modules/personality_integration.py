"""application/modules/personality_integration.py

Bridges the refactored emotion engine and short-term memory store to the
LLM pipeline for consistent character state, prompt enrichment, and
recommendation-aware streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from domain.personality.emotion_engine import EmotionEngine
from domain.memory.stores.short_term import ShortTermMemoryStore

logger = logging.getLogger(__name__)

STATE_PATH = Path("data/memory/character_state.json")
MEMORY_PATH = Path("data/memory/short_term_memory.json")


class PersonalityContext:
    """Bridges emotion/memory systems with LLM prompt generation."""

    def __init__(self) -> None:
        self.emotion = EmotionEngine.get_singleton()
        self.memory = ShortTermMemoryStore(
            max_items=200,
            persistence_path=MEMORY_PATH,
        )
        self.conversation_turns: List[Dict[str, Any]] = []
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize memory and restore persisted character state."""
        async with self._init_lock:
            if self._initialized:
                return
            try:
                await self.memory.initialize()
            except Exception as exc:
                logger.warning("Personality memory initialization failed: %s", exc)
            self.load_state()
            self._initialized = True

    async def build_prompt_context(self, user_input: str) -> Tuple[str, List[float]]:
        """Return an augmented prompt and the current vibe vector."""
        emotional_state = self.emotion.get_emotional_state()
        vibe = emotional_state.get("vibe", [0.5] * 10)

        recent_items = []
        try:
            recent_items = await self.memory.search("", top_k=5)
        except Exception:
            logger.exception("Could not fetch recent memory for prompt context")

        history = self._format_recent_history(recent_items)

        prompt = (
            "[Character: Kitsu - energetic, curious, slightly mischievous AI assistant]\n"
            f"[Current Mood: {self._mood_to_text(emotional_state.get('mood', 'behave'))}]\n"
            f"[Recent context: {history}]\n"
            f"User: {user_input}\n"
            "Kitsu: "
        )

        return prompt, vibe

    def _format_recent_history(self, items: list[Dict[str, Any]], max_items: int = 5) -> str:
        """Build a compact recent context summary for prompt enrichment."""
        if not items:
            return "none"

        formatted = []
        for item in items[-max_items:]:
            user = item.get("user", "")
            assistant = item.get("assistant", item.get("response", ""))
            if user or assistant:
                formatted.append(f"User: {user}; Kitsu: {assistant}")
        return " | ".join(formatted) if formatted else "none"

    async def update_after_response(self, response: str, user_input: str) -> None:
        """Update emotion and memory after a completed response."""
        self.conversation_turns.append({
            "user": user_input,
            "assistant": response,
            "timestamp": time.time(),
        })

        try:
            self.emotion.process_interaction_context(user_input, response)
        except Exception:
            logger.exception("Failed to process interaction context")

        try:
            key = f"{int(time.time() * 1000)}"
            await self.memory.write(
                key,
                {
                    "user": user_input,
                    "assistant": response,
                    "vibe": self.emotion.get_emotional_state().get("vibe", [0.5] * 10),
                    "timestamp": time.time(),
                },
            )
        except Exception:
            logger.exception("Failed to write personality memory entry")

        try:
            self.save_state()
        except Exception:
            logger.exception("Failed to save character state")

    def save_state(self) -> None:
        """Persist character state to disk between sessions."""
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            state = self.emotion.get_emotional_state()
            vibe = state.get("vibe", [0.5] * 10)
            with STATE_PATH.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "current_mood": state.get("mood", "behave"),
                        "energy_level": state.get("energy_level", 0.7),
                        "valence": float(vibe[1]) if len(vibe) > 1 else 0.5,
                        "arousal": float(vibe[2]) if len(vibe) > 2 else 0.5,
                        "conversation_count": len(self.conversation_turns),
                        "last_interaction": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "learned_preferences": {
                            "likes_topic": [
                                k
                                for k, v in self.emotion.personality_traits.items()
                                if v >= 0.6
                            ],
                            "humor_style": "puns_and_wordplay",
                        },
                    },
                    f,
                    indent=2,
                )
        except Exception as exc:
            logger.exception("Could not save character state: %s", exc)

    def load_state(self) -> None:
        """Load persisted character state if available."""
        if not STATE_PATH.exists():
            return

        try:
            with STATE_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)

            mood = data.get("current_mood")
            if mood:
                self.emotion.mood = mood

            energy_level = data.get("energy_level")
            if energy_level is not None:
                self.emotion.energy_level = float(energy_level)

            valence = data.get("valence")
            if valence is not None:
                self.emotion.trust_level = float(valence)

            arousal = data.get("arousal")
            if arousal is not None:
                self.emotion.personality_traits["playfulness"] = float(arousal)

        except Exception as exc:
            logger.exception("Could not load character state: %s", exc)

    def _mood_to_text(self, mood: str) -> str:
        return mood.capitalize() if mood else "neutral"


personality = PersonalityContext()
