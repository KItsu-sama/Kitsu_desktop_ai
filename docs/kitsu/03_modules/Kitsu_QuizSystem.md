# Kitsu Quiz System

The Quiz System is a specialized extension of Kitsu designed to provide high-speed, context-aware assistance for browser-based quizzes and tests.

## Architecture

Unlike the main chat pipeline, the Quiz System bypasses the `EventBus` for maximum performance and determinism. It operates via a dedicated WebSocket server.

### Communication Flow
1.  **Extraction**: A browser extension extracts the question and options from the webpage.
2.  **Request**: The extension sends a JSON payload to `ws://localhost:7731`.
3.  **Processing**: `QuizHandler` receives the data and calls the SLM (Small Language Model) directly.
4.  **Answer**: The system returns the predicted answer index and a confidence score.

## Mode Selection

The system supports three distinct operation modes to balance speed and stealth:

-   **Rush**: 0s cooldown. Best for minimizing time.
-   **Normal**: 5–15s randomized cooldown. Simulates human thinking time to avoid detection.
-   **Adapt**: Dynamic cooldown and tool usage (e.g., score multipliers) where supported by the quiz platform.

## Self-Learning & Review

Every quiz interaction is recorded in the `ANSWER_STORE`. This data is used for two purposes:
1.  **Auto-Solver Gating**: If the user's average score in a topic falls below 60%, the auto-solver is automatically disabled for that topic to encourage manual learning.
2.  **Review Triggers**: Kitsu can use stored questions to pop up "Review Quizzes" during idle time to help the user master topics they previously failed.

## Implementation Details

-   **Location**: `src/kitsu/modules/quiz_handler.py`
-   **Model**: Direct access to `SLMInterface` (Qwen2.5-1.5B).
-   **Storage**: Results are hashed by question text to ensure O(1) retrieval for repeated questions.
