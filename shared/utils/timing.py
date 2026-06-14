import time
try:
    # Preferred: local project context
    from application.core.context import RequestContext  # type: ignore
except Exception:
    # Fallback for alternate package layouts
    from kitsu.core.context import RequestContext  # type: ignore


def within_budget(ctx: RequestContext) -> bool:
    """Returns True if current monotonic time is within the request budget.

    RequestContext uses `start_time_ns`. Some older code may still refer to
    `start_time`; keep a safe fallback.
    """
    start_ns = getattr(ctx, "start_time_ns", None)
    if start_ns is None:
        # Backward-compat: if `start_time` existed, treat it as ns.
        start_ns = getattr(ctx, "start_time", 0)

    elapsed_ns = time.monotonic_ns() - start_ns
    budget_ns = ctx.latency_budget_ms * 1_000_000
    return elapsed_ns < budget_ns

