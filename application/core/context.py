"""
application/core/context.py

RequestContext — carries everything for one request through the pipeline.

Rules:
- Every field set at construction or by the ONE module responsible for it.
- No module writes to a field it doesn't own.
- `responded` is a one-way latch; once True it never goes back.
- `can_respond(ctx)` is the ONLY gate before emitting RESPONSE_READY.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

from domain.contracts.lifecycle import ModuleState


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class RequestState(Enum):
    """Request processing states for better tracking."""
    CREATED = "created"
    PROCESSING = "processing"
    ROUTED = "routed"
    RESPONDED = "responded"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class RequestContext:
    # ── Input ──────────────────────────────────────────────────────────────
    text: str = ""                           # normalized text (set by InputMux)
    original_text: str = ""                  # raw text before normalization
    input_type: Optional[str] = None         # voice/text/command/etc

    # ── Identity & routing ─────────────────────────────────────────────────
    id: str = field(default_factory=_new_id)
    route: str = ""                          # "REFLEX" | "SLM" | "LLM"
    state: RequestState = RequestState.CREATED

    # ── Semantic fingerprint ────────────────────────────────────────────────
    simhash: int = 0                         # set by preprocess
    confidence: float = 1.0                   # processing confidence

    # ── Personality & context ───────────────────────────────────────────────
    # 10-float vibe vector; pulled from EmotionEngine, not from this input
    vibe: list[float] = field(default_factory=lambda: [0.5] * 10)
    context: Dict[str, Any] = field(default_factory=dict)  # additional context data

    # ── Response ────────────────────────────────────────────────────────────
    response: str = ""
    responded: bool = False                   # one-way latch — only set via can_respond()


    # Immutable response metadata (set exactly once by the module that emits RESPONSE_READY)
    response_owner: str = ""  # e.g. "reflex" | "slm" | "llm"
    response_timestamp_ns: int = 0
    response_confidence: float = 0.0

    # Event trace for debugging/arbitration inspection/replay systems
    trace: list[tuple[object, ...]] = field(default_factory=list)

    # ── Mode & budget ───────────────────────────────────────────────────────

    mode: str = "chat"                       # "chat" | "quiz" | "task"
    latency_budget_ms: int = 5000
    start_time_ns: int = field(default_factory=time.monotonic_ns)

    # ── Loop control (LLM re-generation) ────────────────────────────────────
    loop_count: int = 0                      # incremented by llm.py each iteration
    
    # ── Error handling ───────────────────────────────────────────────────────
    error: Optional[str] = None              # last error if any
    retry_count: int = 0                     # number of retries attempted

    # ── Resource tracking ───────────────────────────────────────────────────
    resource_tier: Optional[str] = None      # current resource tier used
    processing_cost: float = 0.0              # estimated processing cost

    def mark_state(self, new_state: RequestState) -> None:
        """Safely transition to a new state."""
        self.state = new_state

    def add_context(self, key: str, value: Any) -> None:
        """Add context data."""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context data."""
        return self.context.get(key, default)

    def set_error(self, error: str) -> None:
        """Set error and mark as failed."""
        self.error = error
        self.mark_state(RequestState.FAILED)

    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if request can be retried."""
        return self.retry_count < max_retries and self.state != RequestState.RESPONDED

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1


def can_respond(ctx: RequestContext) -> bool:
    """
    Gate for RESPONSE_READY.  Call this at the top of every handler that
    might emit RESPONSE_READY.  Returns True and latches ctx.responded=True
    atomically (single-threaded asyncio — no lock needed).
    """
    if ctx.responded:
        return False
    ctx.responded = True
    ctx.mark_state(RequestState.RESPONDED)
    return True


def within_budget(ctx: RequestContext) -> bool:
    """True while elapsed time is under the latency budget."""
    elapsed_ns = time.monotonic_ns() - ctx.start_time_ns
    return elapsed_ns < ctx.latency_budget_ms * 1_000_000


def is_timeout(ctx: RequestContext) -> bool:
    """Check if request has exceeded its budget."""
    return not within_budget(ctx)


def mark_timeout(ctx: RequestContext) -> None:
    """Mark request as timed out."""
    ctx.mark_state(RequestState.TIMEOUT)


# Factory function for creating contexts with proper initialization
def create_request_context(
    text: str,
    original_text: Optional[str] = None,
    mode: str = "chat",
    route: str = "",
    latency_budget_ms: int = 5000
) -> RequestContext:
    """Create a new RequestContext with proper initialization."""
    ctx = RequestContext(
        text=text,
        original_text=original_text or text,
        mode=mode,
        route=route,
        latency_budget_ms=latency_budget_ms
    )
    ctx.mark_state(RequestState.CREATED)
    return ctx
