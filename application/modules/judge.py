# application/modules/judge.py --- Simple heuristic-based judge for response evaluation

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from ..core.context import RequestContext

# Threshold — tunable per deployment
THETA: float = 0.65

_WEIGHTS = {
    "chat": (0.5, 0.3, 0.2),
    "quiz": (0.2, 0.3, 0.5),
    "task": (0.3, 0.4, 0.3),
}

_TRUNCATION = re.compile(r"[.!?…~🦊👋😊😺😤⚡🌙☀️🕒🐱💡✨🙂🙃😘😎]$")
_SENTENCE_MIN = 2
_FACT_PATTERNS = re.compile(
    r"\b(the (population|capital|president|ceo|speed|distance|height|weight|"
    r"temperature|date|year|number) (of|is|was|are|were)|"
    r"in \d{4}|born in|died in|located in|invented by)\b",
    re.IGNORECASE,
)


@dataclass
class JudgeResult:
    in_character: int  # 0 or 1
    coherent: int  # 0 or 1
    factually_safe: int  # 0 or 1

    def confidence(self, mode: str = "chat") -> float:
        w = _WEIGHTS.get(mode, _WEIGHTS["chat"])
        return w[0] * self.in_character + w[1] * self.coherent + w[2] * self.factually_safe

    def passes(self, mode: str = "chat", theta: float = THETA) -> bool:
        return self.confidence(mode) >= theta


def _in_character(response: str, vibe: List[float]) -> int:
    if not response:
        return 0

    words = response.split()
    if len(words) <= 5:
        return 1

    n = max(len(words), 1)
    tone = [
        min(response.count("!") / n, 1.0),
        min(response.count("?") / n, 1.0),
        min(sum(1 for c in response if ord(c) > 127) / max(len(response), 1), 1.0),
        min(sum(len(w) for w in words) / (n * 10), 1.0),
        1.0 if response[0].isupper() else 0.0,
        # Pad positions 5-9 with neutral values instead of zeros to match vibe magnitude
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
    ]

    dot = sum(a * b for a, b in zip(tone, vibe))
    mag_t = sum(x * x for x in tone) ** 0.5
    mag_v = sum(x * x for x in vibe) ** 0.5
    if mag_t == 0 or mag_v == 0:
        return 1
    sim = dot / (mag_t * mag_v)
    return 1 if sim > 0.4 else 0


def _coherent(response: str, ctx_text: str) -> int:
    stripped = response.rstrip()
    if not stripped or len(stripped.split()) < _SENTENCE_MIN:
        return 0

    last_char = stripped[-1]
    if last_char.isalpha() and len(stripped.split()) < 4:
        return 0

    return 1


def _factually_safe(response: str, ctx_text: str) -> int:
    if _FACT_PATTERNS.search(response):
        fact_words = set(match[0].lower() for match in _FACT_PATTERNS.findall(response))
        input_words = set(ctx_text.lower().split())
        if not fact_words.intersection(input_words):
            return 0
    return 1


def judge(response: str, ctx_text: str, vibe: List[float], mode: str = "chat") -> JudgeResult:
    return JudgeResult(
        in_character=_in_character(response, vibe),
        coherent=_coherent(response, ctx_text),
        factually_safe=_factually_safe(response, ctx_text),
    )


# ── Streaming validation ─────────────────────────────────────────────

STREAM_CHECK_INTERVAL = 3  # tokens
STREAM_BUFFER = []  # per-request buffer (managed by caller)


async def stream_validate(buffer: str, ctx: RequestContext) -> tuple[bool, str]:
    """Validate mid-stream.

    Returns:
        (should_continue, warning_message)

    Notes:
    - Uses quick coherence + tone checks (no fact check mid-stream).
    - Buffer is expected to be maintained per-request by the caller.
    """

    if not buffer:
        return True, ""

    # Conservative token approximation
    if len(buffer.split()) < STREAM_CHECK_INTERVAL:
        return True, ""

    # Quick coherence check (no fact check needed mid-stream)
    coherent_ok = _coherent(buffer, ctx.text)
    if not coherent_ok:
        return False, "Response became incoherent"

    # Tone check against vibe
    in_char_ok = _in_character(buffer, ctx.vibe)
    if not in_char_ok:
        return False, "Response drifted out of character"

    return True, ""


def judge_response(ctx: RequestContext, response_text: str) -> JudgeResult:
    return judge(response_text, ctx_text=ctx.text, vibe=ctx.vibe, mode=ctx.mode)

