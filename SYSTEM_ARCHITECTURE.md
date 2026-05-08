# Kitsu System Architecture Documentation

## Overview
Kitsu is a local-first desktop AI companion with a **modern 4-layer architecture** that provides robust startup, lifecycle management, and resource-aware operation. The system has evolved from a simple AI assistant into a sophisticated cognitive runtime with comprehensive safety and stability systems.

---

## Table of Contents
1. [Modern 4-Layer Architecture](#modern-4-layer-architecture)
2. [Startup Flow](#startup-flow)
3. [Folder Structure & Systems](#folder-structure--systems)
4. [Core Systems](#core-systems)
5. [Data Flow](#data-flow)
6. [Critical Stability Systems](#critical-stability-systems)

---

## Modern 4-Layer Architecture

Kitsu runs on a **modern 4-layer architecture** that provides robust startup, lifecycle management, and resource-aware operation:

```
ServiceContainer → ModuleRegistry → LifecycleManager → RuntimeOrchestrator
```

### Architecture Layers

**1. ServiceContainer (Dependency Injection)**
- **Purpose**: Automatic dependency resolution and service lifetime management
- **Features**: Constructor injection with circular dependency detection
- **Key Files**: `runtime/service_container.py`

**2. ModuleRegistry (Module Management)**
- **Purpose**: Centralized module registration and dependency validation
- **Features**: State tracking (CREATED → INITIALIZING → RUNNING → DEGRADED → STOPPED)
- **Key Files**: `runtime/module_registry.py`

**3. LifecycleManager (Orchestration)**
- **Purpose**: Phased startup with graceful degradation and health monitoring
- **Features**: Resource-aware module management and automatic recovery
- **Key Files**: `runtime/lifecycle_manager.py`

**4. RuntimeOrchestrator (Main Loop)**
- **Purpose**: Event-driven coordination and cross-system communication
- **Features**: State machine integration and runtime behavior coordination
- **Key Files**: `runtime/runtime_orchestrator.py`

### Startup Phases

The modern architecture executes startup in deterministic phases:

1. **Phase 0** - Core Services (logger, config, container)
2. **Phase 1** - Communication (event_bus, message_bus)
3. **Phase 2** - Runtime Control (orchestrator, registry, lifecycle)
4. **Phase 3** - Monitoring (health_monitor, performance_manager)
5. **Phase 4** - Cognition (memory, emotion, judge, router, slm, llm)
6. **Phase 5** - Shell Systems (desktop_pet, wallpaper, cursor, voice)

### Legacy Compatibility

The system maintains **full backward compatibility** through:
- **Legacy Compatibility Layer** (`runtime/legacy_compat.py`)
- **Adapter Pattern** for legacy modules
- **Graceful Migration Path** from legacy to modern architecture

## Startup Flow

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

The legacy startup flow is preserved for compatibility:
r.py (SINGLE ENTRY POINT)
   ├─ Feature Flags:
   │  ├─ --first-run        → scripts/first_run.py
   │  ├─ --bootstrap-only   → bootstrap.py  
   │  ├─ --test-mode        → quick_start.py
   │  ├─ --status           → health dashboard
   │  └─ (default)          → full startup
   ↓
launcher.py (Phase 0: Initialization)
   ├─ CLI Parsing & Feature Flag Routing
   ├─ Logging Setup + Startup Timer
   ├─ Crash Recovery Check (data/runtime/last_crash.json)
   ├─ First-Run Check (FIRST_RUN_FLAG: data/runtime/.first_run_complete)
   │  └─ If NOT Complete → Call first_run.py
   │     ├─ Detect System Capabilities
   │     ├─ Run SetupWizard (interactive)
   │     ├─ Write Config Files (data/config/)
   │     └─ Mark first_run_complete
   ├─ Load Config Files (shared/config.py - ConfigMerger)
   │  ├─ defaults.yaml (Kitsu defaults)
   │  ├─ system_config.json (User system settings)
   │  ├─ profile.json (Hardware profile)
   │  └─ CLI overrides (highest priority)
   ├─ Hardware Profile Detection
   ├─ Capability Flags Lock (Read-only after this)
   └─ BuildAppContainer (Dependency Injection)
   
   ↓
bootstrap.py (Phase 1: Container Setup)
   ├─ Create ServiceContainer (DI)
   ├─ Register Core Services
   │  ├─ MessageBus (Event system)
   │  ├─ ClockService (Time management)
   │  ├─ HealthMonitor (System health + dashboard)
   │  ├─ PerformanceManager (Resource management)
   │  └─ AI Providers (FastBrain, SLM, LLM)
   ├─ Register Domain Services
   │  ├─ EmotionEngine (Personality system)
   │  ├─ MemoryManager (Long-term learning)
   │  └─ InputManager (User interaction handling)
   └─ Return AppContainer
   
   ↓
main.py (Phase 2: Runtime Startup)
   ├─ Start All Modules (Module Registry)
   ├─ Start KitsuEngine
   ├─ Connect Event Subscriptions
   └─ Run Orchestrator Event Loop
   
   ↓
orchestrator.py (Phase 3: Main Event Loop)
   ├─ Listen for Events (User Input, System Events)
   ├─ Route to Personality Engine
   ├─ Generate Response
   ├─ Update Emotion State
   └─ Send to UI/Avatar
```

### Key Decision Points

**First-Run Flow:**
```python
if not FIRST_RUN_FLAG.exists():
    # User hasn't set up Kitsu yet
    run_first_run()  # Interactive setup wizard
    _mark_first_run_complete()
else:
    # Existing config - load and continue
    load_system_config()
    load_profile()
```

**Safe Mode Fallback:**
```python
if crash_detected() and crash_count > THRESHOLD:
    # Degrade to ultra_low profile (CPU only)
    profile = select_profile("ultra_low")
elif --safe flag:
    profile = select_profile("ultra_low")
else:
    # Auto-detect based on hardware
    profile = detect_hardware_profile()
```

---

## Folder Structure & Systems

### 📂 `scripts/` - Setup & Initialization
**Purpose:** Bootstrap scripts that run before the main application.

| File | Purpose |
|------|---------|
| `first_run.py` | **First-time setup wizard** - Detects system capabilities, runs interactive setup, writes initial config files |
| `setup_wizard.py` | Interactive CLI for feature selection (audio, GPU, display) |
| `quick_start.py` | Fast initialization for development/testing |
| `quick_start.bat` / `quick_start.sh` | Platform-specific launch helpers |
| `fast_brain_trainer.py` | Trains the FastBrain Markov model from conversation history |

**How First Run Works:**
1. `launcher.py` checks for `data/runtime/.first_run_complete`
2. If missing → calls `first_run.py`
3. Calls `detect_system_info()` to check GPU, audio, platform
4. Optionally runs `SetupWizard` for user choices
5. Writes config to `data/config/` (system_config.json, feature_config.yaml, etc.)
6. Creates directory structure in `data/` folder
7. Sets `FIRST_RUN_FLAG` to mark complete

---

### 📂 `runtime/` - Core Application Engine
**Purpose:** Application startup, configuration management, event system, and main orchestrator.

| File | Purpose |
|------|---------|
| **`launcher.py`** | **Phase 0: Main entry point** - Handles CLI parsing, first-run check, config loading, hardware detection, builds DI container |
| **`main.py`** | Alternative/legacy entry point - Duplicates launcher.py logic |
| **`kitsu_launcher.py`** | Modern launcher variant with module registry integration |
| **`bootstrap.py`** | **Phase 1: Container setup** - Creates AppContainer with all services, registers singletons (MessageBus, HealthMonitor, etc.) |
| **`orchestrator.py`** | **Phase 3: Main event loop** - Receives events, routes to personality engine, manages module lifecycle |
| **`container.py`** | Dependency injection container (DIContainer) - Manages service registration, resolution, and lifetime |
| **`bus.py`** | MessageBus/EventBus - Unified pub/sub system for events and request/response messaging |
| **`application.py`** | High-level application facade - Coordinates between modules |
| **`engine.py`** | KitsuEngine - AI inference pipeline coordinator (FastBrain → SLM → LLM) |
| **`behavior_engine.py`** | Attention & behavior state machine |
| **`clocks.py`** | ClockService - Time tracking and tick management for all systems |
| **`health.py`** | HealthMonitor - Tracks module health, detects failures, triggers recovery |
| **`performance_manager.py`** | Resource manager - Monitors memory/CPU, unloads models, manages tier degradation |
| **`system_monitor.py`** | System metrics - Tracks OS-level resource usage |
| **`module_registry.py`** | Registry of all loadable modules - Tracks startup order and dependencies |
| **`runtime_config.py`** | Configuration merger - Combines defaults.yaml + system_config.json + profile overrides |
| **`profiles.py`** | Hardware profiles (ultra_low, balanced, full) - Maps hardware → capability flags |
| **`lifecycle.py`** | Module lifecycle state machine (stopped → starting → running → stopping) |
| **`policy_router.py`** | Intent classification router - Determines which AI model to use |
| **`events.py`** | Event definitions - InputReceived, ResponseReady, EmotionChanged, etc. |
| **`strip_controller.py`** | LED strip animation controller |
| **`idle_manager.py`** | Handles idle state detection and transitions |
| **`kitsu_identity.py`** | Kitsu self-model and identity management |

**Key Files Explained:**

**`r.py` - SINGLE ENTRY POINT**

```python
# Feature flag routing
if "--bootstrap-only" in sys.argv:
    launcher.bootstrap()
elif "--test-mode" in sys.argv:
    launcher.quick_start()
elif "--status" in sys.argv:
    launcher.show_status()
else:
    launcher.full_startup()  # default
```

**`launcher.py` - Core Launcher Methods**
```python
# Phase 0 Startup (with feature flags)
1. parse_args() → Get CLI flags + feature routing
2. _setup_logging() → Initialize logger + start timer
3. _check_crash_recovery() → Load last_crash.json
4. _check_first_run() → Need setup?
   └─ YES: run_first_run() (from scripts/)
5. load_config() → ConfigMerger.load() (shared/config.py)
   ├─ defaults.yaml (base)
   ├─ system_config.json (user)
   ├─ profile.json (hardware)
   └─ CLI overrides (highest)
6. select_profile() → Choose hardware profile
7. validate_config() → Check config validity
8. build_runtime_config() → Merge all configs
9. build_app_container() → DI setup (→ bootstrap.py)
10. orchestrator.startup() → Start modules
11. kitsu_engine.startup() → Start AI system
12. orchestrator.run() → Main loop + health monitoring
```

**`bootstrap.py` - Dependency Injection**
```python
# Phase 1: Create container with:
- MessageBus (event routing)
- ClockService (time coordination)
- HealthMonitor (failure detection)
- PerformanceManager (resource management)
- AI Providers (FastBrain, SLM, LLM)
- EmotionEngine (personality system)
- MemoryManager (learning system)
- AvatarController (visual rendering)
```

**`orchestrator.py` - Main Event Loop**
```python
# Phase 3: Runtime loop
While running:
  1. Wait for event (InputReceived, IdleStateChanged, etc.)
  2. Route to ReactionMapper
  3. EmotionEngine processes → emotion state change
  4. GenerateResponse (FastBrain → SLM → LLM as needed)
  5. EmotionController modulates output
  6. Send to avatar/UI
  7. Update MemoryManager (learning)
```

---

### 📂 `domain/` - Core Business Logic
**Purpose:** Domain models and business rules for personality, emotions, memory, and AI reasoning.

| File | Purpose |
|------|---------|
| **`unified_manager.py`** | Facade coordinating all domain subsystems |
| **`unified_events.py`** | Domain-level event definitions |
| **`policy.py`** | Policy engine - Rules for when to use different AI models |
| **`capabilities.py`** | Tracks system capabilities (GPU available, audio support, etc.) |
| **`triggers.py`** | Trigger system - Keyword-based emotional responses |
| **`rules.py`** | Business rules engine - Constraints and guardrails |
| **`builder.py`** | Builder pattern for complex domain objects |
| **`rate_limit.py`** | Rate limiter - Prevents response flooding |
| **`loop_guard.py`** | Prevents infinite loops in reasoning |
| **`energy.py`** | Energy/fatigue system - Limits inference activity |
| **`inertia.py`** | Momentum system - Personality stability over time |
| **`vector.py`** | Vector operations for embeddings/similarity |
| **`presets.py`** | Preset emotion configurations |

**Subdirectories:**

#### `domain/personality/` - Emotion & Personality System
```
Core emotion processing pipeline
User Input → ReactionMapper → EmotionEngine → PersonalityMapper → Output
```

| File | Purpose |
|------|---------|
| **`emotion_engine.py`** | Main emotion coordinator - Stack management, decay, intensity |
| **`emotion_controller.py`** | High-level API for emotion manipulation |
| **`emotion_stack_manager.py`** | Stack operations (push, pop, decay, resist) |
| **`personality_mapper.py`** | Emotion state → personality traits mapping |
| **`kitsu_self.py`** | Core personality identity and traits |
| **`reaction_mapper.py`** | User interaction → emotion mapping |
| **`emotional_triggers.py`** | Configuration-based trigger detection |
| **`trigger_manager.py`** | Trigger lifecycle and cooldown |
| **`memory_manager.py`** | Long-term learning and pattern storage |

**Personality Model (3-Layer):**
```
1. mood (4 states): behave, mean, flirty, protective
2. style (7 states): chaotic, sweet, cold, direct, sarcastic, playful, eerie
3. state (6 states): normal, tsundere, yandere, kuudere, dere, chaotic
   → 4 × 7 × 6 = 1,260 personality combinations
```

**Emotion Stack Example:**
```python
# User does something
event = UserInteraction(action="headpat")

# Maps to emotion
reaction = ReactionMapper.map(event)  # → EmotionReaction(emotion="happy", intensity=0.8)

# Pushed to stack
emotion_engine.push(reaction)  # Stack: [happy(0.8), ...]

# Over time, decays
emotion_engine.decay()  # happy(0.8) → happy(0.7) → happy(0.6) → ...

# Can be resistant (sticky emotions)
if emotion.resistant:
    decay_rate *= 0.5  # Decays slower
```

#### `domain/ai/` - AI Provider System
| File | Purpose |
|------|---------|
| `fast_brain/provider.py` | FastBrain provider (Markov + Huffman tree) - instant responses |
| `slm/provider.py` | Small Language Model provider - personality + reasoning |
| `llm/provider.py` | Large Language Model provider - complex queries |

#### `domain/memory/` - Learning System
| File | Purpose |
|------|---------|
| `short_term.py` | Session-only memory (cleared on restart) |
| `long_term.py` | Persistent learning (stored in data/learning/) |
| `episodic.py` | Event-based memory (what happened when) |
| `semantic.py` | Knowledge memory (facts, preferences) |

#### `domain/interaction/` - User Input
| File | Purpose |
|------|---------|
| `input_manager.py` | Central input handler - Routes user inputs to emotion system |
| `gesture_parser.py` | Parses mouse gestures (headpat, poke, etc.) |
| `text_parser.py` | NLP preprocessing for text input |

#### `domain/contracts/` - Interface Definitions
| File | Purpose |
|------|---------|
| `contracts.py` | Abstract base classes - AIProvider, MemoryStore, SystemGateway, etc. |
| `interfaces.py` | Modern interface definitions with dependency inversion |

---

### 📂 `app/` - Application Layer
**Purpose:** CLI commands, user management, and adapter patterns.

| File | Purpose |
|------|---------|
| `__init__.py` | Package initialization |
| `user_manager.py` | User profile management (multiple Kitsu instances per system) |
| `adapters.py` | Adapter patterns for external systems |

#### `app/adapters/` - System Integrations
| File | Purpose |
|------|---------|
| `browser_adapter.py` | Browser integration (read web context) |
| `system_adapter.py` | OS-level integrations |
| `ollama_adapter.py` | Ollama local LLM integration |

#### `app/commands/` - CLI Commands
| File | Purpose |
|------|---------|
| `start.py` | Start Kitsu desktop |
| `config.py` | Configuration management CLI |
| `reset.py` | Reset to defaults |

---

### 📂 `interfaces/` - UI & Display Layers
**Purpose:** Rendering, user-facing input/output, and desktop integration.

#### `interfaces/desktop/` - Desktop Application
| File | Purpose |
|------|---------|
| `gateway.py` | Permission/security gateway for system access |
| `permission_manager.py` | RBAC and permission checking |

#### `interfaces/desktop/avatar/` - Visual Rendering
| File | Purpose |
|------|---------|
| `controller.py` | Main avatar controller - Directs animation/expression |
| `animator.py` | Animation state machine |
| `expression_set.py` | Available facial expressions |
| `gesture.py` | Body gestures and poses |

#### `interfaces/overlay/` - Always-On Display
| File | Purpose |
|------|---------|
| `overlay_window.py` | Persistent overlay rendering |
| `hotspot_manager.py` | Interactive regions on screen |

#### `interfaces/tauri/` - Desktop Framework
| File | Purpose |
|------|---------|
| `command_bridge.py` | Rust ↔ Python communication layer |
| `event_bridge.py` | Event forwarding to Tauri |

#### `interfaces/ui/` - Web UI & Dashboard
| File               | Purpose                                                                        |
|--------------------|--------------------------------------------------------------------------------|
| **`dashboard.py`** | **Health monitoring dashboard** - Terminal UI with module status, personality, AI tier, memory usage |
| `api_server.py`    | REST API for UI communication                                                  |

#### `interfaces/api/` - External APIs
| File | Purpose |
|------|---------|
| `rest_api.py` | HTTP endpoints for integration |
| `websocket_api.py` | Real-time WebSocket communication |

#### `interfaces/learning/` - Analytics UI
| File | Purpose |
|------|---------|
| `stats_panel.py` | Display learning statistics |

---

### 📂 `infra/` - Infrastructure & Services
**Purpose:** Low-level utilities, LLM integration, storage, and system operations.

| File | Purpose |
|------|---------|
| `smart_retrieval.py` | Smart caching and retrieval optimization |

#### `infra/llm/` - AI Model Integration
| File | Purpose |
|------|---------|
| `llm_fallback_generator.py` | Fallback LLM if primary fails |
| `model_loader.py` | Load/unload models dynamically |
| `prompt_builder.py` | Construct system prompts |
| `token_counter.py` | Count tokens before inference (prevent overflow) |

#### `infra/logging/` - Logging System
| File | Purpose |
|------|---------|
| `structured_logger.py` | Structured logging with JSON output |
| `file_rotator.py` | Rotate log files (data/logs/) |
| `performance_logger.py` | Track performance metrics |

#### `infra/multimodal/` - Multi-Modal Processing
| File | Purpose |
|------|---------|
| `image_processor.py` | Image → description via vision model |
| `audio_processor.py` | Audio → text via speech recognition |

#### `infra/sandbox/` - Isolated Execution
| File | Purpose |
|------|---------|
| `executor.py` | Safe code execution environment |
| `restricted_env.py` | Restricted Python environment for user code |

#### `infra/storage/` - Data Persistence
| File | Purpose |
|------|---------|
| `file_store.py` | File-based storage backend |
| `sqlite_store.py` | SQLite database backend |

#### `infra/stores/` - Store Implementations
| File | Purpose |
|------|---------|
| `memory_store.py` | In-memory cache layer |
| `persistence_layer.py` | Persistent storage abstraction |
| `vector_store.py` | Vector embeddings storage |

#### `infra/system/` - System Operations
| File | Purpose |
|------|---------|
| `process_manager.py` | Subprocess management |
| `resource_monitor.py` | RAM/CPU monitoring |
| `network_manager.py` | Network connectivity checks |

---

### 📂 `features/` - Pluggable Features
**Purpose:** Optional features that can be loaded/unloaded dynamically.

| File | Purpose |
|------|---------|
| `loader.py` | Plugin loader and manager |
| `plugin_api.py` | Plugin interface - How to create custom features |

#### `features/browser_integration/` - Web Integration
| File | Purpose |
|------|---------|
| `tab_monitor.py` | Track browser tabs and URL changes |
| `context_extractor.py` | Extract page content for context |

#### `features/quiz_solver/` - Educational
| File | Purpose |
|------|---------|
| `quiz_detector.py` | Detect quiz interfaces |
| `answer_solver.py` | Find and submit answers |

#### `features/community_features/` - User-Created Features
| File | Purpose |
|------|---------|
| `feature_marketplace.py` | Browse and install community features |

---

### 📂 `shared/` - Shared Utilities
**Purpose:** Cross-cutting concerns and shared utilities.

| File | Purpose |
|------|---------|
| **`config.py`** | **Standardized config loading** - ConfigMerger class with priority order |
| **`unified_config.py`** | Central configuration management (legacy) |
| **`config_loader.py`** | YAML/JSON configuration file loading (legacy) |
| **`defaults.yaml`** | Default configuration values |
| `capability_flags.py` | Feature flags for capability management |
| `complexity.py` | Complexity scoring for prompts |
| `file_security.py` | Safe file read/write with validation |
| `logging.py` | Logging utilities |
| `mood_tracker.py` | Mood state tracking |
| `retention.py` | Data retention policies |
| `sass_generator.py` | CSS-in-Python for UI |
| `self_model.py` | Kitsu's self-representation model |
| `session_logger.py` | Session-specific logging |
| `signals.py` | Signal system for callbacks |
| `snapshot.py` | State snapshots for debugging |
| `tiers.py` | Tier definitions (ultra_low, balanced, full) |
| `transitions.py` | State transition helpers |
| `triggers.json` | Trigger definitions |
| `ul_templates.json` | Micro-interaction templates |
| `personality_config.py` | Personality system configuration |
| `model_dict.json` | Available models manifest |
| `factual_exceptions.json` | Override incorrect AI responses |
| `mappings.py` | Entity/intent mappings |
| `budgets.py` | Token and resource budgets |

---

### 📂 `data/` - Runtime Data & User State
**Purpose:** Persistent storage for user data, configuration, and runtime state.

```
data/
├── config/
│   ├── system_config.json        # User-specific settings
│   ├── feature_config.yaml       # Enabled features
│   ├── personality_config.json   # Personality state
│   └── profiles/                 # Custom hardware profiles
├── runtime/
│   ├── .first_run_complete       # Flag file (first setup done)
│   ├── crash.log                 # Crash dump for recovery
│   ├── last_crash.json           # Crash recovery data (timestamp, error, recovered)
│   └── metrics.json              # Performance metrics
├── learning/
│   ├── fast_brain.pkl            # Trained Markov model
│   ├── user_preferences.json     # Learned user patterns
│   └── interaction_log.db        # Interaction history
├── memory/
│   ├── short_term.json           # Session memory
│   ├── long_term/                # Persistent memories
│   │   ├── episodic.db           # "What happened when"
│   │   ├── semantic.db           # "Facts and knowledge"
│   │   └── procedural.db         # "How to do things"
│   └── profiles/                 # User profiles
├── models/
│   ├── local/                    # Downloaded models
│   │   ├── mistral-7b/
│   │   ├── neural-chat-7b/
│   │   └── ...
│   └── cache/                    # Model inference cache
├── lora/
│   ├── kitsu-personality.lora    # Fine-tuning data for personality
│   └── user-preferences.lora     # Fine-tuning for user patterns
├── logs/
│   ├── app.log                   # General application log
│   ├── performance.log           # Performance metrics
│   ├── error.log                 # Error log (rotated)
│   └── 2024-04-30.log           # Daily logs
└── screenshots/                  # User interaction recordings
```

---

### 📂 `docs/` - Documentation
**Purpose:** Architecture docs, guides, API documentation, and design notes.

| File | Purpose |
|------|---------|
| `SECURITY.md` | Security model and threat analysis |

#### `docs/architecture/` - Design Docs
| File | Purpose |
|------|---------|
| `personality_model.md` | Emotion system design |
| `ai_pipeline.md` | Inference pipeline architecture |
| `memory_system.md` | Learning and memory design |

#### `docs/guides/` - User Guides
| File | Purpose |
|------|---------|
| `setup.md` | Installation and first-run |
| `customization.md` | Personalizing Kitsu |
| `troubleshooting.md` | Common issues and fixes |

---

### 📂 `vendor/` - Third-Party Libraries
**Purpose:** Bundled third-party code (if needed for offline support).

---

### 📂 `src-tauri/` - Desktop Frontend
**Purpose:** Rust-based desktop application using Tauri framework.

```
src-tauri/
├── src/
│   ├── main.rs              # Tauri entry point
│   ├── commands.rs          # Exposed Rust → Python commands
│   └── window_manager.rs    # Window lifecycle
└── tauri.conf.json          # Tauri configuration
```

---

### 📂 `tests/` - Test Suite
**Purpose:** Unit tests, integration tests, and test utilities.

```
tests/
├── unit/
│   ├── test_emotion_engine.py
│   ├── test_fast_brain.py
│   └── test_memory_manager.py
├── integration/
│   ├── test_startup_flow.py
│   ├── test_emotion_pipeline.py
│   └── test_end_to_end.py
└── fixtures/
    ├── mock_config.json
    └── sample_responses.json
```

---

## Core Systems

### 1. Startup System (`launcher.py` → `bootstrap.py` → `orchestrator.py`)

**12-Step Startup Process:**

```
┌─────────────────────────────────────────────────────────┐
│ Phase 0: Initialization (launcher.py)                  │
├─────────────────────────────────────────────────────────┤
│ 1. Parse CLI arguments                                  │
│ 2. Setup logging                                        │
│ 3. Check first-run flag                                 │
│    └─ If missing: run_first_run()                       │
│ 4. Load defaults.yaml                                   │
│ 5. Load system_config.json                              │
│ 6. Detect hardware profile (GPU/CPU/Memory)             │
│ 7. Merge configs (priority: CLI > system > defaults)    │
│ 8. Validate configuration                               │
│ 9. Check crash history (fallback to safe mode)          │
│ 10. Build RuntimeConfig object                          │
└─────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Bootstrap (bootstrap.py)                       │
├─────────────────────────────────────────────────────────┤
│ 11. Create DIContainer                                  │
│ 12. Register core services:                             │
│     - MessageBus (event routing)                        │
│     - ClockService (time management)                    │
│     - HealthMonitor (failure detection)                 │
│     - PerformanceManager (resource limits)              │
│     - AI Providers (FastBrain, SLM, LLM)                │
│     - EmotionEngine (personality)                       │
│     - MemoryManager (learning)                          │
│ 13. Create AppContainer                                 │
└─────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 2: Runtime Startup (main.py / kitsu_launcher.py)  │
├─────────────────────────────────────────────────────────┤
│ 14. Get all modules from ModuleRegistry                 │
│ 15. Start each module in dependency order               │
│ 16. Start KitsuEngine                                   │
│ 17. Connect event subscriptions                         │
│ 18. Start SystemMonitor                                 │
│ 19. Mark startup complete                               │
└─────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 3: Main Event Loop (orchestrator.py)              │
├─────────────────────────────────────────────────────────┤
│ 20. await orchestrator.run()                            │
│     While running:                                      │
│       - Listen for events (bus.subscribe)               │
│       - Route InputReceived to InputManager              │
│       - Call EmotionEngine (emotion state change)        │
│       - Generate response (FastBrain → SLM → LLM)       │
│       - Modulate via EmotionController                  │
│       - Send to AvatarController                        │
│       - Update MemoryManager (learning)                 │
│       - Publish ResponseReady event                     │
│ 21. Health checks every N seconds                       │
│ 22. Graceful shutdown on SIGTERM                        │
└─────────────────────────────────────────────────────────┘
```

---

### 2. Personality & Emotion System (`domain/personality/`)

**Emotion Processing Pipeline:**

```
User Input (text/gesture/idle event)
  ↓
InputManager.handle()
  ↓
ReactionMapper.map(input) → EmotionReaction
  ↓
EmotionEngine.process_reaction()
  ├─ Check triggers from data/triggers.json
  ├─ Push to emotion stack
  ├─ Apply decay/resistance calculations
  └─ Update current emotion
  ↓
PersonalityMapper.map_emotion_to_personality()
  ├─ Emotion intensity → mood (behave/mean/flirty/protective)
  ├─ Emotion type → style (chaotic/sweet/cold/direct/sarcastic/playful/eerie)
  └─ Emotion history → state (normal/tsundere/yandere/kuudere/dere/chaotic)
  ↓
Generate response with personality filter
  ├─ FastBrain (instant) or
  ├─ SLM (styled) or
  └─ LLM (complex)
  ↓
EmotionController.modulate_response()
  ├─ Adjust response tone based on current mood/style/state
  ├─ Add appropriate emojis/expressions
  └─ Adjust speaking rate/pitch
  ↓
AvatarController.render()
  ├─ Set avatar expression
  ├─ Play animation
  └─ Send to UI
  ↓
MemoryManager.learn()
  └─ Add interaction to episodic memory
  └─ Update semantic preferences
  └─ Feed back to FastBrain training
```

**Example:**
```
User hovers mouse → InputReceived(gesture="hover")
  ↓
ReactionMapper.map() → EmotionReaction(emotion="curious", intensity=0.4)
  ↓
emotion_engine.push(reaction)
  ├─ Stack: [curious(0.4), neutral(0.7)]
  └─ Decay old emotions
  ↓
PersonalityMapper.map()
  ├─ curious(0.4) → mood="behave", style="playful", state="normal"
  ↓
Generate response: "Ooh, what's that?"  [tone: playful behave]
  ↓
EmotionController adds: "😺 Ooh, what's that?"
  ↓
Avatar tilts head + plays "curious" animation
```

---

### 3. AI Inference Pipeline (`engine.py`)

**Tier System (Auto-Degrades on Resource Pressure):**

```
FastBrain
  │
  ├─ Is input in training data? (Markov lookup)
  │  ├─ YES → Return cached response (0ms, 0 VRAM)
  │  └─ NO ↓
  │
  └─ SLM Layer (lightweight reasoning)
      │
      ├─ Is query simple? (policy_router classification)
      │  ├─ YES → Run on SLM (100-200ms, 4GB VRAM)
      │  └─ NO ↓
      │
      └─ LLM Layer (deep reasoning)
          │
          └─ Complex query → Run on LLM (1-5s, 8-12GB VRAM)
```

**Resource Gating:**
```python
if memory_available < 2GB:
    # Skip LLM, use SLM only
    tier_cap = "slm"
elif memory_available < 4GB:
    # Unload LLM during SLM inference
    auto_unload = True
elif cpu_usage > 90%:
    # Reduce batch size, increase timeout
    batch_size = 1
    inference_timeout = 10s
```

---

### 4. Event Bus System (`bus.py`)

**Pub/Sub + Request/Response Hybrid:**

```
# Event Publishing (fire-and-forget)
bus.publish(InputReceived(text="hello"))
  └─ All subscribers receive immediately (async-safe)

# Request/Response (RPC-style)
result = await bus.request("ai.infer", {"prompt": "hello"})
  └─ Waits for handler response (timeout: 30s default)

# Subscriber Example
def on_input(event: InputReceived):
    print(f"Got: {event.text}")

bus.subscribe(InputReceived, on_input)
```

---

### 5. Memory & Learning System (`domain/memory/`)

**Four Memory Types:**

```
1. Short-Term (Session)
   - Cleared on restart
   - Context window for current conversation
   - Stored in: data/memory/short_term.json

2. Long-Term (Persistent)
   - Survives app restart
   - Stored in: data/memory/long_term/

3. Episodic (What Happened)
   - "On 2024-04-30 at 14:30, user said X"
   - Stored in: data/memory/long_term/episodic.db

4. Semantic (Facts & Knowledge)
   - "User likes cats", "User prefers puns"
   - Learned from interactions
   - Stored in: data/memory/long_term/semantic.db

Example Flow:
User: "I like cats"
  ↓
Input → Personality system → Response: "Meow! 🐱"
  ↓
MemoryManager.learn()
  ├─ Add to episodic: "2024-04-30 14:30: User mentioned liking cats"
  ├─ Add to semantic: {preference: "likes cats", confidence: 0.9}
  └─ Update FastBrain training data
  ↓
Next time user is mentioned:
  → Personality pulls: "user likes cats" → adjusts personality
  → FastBrain suggests: "Meow~" (common response)
```

---

### 6. Configuration System (`shared/config.py`)

**Standardized Config Loading with ConfigMerger:**

```python
# shared/config.py - Single source of truth
class Config:
    @classmethod
    def load(cls, cli_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        return ConfigMerger([
            "shared/defaults.yaml",           # 1. Defaults
            "data/config/system_config.json", # 2. User settings  
            "data/config/profile.json",       # 3. Hardware profile
            CLI_ARGS                          # 4. CLI overrides (highest)
        ]).merge()
```

**Config Merge Priority:**

```
1. Default Values (shared/defaults.yaml)
   ↓ OVERRIDE
2. User System Config (data/config/system_config.json)
   ↓ OVERRIDE
3. Hardware Profile (data/config/profile.json)
   ↓ OVERRIDE
4. CLI Arguments (--profile, --safe, --debug, etc.)
   ↓ RESULT
RuntimeConfig.merged (final configuration)
```

**Key Features:**

- **ConfigMerger class** handles deep merging of dictionaries
- **Priority order** ensures CLI args override everything
- **Validation** ensures required config sections exist
- **Backward compatibility** with existing config loaders
- **Error handling** for missing or malformed config files

**Key Config Files:**

1. **`defaults.yaml`** - Shipping defaults

   ```yaml
   runtime:
     model: mistral-7b
     inference_timeout: 30s
     batch_size: 8
   ```

2. **`system_config.json`** - User customization
   ```json
   {
     "runtime": {"model": "neural-chat-7b"},
     "completed_setup": true
   }
   ```

3. **Hardware Profiles** - Tier-based:

   ```text
   ultra_low    → CPU only, small models
   balanced     → GPU preferred, medium models
   full         → GPU required, all features
   ```

---

### 7. Health Monitoring & Dashboard (`runtime/health.py` + `interfaces/ui/dashboard.py`)

**Real-time Health Monitoring:**

```python
# runtime/health.py - HealthMonitor.get_status()
{
    "personality": "playful/happy (0.8)",
    "ai_tier": "SLM (4GB VRAM used)",
    "memory_usage": "6.2/16GB (39%)",
    "modules": "18/20 running",
    "resources": "CPU: 23% │ GPU: 67%",
    "module_details": {
        "orchestrator": {"ok": True, "latency_ms": 2.1},
        "emotion_engine": {"ok": True, "latency_ms": 1.8},
        "llm_provider": {"ok": False, "detail": "OOM"}
    }
}
```

**Terminal Dashboard Output:**
```
┌─ Kitsu Health Dashboard ──────────────────────┐
│ 🟢 Personality: playful/happy (0.8)           │
│ 🟡 AI Tier: SLM (4GB VRAM used)              │
│ 🟢 Modules: 18/20 running                    │
│ Memory: 6.2/16GB (39%) │ CPU: 23% │ GPU: 67% │
├─ Module Status ────────────────────────────┤
│ 🟢 orchestrator: running (2.1ms)            │
│ 🟢 emotion_engine: running (1.8ms)          │
│ 🔴 llm_provider: failed (OOM)               │
└──────────────────────────────────────────────┘
```

**Features:**

- **Real-time monitoring** of all modules via health checks
- **Visual indicators** (🟢🟡🔴) for quick status assessment
- **Performance metrics** (latency, memory, CPU/GPU usage)
- **CLI access**: `python r.py --status`
- **WebSocket integration** for web dashboard
- **Crash recovery tracking** with `last_crash.json`

---

## Critical Stability Systems

Kitsu includes comprehensive safety and stability systems that ensure reliable operation:

### 1. Capability Permissions System (`domain/capabilities/`)

**Purpose**: Prevent dangerous operations by requiring explicit permission.

**Key Components**:
- `CapabilityManager` - Central permission controller
- `Capability` enum - Defines dangerous operations (file access, desktop control, etc.)
- `PermissionLevel` - DENIED, PROMPT, TEMPORARY, GRANTED
- `AuditEntry` - Comprehensive audit logging

**Features**:
- Permission prompts with scope limits
- Temporary grants with expiration
- Risk assessment and auto-grant rules
- Comprehensive audit trail

### 2. Resource-Aware Inference Controller (`domain/inference/`)

**Purpose**: Dynamically adapts to system resources for student laptop compatibility.

**Key Components**:
- `ResourceController` - System resource monitor
- `InferenceTier` - LLM → SLM → REFLEX
- `RenderTier` - 3D → 2D → CHIBI → MINIMAL
- `SystemMetrics` - CPU, memory, battery, thermal monitoring

**Features**:
- Automatic tier switching based on resources
- Battery and thermal awareness
- Performance monitoring and optimization
- Student laptop optimization

### 3. State Machine Layer (`domain/state/`)

**Purpose**: Provides structured behavior states for consistent, efficient operation.

**Key Components**:
- `BehaviorStateMachine` - State transition controller
- `BehaviorState` - ACTIVE, IDLE, SLEEPY, FOCUSED, PLAYFUL, OVERLOADED, LOW_POWER
- `StateConfig` - Resource allocation per state
- `StateTransitionRule` - Conditional state changes

**Features**:
- Seven behavior states with different resource profiles
- Smooth transitions and conditional rules
- Resource-aware state selection
- History tracking and analytics

### 4. Tool Grounding System (`domain/grounding/`)

**Purpose**: The REAL hallucination solution - models don't invent, tools verify.

**Key Components**:
- `ToolGroundingSystem` - Central grounding controller
- `GroundingType` - FILE_SYSTEM, SYSTEM_INFO, NETWORK, etc.
- `VerificationStatus` - VERIFIED, FAILED, PARTIAL, DENIED
- `GroundedResponse` - Response generated from verified data

**Process Flow**:
1. Model decides what information is needed
2. Tool verifies and retrieves actual data
3. Response generated from tool output
4. Confidence score based on verification success

### 5. Failure Recovery System (`domain/core/failure_recovery.py`)

**Purpose**: Automatic detection, recovery, and prevention of system failures.

**Features**:
- Rule-based recovery strategies
- Health monitoring with circuit breaker patterns
- Comprehensive logging and analytics
- Automatic degradation and escalation

### 6. Energy Budget System (`shared/budgets.py`)

**Purpose**: Balances performance with battery life for mobile efficiency.

**Key Components**:
- `BudgetManager` - Central budget controller
- `BudgetType` - LATENCY, ENERGY, CPU, MEMORY, NETWORK, ANIMATION
- `EnergyBudget` - Specialized energy management
- `BudgetState` - Current usage and status

**Features**:
- Real-time budget monitoring
- Automatic budget adjustments
- Energy-aware resource allocation
- Performance optimization

## System Integration

The `KitsuOrchestrator` (`domain/core/`) coordinates all critical systems:

### Integration Flow
1. **User Input** → Attention Engine → State Machine
2. **State Changes** → Resource Controller → Budget Manager  
3. **Budget Alerts** → Resource Controller → Inference/Render Tiers
4. **Capability Requests** → Safety Check → Permission Grant/Deny
5. **Model Responses** → Tool Grounding → Verified Output

### Key Integrations
- **Attention → State Machine**: Emotional triggers update behavior state
- **Resource → State Machine**: CPU/memory/battery affect state transitions
- **Budget → Resource**: Energy limits force lower inference/render tiers
- **State → Budget**: LOW_POWER state enables energy saving
- **Capability → Safety**: All dangerous operations require permission

## Data Flow

### Complete Request → Response Flow

```
┌────────────────────────────────────────────────────────────┐
│ 1. INPUT                                                   │
│    User types: "Hello Kitsu!"                              │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 2. MESSAGE BUS                                             │
│    bus.publish(InputReceived(text="Hello Kitsu!"))         │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 3. INPUT MANAGER                                           │
│    InputManager.handle(event)                              │
│    ├─ Parse text ("Hello" = greeting)                      │
│    └─ Detect intent (greeting, question, complaint, etc.)  │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 4. REACTION MAPPER                                         │
│    ReactionMapper.map(intent)                              │
│    ├─ Look up data/triggers.json                           │
│    └─ Return: EmotionReaction(emotion="happy", intensity=0.6)
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 5. EMOTION ENGINE                                          │
│    EmotionEngine.process_reaction(reaction)                │
│    ├─ Push to emotion_stack                                │
│    ├─ Apply decay_rate                                     │
│    └─ Update current_emotion = happy(0.6)                  │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 6. PERSONALITY MAPPER                                      │
│    PersonalityMapper.map(emotion_state)                    │
│    ├─ happy(0.6) + history → mood="behave"                 │
│    ├─ + context → style="sweet"                            │
│    └─ + time_of_day → state="normal"                       │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 7. POLICY ROUTER                                           │
│    PolicyRouter.classify(input="Hello")                    │
│    ├─ Is input simple? YES                                 │
│    └─ → Use FastBrain first                                │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 8. INFERENCE TIER 1: FASTBRAIN                             │
│    FastBrain.generate(input)                               │
│    ├─ Lookup: "Hello" → Markov chain                       │
│    ├─ Found: {response: "Hey there!", prob: 0.9}           │
│    └─ Return response                                      │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 9. EMOTION MODULATION                                      │
│    EmotionController.modulate(response, emotion_state)     │
│    ├─ Current emotion: happy(0.6), behave, sweet           │
│    ├─ Adjust tone: capitalize, add emoji                   │
│    └─ Result: "Hey there! 😊"                              │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 10. MEMORY UPDATE                                          │
│    MemoryManager.learn(input, response, emotion_state)     │
│    ├─ Add to episodic: timestamp + interaction             │
│    ├─ Update semantic: "User greets at $TIME_OF_DAY"       │
│    └─ Feed to FastBrain: train new Markov transition       │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 11. RENDERING                                              │
│    AvatarController.render(response, emotion_state)        │
│    ├─ Set expression: happy_smile                          │
│    ├─ Play animation: wave hand                            │
│    ├─ Text-to-speech: "Hey there! 😊"                      │
│    └─ Display in overlay                                   │
└────────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────────┐
│ 12. OUTPUT                                                 │
│    User sees: Kitsu waves + says "Hey there! 😊"            │
└────────────────────────────────────────────────────────────┘
```

---

## Quick Reference

### File Locations
- **Entry Point**: `r.py` → `runtime/launcher.py`
- **First Run**: `scripts/first_run.py` (called if needed)
- **Configuration**: `data/config/` + `shared/defaults.yaml`
- **Main Loop**: `runtime/orchestrator.py`
- **Personality**: `domain/personality/emotion_engine.py`
- **Memory**: `domain/memory/` (episodic, semantic, short-term, long-term)
- **Rendering**: `interfaces/desktop/avatar/controller.py`
- **Events**: `runtime/bus.py` (MessageBus)

### Key Decision Trees
**"Should I use SLM or LLM?"**
→ `runtime/policy_router.py` classifies intent

**"How is Kitsu feeling?"**
→ `domain/personality/emotion_engine.py` emotion_stack + decay

**"What did the user teach Kitsu?"**
→ `domain/memory/long_term/` (episodic + semantic)

**"Why is response slow?"**
→ `runtime/performance_manager.py` checks tier + resources

---

## Debugging Guide

### "First run isn't completing"
1. Check: Does `data/runtime/.first_run_complete` exist?
2. If not: `scripts/first_run.py` is being skipped or failing
3. Check logs: `data/logs/error.log`

### "Personality isn't changing"
1. Check: `data/memory/long_term/semantic.db` — Does it have user preferences?
2. Check: `domain/personality/emotional_triggers.py` — Are triggers loaded?
3. Check: `data/config/personality_config.json` — Is personality enabled?

### "Responses are slow"
1. Check: `runtime/performance_manager.py` - What tier are we at?
2. Check: `data/runtime/metrics.json` - Memory/CPU usage?
3Fallback: `runtime/policy_router.py` - Should we degrade tier?

### "Model won't load"
1. Check: `data/models/local/` — Does model exist?
2. Check: `infra/llm/model_loader.py` — Load errors?
3. Fallback: `infra/llm/llm_fallback_generator.py` — Use fallback?

