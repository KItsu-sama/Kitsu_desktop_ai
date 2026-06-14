"""application/modules/system_state_reflex.py

Early handler that intercepts small-talk check-ins like:
  - "how are you"
  - "how r u"
  - "are you ok"

Requirement:
- If the current *style* is DIRECT, respond with the *whole system state*.
- Otherwise, do nothing and let the normal pipeline handle it.

Design:
- Subscribes to INPUT_RECEIVED so it runs before router/reflex/slm/llm.
- Emits RESPONSE_READY only when it matches and ctx is eligible.

"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from ..core.event_bus import bus
from ..core.context import RequestContext, can_respond
from ..core.subscriptions import register


# Direct-style trigger phrases
_PAT = re.compile(r"^\s*(how\s+are\s+you|how\s+r\s+u|are\s+you\s+ok)\s*[!?\.]?\s*$", re.IGNORECASE)


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name, default)
    except Exception:
        return default


def _format_snapshot(snapshot: Dict[str, Any]) -> str:
    # Keep it readable in terminal chat.
    return (
        "🧭 SYSTEM STATE SNAPSHOT (DIRECT)\n"
        "--------------------------------\n"
        + json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
    )


async def _on_input_received(ctx: RequestContext) -> None:
    # Only intercept if phrase matches.
    if not ctx or not ctx.text:
        return

    if not _PAT.match(ctx.text):
        return

    # Determine "direct" style.
    # Style can come from ctx.mode/vibe pipeline; in this codebase, personality
    # style is typically in the emotion engine and is exposed as ctx.vibe only.
    # However, many systems already attach emotion state; we attempt several.
    style = None

    # 1) If context has direct style stored by other layers.
    style = _safe_getattr(ctx, "style", None)
    if not style:
        style = ctx.get_context("style") if hasattr(ctx, "get_context") else None

    # 2) Pull from EmotionEngine singleton if available.
    if not style:
        try:
            from domain.personality.emotion_engine import EmotionEngine

            ee = EmotionEngine.get_singleton()
            state = ee.get_emotional_state()
            style = state.get("style")
        except Exception:
            style = None

    if str(style).lower() != "direct":
        return

    if not can_respond(ctx):
        return

    # Build whole system state snapshot.
    snapshot: Dict[str, Any] = {
        "request": {
            "id": getattr(ctx, "id", None),
            "text": getattr(ctx, "text", None),
            "mode": getattr(ctx, "mode", None),
            "route": getattr(ctx, "route", None),
        },
        "emotion": None,
        "resources": None,
        "budgets": None,
        "orchestrator": None,
        "trace": getattr(ctx, "trace", []),
    }

    # Emotion state
    try:
        from domain.personality.emotion_engine import EmotionEngine

        ee = EmotionEngine.get_singleton()
        snapshot["emotion"] = ee.get_state_dict() if hasattr(ee, "get_state_dict") else ee.get_emotional_state()
    except Exception:
        snapshot["emotion"] = {"error": "failed_to_load_emotion_state"}

    # Orchestrator system status (detailed)
    try:
        from domain.core.kitsu_orchestrator import KITSU_ORCHESTRATOR

        if hasattr(KITSU_ORCHESTRATOR, "get_detailed_status"):
            snapshot["orchestrator"] = KITSU_ORCHESTRATOR.get_detailed_status()
        elif hasattr(KITSU_ORCHESTRATOR, "get_system_status"):
            snapshot["orchestrator"] = {
                "system_status": _safe_getattr(KITSU_ORCHESTRATOR, "get_system_status")
            }
        else:
            snapshot["orchestrator"] = {"error": "orchestrator_status_getter_not_found"}
    except Exception as e:
        snapshot["orchestrator"] = {"error": f"failed_to_load_orchestrator: {e}"}

    # Fallback: budgets/resources directly (best effort)
    try:
        from domain.inference import RESOURCE_CONTROLLER
        from shared.flags.budgets import BUDGET_MANAGER
        
        snapshot["resources"] = RESOURCE_CONTROLLER.get_system_status() if hasattr(RESOURCE_CONTROLLER, "get_system_status") else _safe_getattr(RESOURCE_CONTROLLER, "metrics", None)
        snapshot["budgets"] = BUDGET_MANAGER.get_budget_summary() if hasattr(BUDGET_MANAGER, "get_budget_summary") else None
    except Exception:
        pass

    ctx.response = _format_snapshot(snapshot)
    ctx.response_owner = "system_state_reflex"

    # Important: RESPONSE_READY should be emitted with ctx so ChatApp unblocks.
    await bus.emit("RESPONSE_READY", ctx)


register("INPUT_RECEIVED", _on_input_received, priority=-10)

