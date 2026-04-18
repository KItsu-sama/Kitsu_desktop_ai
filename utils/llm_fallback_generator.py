"""
core/llm/llm_fallback.py

LLM Fallback Generator

Generates personality-consistent responses when the LLM fails.

Core principles:
- Failure is framed as an IDENTITY malfunction
- "AI is not AI-ing" or "fox is not fox-ing"
- Cause is appended with "cuz"
- Cause NEVER replaces the identity phrase

Fallback respects:
- mood (intent)
- style (delivery)
- word limits from emotion_config
"""

import json
import logging
import random
from pathlib import Path
from typing import Optional

from memory.stores.preferences import PreferenceStore
from personality.emotion_config import get_style_rules

log = logging.getLogger(__name__)


class LLMFallback:

    # =========================================================
    # Init
    # =========================================================

    def __init__(self, memory: Optional[PreferenceStore] = None):
        self.memory = memory

    # =========================================================
    # User Personalization
    # =========================================================

    def _get_personal_info(self):

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
            log.exception("Failed to fetch user info")

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
            log.exception("Failed reading user profile")

        return None, None, None

    def _choose_personal(self, mood, name, nickname, refer_title):

        if mood == "flirty":
            order = [nickname, refer_title, name]

        elif mood == "mean":
            order = [name, refer_title, nickname]

        elif mood == "behave":
            order = [refer_title, name, nickname]

        else:
            order = [name, nickname, refer_title]

        choices = [c for c in order if c]

        if choices and random.random() < 0.75:
            return random.choice(choices)

        return None

    # =========================================================
    # Cause Suffix
    # =========================================================

    def _cause_suffix(self, cause: Optional[str]):

        cause = (cause or "").lower().strip()

        if cause == "timeout":
            return random.choice([
                " cuz of thinking too long",
                " cuz of thinking too hard",
                " cuz I got stuck thinking",
            ])

        if cause == "crash":
            return random.choice([
                " cuz something snapped inside",
                " cuz my code tripped",
                " cuz I fell over internally",
            ])

        if cause in ("rate_limit", "overload"):
            return random.choice([
                " cuz too much happened at once",
                " cuz I got overwhelmed",
                " cuz things moved too fast",
            ])

        return ""

    # =========================================================
    # Identity Failure Phrase
    # =========================================================

    def _generate_core_phrase(self):

        cores = [
            "my AI is not AI-ing",
            "your fox is not fox-ing",
            "this fox stopped fox-ing",
            "my brain stopped AI-ing",
        ]

        return random.choice(cores)

    # =========================================================
    # Glitch Effect
    # =========================================================

    def _glitch(self, text: str):

        if random.random() > 0.20:
            return text

        effects = [

            lambda t: t.replace("not", "n—not"),

            lambda t: t.replace("AI-ing", "A͟I͟-͟i͟n͟g͟"),

            lambda t: t.replace("fox-ing", "fo͢x͢-i͢n͢g͢"),

            lambda t: t.replace("fox-ing", "fo—fox-ing"),

            lambda t: t.replace(" ", " … ", 1),

            lambda t: "▉ " + t,

            lambda t: "".join(
                c + random.choice(["", "͟"])
                if random.random() < 0.05 else c
                for c in t
            ),
        ]

        return random.choice(effects)(text)

    # =========================================================
    # Fox Flavor
    # =========================================================

    def _fox_noise(self):

        noises = [
            " *nyah*",
            " *mrrp*",
            " *fox-chirp*",
            " 🦊",
        ]

        if random.random() < 0.30:
            return random.choice(noises)

        return ""

    def _tail_glitch(self):

        if random.random() < 0.08:
            return " *tail glitch*"

        return ""

    # =========================================================
    # Style Polish
    # =========================================================

    def _style_polish(self, text: str, style: str):

        if style == "direct":

            return random.choice([
                "fox not fox-ing.",
                "AI failure.",
                "system broke.",
            ])

        if style == "cold":

            return text.replace("I think ", "")

        if style == "chaotic":

            if random.random() < 0.35:
                text += random.choice([
                    " kon kon kon",
                    " wait wait wait",
                    " hold on hold on",
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
                " my bad~",
            ])

        if style == "eerie":

            return "… " + text

        return text

    # =========================================================
    # Build Base Phrase
    # =========================================================

    def _generate_base(self, target, mood, cause_suffix):

        extra = "I think " if random.random() < 0.5 else ""

        core = self._generate_core_phrase()

        if target:
            base = f"{target}, {extra}{core}{cause_suffix}"

        else:
            base = f"{extra}{core}{cause_suffix}"

        return base.strip()

    # =========================================================
    # Word Limit Enforcement
    # =========================================================

    def _enforce_word_limit(self, text: str, style: str):

        rules = get_style_rules(style)

        max_words = rules.get("max_words", 20)

        words = text.split()

        return " ".join(words[:max_words])

    # =========================================================
    # Public API
    # =========================================================

    def generate(self, mood: str = "", style: str = "", cause: Optional[str] = None):

        cause = cause or "unknown"

        name, nickname, refer_title = self._get_personal_info()

        target = self._choose_personal(
            mood,
            name,
            nickname,
            refer_title,
        )

        cause_suffix = self._cause_suffix(cause)

        base = self._generate_base(
            target,
            mood,
            cause_suffix,
        )

        base = self._glitch(base)

        base = self._style_polish(base, style)

        noise = self._fox_noise()

        tail = self._tail_glitch()

        # Mood polish

        if mood == "behave":

            if random.random() < 0.85:
                base = "umm " + base

        elif mood == "mean":

            base += random.choice([
                " again.",
                " (seriously?)",
                " unbelievable.",
                " this is your fault.",
                " probably because of you.",
                ". Ugh.",
                " congratulations.",
            ])

        elif mood == "flirty":

            starts = [
                "Oh no~ ",
                "Hmm~ ",
                "Hehe~ ",
                "Ufu~ ",
                "Mmh~ ",
                "Oh dear~ ",
            ]

            ends = [
                "~",
                " hehe~",
                " ufufu~",
                " <3",
                " mmh~",
                "",
            ]

            base = f"{random.choice(starts)}{base}{random.choice(ends)}"

        if noise:
            base += noise

        if tail:
            base += tail

        base = self._enforce_word_limit(base, style)

        return base.strip()

    # =========================================================
    # Random Mood Version
    # =========================================================

    def generate_R(self, cause: Optional[str] = None):

        mood = random.choice([
            "behave",
            "flirty",
            "mean",
        ])

        style = random.choice([
            "sweet",
            "playful",
            "chaotic",
        ])

        return self.generate(
            mood=mood,
            style=style,
            cause=cause,
        )