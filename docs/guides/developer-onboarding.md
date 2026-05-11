---
title: Developer Onboarding Guide
tags: [development, onboarding, setup]
links: [[project-overview], [system-architecture], [Kitsu_EventBus]]
created: 2026-04-27
updated: 2026-04-30
---

# Developer Onboarding Guide (Production Core)

Welcome to the Kitsu development team! This guide will get you up to speed with our new production-grade event-driven architecture.

## Project Setup

### 1. Environment Setup
We recommend using Python 3.10+ for the best `asyncio` performance.

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode to ensure absolute imports resolve correctly
pip install -e .
```

### 2. Running the Application
The primary entry point for the AI core is the interactive chat loop:
```bash
python src/kitsu/main.py
```

## Key Architectural Concepts

### 1. The Event Bus
All communication happens via `kitsu.core.event_bus`.
- **Rule**: Never call another module directly.
- **Rule**: Only emit `RESPONSE_READY` if you are the designated response path.

### 2. Request Context
Every request is an instance of `RequestContext`. It carries all state. If you need to pass data between modules, add a field to this dataclass.

### 3. Cascading Tiers
Understand the pipeline flow:
`Preprocess` -> `Router` -> (`Reflex` | `SLM` | `LLM`) -> `Judge` -> `Display`

## Common Development Tasks

### Adding a New Processor
1.  Create a file in `src/kitsu/modules/`.
2.  Import the global `bus` from `kitsu.core.event_bus`.
3.  Define your handler and subscribe to the relevant event.
4.  **Important**: Import your new module in `src/kitsu/main.py` to ensure it registers during startup.

### Modifying the Routing Logic
Tier selection logic lives in `src/kitsu/modules/router.py`. We use a combination of SimHash (for cache) and complexity scoring (for model selection).

## Testing
Always run the pipeline verification script after making architectural changes:
```bash
# Create a test script using absolute imports from kitsu
python test_pipeline.py
```

## Documentation Standards
- **Obsidian Links**: Use `[[note-name]]` for internal linking.
- **Technical Contracts**: Ensure any changes to the `EventBus` or `RequestContext` are updated in `SYSTEM_ARCHITECTURE.md`.

Welcome to Kitsu! 🦊
