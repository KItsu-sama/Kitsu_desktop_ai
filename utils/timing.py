import time
from core.context import RequestContext

def within_budget(ctx: RequestContext) -> bool:
    """
    Returns True if the current time is within the latency budget of the request.
    Uses nanoseconds internally to avoid float drift.
    """
    elapsed_ns = time.monotonic_ns() - ctx.start_time
    budget_ns = ctx.latency_budget_ms * 1_000_000
    return elapsed_ns < budget_ns
