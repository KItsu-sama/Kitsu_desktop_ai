"""
application/modules/reflex.py

Subscribes to: REFLEX_PATH
Emits:         RESPONSE_READY  (or escalates to SLM_PATH)

Architecture-compliant reflex layer.  Replaces the old regex + flat-cache
approach with group-based associative retrieval.

Pipeline (per request):
    normalize → fingerprint → retrieve candidate groups → hybrid score
    → weighted response selection → judge → emit / escalate

Budget: <100 ms total.

Key design decisions
────────────────────────────────────────────────
* Groups are the memory unit (not question→answer pairs).
* Matching uses a hybrid of SimHash similarity, trigram similarity, and
  token overlap — no embeddings, no vector DBs, no neural retrieval.
* Responses are selected by weighted random draw that avoids recent repeats.
* Tool groups route to a tool-call helper instead of emitting static text.
* The learned cache (simhash→response from previous LLM-validated runs) is
  checked FIRST as an exact-fingerprint shortcut.
* Reflex never hard-fails — it always escalates to SLM_PATH on miss.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Awaitable, Callable

from ..core.context import RequestContext, can_respond, within_budget
from ..core.event_bus import bus
from ..core.subscriptions import register
from .judge import judge
from .reflex_compiler import load_runtime


# ── Similarity helpers ────────────────────────────────────────────────────
# Import path may need adjusting depending on your package layout.
try:
    from shared.utils.simhashh import (
        simhash as compute_simhash,
        similarity as simhash_similarity,
        trigram_similarity,
        token_overlap,
    )
except ImportError:  # pragma: no cover
    # Use the real (non-placeholder) implementation from shared.utils.
    # This keeps reflex functional without type-ignore comments.
    from shared.utils.simhashh import (
        simhash as compute_simhash,
        similarity as simhash_similarity,
        trigram_similarity,
        token_overlap,
    )



log = logging.getLogger("app.reflex")

# Import debug logging utilities
try:
    from shared.debug_timer import (
        debug_timer,
        debug_reflex_match,
        debug_reflex_candidates,
        debug_reflex_cache_operation,
        debug_escalate,
        debug_judge_score,
        debug_match_details,
        debug_response_pipeline,
        _debug
    )
except ImportError:
    # Graceful fallback if debug_timer not available
    def debug_reflex_match(*args, **kwargs): pass
    def debug_reflex_candidates(*args, **kwargs): pass
    def debug_reflex_cache_operation(*args, **kwargs): pass
    def debug_escalate(*args, **kwargs): pass
    def debug_judge_score(*args, **kwargs): pass
    def debug_match_details(*args, **kwargs): pass
    def debug_response_pipeline(*args, **kwargs): pass
    def debug_timer(*args, **kwargs):
        from contextlib import contextmanager
        @contextmanager
        def noop(): yield
        return noop()

# ── Config ────────────────────────────────────────────────────────────────
MATCH_THRESHOLD: float = float(os.environ.get("REFLEX_MATCH_THRESHOLD", "0.35"))
HISTORY_WINDOW: int = 5
HISTORY_MAX: int = 40

# ── Learned cache ────────────────────────────────────────────────────────
CACHE_FILE = Path("data/reflex_cache.json")
_cache: dict[str, str] = {}


def _load_cache() -> None:
    global _cache
    if CACHE_FILE.exists():
        try:
            raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            _cache = {str(k): str(v) for k, v in raw.items()}
            log.info("reflex: %d cache entries loaded", len(_cache))
        except Exception as e:
            log.exception("reflex: cache load failed — starting empty")
            try:
                import traceback

                from application.splash import display_kitsu_error_box

                display_kitsu_error_box(
                    title="Kitsu Runtime Error",
                    message=str(e) if str(e) else "Cache load failed",
                    details=(
                        f"{CACHE_FILE.resolve()}\n"
                        f"While loading reflex cache.\n\n"
                        f"{traceback.format_exc()}"
                    ),
                )
            except Exception:
                pass
            _cache = {}



_load_cache()

# ── Cache accessors (router must not own cache) ─────────────────────────

def cache_has(simhash: int) -> bool:
    """Check if reflex cache contains this simhash."""
    return str(simhash) in _cache


def cache_get(simhash: int) -> Optional[str]:
    """Get cached response for simhash, or None if not found."""
    result = _cache.get(str(simhash))
    debug_reflex_cache_operation("GET", str(simhash)[:8], str(result)[:40] if result else "", result is not None)
    return result


def cache_put(simhash: int, response: str) -> None:
    """Store response in reflex cache (used by LLM after validation)."""
    _cache[str(simhash)] = response
    debug_reflex_cache_operation("PUT", str(simhash)[:8], response[:40], True)
    try:
        CACHE_FILE.write_text(json.dumps(_cache, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("reflex: failed to write cache: %s", e)
        debug_reflex_cache_operation("PUT_WRITE_FAIL", str(simhash)[:8], "", False)

# ── Runtime group index (compiled at startup) ────────────────────────────

_groups: list[dict[str, Any]] = []


def _load_groups() -> None:
    global _groups
    _groups = load_runtime()
    log.info("reflex: %d groups loaded", len(_groups))


_load_groups()

# ── Recent response history (anti-repeat) ────────────────────────────────
_history: list[str] = []


def _time_of_day() -> str:
    h = datetime.now().hour
    if h < 12:
        return "morning"
    if h < 17:
        return "afternoon"
    return "evening"


def _interpolate(text: str) -> str:
    return (
        text
        .replace("{time}", datetime.now().strftime("%H:%M"))
        .replace("{time_of_day}", _time_of_day())
    )


async def _clock_now_tool(ctx: RequestContext) -> Optional[str]:
    return _interpolate("It's currently {time}. 🕒")


TOOL_HANDLERS: dict[str, Callable[[RequestContext], Awaitable[Optional[str]]]] = {
    "clock.now": _clock_now_tool,
}


def _score_group(query: str, qhash: int, group: dict[str, Any]) -> float:
    best = 0.0
    for trigger_text, trigger_hash in zip(group["trigger_texts"], group["fingerprints"]):
        sh = simhash_similarity(qhash, trigger_hash)

        tg = trigram_similarity(query, trigger_text)
        to = token_overlap(query, trigger_text)

        score = tg * 0.4 + to * 0.3 + sh * 0.3
        if score > best:
            best = score

    return best


def _retrieve_candidates(
    query: str,
    qhash: int,
    threshold: float = MATCH_THRESHOLD,
    top_k: int = 0,
) -> list[tuple[float, dict[str, Any]]]:
    results: list[tuple[float, dict[str, Any]]] = []
    for group in _groups:
        score = _score_group(query, qhash, group)
        if score >= threshold:
            results.append((score, group))

    results.sort(key=lambda x: (x[0], x[1]["priority"]), reverse=True)
    
    # Debug output
    top_score = results[0][0] if results else 0.0
    debug_reflex_candidates(len(results), top_score)
    
    # Show top 3 matches if debug enabled
    for i, (score, group) in enumerate(results[:3]):
        debug_match_details(
            group.get("group", "unknown"),
            group.get("trigger_texts", [])[:2],
            {"score": score},
            group.get("responses", [{}])[0].get("text", "")[:30] if group.get("responses") else ""
        )
    
    if top_k > 0:
        return results[:top_k]
    return results


def _pick_response(group: dict[str, Any]) -> str:
    recent = set(_history[-HISTORY_WINDOW:]) if _history else set()
    responses = group["responses"]

    texts = [r["text"] for r in responses]
    weights = [0 if r["text"] in recent else r["weight"] for r in responses]

    if sum(weights) == 0:
        weights = [r["weight"] for r in responses]

    total = sum(weights)
    roll = random.uniform(0, total)
    running = 0.0
    for text, w in zip(texts, weights):
        running += w
        if roll <= running:
            return text

    return texts[-1]


async def _invoke_tool(tool: str, ctx: RequestContext) -> Optional[str]:
    handler = TOOL_HANDLERS.get(tool)
    if handler is None:
        log.debug("reflex: unknown tool %r — treating as unavailable", tool)
        return None

    return await handler(ctx)


async def on_reflex_path(ctx: RequestContext) -> None:
    t0 = time.monotonic_ns()
    ctx.trace.append(("reflex", "enter", t0))

    if not within_budget(ctx):
        log.debug("reflex: over budget before start id=%s", ctx.id)
        debug_escalate("budget exceeded", "REFLEX_PATH")
        await bus.emit("SLM_PATH", ctx)
        return

    query = ctx.text

    raw_hash = ctx.simhash
    if isinstance(raw_hash, int):
        qhash = raw_hash
    elif isinstance(raw_hash, str):
        if raw_hash.isdigit():
            qhash = int(raw_hash)
        elif len(raw_hash) == 32:
            qhash = compute_simhash(query)
        else:
            qhash = compute_simhash(query)
    else:
        qhash = compute_simhash(query)

    ctx.simhash = qhash

    # Learned cache is a fast path for exact simhash hits. Fuzzy retrieval
    # still happens via group matching if the cache misses.
    response = cache_get(qhash)  # Use accessor
    if response is not None:
        ctx.trace.append(("reflex", "cache_hit"))
        debug_reflex_match(query, "CACHE", 1.0, 0.35, is_cache_hit=True)
        log.debug("reflex: cache hit id=%s", ctx.id)


    if response is None:
        debug_response_pipeline("Retrieving candidates")
        candidates = _retrieve_candidates(query, qhash)

        if not candidates:
            log.debug("reflex: no candidates, escalating id=%s", ctx.id)
            ctx.trace.append(("reflex", "no_candidates"))
            debug_escalate("no candidates matched", "REFLEX")
            await bus.emit("SLM_PATH", ctx)
            return

        score, best_group = candidates[0]
        ctx.trace.append(("reflex", "group_match", best_group["group"], round(score, 3)))
        debug_reflex_match(query, best_group.get("group", "unknown"), score, MATCH_THRESHOLD, False)
        log.debug(
            "reflex: matched group=%r score=%.3f id=%s",
            best_group["group"],
            score,
            ctx.id,
        )

        if best_group.get("tool"):
            debug_response_pipeline(f"Invoking tool: {best_group['tool']}")
            tool_result = await _invoke_tool(best_group["tool"], ctx)
            if tool_result is not None:
                response = tool_result
                ctx.trace.append(("reflex", "tool_ok", best_group["tool"]))
                debug_response_pipeline(f"Tool executed: {best_group['tool']}", tool_result[:40])
            else:
                log.debug("reflex: tool %r unavailable, escalating id=%s", best_group["tool"], ctx.id)
                ctx.trace.append(("reflex", "tool_unavailable", best_group["tool"]))
                debug_escalate(f"tool unavailable: {best_group['tool']}", "REFLEX")
                await bus.emit("SLM_PATH", ctx)
                return

        if response is None:
            response = _interpolate(_pick_response(best_group))
            debug_response_pipeline("Response selected", response[:50])

    # Judge the response
    debug_response_pipeline("Running judge")
    result = judge(response, query, ctx.vibe, ctx.mode)
    judge_passed = result.in_character
    debug_judge_score(result.confidence(ctx.mode), 0.8, judge_passed, "tone validation")
    
    if not judge_passed:
        log.debug("reflex: judge rejected (tone), escalating id=%s", ctx.id)
        ctx.trace.append(("reflex", "judge_rejected"))
        debug_escalate("judge rejected response", "REFLEX")
        await bus.emit("SLM_PATH", ctx)
        return

    ctx.response = response
    ctx.response_owner = "reflex"
    ctx.response_confidence = result.confidence(ctx.mode)

    _history.append(response)
    if len(_history) > HISTORY_MAX:
        _history.pop(0)

    elapsed_ms = (time.monotonic_ns() - t0) / 1_000_000
    ctx.trace.append(("reflex", "done", round(elapsed_ms, 2)))
    debug_response_pipeline("Reflex complete", f"response ready in {elapsed_ms:.1f}ms")
    log.debug("reflex: response ready %.1f ms id=%s", elapsed_ms, ctx.id)

    if not can_respond(ctx):
        log.debug("reflex: already responded id=%s", ctx.id)
        return

    await bus.emit("RESPONSE_READY", ctx)


register("REFLEX_PATH", on_reflex_path)

