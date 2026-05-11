# Kitsu Orchestrator (LEGACY)

> [!WARNING]
> This documentation refers to the legacy synchronous architecture.
> For the new production-grade event-driven core, please see [[system-architecture]] and [[application-lifecycle]].

## Overview
The `Orchestrator` was previously the central coordinator for the Kitsu AI system. It has been replaced by the decoupled `EventBus` and `ChatApp` structure in the `src/kitsu/` package.

## Legacy Responsibilities
- Coordinating startup of all modules.
- Managing synchronous request/response loops.
- Handling hard-coded routing logic.

## Transition to EventBus
The responsibilities of the Orchestrator have been distributed among several modules:
- **Routing**: Now handled by `kitsu.modules.router`.
- **Coordination**: Now handled via events on the `kitsu.core.event_bus`.
- **Session State**: Now handled by `kitsu.main.ChatApp`.
