"""
shared/debug_timer.py

Comprehensive debug logging with timing for router, personality, reflex, and response paths.
Shows every step of request processing with millisecond precision.
"""

import logging
import time
from typing import Optional, Any, Dict
from contextlib import contextmanager
from datetime import datetime

from .logger import is_debug_output_enabled

# Create dedicated debug logger
debug_log = logging.getLogger("kitsu.debug")

# Track timing across the request lifecycle
_request_timers: Dict[str, Dict[str, Any]] = {}


def _format_time(ms: float) -> str:
    """Format milliseconds with appropriate unit."""
    if ms < 1:
        return f"{ms*1000:.0f}μs"
    elif ms < 1000:
        return f"{ms:.1f}ms"
    else:
        return f"{ms/1000:.2f}s"


def _debug(component: str, action: str, details: str = "", level: str = "INFO") -> None:
    """
    Universal debug log output.
    
    Args:
        component: Major component (ROUTER, REFLEX, PERSONALITY, MEMORY, etc)
        action: What happened (MATCH, CACHE_HIT, ESCALATE, etc)
        details: Additional context
        level: Log level (INFO, DEBUG, WARNING)
    """
    if not is_debug_output_enabled():
        return
    
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    msg = f"[{timestamp}] [{component:12s}] {action:15s}"
    
    if details:
        msg += f" | {details}"
    
    log_func = {
        "INFO": debug_log.info,
        "DEBUG": debug_log.debug,
        "WARNING": debug_log.warning,
    }.get(level, debug_log.info)
    
    log_func(msg)


@contextmanager
def debug_timer(request_id: str, component: str, operation: str):
    """
    Context manager for timing operations with automatic logging.
    
    Usage:
        with debug_timer("req-123", "REFLEX", "match_groups"):
            # do work
    """
    if not is_debug_output_enabled():
        yield
        return
    
    start = time.time()
    _debug(component, f"▶ {operation}", f"started", "DEBUG")
    
    try:
        yield
    finally:
        elapsed_ms = (time.time() - start) * 1000
        _debug(component, f"✓ {operation}", f"completed in {_format_time(elapsed_ms)}", "DEBUG")


def debug_route_decision(
    input_text: str,
    route: str,
    reason: str = "",
    confidence: float = 0.0
) -> None:
    """Log router decision with reasoning."""
    details = f"route={route:10s}"
    if confidence > 0:
        details += f" confidence={confidence:.2%}"
    if reason:
        details += f" reason={reason}"
    _debug("ROUTER", "DECIDE", details)


def debug_reflex_match(
    input_text: str,
    matched_group: Optional[str] = None,
    score: float = 0.0,
    threshold: float = 0.35,
    is_cache_hit: bool = False
) -> None:
    """Log reflex matching attempt."""
    if is_cache_hit:
        _debug("REFLEX", "CACHE_HIT", f"group={matched_group} score={score:.3f}")
    else:
        status = "✓ MATCH" if score >= threshold else "✗ NO_MATCH"
        _debug("REFLEX", status, f"score={score:.3f} threshold={threshold:.3f} group={matched_group}")


def debug_reflex_candidates(candidates_count: int, top_score: float = 0.0) -> None:
    """Log reflex candidate retrieval."""
    _debug("REFLEX", "CANDIDATES", f"found {candidates_count} candidate(s), top_score={top_score:.3f}")


def debug_personality_change(
    emotion: str,
    mood: str = "",
    style: str = "",
    trigger: str = "",
    strength: float = 0.0
) -> None:
    """Log personality/emotion changes."""
    details = f"emotion={emotion}"
    if mood:
        details += f" mood={mood}"
    if style:
        details += f" style={style}"
    if trigger:
        details += f" trigger={trigger}"
    if strength > 0:
        details += f" strength={strength:.2f}"
    
    _debug("PERSONALITY", "CHANGE", details)


def debug_reflex_cache_operation(
    operation: str,
    simhash: str = "",
    result: str = "",
    success: bool = True
) -> None:
    """Log reflex cache operations (get/put)."""
    status = "✓" if success else "✗"
    details = f"{operation.upper()}"
    if simhash:
        details += f" hash={simhash[:8]}..."
    if result:
        details += f" cached={bool(result)}"
    
    _debug("MEMORY", status, details)


def debug_response_pipeline(
    stage: str,
    details: str = "",
    elapsed_ms: float = 0.0
) -> None:
    """Log response pipeline stages."""
    msg = stage
    if elapsed_ms > 0:
        msg += f" ({_format_time(elapsed_ms)})"
    if details:
        msg += f" | {details}"
    
    _debug("PIPELINE", "PROCESS", msg)


def debug_judge_score(
    score: float,
    threshold: float = 0.8,
    passed: bool = True,
    reason: str = ""
) -> None:
    """Log judge scoring decision."""
    status = "✓ PASS" if passed else "✗ FAIL"
    details = f"score={score:.3f} threshold={threshold:.3f}"
    if reason:
        details += f" reason={reason}"
    
    _debug("JUDGE", status, details)


def debug_escalate(reason: str, from_stage: str = "") -> None:
    """Log escalation to next stage."""
    details = f"reason={reason}"
    if from_stage:
        details += f" from={from_stage}"
    
    _debug("ESCALATE", "→ NEXT", details)


def debug_timing_summary(request_id: str, total_ms: float, stages: Dict[str, float]) -> None:
    """Log timing summary for entire request."""
    if not is_debug_output_enabled():
        return
    
    summary = f"Total: {_format_time(total_ms)}"
    for stage, ms in sorted(stages.items(), key=lambda x: x[1], reverse=True):
        pct = (ms / total_ms * 100) if total_ms > 0 else 0
        summary += f" | {stage}: {_format_time(ms)} ({pct:.0f}%)"
    
    _debug("TIMING", "SUMMARY", summary)


def debug_match_details(
    group_name: str,
    trigger_phrases: list = None,
    scores: Dict[str, float] = None,
    selected_response: str = ""
) -> None:
    """Log detailed reflex match information."""
    if not is_debug_output_enabled():
        return
    
    details = f"group={group_name}"
    if trigger_phrases:
        details += f" triggers={len(trigger_phrases)}"
    if scores:
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        details += f" avg_score={avg_score:.3f}"
    if selected_response:
        preview = selected_response[:40].replace("\n", " ")
        details += f" response='{preview}...'"
    
    _debug("REFLEX", "DETAIL", details)


def debug_cache_put(simhash: str, response_preview: str, quality_score: float) -> None:
    """Log cache storage decision."""
    preview = response_preview[:30].replace("\n", " ")
    details = f"hash={simhash[:8]}... quality={quality_score:.2f} text='{preview}...'"
    _debug("MEMORY", "CACHE_PUT", details)


def debug_response_routing(
    from_stage: str,
    to_route: str,
    reason: str = "",
    confidence: float = 0.0
) -> None:
    """Log response routing decisions."""
    details = f"{from_stage} → {to_route}"
    if confidence > 0:
        details += f" conf={confidence:.2%}"
    if reason:
        details += f" ({reason})"
    
    _debug("ROUTER", "ROUTE", details)
