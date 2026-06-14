"""application.modules.vtuber_control

VTuber model control - safe stub.

Design:
- Subscribe to RESPONSE_READY and translate personality/mood into
  avatar expression and animation cues.
- Since the actual vtuber integration (OBS websocket, VRM SDK, Tauri
  overlay, etc.) is environment-specific, this module provides a stub
  that emits internal events and logs.

Events:
- Emits VTUBER_EXPRESSION with: {expression, intensity, mood, raw_text}
"""

from __future__ import annotations

import logging
from typing import Any

from ..core.event_bus import bus
from ..core.subscriptions import register

logger = logging.getLogger("vtuber.control")


def _choose_expression(mood: str | None, valence: float | None = None) -> tuple[str, float]:
    mood_l = (mood or "").lower()
    # Simple mapping
    if mood_l in ("excited", "happy", "joy", "playful"):
        return "smile", 0.9
    if mood_l in ("angry", "rage"):
        return "angry", 0.8
    if mood_l in ("sad", "down"):
        return "sad", 0.7
    if mood_l in ("direct", "neutral"):
        return "neutral", 0.4
    if mood_l in ("chaotic", "mischievous"):
        return "grin", 0.85

    # Default
    if valence is not None and valence < 0.4:
        return "serious", 0.5
    return "smile", 0.55


@register("RESPONSE_READY")
async def on_response_ready(ctx: Any) -> None:
    try:
        mood = getattr(ctx, "mode", None)
        # personality_integration persists more detailed state, but we only
        # have best-effort here.
        mood = mood or getattr(ctx, "debug_reason", None) or "behave"

        # Try to read valence/arousal from character_state.json if available.
        valence = None
        try:
            import json
            from pathlib import Path

            p = Path("data/memory/character_state.json")
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                valence = data.get("valence", None)
        except Exception:
            valence = None

        expression, intensity = _choose_expression(mood, valence=valence)
        payload = {
            "expression": expression,
            "intensity": intensity,
            "mood": mood,
            "response_preview": (getattr(ctx, "response", "") or "")[:120],
        }

        logger.info("VTUBER_EXPRESSION %s", payload)
        await bus.emit("VTUBER_EXPRESSION", payload)

    except Exception:
        logger.exception("vtuber_control failed")

