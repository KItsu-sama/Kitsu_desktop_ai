---
title: System Architecture
tags: [architecture, core-system, design]
links: [[project-overview], [ai-pipeline], [personality-system], [event-system]]
created: 2026-04-27
updated: 2026-04-27
---

# System Architecture

## Overview

Kitsu follows a **layered architecture** with clear separation of concerns and capability-based feature toggling.

## Core Components

### Application Layer (`src/application.py`)
Main application orchestrator that coordinates all subsystems.

### Event Bus (`src/bus.py`)
Central event-driven communication system connecting all modules.

### Contract System (`src/contracts.py`)
Defines interfaces and data contracts between components.

### Configuration (`shared/config/`)
Capability flags, YAML schemas, and hardware profiles.

## Module Organization

### AI Pipeline (`modules/ai_pipeline/`)
- **FastBrain** - Markov chain + Huffman compression
- **SLM** - Style-shaping small language model  
- **LLM** - Full LLM bridge (local GGUF or API)
- **Postprocessing** - Response ranking and safety

### Personality System (`modules/personality_system/`)
- **Emotion Engine** - Mood/style/state system
- **Memory Manager** - Short-term and episodic memory
- **Reaction Mapper** - Personality-driven responses

### Desktop Companion (`modules/desktop_companion/`)
- **Avatar Controller** - 2D/3D rendering
- **Shimeji Physics** - Desktop overlay behavior
- **Speech System** - Voice input/output
- **Terminal Interface** - Command-line interaction

### Community Features (`modules/community_features/`)
- **Plugin Loader** - Community mod API
- **Quiz Solver** - Automated quiz assistance
- **Browser Integration** - Web interaction tools

## Communication Patterns

### Event-Driven Architecture
All modules communicate through the central EventBus:

```python
# Example: Emotion change event
event_bus.emit("emotion_changed", {
    "new_emotion": "playful",
    "trigger": "user_joke",
    "intensity": 0.8
})
```

### Capability Gateway
All system actions pass through permission checks:

```python
# File access requires permission
gateway.check_permission("filesystem", "read", path)
```

## Startup Sequence

1. **Logging initialization**
2. **Configuration validation**
3. **Hardware detection**
4. **Capability flag setting**
5. **Subsystem bootstrap**
6. **Event loop start**

## Import Discipline

Modules only import "downward":
- `core/` never imports from feature modules
- `config/` imports nothing from the project
- Cross-module communication goes through `EventBus`

## Performance Strategy

### Dynamic Model Loading
- Load/unload models based on usage patterns
- Never keep heavy models idle
- FastBrain stays loaded at all times

### Memory Management
- Vector stores for semantic memory
- Episodic memory with decay
- FastBrain pattern cache

## Security Architecture

### Permission System
Category-based permissions with scope + risk levels:
- `filesystem` - File access operations
- `display` - Wallpaper, overlay, cursor
- `system` - Sleep, shutdown, monitor control
- `browser` - Tab manipulation (extension only)
- `network` - Web search and API calls
- `audio` - Microphone and sound
- `automation` - Keyboard/mouse control

### Safety Features
- Cooldowns and rate limits
- Kill switch for automation
- Session-based permissions
- Explicit confirmation for dangerous actions

## Related Documentation

- [[event-system]] - EventBus implementation details
- [[capability-system]] - Feature flag management
- [[security-model]] - Permission and safety systems
- [[performance-strategy]] - Optimization techniques
