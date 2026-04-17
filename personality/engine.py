from __future__ import annotations

import logging
import random
from typing import Any

from personality.emotion_engine import EmotionEngine

logger = logging.getLogger('kitsu.personality.engine')


class PersonalityEngine:
    """Inject personality style into generated responses."""

    def __init__(self, emotion_engine: EmotionEngine, persona_name: str = 'Kitsu') -> None:
        self.emotion_engine = emotion_engine
        self.persona_name = persona_name

    def decorate_response(self, response_text: str, source: str = 'fast_brain') -> str:
        """Apply mood/style-based personality cues to a response string."""
        if not response_text:
            return response_text

        mood = getattr(self.emotion_engine, 'mood', 'behave')
        style = getattr(self.emotion_engine, 'style', 'chaotic')

        prefix = self._select_prefix(mood, style)
        suffix = self._select_suffix(mood, style)
        tone = self._select_tone_modifier(mood, style)

        decorated = response_text.strip()
        if prefix:
            decorated = f"{prefix} {decorated}"
        if suffix:
            decorated = f"{decorated} {suffix}"
        if tone and random.random() < 0.5:
            decorated = f"{decorated} {tone}"

        return decorated.strip()

    def _select_prefix(self, mood: str, style: str) -> str:
        if mood == 'flirty' or style == 'sweet':
            return random.choice(['Hehe,', 'Aww,', 'Sure thing,'])
        if mood == 'mean' or style == 'cold':
            return random.choice(['Fine,', 'Listen,', 'Whatever,'])
        if mood == 'behave':
            return random.choice(['Okay,', 'Right away,', 'Sure,'])
        return ''

    def _select_suffix(self, mood: str, style: str) -> str:
        if mood == 'flirty':
            return random.choice(['💖', '😉', '😏'])
        if style == 'chaotic':
            return random.choice(['... not that you care.', '😼', ''])
        if style == 'direct':
            return random.choice(['.', '!'])
        return ''

    def _select_tone_modifier(self, mood: str, style: str) -> str:
        if mood == 'happy':
            return random.choice(['😊', '✨'])
        if mood == 'angry':
            return random.choice(['😠', '...'])
        if mood == 'curious':
            return random.choice(['🤔', ''])
        if style == 'sarcastic':
            return random.choice(['right...', 'sure.'])
        return ''

    def get_personality_hint(self) -> dict[str, Any]:
        return {
            'persona_name': self.persona_name,
            'mood': getattr(self.emotion_engine, 'mood', 'behave'),
            'style': getattr(self.emotion_engine, 'style', 'chaotic'),
        }
