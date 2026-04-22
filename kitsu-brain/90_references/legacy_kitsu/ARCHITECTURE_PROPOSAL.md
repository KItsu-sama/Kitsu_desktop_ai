# Kitsu Architecture Proposal

## Acknowledgment of Rules

✅ **ACKNOWLEDGED:**
- `core/` MUST NEVER write files or train models
- `engine/` = logic, decision making, behavior selection
- `manager/` = lifecycle, memory, state machines
- `controller/` = orchestration, routing, coordination
- `interface/` = contracts, commands, schemas, APIs
- `io/` = transport only (input/output, devices, streams)
- `data/` = data only (JSON, configs, assets) — NO CODE
- `tests/` = tests only
- `main.py` NEVER asks questions — only executes answers
- Command parsing → `controller/command_router.py`

---

## Proposed Folder Structure

```
Kitsu/
├── core/                    # Identity, personality, emotion models ONLY
│   ├── __init__.py
│   ├── personality/
│   │   ├── __init__.py
│   │   ├── kitsu_identity.py      # Core identity traits (static + evolving)
│   │   ├── emotion_model.py       # Emotion state model (pure data structures)
│   │   └── reaction_definitions.py # Reaction mappings (blush, pout, glare, etc.)
│   └── config/
│       ├── __init__.py
│       └── personality_config.py  # VALID_MOODS, VALID_STYLES, mappings
│
├── engine/                  # Logic, decision making, behavior selection
│   ├── __init__.py
│   ├── behavior_engine.py   # Decides what Kitsu should do
│   ├── response_engine.py    # Generates responses based on mood/style
│   └── reaction_engine.py   # Maps triggers to reactions
│
├── manager/                 # Lifecycle, memory, state machines
│   ├── __init__.py
│   ├── memory_manager.py    # Short/episodic/long-term memory
│   ├── emotion_manager.py   # Emotion state lifecycle (decay, transitions)
│   ├── idle_manager.py      # Idle behavior (5min check-in, 10min sleep)
│   └── state_manager.py     # Overall state machine coordination
│
├── controller/              # Orchestration, routing, coordination
│   ├── __init__.py
│   ├── command_router.py    # Command parsing and routing
│   ├── event_controller.py  # OS event handling (clicks, installs, etc.)
│   ├── plugin_controller.py # Plugin system coordination
│   └── lifecycle_controller.py # Startup/shutdown orchestration
│
├── interface/               # Contracts, commands, schemas, APIs
│   ├── __init__.py
│   ├── command_schema.py   # Command definitions and validation
│   ├── event_schema.py      # Event type definitions
│   ├── plugin_api.py        # Plugin interface contracts
│   └── response_formatter.py # Response formatting contracts
│
├── io/                      # Transport only (input/output, devices, streams)
│   ├── __init__.py
│   ├── input_handler.py    # Raw input collection (text, voice, events)
│   ├── output_handler.py   # Raw output delivery (text, voice, visual hooks)
│   ├── voice_io.py          # Audio I/O transport
│   └── system_events.py     # OS event capture (read-only)
│
├── data/                    # Data only (JSON, configs, assets) — NO CODE
│   ├── config/
│   │   ├── personality.json
│   │   ├── user_profile.json
│   │   └── permissions.json
│   ├── runtime/
│   │   ├── memory.json
│   │   ├── emotion_state.json
│   │   └── kitsu_state.json
│   └── assets/
│       └── (existing asset files)
│
├── tests/                   # Tests only
│   ├── __init__.py
│   ├── test_core/
│   ├── test_engine/
│   ├── test_manager/
│   └── test_controller/
│
├── launcher.py              # First-run logic, config generation
├── main.py                  # Runtime entry point (executes only, never asks)
└── requirements.txt
```

---

## Key Classes Per Folder

### `core/personality/` (Identity & Personality Models)

**`kitsu_identity.py`**
- `KitsuIdentity`: Core identity traits (static + evolving)
- Stores: traits, reflection values, mode preferences
- NO file I/O, NO training
- Pure domain model

**`emotion_model.py`**
- `EmotionState`: Data structure for emotion state
- `EmotionStack`: Stack-based emotion tracking
- Pure data models, no logic

**`reaction_definitions.py`**
- `ReactionMap`: Maps triggers → reactions (blush, pout, glare, giggle, hide, jump, fluster, annoyed)
- Reaction metadata (intensity, duration, visual hints)

**`core/config/personality_config.py`**
- `VALID_MOODS = {"behave", "mean", "flirty", "protective"}`
- `VALID_STYLES = {"chaotic", "sweet", "cold", "direct", "sarcastic", "playful", "eerie"}`
- Emotion → mood/style mappings
- Style rules (word limits, emoji rules)

---

### `engine/` (Logic & Decision Making)

**`behavior_engine.py`**
- `BehaviorEngine`: Decides what Kitsu should do
- Input: current state, user input, context
- Output: action decision (respond, react, idle, sleep)
- Logic only, no state management

**`response_engine.py`**
- `ResponseEngine`: Generates responses based on mood/style
- Applies style rules (word limits, emoji rules)
- Formats responses according to personality state
- NO LLM calls (delegates to interface)

**`reaction_engine.py`**
- `ReactionEngine`: Maps triggers to reactions
- Determines appropriate reaction based on emotion state
- Returns reaction metadata (not visual rendering)

---

### `manager/` (Lifecycle & State)

**`memory_manager.py`**
- `MemoryManager`: Short/episodic/long-term memory
- Memory storage, retrieval, compression
- File I/O for memory persistence (only manager that writes)

**`emotion_manager.py`**
- `EmotionManager`: Emotion state lifecycle
- Emotion decay, transitions, stack management
- Updates emotion state based on triggers
- NO file I/O (delegates to memory_manager for persistence)

**`idle_manager.py`**
- `IdleManager`: Idle behavior coordination
- 5 min: check-in behavior
- 10 min: sleep mode (memory compression + animation)
- Tracks idle time, triggers behaviors

**`state_manager.py`**
- `StateManager`: Overall state machine coordination
- Coordinates between managers
- State transitions, validation

---

### `controller/` (Orchestration)

**`command_router.py`**
- `CommandRouter`: Parses commands (`/mood`, `/stats`, etc.)
- Routes to appropriate handlers
- Permission validation
- Returns structured results

**`event_controller.py`**
- `EventController`: OS event handling
- Processes: clicks, installs, deletes, notifications
- Can ignore events selectively
- Routes events to appropriate handlers

**`plugin_controller.py`**
- `PluginController`: Plugin system coordination
- Loads plugins, manages plugin lifecycle
- Plugin permission gating

**`lifecycle_controller.py`**
- `LifecycleController`: Startup/shutdown orchestration
- Coordinates initialization order
- Manages background tasks

---

### `interface/` (Contracts & Schemas)

**`command_schema.py`**
- Command type definitions
- Command validation schemas
- Permission requirements per command

**`event_schema.py`**
- Event type definitions
- Event validation schemas

**`plugin_api.py`**
- Plugin interface contracts
- Hook definitions
- Plugin permission model

**`response_formatter.py`**
- Response formatting contracts
- Format specifications for different output types

---

### `io/` (Transport Only)

**`input_handler.py`**
- `InputHandler`: Raw input collection
- Text input, voice input, system events
- NO interpretation, just transport

**`output_handler.py`**
- `OutputHandler`: Raw output delivery
- Text output, voice output, visual hooks (events only, no rendering)
- NO formatting logic

**`voice_io.py`**
- `VoiceIO`: Audio I/O transport
- Mic input, speaker output
- NO voice recognition (that's interface layer)

**`system_events.py`**
- `SystemEventCapture`: OS event capture (read-only)
- Monitors: clicks, installs, deletes, notifications
- NO interpretation, just event capture

---

## Data Flow

```
User Input
  ↓
io/input_handler.py          (raw input)
  ↓
interface/command_schema.py   (parse meaning)
  ↓
controller/command_router.py (route)
  ↓
engine/behavior_engine.py    (decide action)
  ↓
manager/emotion_manager.py   (update state)
  ↓
engine/response_engine.py    (generate response)
  ↓
interface/response_formatter.py (format)
  ↓
io/output_handler.py         (deliver output)
```

---

## Implementation Order

1. **Core Layer** (models only)
   - `core/config/personality_config.py` - Constants and mappings
   - `core/personality/kitsu_identity.py` - Identity model
   - `core/personality/emotion_model.py` - Emotion data structures
   - `core/personality/reaction_definitions.py` - Reaction mappings

2. **Manager Layer** (state & lifecycle)
   - `manager/emotion_manager.py` - Emotion lifecycle
   - `manager/memory_manager.py` - Memory system
   - `manager/idle_manager.py` - Idle behavior
   - `manager/state_manager.py` - State coordination

3. **Engine Layer** (logic)
   - `engine/behavior_engine.py` - Decision logic
   - `engine/response_engine.py` - Response generation
   - `engine/reaction_engine.py` - Reaction logic

4. **Interface Layer** (contracts)
   - `interface/command_schema.py` - Command definitions
   - `interface/event_schema.py` - Event definitions
   - `interface/response_formatter.py` - Format contracts

5. **Controller Layer** (orchestration)
   - `controller/command_router.py` - Command routing
   - `controller/event_controller.py` - Event handling
   - `controller/lifecycle_controller.py` - Lifecycle

6. **IO Layer** (transport)
   - `io/input_handler.py` - Input transport
   - `io/output_handler.py` - Output transport
   - `io/system_events.py` - Event capture

---

## Boundary Enforcement

- **core/**: NO file I/O, NO training, pure models only
- **engine/**: Logic only, no state persistence
- **manager/**: State & lifecycle, only memory_manager writes files
- **controller/**: Orchestration only, delegates to engine/manager
- **interface/**: Contracts only, no implementation
- **io/**: Transport only, no interpretation
- **data/**: JSON/config files only, NO Python code
