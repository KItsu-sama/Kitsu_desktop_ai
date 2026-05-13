---
tags: [architecture, design, system-overview, documentation]
aliases: ["System Architecture", "Kitsu Design"]
project: Kitsu Desktop AI
type: documentation
created: 2026-04-27
modified: 2026-04-27
---
# Kitsu System Design (Production Grade)

## High-Level Vision
Kitsu is designed as a modular, local-first AI companion. The primary design goals are **loose coupling**, **low latency**, and **deterministic state management**.

## Architectural Framework

### Event-Driven Core
The system is built on a central `EventBus` (located in `src/kitsu/core/event_bus.py`). This bus allows modules to interact without knowing about each other's existence.

- **Parallel Execution**: Uses `asyncio.gather` for non-blocking subscriber notification.
- **Error Isolation**: Individual module failures are caught and logged, preventing the system from hanging.
- **Sync/Async Support**: Synchronous handlers are automatically offloaded to a thread pool.

### Shared Request Context
State is never global. Every interaction is governed by a `RequestContext` (`src/kitsu/core/context.py`). This context contains:
- Unique Request ID
- Raw Input Text
- Computed SimHash (for cache lookups)
- Vibe Vector (10-float emotional state)
- Latency Budget (nanosecond precision)

## The Cascading Inference Pipeline

To achieve instant responses while maintaining reasoning depth, Kitsu implements a cascading tier strategy:

1.  **Reflex Tier**: O(1) lookups. Matches SimHash against a JSON-based learned cache or runs a Markov template engine.
2.  **SLM Tier**: Small Language Model (Qwen2.5-1.5B). Personality-rich, context-aware generation with vibe injection.
3.  **LLM Tier**: Deep reasoning loop. Iteratively generates and evaluates responses until a quality threshold (Score ≥ 0.65) is met.

## Package Organization (`src/kitsu/`)

-   **`core/`**: The system's heart. Contains the bus and context definitions.
-   **`modules/`**: Functional logic blocks. Each file in this directory represents a stage in the AI pipeline.
-   **`utils/`**: Shared utilities, primarily for timing and budget enforcement.

## Performance & Resource Management

### Hardware Adaptation
The system adjusts its active "Strips" based on available RAM:
- **Ultra Low**: Reflex only.
- **Low/Mid**: SLM enabled.
- **Full**: LLM रीजनिंग reasoning loops enabled.

### Non-Blocking I/O
All blocking operations (Standard Input, JSON writes/reads) are wrapped in `run_in_executor` calls to ensure the AI pipeline remains responsive to events.

## Safety & Quality Control
A **Quality Judge** module sits between generation and display. It assigns a confidence score based on character consistency, coherence, and safety. Only passing responses are shown to the user and promoted to the reflex cache.
