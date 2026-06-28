---
title: "Kitsu Desktop AI"
sdk: "docker"
app_file: "r.py"
---

# Kitsu Desktop AI

Local-first desktop AI companion (Python backend + Tauri/Rust frontend).

## What it does
- Runs fully on your machine (no required cloud).
- Modular, event-driven runtime (EventBus + modules).
- Tiered responses: **reflex/fast** → **SLM (small local model)** → **LLM (fallback/heavier)** with **Judge** validation.
- Permission-gated desktop integration layer.

## Quick Start

### First run
```bash
python r.py --first-run
```

### Start normally
```bash
python r.py
```

### Useful flags
```bash
python r.py --debug
python r.py --status
```

## Repository layout (where to look)
- **Runtime / AI pipeline (Python)**: `application/`
- **Domain logic (policies, state, rules, memory concepts, etc.)**: `domain/`
- **Integrations/services (LLM, storage, logging, sandbox, etc.)**: `infrastructure/`
- **Desktop frontend (Tauri)**: `src-tauri/`
- **Assets (models, images, screenshots, sounds, etc.)**: `assets/`
- **Config & data**: `data/`

## Architecture at a glance (modern runtime)

Input is normalized then routed through the AI pipeline:

**Input → InputMux → EventBus → InputManager → (reflex / SLM / LLM) → Judge → Response → UI**

### High-level diagram

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   User Input   │───▶│   InputMux   │───▶│   EventBus     │───▶│ InputManager │
│   (Text/Speech) │    │ (Sanity Layer)│    │   (Pub/Sub)    │    │ (Coordinator) │
└─────────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
                                                                   │
                                                                   ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│  Response      │◀───│  ChatApp     │◀───│  RESPONSE_READY │◀───│  AI Pipeline  │
│   Display      │    │   (Main UI)  │    │    (Event)      │    │ (SLM/LLM/etc)│
└─────────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
```

## Modern runtime layers

### 1) InputMux (normalization / classification)
- File: `application/modules/input_mux.py`
- Responsibilities:
  - Normalize and clean incoming text
  - Classify input type (text/speech/command)
  - Attach metadata (confidence/type)

### 2) EventBus (pub/sub decoupling)
- File: `application/core/event_bus.py`
- Responsibilities:
  - Async pub/sub between modules
  - Error isolation + handling
  - Response lifecycle / duplicate prevention

### 3) InputManager (pipeline coordinator)
- File: `application/modules/input_manager.py`
- Responsibilities:
  - Route normalized input to the right tier/module
  - Coordinate fallback behavior
  - Manage the response lifecycle

### 4) ChatApp (UI entry point)
- File: `application/main.py` (and related launcher pathway)
- Responsibilities:
  - Create request context(s)
  - Start runtime/event loop
  - Display formatted responses

## AI processing pipeline (tiered + Judge validation)

Typical flow:

```
RAW_INPUT → preprocess → route → judge → response
```

### Runtime tiers
- **reflex**: fast cached/template responses
- **local_model (SLM)**: small local model generation
- **fallback_model (LLM)**: heavier fallback generation

### Judge validation
All generated responses pass through a Judge module that evaluates:
- **In-character** (matches persona)
- **Coherent** (logical/consistent)
- **Factually safe** (avoids harmful content)

## Module system (how modules plug in)

Modern modules are event-driven and typically:
- implement an async event handler
- subscribe to events via EventBus
- are imported/registered during startup

Pattern (conceptual):
```python
# Auto-import modules to register subscribers
import application.modules.preprocess
import application.modules.router
import application.modules.reflex
import application.modules.slm
import application.modules.llm
import application.modules.memory
import application.modules.input_mux
import application.modules.input_manager
```

## Configuration

Relevant config areas:
- `data/config/modern_config.json` (modern module settings)
- `data/config/system_config.json` (capabilities/system)
- `data/config/user_profile.json` (user preferences)
- `data/config/personality.json` (persona)
- `data/config/permissions.json` (security/permissions)

Example shape (event/pipeline, conceptual):
```json
{
  "event_system": {
    "bus_type": "kitsu.core.event_bus",
    "max_subscribers": 100,
    "timeout_ms": 5000
  },
  "pipeline": {
    "tiers": ["fast_brain", "slm", "llm"],
    "judge_validation": true,
    "behavior_gating": true
  }
}
```

## User Guide (text mode)

### Basic interaction

Examples (commands begin with `/`):

```
🦊 You: hello
Kitsu: I am a kitsu fox with vibe 0.10,0.50,0.20... You said: hello.

🦊 You: /help
Kitsu: Available commands:
  help    - Show this help message
  status  - Show system status
  quit    - Exit the application
```

### Commands

- `/help` — show available commands
- `/status` — display system status
- `/quit` or `/exit` — exit application
- `/mood <mood>` — change current mood
- `/style <style>` — change expression style

Example:
```
🦊 You: /mood flirty
*switches to flirty mood*
Kitsu:  Hey there~ How can I help you today? 😉

🦊 You: /status
Kitsu: System Status:
  Modules: 8 registered
  Legacy OK: True
  Engine OK: True
  Overall OK: True
```

### Input types
- **Text**: normal chat
- **Commands**: system commands starting with `/`

### Advanced behavior

#### Behavior gating
Kitsu may ignore/respond differently based on:
- input content
- current mood
- conversation context
- user preferences

#### Emotion system
Kitsu maintains an emotional state that affects responses:
- emotions decay over time
- multiple emotions can stack
- user input influences emotional changes
- personality settings govern emotion thresholds

#### Multi-modal (future)
Designed to support speech input (STT), avatar/gestures, uploads, and images.

## Troubleshooting

### Common issues
- **App does not respond**
  - run with `python r.py --debug`
  - check module load + event routing logs
- **LLM tier fails**
  - verify provider/model configuration under `data/config/`
  - verify model files under `assets/models/` and/or `data/models/`
- **Generic/flat responses**
  - try changing mood/style
  - check personality configuration
  - ensure models are loaded
- **Memory not working**
  - verify `data/memory/` exists and is writable
  - check memory configuration

### Debug workflow
```bash
python r.py --debug
```

### Reset configuration / first-run wizard
```bash
python r.py --first-run
```

## Security

Security policy highlights (local-first):
- Data is stored locally under `data/`.
- Dangerous actions require explicit permission (via the permission model/config).
- Optional subsystems are designed to degrade gracefully.

Supported security update cadence (as documented in `docs/SECURITY.md`):
- 5.1.x: supported
- 5.0.x: not supported
- 4.0.x: supported
- < 4.0: not supported

For vulnerability reporting, follow the project’s security policy doc.

## Performance / requirements

- **Minimum**: Python 3.8+, ~4GB RAM, ~2GB free disk
- **Recommended**: Python 3.10+, ~8GB RAM, ~5GB free disk, optional GPU

Tips:
- use appropriate model for hardware
- enable/disable features depending on needs
- monitor with `/status`
- adjust temperature for response variety

## Development (where to extend)

### Adding a new module
- create a module under `application/modules/`
- implement event handler(s)
- ensure it is imported/registered during startup

Conceptual pattern:
```python
from application.core.event_bus import bus
from application.core.context import RequestContext

async def handle_custom_event(ctx: RequestContext):
    await bus.emit("CUSTOM_RESPONSE", ctx)

bus.subscribe("CUSTOM_EVENT", handle_custom_event)
```

## Docs consolidation note

This repository keeps most documentation in a single place: this **README.md**.


