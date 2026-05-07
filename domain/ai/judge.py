from dataclasses import dataclass

@dataclass
class JudgeResult:
    in_character: int
    coherent: int  
    factually_safe: int
    
    def confidence(self, mode: str = "chat") -> float:
        weights = {"chat": (0.5, 0.3, 0.2), "quiz": (0.2, 0.3, 0.5), "task": (0.3, 0.4, 0.3)}
        w = weights.get(mode, weights["chat"])
        return w[0]*self.in_character + w[1]*self.coherent + w[2]*self.factually_safe

def judge(response: str, vibe: list[float], ctx_text: str, mode: str = "chat") -> JudgeResult:
    return JudgeResult(
        in_character=1 if len(response) > 3 else 0,  # v0 heuristic
        coherent=1 if response.strip() else 0,
        factually_safe=1  # v0: always safe
    )