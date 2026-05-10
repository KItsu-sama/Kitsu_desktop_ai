from dataclasses import dataclass
from kitsu.core.context import RequestContext

@dataclass
class JudgeResult:
    in_character: int   # 0 or 1
    coherent: int       # 0 or 1
    factually_safe: int # 0 or 1

    def confidence(self, mode: str) -> float:
        weights = {
            'chat': (0.5, 0.3, 0.2),
            'quiz': (0.2, 0.3, 0.5),
            'task': (0.3, 0.4, 0.3),
        }
        w = weights.get(mode, (0.33, 0.33, 0.34))
        return w[0]*self.in_character + w[1]*self.coherent + w[2]*self.factually_safe

def judge_response(ctx: RequestContext, response_text: str) -> JudgeResult:
    """
    Called inline from slm.py and llm.py.
    Checks three binary signals: in_character, coherent, factually_safe.
    """
    # 1. in_character: Simplified tone check
    # Compare response tone against vibe vector (mocked)
    in_character = 1
    if len(response_text) < 2:
        in_character = 0

    # 2. coherent: Basic check
    coherent = 1
    if not any(p in response_text for p in ".!?"):
        coherent = 0 # No punctuation might mean truncated

    # 3. factually_safe: flag if response asserts specific facts (simplified)
    factually_safe = 1
    # Simple check for forbidden words or patterns

    return JudgeResult(
        in_character=in_character,
        coherent=coherent,
        factually_safe=factually_safe
    )

def _check_character(response: str, vibe: list[float]) -> int:
    # v0: warmth index. if warmth > 0.6, response should not be terse/harsh
    # implement as simple heuristic first, replace with tiny embedding later
    warmth = vibe[0] if len(vibe) > 0 else 0.5
    if warmth > 0.7 and len(response) < 10:
        return 0  # warmth mode should not give 1-word responses
    return 1

def _check_coherent(response: str, ctx_text: str) -> int:
    # v0: must have a complete sentence, not empty, not truncated
    return 1 if response and response.strip() and len(response) > 3 else 0

def _check_factual(response: str, ctx_text: str) -> int:
    # v0: conservative — flag responses asserting specific numbers/dates not in ctx
    # implement proper RAG cross-check in v1
    return 1  # default safe, add heuristics incrementally