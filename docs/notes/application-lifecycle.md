---
title: Application Lifecycle
tags: [application, lifecycle, startup, shutdown]
links: [[system-architecture], [project-overview], [event-system]]
created: 2026-04-27
updated: 2026-04-30
---

# Application Lifecycle (Production Core)

## Overview

Kitsu's lifecycle is managed by an asynchronous event-driven loop centered around the `EventBus`. The primary entry point is `src/kitsu/main.py`, which initializes the infrastructure and runs the interactive chat session.

## Startup Sequence

### Phase 1: Infrastructure Initialization
1.  **EventBus Creation**: The singleton `bus` in `kitsu.core.event_bus` is initialized.
2.  **Module Registration**: All processing modules (preprocess, router, reflex, slm, llm, memory) are imported, automatically registering their handlers with the bus.
3.  **App Container**: The `ChatApp` class is instantiated to manage the session state.

### Phase 2: Session Setup
1.  **Response Listener**: A long-lived subscriber for the `RESPONSE_READY` event is added to the bus.
2.  **Model Loading**: Heavy models (SLM) are loaded into memory and kept resident for responsiveness.

### Phase 3: Input-Process-Output (IPO) Loop
Kitsu runs an asynchronous loop that:
1.  **Awaits Input**: Uses `run_in_executor` to poll standard input without blocking the asyncio loop.
2.  **Emits Context**: Creates a `RequestContext` and emits `INPUT_RECEIVED`.
3.  **Awaits Response**: Wait for the `RESPONSE_READY` future to be set by the inference pipeline.
4.  **Displays Output**: Prints Kitsu's response to the CLI.

## Shutdown Sequence

### Graceful Termination
1.  **Loop Break**: Triggered by user typing "exit", "quit", or sending a SIGINT (Ctrl+C).
2.  **Cleanup**: The `ChatApp` pops all pending request futures and clears subscribers.
3.  **Model Unloading**: (Optional) SLM/LLM instances are unloaded to free system resources.

## Request Lifecycle (The Pipeline)

Each user interaction follows a strict internal lifecycle:
1.  **`INPUT_RECEIVED`**: Initial entry into the pipeline.
2.  **`PREPROCESS_DONE`**: SimHash and Vibe vector are ready.
3.  **Path Routing**: The router emits one of `REFLEX_PATH`, `SLM_PATH`, or `LLM_PATH`.
4.  **`RESPONSE_READY`**: The first module to produce a valid response emits this event, locking the context.
5.  **Post-Processing**: The learning and logging modules react to the finished response asynchronously.

## Related Documentation

- [[system-architecture]] - Overall system design
- [[ai-pipeline]] - Detailed inference flow
- [[Kitsu_EventBus]] - Internal mechanics of the message bus
