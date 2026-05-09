from dataclasses import dataclass, field
import time
import uuid
from typing import List, Optional

@dataclass
class RequestContext:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    simhash: Optional[str] = None
    vibe: List[float] = field(default_factory=lambda: [0.0] * 10)
    route: Optional[str] = None
    response: Optional[str] = None
    responded: bool = False
    mode: str = "chat"  # chat/quiz/task
    latency_budget_ms: int = 5000
    start_time: float = field(default_factory=time.monotonic_ns)
    loop_count: int = 0

def can_respond(ctx: RequestContext) -> bool:
    """Checks if the request has already been responded to."""
    return not ctx.responded
