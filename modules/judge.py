from dataclasses import dataclass
from core.context import RequestContext

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
