"""
infrastructure/llm/llm_fallback_generator.py

LLM Fallback Generator

Generates personality-consistent responses when the LLM fails.

Core principles:
- Failure is framed as an IDENTITY malfunction
- MAIN identity phrases are preserved:
    - "my AI is not AI-ing"
    - "fox not fox-ing"
- Cause is appended with "cuz"
- Cause NEVER replaces the identity phrase
- Lightweight and deterministic
- No heavy NLP / embeddings / AI logic

Fallback respects:
- mood (intent)
- style (delivery)
- word limits from emotion_config

Only used when LLM fails to generate a response.
"""

import re
import json
import time
import random
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

try:
    from preferences import PreferenceStore
except ImportError:
    class PreferenceStore:
        def get_user_info(self):
            return {}

from domain.personality.emotion_config import get_style_rules

log = logging.getLogger(__name__)


# =========================================================
# Context
# =========================================================

@dataclass
class ConversationContext:
    user_name: Optional[str] = None
    last_interaction: float = field(default_factory=time.time)


# =========================================================
# Main Generator
# =========================================================

class LLMFallback:
    """Personality-consistent lightweight fallback generator"""

    # =========================================================
    # Init
    # =========================================================

    def __init__(
        self,
        memory: Optional[PreferenceStore] = None,
        low_spec_mode: bool = False,
    ):
        self.memory = memory
        self.low_spec_mode = low_spec_mode

        self.context = ConversationContext()

        self.fallback_count = 0
        self.last_fallback_time = 0

        # =====================================================
        # Safe glitch effects
        # Only lightly mutate text readability
        # =====================================================

        self.glitch_effects = [
            lambda t: t.replace("not", "n—not", 1),
            lambda t: t.replace("AI-ing", "A͟I͟-͟i͟n͟g͟", 1),
            lambda t: t.replace("fox-ing", "fo—fox-ing", 1),
            lambda t: "▉ " + t,
            lambda t: t.replace(" ", " … ", 1),
        ]

        # =====================================================
        # Fox noises
        # =====================================================

        self.fox_noises = {
            "behave": [
                " *mrrp*",
                " *chirp*",
                " *sniff*",
            ],
            "flirty": [
                " *nya~*",
                " *purr*",
                " *mrr~*",
            ],
            "mean": [
                " *tch*",
                " *hiss*",
                " *snort*",
            ],
            "protective": [
                " *alert*",
                " *guard*",
                " *watch*",
            ],
        }

    # =========================================================
    # Personal Info
    # =========================================================

    def _get_personal_info(self):
        """Retrieve user personalization data"""

        try:
            if self.memory:
                info = self.memory.get_user_info() or {}

                if isinstance(info, dict):
                    return (
                        info.get("name"),
                        info.get("nickname"),
                        info.get("refer_title"),
                    )

        except Exception:
            log.exception("Failed loading user info")

        try:
            cfg = Path("data/config/user_profile.json")

            if cfg.exists():
                data = json.loads(cfg.read_text(encoding="utf-8"))

                if isinstance(data, dict):
                    return (
                        data.get("name"),
                        data.get("nickname"),
                        data.get("refer_title"),
                    )

        except Exception:
            pass

        return (None, None, None)

    # =========================================================
    # Address Selection
    # =========================================================

    def _choose_personal(
        self,
        mood: str,
        name: Optional[str],
        nickname: Optional[str],
        refer_title: Optional[str],
    ) -> Optional[str]:
        """
        Personality-based address selection.

        Rules:
        - flirty     -> prefers nickname
        - behave     -> prefers refer_title
        - mean       -> prefers name
        - protective -> prefers name

        BUT:
        - 20% chance to ignore preference
        - Kitsu does not always follow rules
        """

        available = [
            x for x in [name, nickname, refer_title]
            if x
        ]

        if not available:
            return None

        preferred = None

        if mood == "flirty":
            preferred = nickname

        elif mood == "behave":
            preferred = refer_title

        elif mood in ("mean", "protective"):
            preferred = name

        # fallback if preferred missing
        if not preferred:
            preferred = random.choice(available)

        # 80% follow preference
        # 20% random creativity
        if random.random() < 0.80:
            return preferred

        return random.choice(available)

    # =========================================================
    # Cause Detection
    # =========================================================

    def _detect_cause_from_input(self, user_input: str) -> str:
        text = user_input.lower()

        if any(x in text for x in ["none", "retune none", "model unavailable", "language model unavailable", "no model", "model not available", "model isn't available", " "]):
            return "model_unavailable"

        if any(x in text for x in ["why", "how", "what", "when"]):
            return "question"

        if len(user_input) > 120:
            return "long_input"

        if any(x in text for x in ["hello", "hi", "hey"]):
            return "greeting"

        if any(x in text for x in ["bye", "goodbye"]):
            return "farewell"

        return "unknown"

    # =========================================================
    # Cause Suffix
    # =========================================================

    def _cause_suffix(
        self,
        cause: Optional[str],
        user_input: str = "",
    ) -> str:

        cause = (cause or "").lower().strip()

        if cause == "unknown" and user_input:
            cause = self._detect_cause_from_input(user_input)

        cause_map = {
            "timeout": [
                " cuz thinking too long",
                " cuz my brain got stuck",
                " cuz processing stalled",
            ],

            "crash": [
                " cuz something snapped inside",
                " cuz my code tripped",
                " cuz my brain exploded",
            ],

            "rate_limit": [
                " cuz too much happened at once",
                " cuz I got overwhelmed",
                " cuz things moved too fast",
            ],

            "question": [
                " cuz that's too deep",
                " cuz my tiny brain hurts",
                " cuz hard question",
            ],

            "long_input": [
                " cuz you wrote so much",
                " cuz that was a lot",
                " cuz my eyes glazed over",
            ],

            "greeting": [
                " cuz you surprised me",
                " cuz I got excited",
            ],

            "farewell": [
                " cuz goodbye is hard",
                " cuz you're leaving",
            ],

            "model_unavailable": [
                " cuz my language model is unavailable right now",
            ],
        }

        default_choices = [
            " cuz something happened",
        ]

        choices = cause_map.get(cause, default_choices)

        return random.choice(choices)

    # =========================================================
    # Core Identity Phrase
    # =========================================================

    def _generate_core_phrase(self, mood: str) -> str:
        """
        KEEP MAIN IDENTITY PHRASES
        """

        cores = {
            "behave": [
                "my AI is not AI-ing",
                "fox not fox-ing",
            ],

            "flirty": [
                "my AI is not AI-ing~",
                "fox not fox-ing~",
            ],

            "mean": [
                "my AI is not AI-ing",
                "fox not fox-ing",
            ],

            "protective": [
                "my AI is not AI-ing",
                "fox not fox-ing",
            ],
        }

        return random.choice(
            cores.get(mood, cores["behave"])
        )

    # =========================================================
    # Cuz -> Cause (mood-aware)
    # =========================================================

    def _maybe_cuz_to_cause(self, text: str, mood: str) -> str:
        """In behave/protective moods, convert ' cuz ' -> ' cause ' with 80% chance."""

        if mood not in ("behave", "protective"):
            return text

        if random.random() >= 0.80:
            return text

        # Marker-only replacement; keep the rest of the suffix unchanged.
        return re.sub(r"\bcuz\b", "cause", text)


    # =========================================================
    # Glitch
    # =========================================================


    def _glitch(
        self,
        text: str,
        intensity: float = 0.20,
    ) -> str:

        """
        Light safe glitching.

        ONLY affects identity area lightly.
        """

        if random.random() > intensity:
            return text

        parts = text.split(" cuz ", 1)

        core = parts[0]

        effect = random.choice(self.glitch_effects)

        core = effect(core)

        if len(parts) > 1:
            return core + " cuz " + parts[1]

        return core

    # =========================================================
    # Fox Flavor
    # =========================================================

    def _fox_noise(self, mood: str) -> str:

        noises = self.fox_noises.get(
            mood,
            self.fox_noises["behave"]
        )

        if random.random() < 0.30:
            return random.choice(noises)

        return ""

    # =========================================================
    # Style Polish
    # =========================================================

    def _style_polish(
        self,
        text: str,
        style: str,
        mood: str,
    ) -> str:

        if style == "direct":
            return text

        if style == "cold":
            return text + random.choice([
                "",
                " obviously.",
                " indeed.",
            ])

        if style == "chaotic":
            if random.random() < 0.35:
                text += random.choice([
                    " wait wait",
                    " rebooting",
                    " kon kon kon",
                ])
            return text

        if style == "sarcastic":
            return text + random.choice([
                " amazing.",
                " fantastic.",
                " what a surprise.",
            ])

        if style == "playful":
            return text + random.choice([
                " hehe",
                " oops~",
                " teehee~",
            ])

        if style == "eerie":
            return random.choice([
                "… ",
                "~… ",
                "◈… ",
            ]) + text

        if style == "sweet":
            return text + random.choice([
                " ♡",
                " ✨",
                " 💫",
            ])

        return text

    # =========================================================
    # Mood Openers
    # =========================================================

    def _get_mood_opener(
        self,
        mood: str,
        style: str,
    ) -> str:

        openers = {
            "behave": [
                "umm ",
                "ah ",
                "well ",
                "hmm ",
            ],

            "flirty": [
                "hehe~ ",
                "ufu~ ",
                "oh no~ ",
            ],

            "mean": [
                "ugh ",
                "seriously? ",
                "tch ",
            ],

            "protective": [
                "careful! ",
                "warning! ",
                "alert! ",
            ],
        }

        choices = openers.get(
            mood,
            openers["behave"]
        )

        if random.random() < 0.85:
            return random.choice(choices)

        return ""

    # =========================================================
    # Japanese Flavor
    # =========================================================

    def _apply_japanese_replacements(
        self,
        text: str,
        mood: str,
    ) -> str:

        replacements = {
            "hello": "Konnichiwa",
            "goodbye": "Sayonara",
        }

        for eng, jap in replacements.items():
            text = re.sub(
                re.escape(eng),
                jap,
                text,
                flags=re.IGNORECASE,
            )

        if random.random() < 0.12 and mood != "mean":
            text += random.choice([
                " ne",
                " yo",
                " wa",
            ])

        return text

    # =========================================================
    # Japanese Input Detection
    # =========================================================

    def _check_japanese_input(
        self,
        user_input: str,
    ) -> Optional[str]:

        # hiragana + katakana only
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', user_input):

            return random.choice([
                "Sumimasen. Nihongo wakarimasen.",
                "Gomen, no Japanese yet!",
                "Ah, still learning Japanese!",
            ])

        return None

    # =========================================================
    # Word Limit
    # =========================================================

    def _enforce_word_limit(
        self,
        text: str,
        style: str,
    ) -> str:

        rules = get_style_rules(style)

        max_words = rules.get("max_words", 40)

        # low-spec:
        # strict predictable limit
        if self.low_spec_mode:
            words = text.split()

            if len(words) > max_words:
                return " ".join(words[:max_words]) + "..."

            return text

        # desktop:
        # softer overflow
        soft_limit = max_words + 10

        words = text.split()

        if len(words) > soft_limit:
            return " ".join(words[:soft_limit]) + "..."

        return text

    # =========================================================
    # Generate
    # =========================================================

    def generate(
        self,
        mood: str = "behave",
        style: str = "sweet",
        cause: Optional[str] = None,
        raw_input: str = "",
    ) -> str:

        self.fallback_count += 1
        self.last_fallback_time = time.time()

        # decay fallback chaos slowly
        if self.fallback_count > 0:
            self.fallback_count = max(
                1,
                self.fallback_count - 0.05,
            )

        # Japanese handling
        jap = self._check_japanese_input(raw_input)

        if jap:
            return jap

        # Personal info
        name, nickname, refer_title = (
            self._get_personal_info()
        )

        target = self._choose_personal(
            mood,
            name,
            nickname,
            refer_title,
        )

        # Cause
        cause_suffix = self._cause_suffix(
            cause,
            raw_input,
        )

        # Opener
        opener = self._get_mood_opener(
            mood,
            style,
        )

        # Identity phrase
        core = self._generate_core_phrase(
            mood,
        )

        # Build
        if target:
            text = f"{opener}{target}, {core}{cause_suffix}"
        else:
            text = f"{opener}{core}{cause_suffix}"

        # Glitch intensity
        glitch_intensity = min(
            0.45,
            self.fallback_count / 10,
        )

        text = self._glitch(
            text,
            glitch_intensity,
        )

        # mood-aware cuz->cause conversion
        text = self._maybe_cuz_to_cause(text, mood)


        # Style

        text = self._style_polish(
            text,
            style,
            mood,
        )

        # Noise
        noise = self._fox_noise(mood)

        if noise:
            text += noise

        # Japanese flavor
        text = self._apply_japanese_replacements(
            text,
            mood,
        )

        # Word limit
        text = self._enforce_word_limit(
            text,
            style,
        )

        return text.strip()

    # =========================================================
    # Random Test
    # =========================================================

    def generate_R(
        self,
        cause: Optional[str] = None,
    ) -> str:

        mood = random.choice([
            "behave",
            "flirty",
            "mean",
            "protective",
        ])

        style = random.choice([
            "sweet",
            "playful",
            "chaotic",
            "cold",
            "direct",
            "sarcastic",
            "eerie",
        ])

        return self.generate(
            mood=mood,
            style=style,
            cause=cause,
        )

    # =========================================================
    # Stats
    # =========================================================

    def get_stats(self) -> Dict[str, Any]:

        return {
            "fallback_count": self.fallback_count,
            "last_fallback_time": self.last_fallback_time,
            "low_spec_mode": self.low_spec_mode,
        }