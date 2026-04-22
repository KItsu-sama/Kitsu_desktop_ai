# Kitsu Architecture — Cleaned Design

## Core Principles

```
User
 ↓
IO layer        (raw input)
 ↓
Interface       (what does this mean?)
 ↓
Engine          (what should I do?)
 ↓
Interface       (format response)
 ↓
IO layer        (output)
```

## File Responsibilities

### `launcher.py`

**MUST:**

- Resolve first-run logic BEFORE calling main.py
- Produce complete, immutable `runtime_config`
- Detect user device/platform capabilities
- Invoke SetupWizard when needed
- Install or enable selective plugins
- Generate or modify system-level configuration
- Load and validate USER_INFO
- Pass final runtime configuration to main.py

**MUST NOT:**
- Instantiate runtime subsystems
- Perform inference or training
- Modify config after main.py starts
- Depend on runtime state
- Run async runtime logic
- Start background tasks

---

### `main.py`

**MUST:**

- Accept `runtime_config` from launcher.py
- Instantiate KitsuEngine with config
- Wire async event loop
- Register lifecycle hooks (startup, shutdown)
- Start background tasks (memory autosave, emotion decay)
- Delegate to UI layer for interface

**MUST NOT:**

- Ask questions (only execute answers)
- Perform first-run detection
- Modify configuration
- Parse commands directly
- Perform training or model management

---

### `core/kitsu_engine.py`

**MUST:**

- Initialize all subsystems in dependency order
- Process input through cognition pipeline
- Execute actions and generate responses
- Manage runtime state and lifecycle

**MUST NOT:**

- Write files (delegates to subsystems)
- Train models (delegates to learning/)
- Render UI
- Load configuration

**Naming Convention:**

- `engine` = logic
- `manager` = lifecycle/state
- `controller` = orchestration

---

### `core/personality/kitsu_self.py` (Domain Layer)

**MUST:**

- Store personality traits (static + evolving)
- Provide APIs for emotion_engine, triggers
- Track emotional reflection states
- Export state dict for persistence

**MUST NOT:**

- Write files (delegates to memory_manager)
- Perform training
- Import any file I/O libraries

---

### `ui_layer/terminal.py` (UI Layer)

**MUST:**

- Display chat interface
- Capture user input
- Route commands to interface/command_router
- Display formatted responses

**MUST NOT:**

- Process logic (delegates to engine)
- Execute commands (delegates to command_router)
- Perform file I/O
- Modify configuration

---

### `interface/command_router.py` (Interface Layer)

**MUST:**

- Parse command syntax (`/mood`, `/stats`, etc.)
- Route to appropriate handlers
- Return structured results
- Validate command permissions

**MUST NOT:**

- Directly manipulate engine internals
- Render UI
- Perform file I/O

---

### `io_layer/` (Transport Layer)

**MUST:**

- Read input from devices/streams
- Write output to devices/streams
- Handle audio/video I/O
- Format data for transport

**MUST NOT:**

- Parse commands (delegates to interface/)
- Process logic (delegates to engine)
- Make decisions

---

## Data Flow

```
launcher.py
  ↓
  builds RuntimeConfig (immutable)
  ↓
  calls main.py
  ↓
  main.py builds KitsuEngine
  ↓
  KitsuEngine.initialize()
    ├─ KitsuSelf (personality/domain)
    ├─ MemoryManager (state)
    ├─ LLMInterface (executor)
    ├─ EmotionEngine (state)
    └─ MetaController (logic)
  ↓
  main.py starts UI layer
  ↓
  TerminalUI captures input
  ↓
  CommandRouter OR Engine.process_input()
  ↓
  Response back to UI
  ↓
  TerminalUI displays response
```

## First Run Flow

```
launcher.py
  ↓
  checks first_run flag
  ↓
  if first run:
    ├─ script/first_run.py
    │   ├─ check device capabilities
    │   ├─ run SetupWizard (if interactive)
    │   ├─ install selective plugins
    │   └─ write:
    │       ├─ first_run flag
    │       ├─ system_config.json
    │       ├─ user_profile.json
    │       └─ permissions.json
    ↓
  launcher.py loads & merges configs
  ↓
  runtime_config (final, frozen)
  ↓
  main.py
```

## Directory Structure (Cleaned)

```
core/
  ├─ kitsu_engine.py        # Core runtime coordinator (logic)
  ├─ personality/
  │   ├─ kitsu_self.py      # Domain: personality/identity
  │   └─ emotion_engine.py  # Manager: emotion lifecycle
  ├─ memory/
  │   └─ memory_manager.py  # Manager: memory state
  ├─ llm/
  │   └─ llm_interface.py   # Executor: LLM operations
  └─ meta/
      └─ meta_controller.py # Controller: decision orchestration

interface/
  └─ command_router.py      # Contract: command grammar

io_layer/
  ├─ terminal.py            # Transport: stdin/stdout
  ├─ voice.py               # Transport: audio I/O
  └─ avatar.py              # Transport: visual rendering

ui_layer/
  ├─ terminal.py            # UI: terminal interface
  └─ desktop.py             # UI: desktop window

data/
  ├─ runtime/               # Runtime state (JSON only)
  │   ├─ memory.json
  │   ├─ kitsu_state.json
  │   └─ runtime_manifest.json
  └─ config/                # Configuration (JSON only)
      ├─ personality.json
      ├─ user_profile.json
      └─ permissions.json

scripts/
  ├─ first_run.py           # First-run detection & setup
  └─ setup_wizard.py        # Interactive configuration
```

## Key Rules

1. **`core/` NEVER writes files or trains models**
2. **No test files outside `tests/`**
3. **`data/` never contains code**
4. **`main.py` only executes, never asks questions**
5. **Command parsing → `/interface/command_router.py`**
6. **IO = transport, Interface = contract**
7. **`launcher.py` handles ALL first-run logic**
8. **`runtime_config` is immutable after launcher**

## Command Protocol Contract

`interface/command_router.py` command handlers should always return:

- `{"success": bool, "output": str, ...optional metadata}`

Important protocol guarantees:

- Every command path returns a dict (never a raw string).
- Unknown commands and handler failures still produce a valid dict payload.
- Router supports both `DesktopController` and direct `KitsuEngine` injection for compatibility in tests and script environments.
- Optional command features that depend on desktop runtime (for example `/auto_prompt`) should fail gracefully with a clear error message instead of crashing.

## Layer Separation

| Layer | Purpose | Examples |
|-------|---------|----------|
| **Domain** | Core business logic | `KitsuSelf`, personality traits |
| **Engine** | Coordination logic | `KitsuEngine`, pipeline orchestration |
| **Manager** | Lifecycle/state | `MemoryManager`, `EmotionEngine` |
| **Controller** | Orchestration | `MetaController`, decision routing |
| **Interface** | Contracts | `CommandRouter`, API schemas |
| **IO** | Transport | `terminal.py`, audio I/O |
| **UI** | Presentation | `TerminalUI`, formatting |