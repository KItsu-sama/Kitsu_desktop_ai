import asyncio
import json
import logging
import hashlib
from typing import Dict, Any, Optional
from kitsu.core.context import RequestContext
from kitsu.modules.slm import slm_instance

logger = logging.getLogger(__name__)

# Answer store (mocked as in-memory dict for now)
ANSWER_STORE = {}

class QuizHandler:
    async def handle_quiz(self, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes quiz from extension.
        Applies mode cooldown.
        Returns {answer_index: int, confidence: float}.
        """
        question = quiz_data.get("question", "")
        options = quiz_data.get("options", [])
        mode = quiz_data.get("mode", "normal")

        # 1. Cooldown logic
        cooldown = self._get_cooldown(mode)
        if cooldown > 0:
            await asyncio.sleep(cooldown)

        # 2. Call SLM directly (bypass main event bus)
        # We mock this by picking a random option
        vibe = [0.1] * 10 # Generic vibe for quiz
        response, logit_conf = slm_instance.generate(f"Question: {question}. Options: {options}", vibe, "quiz")

        # Simplified answer selection
        answer_index = 0
        confidence = 0.85

        # 3. Store result
        q_hash = hashlib.md5(question.encode()).hexdigest()
        ANSWER_STORE[q_hash] = {
            "question": question,
            "answer_index": answer_index,
            "was_correct": None, # Updated later when result is known
            "timestamp": asyncio.get_event_loop().time()
        }

        return {
            "answer_index": answer_index,
            "confidence": confidence
        }

    def _get_cooldown(self, mode: str) -> float:
        if mode == "rush":
            return 0
        if mode == "normal":
            import random
            return random.uniform(5, 15)
        if mode == "adapt":
            return 2.0 # Dynamic cooldown would be here
        return 0

async def quiz_server_mock():
    """
    Mock WebSocket server for quiz extension.
    Listens on ws://localhost:7731
    """
    handler = QuizHandler()
    logger.info("Quiz WebSocket server started on port 7731")
    # In real impl, use 'websockets' library
    pass

if __name__ == "__main__":
    # Test quiz handler
    async def test():
        qh = QuizHandler()
        res = await qh.handle_quiz({
            "question": "What is 2+2?",
            "options": ["3", "4", "5"],
            "mode": "rush"
        })
        print(f"Quiz Result: {res}")

    asyncio.run(test())
