# Kitsu — local desktop AI companion

Kitsu (kitsu) is a local-first desktop AI companion with a Shimeji-style presence,
a layered emotion system, and a self-learning fast-response brain. She runs on any
device from a weak CPU-only laptop up to a high-end workstation, adapting her
capability profile to the hardware she runs on.

---

## What kitsu is

- A **desktop overlay companion** — lives on your screen, reacts to what you do
- A **local AI** — no cloud required; all inference runs on your machine
- A **self-learning system** — her fast-brain learns your patterns over time,
  responding to common inputs instantly without ever touching a model
- A **personality, not a chatbot** — emotion state shapes every response at every tier

---

## AI ARCHITECTURE

## Modern 4-Layer Architecture

Kitsu runs on a **modern 4-layer architecture** that provides robust startup, lifecycle management, and resource-aware operation:

```
ServiceContainer → ModuleRegistry → LifecycleManager → RuntimeOrchestrator
```

### Architecture Layers

**1. ServiceContainer (Dependency Injection)**
- Automatic dependency resolution
- Constructor injection with circular dependency detection
- Service lifetime management

**2. ModuleRegistry (Module Management)**
- Centralized module registration
- Dependency validation
- State tracking (CREATED → INITIALIZING → RUNNING → DEGRADED → STOPPED)

**3. LifecycleManager (Orchestration)**
- Phased startup with graceful degradation
- Health monitoring and automatic recovery
- Resource-aware module management

**4. RuntimeOrchestrator (Main Loop)**
- Event-driven coordination
- State machine integration
- Cross-system communication

### Startup Phases

1. **Phase 0** - Core Services (logger, config, container)
2. **Phase 1** - Communication (event_bus, message_bus)
3. **Phase 2** - Runtime Control (orchestrator, registry, lifecycle)
4. **Phase 3** - Monitoring (health_monitor, performance_manager)
5. **Phase 4** - Cognition (memory, emotion, judge, router, slm, llm)
6. **Phase 5** - Shell Systems (desktop_pet, wallpaper, cursor, voice)

## Legacy AI Pipeline

The original AI pipeline is preserved within the modern architecture:

```
User input
    │
    ▼
┌─────────────┐     always-on, learns from every response
│  FastBrain  │◄────────────────────────────────────────┐
│ (Markov +   │                                         │
│  Huffman)   │──► known input? respond instantly       │
└──────┬──────┘                                         │
       │ unknown                                        │
       ▼                                                │
┌─────────────┐                                         │
│ PolicyRouter│──► classify intent                      │
└──────┬──────┘                                         │
       │                                                │
  ┌────┴─────────────────┐                              │
  │                      │                              │
  ▼                      ▼                              │
┌──────┐           ┌──────────┐                         │
│ SLM  │           │   LLM    │                         │
│(fox  │           │(thinking)│                         │
│style)│           └──────────┘                         │
└──┬───┘                 │                              │
   └──────────┬──────────┘                              │
              ▼                                         │
    ┌──────────────────┐                                │
    │  EmotionEngine   │ shapes every response          │
    └────────┬─────────┘                                │
             │                                          │
             ▼                                          │
    final response ─────────────────────────────────────┘
             │          fed back into FastBrain
             ▼
         User + Avatar
```

### Brain Stack (Inference Pipeline)

**FastBrain → SLM → LLM**

#### FastBrain (Base Layer)

- **Binary + Markov Chain + Huffman Tree**
- **Handles:**
  - Common inputs (greetings, repeated phrases)
  - Spam detection
  - Instant responses (0ms)
- **Self-learning:**
  - Promotes frequent inputs via: `score = frequency × recency`
  - Feeds confirmed outputs back into itself

#### SLM (Style + Reasoning Lite)

- Shapes personality (fox-like tone)
- Handles normal conversation
- Lightweight, offline

#### LLM (Deep Reasoning)

- Used only when needed:
  - Complex queries
  - Web search
  - Analysis

### Reasoning Optimization

Pretrained models may hallucinate due to custom prompts/LoRA
**Long-term goal:**

- Custom LLM with:

  - Universal Transformers
  - Tokenizer + embeddings
  - Multi-head attention
  - Value cache
  - Looped reasoning

##  EMOTION SYSTEM

### Layers

**Mood (Primary)**

- behave, mean, flirty, protective

**Style (Expression)**

- chaotic, sweet, cold, direct, sarcastic, playful, eerie

**State (Micro-behavior)**

- normal, fox, glitch, analyst, submissive, detached

### Behavior Model

- Emotions stored in decaying stack
- Dominant emotion determines: `emotion → mood + style + state`
- **Supports:**
  - Triggers
  - Reactions
  - Personality overlays

### Special Rules

- Spam detection → adds irritation
- Unsafe combinations → auto-adjust
- Style rules control:
  - Tone
  - Length
  - Emoji usage

## ⚙️ STRIP / TIER SYSTEM

### Concept

- **Tier system** = user-facing
- **Strip system** = internal flags

### Flags (Read-only after startup)

```
USE_FAST_BRAIN
USE_SLM
USE_LLM
USE_2D / USE_3D
USE_EMOTION
USE_VOICE
USE_SYSTEM_CONTROL
USE_SHIMEJI
```

### Modes

**Ultra Low**
- FastBrain + templates only
- No LLM/SLM

**Balanced**
- SLM + prompt shaping

**Full**
- LoRA + LLM + full emotion system

### Fallback Chain
3D → 2D → SLM → FastBrain → Basic chatbot

## 🛡️ CRITICAL SYSTEMS

Kitsu includes comprehensive safety and stability systems:

### Capability Permissions System
- **Safety gating** for dangerous operations
- **Risk assessment** (High/Medium/Low)
- **Permission levels**: DENIED, PROMPT, TEMPORARY, GRANTED
- **Audit logging** for all operations

### Resource-Aware Controller
- **Dynamic tier switching**: LLM → SLM → REFLEX
- **Student laptop optimization** with automatic adaptation
- **Battery and thermal awareness**
- **Performance monitoring** and degradation

### State Machine
- **7 behavior states**: ACTIVE, IDLE, SLEEPY, FOCUSED, PLAYFUL, OVERLOADED, LOW_POWER
- **Resource-aware transitions** based on system conditions
- **Smooth state changes** with history tracking

### Tool Grounding
- **Hallucination prevention** through tool verification
- **Model decides → Tool verifies → Response generated**
- **Confidence scoring** based on verification success

### Failure Recovery
- **Automatic detection** and recovery from failures
- **Circuit breaker patterns** to prevent cascading failures
- **Health monitoring** with comprehensive logging

## 🖥️ PLATFORM ARCHITECTURE

### Core App (Tauri)
**Handles:**
- AI pipeline
- Emotion system
- VTuber rendering (2D/3D)
- Shimeji behavior
- System control
- Background / cursor

### Browser Extension (Optional)
**Handles:**
- Web interaction
- Quiz solving
- Tab manipulation

**Communication:**
- Extension ⇄ Core App (WebSocket/API)

## 🔐 PERMISSION SYSTEM

### Category-based permissions with scope + risk levels:
```
filesystem
display
system
browser
network
audio
automation
```

### Rules
- Category ON ≠ full access
- **Dangerous actions ALWAYS require confirmation:**
  - Shutdown
  - File deletion
  - Automation

### Safety Features
- Cooldowns
- Rate limits
- Kill switch (automation)
- Session-based permissions

## 💤 IDLE SYSTEM

### States
- **Active**
- **Idle** (~60s)
- **Sleep** (~5min)

### Behavior
- Idle → light animation (bored)
- Sleep → unload models

### Memory Strategy
**Keep:**
- FastBrain
- Minimal emotion state

**Unload:**
- SLM after idle
- LLM always

## 🎮 FEATURES

### Desktop Interaction
- Wallpaper control
- Cursor (fox bite effect)
- Hide/crop tabs
- Shimeji companion
- Power control (sleep/shutdown)

### AI Features
- Web search
- File interaction (permission-based)
- Real-time adaptation to user habits

### Creative Tools (Future)
- Drawing app
- Video editing with live comments

## 🧪 QUIZ SYSTEM

### Modes
- **Rush** → fastest answers
- **Normal** → human-like delay
- **Adapt** → uses tools for best score

### Learning Loop
- Stores solved questions
- Re-tests user later

**Auto-solver disabled if:**
- User score below average

**Re-enabled after:**
- 3 above-average or perfect scores

## 🛍️ COMMUNITY SYSTEM

### Supports
- Personality configs
- Visual assets (2D/3D, cursor, UI)
- Desktop behaviors
- Plugins (quiz, tools)
- Voice packs

### Restrictions
- No core AI routing modification

## ⚡ PERFORMANCE STRATEGY

### Hardware Adaptation
- **Low-end** → FastBrain only
- **Mid** → SLM
- **High** → LLM + 3D

### Model Management
- Load/unload dynamically
- Never keep heavy models idle

### Install Size Target
- Core: 10–20MB
- FastBrain: ~5MB
- Micro-SLM: 5–20MB

## 🔑 KEY DESIGN PRINCIPLES

1. **FastBrain is ALWAYS active**
2. **Heavy models are OPTIONAL and unloadable**
3. **System must work offline at install**
4. **Every feature is permission-gated**
5. **Graceful degradation is mandatory**
6. **Emotion drives personality, not logic**
7. **Extensions are untrusted (must validate)**
8. **No lag on wake (instant FastBrain response)**

---

## Project Layout

```
kitsu-desktop-ai/
├── r.py                           # Simple entry point (delegates to launcher)
├── runtime/                       # Modern 4-layer architecture
│   ├── modern_launcher.py         # Modern launcher with DI and lifecycle
│   ├── legacy_compat.py           # Legacy compatibility layer
│   ├── runtime_orchestrator.py    # Main event loop coordinator
│   ├── module_registry.py         # Module registration and state tracking
│   ├── lifecycle_manager.py       # Lifecycle orchestration
│   ├── service_container.py       # Dependency injection container
│   ├── bootstrap.py               # Legacy bootstrap (preserved)
│   ├── launcher.py                 # Legacy launcher (preserved)
│   ├── orchestrator.py             # Legacy orchestrator (preserved)
│   └── MODULE_SUMMARY.md          # Runtime documentation
├── domain/                        # Core business logic and stability systems
│   ├── core/                      # Central orchestration and contracts
│   ├── capabilities/              # Safety and permission system
│   ├── attention/                 # Attention engine for "alive" feeling
│   ├── state/                     # Behavior state machine
│   ├── inference/                 # Resource-aware AI controller
│   ├── grounding/                 # Tool grounding for hallucination prevention
│   ├── personality/               # Emotion and personality system
│   ├── ai/                        # AI providers (FastBrain, SLM, LLM)
│   ├── memory/                    # Learning and memory systems
│   └── contracts/                 # Interface definitions
├── app/                           # Application layer
│   ├── commands/                  # CLI command handlers
│   ├── adapters/                  # System integration adapters
│   └── user_manager.py            # User profile management
├── interfaces/                    # UI and display layers
│   ├── desktop/                   # Desktop application and permissions
│   ├── api/                       # REST and WebSocket APIs
│   ├── learning/                  # Analytics and learning UI
│   └── overlay/                   # Always-on display components
├── features/                      # Pluggable features
│   ├── browser_integration/        # Web integration features
│   ├── quiz_solver/               # Educational assistance
│   └── community_features/        # User-created features
├── infra/                         # Infrastructure and services
│   ├── llm/                       # AI model integration
│   ├── logging/                   # Structured logging
│   ├── multimodal/                # Multi-modal processing
│   ├── sandbox/                   # Isolated execution
│   └── storage/                   # Data persistence
├── shared/                        # Shared utilities
│   ├── config/                    # Configuration management
│   ├── constants/                 # System constants
│   ├── data/                      # Data files and schemas
│   └── budgets.py                 # Resource budget management
├── src-tauri/                     # Rust-based desktop framework
├── vendor/                        # Third-party libraries
├── scripts/                       # Setup and automation scripts
├── tests/                         # Test suites
├── assets/                        # Static resources
├── data/                          # Runtime data and user state
└── docs/                          # Documentation (Obsidian-ready)
```

## Documentation

This project uses **Obsidian-compatible documentation** with bidirectional linking between code and documentation.

### 📚 Documentation Vault
- **[[docs/README|Documentation Home]]** - Complete documentation index
- **[[docs/guides/developer-onboarding|Developer Onboarding]]** - Getting started guide
- **[[docs/architecture/system-design|System Architecture]]** - Technical architecture overview

### 🔍 Quick Links
- [[docs/kitsu/01_system|System Overview]] - Core system concepts
- [[docs/kitsu/02_core|Core Components]] - Architecture components  
- [[docs/kitsu/03_modules|Modules]] - Feature modules
- [[docs/SECURITY|Security]] - Security policies

### 🛠️ Using with Obsidian
1. Install [Obsidian](https://obsidian.md/)
2. Open the `docs/` folder as a vault
3. Enable community plugins for enhanced navigation
4. Use the graph view to explore connections between concepts

The documentation uses Obsidian's [[wikilinks]] for navigation - click any link to explore related concepts.

---

## Capability tiers

kitsu detects your hardware on first launch and selects a profile automatically.
You can override it in settings.

| Tier   | RAM    | What runs                              | Profile         |
|--------|--------|----------------------------------------|-----------------|
| Micro  | <2 GB  | FastBrain + emotion templates only     | `ultra_low`     |
| Low    | 2–4 GB | FastBrain + Micro-SLM + 2D avatar      | `low`           |
| Mid    | 4–8 GB | FastBrain + Full SLM + 2D/3D toggle    | `balanced`      |
| High   | 8+ GB  | Everything including LLM               | `full`          |

At every tier, the emotion system runs and kitsu has a personality.
The fast brain always runs. She always responds instantly.

---

## Strip system

Each profile sets a combination of capability flags:

```
USE_FAST_BRAIN      always true — cannot be disabled
USE_EMOTION         always true by default — shapes all responses
USE_2D              2D avatar renderer
USE_3D              3D VRM renderer (GPU required)
USE_SLM             small language model layer
USE_LLM             full LLM (local or API)
USE_VOICE           microphone input + TTS output
USE_SHIMEJI         chibi desktop overlay
USE_SYSTEM_CONTROL  OS-level actions (sleep, wallpaper, etc.)
```

Flags are **read-only after startup**. The system validates flag combinations
before locking — invalid combos are corrected or rejected with a clear message.

Custom strip profiles (`strip_mode: custom`) let you mix flags freely within
the validation rules. Example: 3D avatar + no LLM, or voice-only + no avatar.

---

## Startup sequence

### Modern Architecture Startup

```
r.py (Simple Entry Point)
   └── launcher.py (Legacy Compatibility)
         ├── Modern Architecture Delegation
         │     └── runtime/modern_launcher.py
         │           ├── ServiceContainer (DI)
         │           ├── ModuleRegistry
         │           ├── LifecycleManager
         │           └── RuntimeOrchestrator
         └── Legacy Fallback (if needed)
```

### 4-Layer Startup Flow

1. **ServiceContainer** creates DI container and registers core services
2. **ModuleRegistry** validates dependencies and tracks module states
3. **LifecycleManager** executes phased startup with graceful degradation
4. **RuntimeOrchestrator** starts main event loop with health monitoring

### Legacy Startup (Preserved)

```
launcher.py (Phase 0: Initialization)
   ├─ CLI Parsing & Feature Flag Routing
   ├─ Logging Setup + Startup Timer
   ├─ First-Run Check
   ├─ Config Loading (defaults.yaml + system_config.json + profile)
   ├─ Hardware Profile Detection
   ├─ Capability Flags Lock
   └─ BuildAppContainer (Dependency Injection)
   ↓
bootstrap.py (Phase 1: Container Setup)
   ├─ Create ServiceContainer
   ├─ Register Core Services
   └─ Return AppContainer
   ↓
orchestrator.py (Phase 2: Main Event Loop)
   ├─ Listen for Events
   ├─ Route to Personality Engine
   ├─ Generate Response
   └─ Update Emotion State
```

Steps 1–7 failing causes an immediate clean exit with a clear error message.
Steps 8–9 failing triggers degraded mode — kitsu still runs at a lower tier.

---

## 🚀 COMBO ARCHITECTURE

**Kitsu = Open_LLM_VTuber + Tauri + Shimeji + Desktop Local**

This is a hybrid system combining:
- **Open_LLM_VTuber**: AI personality and emotion system
- **Tauri**: Desktop app framework with Rust backend
- **Shimeji**: Desktop overlay companion physics
- **Desktop Local**: Offline-first, permission-gated system

---

## Development phases

| Phase | Directory focus              | Milestone                        |
|-------|------------------------------|----------------------------------|
| 0     | `app/`, `core/`, `config/`   | Skeleton boots, flags work       |
| 1     | `ai/fast_brain/`, `personality/` | FastBrain learns, emotion runs |
| 2     | `ui/avatar/`, `memory/`      | 2D avatar reacts to emotion      |
| 3     | `ui/shimeji/`, `system/`     | Shimeji on desktop, OS actions   |
| 4     | `ai/slm/`, `ai/llm/`         | Full intelligence layer          |
| 5     | `src-tauri/`, `modules/`     | Desktop shell + browser extension|
| 6     | `multimodal/`, training      | Voice, LoRA fine-tuning          |
| 7     | `data/mods/`, community shop | Mod ecosystem opens              |

---

## Key architectural rules

### Modern Architecture Principles

**4-Layer Separation of Concerns:**
- ServiceContainer handles dependency injection only
- ModuleRegistry manages module lifecycle and dependencies
- LifecycleManager orchestrates startup/shutdown phases
- RuntimeOrchestrator coordinates runtime behavior

**Interface-Driven Design:**
- All modules implement standardized lifecycle interfaces
- Capability-based feature detection
- Graceful degradation with null implementations

**Resource-Aware Operation:**
- Automatic tier switching based on system resources
- Battery and thermal awareness
- Student laptop optimization

**Safety First:**
- Capability sandboxing for dangerous operations
- Tool grounding prevents hallucinations
- Comprehensive audit logging

### Legacy Architecture Principles (Preserved)

**Import discipline** — modules only import "downward":
- `domain/` never imports from `app/`, `interfaces/`, or `features/`
- `shared/` imports nothing from the project
- Cross-module communication goes through event bus

**Capability gateway** — all system actions must pass through permission checks

**Data files are the mod API** — everything in `data/` is versioned JSON

**FastBrain is always hot** — even in sleep mode, the FastBrain stays loaded

**Emotion is always on** — even with no avatar, the emotion engine runs and shapes responses

**Null implementations, not flag checks** — every optional subsystem has a null implementation

---

## Permissions

kitsu requests permissions by category, not per-feature:

| Category     | Examples                          | Default |
|--------------|-----------------------------------|---------|
| filesystem   | read/open files                   | off     |
| display      | wallpaper, overlay, cursor        | on      |
| system       | sleep, shutdown, monitor off      | off     |
| browser      | tab hide/crop (extension only)    | off     |
| network      | web search                        | on      |
| audio        | microphone, sound visualizer      | off     |
| automation   | keyboard/mouse control            | off     |

Dangerous actions (shutdown, automation, mass file ops) always require
explicit confirmation with a cooldown, even if the category is enabled.
The automation category has a mandatory kill switch (hotkey to stop).

---

## Community mods

Mods live in `data/mods/`. Each mod is a directory containing:

```
my_mod/
├── manifest.json          name, version, schema_version, author
├── personality_overlay.json  emotion map overrides (optional)
├── anim_map_overlay.json     expression overrides (optional)
├── ul_templates_overlay.json template overrides (optional)
├── assets/                   sprites, wallpapers, cursors, voice packs
└── README.md
```

Mods **cannot** override core routing logic, AI pipeline, or security policy.
They can change: personality, animations, expressions, templates, visual assets,
desktop themes, cursor skins, voice packs, and UI themes.

---

## Contributing

See `docs/CONTRIBUTING.md` for code style, PR process, and testing requirements.

Every PR touching `core/` or `config/` requires two reviewers.
Every PR touching `system/gateway.py` or `system/permission_manager.py`
requires a security review note explaining why the change is safe.

---

## License

See `LICENSE`. The fast-brain, emotion system, and plugin API are open.
Model weights and Live2D/VRM assets are subject to their own licenses.