# Orchestrator Module Summary (LEGACY)

> [!WARNING]
> This module is now legacy. Please refer to `kitsu.core.event_bus` for the new communication backbone.

The `Orchestrator` was the **central coordinator** for the Kitsu AI system. In the production refactor, its logic has been moved to specialized modules under `src/kitsu/modules/` to improve maintainability and performance.

### Logic Migration Map

| Legacy Responsibility | New Production Module |
|-----------------------|-----------------------|
| Event Routing         | `kitsu.core.event_bus`|
| Input Processing      | `kitsu.modules.preprocess`|
| Tier Selection        | `kitsu.modules.router`|
| Generation Orchestration | `kitsu.modules.slm` / `kitsu.modules.llm` |
| Learning Feed         | `kitsu.modules.memory`|
