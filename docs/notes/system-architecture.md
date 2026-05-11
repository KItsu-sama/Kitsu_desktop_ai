---
title: System Architecture
tags: [architecture, core-system, production, event-driven]
links: [[project-overview], [ai-pipeline], [personality-system], [event-system]]
created: 2026-04-27
updated: 2026-04-30
---

# System Architecture (Production Core)

## Overview

Kitsu utilizes a **production-grade event-driven architecture** where state is carried through a central context and modules are fully decoupled via an asynchronous message bus.

## Core Package Layout (`src/kitsu/`)

The system is organized following modern Python standards into three functional categories:

### 1. Core Infrastructure (`kitsu.core`)
- **`EventBus`**: The central communication hub. Supports `asyncio.gather` for parallel handler execution and implements a safety lock for response emission.
- **`RequestContext`**: The single source of truth for a request. Carries the input text, computed SimHash, vibe vector, selected route, and latency status.

### 2. Processing Modules (`kitsu.modules`)
Functional blocks that react to bus events.
- **`preprocess`**: Tokenization and SimHash logic.
- **`router`**: Tier selection logic.
- **`reflex`**: O(1) cache and templates.
- **`slm` / `llm`**: Model inference interfaces.
- **`judge`**: Response validation logic.
- **`memory`**: Persistent learning and cache updates.
- **`quiz_handler`**: Specialized high-speed WebSocket interface for browser quizzes.

### 3. Utilities (`kitsu.utils`)
- **`timing`**: Nanosecond-precision latency tracking to prevent floating-point drift and ensure budget compliance.

## Architectural Constraints

1.  **State Isolation**: Modules never call each other. Communication is strictly: `Subscribe to Event -> Transform Context -> Emit Result`.
2.  **Response Locking**: Only one module may emit `RESPONSE_READY` per request. Enforced by the `EventBus` checking the `ctx.responded` flag.
3.  **Error Isolation**: Handler failures are caught by the `EventBus` to prevent cascading system crashes.
4.  **Early Termination**: All inference modules must check `can_respond(ctx)` at the start of their handlers to avoid wasted computation if a faster path has already succeeded.

## Communication Patterns

### Event Cascades
- `INPUT_RECEIVED` -> `PREPROCESS_DONE`
- `PREPROCESS_DONE` -> `REFLEX_PATH` | `SLM_PATH` | `LLM_PATH`
- Any path -> `RESPONSE_READY`
- `RESPONSE_READY` -> Learning/Logging

## Performance Strategy

- **SimHash Routing**: Minimizes LLM usage by promoting frequent interactions to an O(1) lookup.
- **Nanosecond Budgets**: Default latency budget is 5000ms. Modules are designed to return a "best effort" response if the timer expires.
- **Async I/O**: Sync IO operations are offloaded to a thread pool via `run_in_executor` to keep the main event loop responsive.
