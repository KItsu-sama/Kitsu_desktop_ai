---
tags: [development, onboarding, setup, guide]
aliases: ["Getting Started", "Developer Guide", "Setup Guide"]
project: Kitsu Desktop AI
type: guide
created: 2026-04-27
modified: 2026-04-27
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

```
project-root/
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
### 1. The Event Bus
All communication happens via `kitsu.core.event_bus`.
- **Rule**: Never call another module directly.
- **Rule**: Only emit `RESPONSE_READY` if you are the designated response path.

### 2. Request Context
Every request is an instance of `RequestContext`. It carries all state. If you need to pass data between modules, add a field to this dataclass.

<<<<<<< HEAD
### 1. Understanding the Architecture

Before diving into code, read these key documents:

- [[project-overview]] - High-level system understanding
- [[system-architecture]] - Detailed system design
- [[critical-systems-architecture]] - Safety and stability systems
- [[ai-pipeline]] - AI processing flow
- [[development-workflow]] - Coding guidelines

### 2. Modern 4-Layer Architecture

Kitsu uses a **modern 4-layer architecture**:

```
ServiceContainer → ModuleRegistry → LifecycleManager → RuntimeOrchestrator
```

**Key Concepts**:
- **ServiceContainer**: Dependency injection and service management
- **ModuleRegistry**: Module lifecycle and dependency tracking
- **LifecycleManager**: Phased startup with graceful degradation
- **RuntimeOrchestrator**: Event-driven coordination

**Startup Phases**:
1. **Phase 0** - Core Services (logger, config, container)
2. **Phase 1** - Communication (event_bus, message_bus)
3. **Phase 2** - Runtime Control (orchestrator, registry, lifecycle)
4. **Phase 3** - Monitoring (health_monitor, performance_manager)
5. **Phase 4** - Cognition (memory, emotion, judge, router, slm, llm)
6. **Phase 5** - Shell Systems (desktop_pet, wallpaper, cursor, voice)

### 3. Setting Up Your Development Environment

#### IDE Configuration
Install these VS Code extensions:
- Python
- Rust
- Tauri
- Obsidian (for documentation)

#### Documentation Setup
1. Install Obsidian
2. Open the `docs/` folder as an Obsidian vault
3. Enable community plugins for better navigation

### 3. Running the Application

#### Modern Architecture (Recommended)
```bash
# Start with modern launcher (recommended)
python r.py

# Or with specific profile
python r.py --profile balanced

# Safe mode for development
python r.py --safe
```

#### Legacy Mode (Fallback)
```bash
# Direct legacy launcher (fallback)
python runtime/launcher.py

# Development mode
python runtime/launcher.py --dev
```

#### Tauri Development
```bash
# Start with Tauri frontend
npm run tauri dev
```

### 4. Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/test_ai_pipeline.py

# Run with coverage
python -m pytest --cov=runtime tests/

# Test modern architecture
python -m pytest tests/test_modern_architecture.py
```

## Key Concepts

### 1. Modern 4-Layer Architecture

The system runs on a **modern 4-layer architecture**:

**ServiceContainer (Dependency Injection)**
- Automatic dependency resolution
- Constructor injection with circular dependency detection
- Service lifetime management

**ModuleRegistry (Module Management)**
- Centralized module registration
- Dependency validation
- State tracking (CREATED → INITIALIZING → RUNNING → DEGRADED → STOPPED)

**LifecycleManager (Orchestration)**
- Phased startup with graceful degradation
- Health monitoring and automatic recovery
- Resource-aware module management

**RuntimeOrchestrator (Main Loop)**
- Event-driven coordination
- State machine integration
- Cross-system communication

### 2. Critical Stability Systems

Kitsu includes comprehensive safety and stability systems:

**Capability Permissions System**
- Safety gating for dangerous operations
- Risk assessment (High/Medium/Low)
- Permission levels: DENIED, PROMPT, TEMPORARY, GRANTED
- Audit logging for all operations

**Resource-Aware Controller**
- Dynamic tier switching: LLM → SLM → REFLEX
- Student laptop optimization with automatic adaptation
- Battery and thermal awareness
- Performance monitoring and degradation

**State Machine**
- 7 behavior states: ACTIVE, IDLE, SLEEPY, FOCUSED, PLAYFUL, OVERLOADED, LOW_POWER
- Resource-aware transitions based on system conditions
- Smooth state changes with history tracking

**Tool Grounding**
- Hallucination prevention through tool verification
- Model decides → Tool verifies → Response generated
- Confidence scoring based on verification success

**Failure Recovery**
- Automatic detection and recovery from failures
- Circuit breaker patterns to prevent cascading failures
- Health monitoring with comprehensive logging

### 3. Legacy Compatibility

The system maintains **full backward compatibility**:
- **Legacy Compatibility Layer** (`runtime/legacy_compat.py`)
- **Adapter Pattern** for legacy modules
- **Graceful Migration Path** from legacy to modern architecture

### 4. Capability Tiers and Resource Management

The system adapts to hardware capabilities:

**Hardware Profiles**:
- **Ultra Low** - FastBrain only (CPU-only laptops)
- **Balanced** - FastBrain + SLM (mid-range laptops)
- **Full** - All features including LLM (high-end workstations)

**Resource Adaptation**:
- Automatic tier switching based on system resources
- Battery and thermal awareness
- Student laptop optimization
- Graceful degradation under load

### 5. Event-Driven Architecture

All modules communicate through the central EventBus:

```python
# Emit an event
event_bus.emit("emotion_changed", data)

# Listen for events
@event_bus.on("user_input")
def handle_input(data):
    # Process input
```

### 6. Permission System

All system actions require permissions:

```python
# Check permission before action
if gateway.check_permission("filesystem", "read", path):
    # Perform file operation
```

**Permission Levels**:
- **DENIED**: Never allowed
- **PROMPT**: Ask user each time
- **TEMPORARY**: Granted for limited duration (auto-expire)
- **GRANTED**: Permanent permission

## Coding Guidelines

### 1. Modern Architecture Principles

**4-Layer Separation of Concerns**:
- ServiceContainer handles dependency injection only
- ModuleRegistry manages module lifecycle and dependencies
- LifecycleManager orchestrates startup/shutdown phases
- RuntimeOrchestrator coordinates runtime behavior

**Interface-Driven Design**:
- All modules implement standardized lifecycle interfaces
- Capability-based feature detection
- Graceful degradation with null implementations

**Resource-Aware Operation**:
- Automatic tier switching based on system resources
- Battery and thermal awareness
- Student laptop optimization

**Safety First**:
- Capability sandboxing for dangerous operations
- Tool grounding prevents hallucinations
- Comprehensive audit logging

### 2. Module Organization

**Modern Architecture**:
- Feature-based modules, not file-type grouping
- Clear dependency hierarchy through DI container
- Interface-driven development with standardized contracts

**Legacy Compatibility**:
- Legacy modules wrapped with compatibility adapters
- Gradual migration path from legacy to modern
- Preserve existing functionality during transition

### 3. Import Discipline

```python
# Good - clear dependency hierarchy
from runtime.service_container import ServiceContainer
from domain.capabilities import CapabilityManager
from domain.inference import ResourceController

# Bad - circular dependencies
from runtime.legacy_compat import LegacyModuleAdapter
from runtime.runtime_orchestrator import RuntimeOrchestrator
```

### 4. Error Handling

```python
# Use proper error handling with modern architecture
try:
    result = await process_input(user_input)
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    await handle_failure(e)
    return ErrorResponse(str(e))
```

### 5. Documentation

Every module must have:
- Overview documentation with architecture integration
- API documentation with interface contracts
- Usage examples showing modern patterns
- Bidirectional links to related systems

## Common Development Tasks

### 1. Adding a New Critical System

1. Create system in appropriate `domain/` subdirectory
2. Implement required interfaces from `domain/contracts/`
3. Register with ServiceContainer in modern launcher
4. Add startup phase in LifecycleManager
5. Write tests for integration with 4-layer architecture
6. Update documentation

### 2. Adding New AI Layer

1. Create provider in `domain/ai/`
2. Implement standardized AI provider interfaces
3. Register with ResourceController for tier management
4. Add configuration in `shared/config/`
5. Write tests in `tests/`
6. Update documentation

### 3. Adding Desktop Features

1. Create module in `interfaces/desktop/`
2. Implement permission checks via capability system
3. Add UI components if needed
4. Register with modern architecture
5. Update system architecture docs

### 4. Extending Personality System

1. Modify modules in `domain/personality/`
2. Update emotion configuration
3. Add new personality traits
4. Test integration with state machine
5. Document changes

### 5. Migrating Legacy Modules

1. Create compatibility adapter in `runtime/legacy_compat.py`
2. Implement modern interfaces from `domain/contracts/`
3. Register with ModuleRegistry
4. Test with both legacy and modern launchers
5. Update migration documentation

## Testing Strategy

### 1. Modern Architecture Testing

**Unit Tests**:
- Test individual components in isolation
- Mock dependencies using ServiceContainer
- Focus on business logic and interface contracts

**Integration Tests**:
- Test 4-layer architecture integration
- Verify module dependencies and lifecycle
- Test startup phases and graceful degradation

**System Tests**:
- Test complete modern launcher startup
- Verify critical systems integration
- Test resource adaptation and state transitions

### 2. Legacy Compatibility Testing

**Compatibility Tests**:
- Test legacy module adapters
- Verify legacy launcher still works
- Test migration path from legacy to modern

**Regression Tests**:
- Ensure existing functionality preserved
- Test both modern and legacy entry points
- Verify configuration compatibility

### 3. Performance Tests

- Test AI pipeline performance with resource controller
- Memory usage validation across tiers
- Response time measurement under different loads
- Battery usage optimization testing

## Debugging

### 1. Modern Architecture Debugging

```python
import logging
logger = logging.getLogger(__name__)

# Debug ServiceContainer
logger.debug(f"Registered services: {container.services}")

# Debug ModuleRegistry states
logger.info(f"Module states: {registry.get_all_states()}")

# Debug LifecycleManager phases
logger.debug(f"Current phase: {lifecycle.current_phase}")
```

### 2. Development Tools

- Use VS Code debugger for Python
- Rust debugger for Tauri backend
- Browser dev tools for frontend
- Modern architecture dashboard for system monitoring

### 3. Common Issues

**Modern Architecture**:
- Dependency injection failures → Check ServiceContainer registration
- Module startup failures → Check ModuleRegistry dependencies
- Lifecycle issues → Check phase order in LifecycleManager

**Legacy Compatibility**:
- Import errors → Check legacy adapter mappings
- Permission denied → Verify capability system integration
- Model loading failures → Check resource controller configuration

**Resource Management**:
- Tier switching issues → Check ResourceController metrics
- Battery drain → Verify energy budget system
- Performance problems → Check state machine transitions

## Contributing Guidelines

### 1. Code Review Process

- All changes require PR review
- Two reviewers for core changes
- Security review for permission changes
- Architecture review for 4-layer changes

### 2. Documentation Requirements

- Update relevant docs for architecture changes
- Add links to new code and systems
- Update API documentation for new interfaces
- Document migration path for legacy changes

### 3. Testing Requirements

- Add tests for new features
- Ensure all tests pass
- Performance impact assessment
- Test both modern and legacy compatibility

## Getting Help

### 1. Documentation

- Check `docs/notes/` for specific concepts
- Review `docs/architecture/` for system design
- Consult `docs/api/` for interface details
- Read `CRITICAL_SYSTEMS_ARCHITECTURE.md` for safety systems

### 2. Architecture Resources

- **Modern Architecture**: `runtime/MODULE_SUMMARY.md`
- **Critical Systems**: `CRITICAL_SYSTEMS_ARCHITECTURE.md`
- **System Design**: `SYSTEM_ARCHITECTURE.md`
- **Legacy Migration**: `runtime/legacy_compat.py`

### 3. Community

- GitHub discussions for questions
- Discord server for real-time help
- Weekly developer meetings
- Architecture review sessions

### 4. Code Examples

Check the `examples/` directory for:
- Modern architecture patterns
- Critical system implementations
- Legacy compatibility examples
- Integration patterns

## Next Steps

1. Read through the linked documentation
2. Set up your development environment
3. Run the application with modern launcher
4. Explore the 4-layer architecture
5. Understand the critical systems
6. Pick a good first issue from GitHub
7. Make your first contribution!

Welcome to the Kitsu development team! 🦊

## Quick Reference

### Essential Commands
```bash
# Modern startup
python r.py

# Legacy fallback
python runtime/launcher.py

# Development mode
python r.py --safe

# Status dashboard
python r.py --status

# Test modern architecture
python -m pytest tests/test_modern_architecture.py
```

### Key Files to Understand
- `runtime/modern_launcher.py` - Modern entry point
- `runtime/runtime_orchestrator.py` - Main coordination
- `domain/core/` - Critical systems integration
- `domain/contracts/` - Interface definitions
- `CRITICAL_SYSTEMS_ARCHITECTURE.md` - Safety systems

### Architecture Patterns
- Dependency injection through ServiceContainer
- Interface-driven development
- Phased startup with graceful degradation
- Resource-aware operation
- Capability-based security
=======
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
>>>>>>> origin/kitsu-core-refactor-9524735204188375506
