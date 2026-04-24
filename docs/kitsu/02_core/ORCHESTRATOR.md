# Orchestrator Module Summary

## Purpose

The `Orchestrator` is the **central coordinator** for the Kitsu AI system. It:

- **Manages subsystem lifecycle**: Boots, monitors, and gracefully shuts down all modules (legacy and modern)
- **Routes events**: Bridges legacy event-driven architecture with modern ModuleContract pattern via the event bus
- **Orchestrates AI pipeline**: Coordinates emotion engine, memory manager, LLM inference, and compression
- **Runs the main event loop**: Manages async chat loop, health checks, and shutdown signals
- **Provides fallback mechanisms**: Cascading AI provider chains (FastBrain → SLM → LLM) with graceful degradation

---

## Inputs / Outputs

### Constructor Inputs
```python
def __init__(self, runtime_config: Optional[Any] = None)
```
- **runtime_config**: Dictionary or object with `.merged` attribute containing:
  - `core` → personality config
  - `emotion` → emotion engine settings (e.g., `continuous_decay`)
  - `memory` → memory limits (short-term, episodic)
  - `hybrid` → compression/hybrid generator config

### Dependency Injection (set by bootstrap.py)
```
fast_brain, slm, llm          # AI providers
emotion, avatar                # System components
memory, gateway, personality   # Optional subsystems
```

### Output / Return Types

**Main Processing Output** (`process_input()`)
```python
{
    "response": str,                      # Generated text response
    "emotional_state": Dict[str, Any],    # Emotion engine state snapshot
    "mood": str,                          # Current mood (e.g., "happy", "neutral")
    "style": str,                         # Communication style (e.g., "sweet", "formal")
    "emotion": str,                       # Dominant emotion
    "avatar_hint": Optional[str],         # Avatar expression suggestion
    "voice_params": Dict[str, float],     # Pitch/speed parameters
    "confidence": float,                  # 0.0-1.0 confidence score
    "binary_vector": Optional[List],      # Compressed representation (if available)
    "routing": Dict,                      # Intent routing result
    "generation_time": float,             # ms to generate response
    "error": Optional[str],               # Error message if failed
}
```

**Health Check Output** (`health_check()`)
```python
{
    "ok": bool,                           # Overall system health
    "legacy_subsystems": {                # Legacy component status
        "fast_brain": bool,
        "slm": bool,
        "llm": bool,
        "emotion": bool,
        "avatar": bool,
    },
    "module_count": int,                  # Registered modern modules
}
```

---

## Core Logic

### 1. **Initialization Pipeline** (async)

```
__init__()
  ├── Parse runtime_config (safe extraction via _safe_get_config)
  ├── Initialize legacy subsystem placeholders
  ├── Create modern module registry
  └── Create state machine (KitsuState or MockState fallback)

start()
  ├── Initialize asyncio.Event (lazy init - critical fix)
  ├── wire() → Subscribe to legacy events
  └── _initialize_engine()
       ├── _initialize_personality()        → KitsuSelf
       ├── _initialize_emotion_engine()     → EmotionEngine
       ├── _initialize_memory()             → MemoryManager
       ├── _initialize_emotion_controller() → EmotionController
       └── _initialize_compression()        → CompressionPipeline + HybridGenerator
```

### 2. **Main Event Loop** (async)

```
run()
  ├── Initialize shutdown event
  ├── Start chat_task if enabled
  └── While not shutdown:
       ├── _check_module_health() (periodic, ~10s interval)
       ├── Publish MODULE_STARTED / MODULE_FAILED events
       └── Handle keyboard interrupt gracefully
```

### 3. **Chat Loop** (async)

```
_chat_loop()
  └── While not shutdown:
       ├── Get user input (in executor to prevent blocking)
       ├── Parse commands:
       │    ├── quit/exit/q    → request_stop()
       │    ├── help           → _show_help()
       │    ├── status         → await _show_status()
       │    └── [text]         → await process_input()
       └── Publish ResponseReady event
```

### 4. **Input Processing Pipeline** (async)

```
process_input(user_input: str)
  ├── [VALIDATION] Check input is non-empty string
  ├── [RESET] state.reset() + error handling
  ├── [EMOTIONS] emotion_engine.process_user_input()
  ├── [ROUTING] router.route() → intent classification
  ├── [REASONING] reasoner.reason() → binary features
  ├── [MEMORY] Retrieve relevant memories if flagged
  ├── [GENERATION] Three paths:
  │    ├── Path A: compression_ready + hybrid_generator
  │    │           → generate_fast_response() (template-based)
  │    ├── Path B: compression_ready
  │    │           → _generate_compressed() → LLM
  │    └── Path C: Fallback
  │                → _generate_fallback() (FastBrain/SLM/LLM cascade)
  ├── [VALIDATION] Validate response is non-empty string
  ├── [MEMORY] Store non-empty response in short-term memory
  ├── [PUBLISH] EmotionChanged + AvatarExpressionRequest events
  └── Return result dict with all metadata
```

### 5. **AI Provider Cascade** (async)

```
_on_input(event)
  ├── Validate event.text is string
  └── Try providers in order:
       ├── FastBrain (pure Python, fastest)
       ├── SLM (small language model, medium)
       ├── LLM (large model, slowest but best)
       └── If all fail → log warning

_generate_fallback()
  ├── Try LLM query()
  ├── If LLM fails → llm_fallback.generate()
  │    (personality-aware templated response)
  └── Return response
```

### 6. **Module Lifecycle Management**

```
register(module: ModuleContract)
  └── Add to _modules dict + create ModuleStatus

start_module(module_id)
  ├── Call module.start()
  ├── Update status (healthy, started, errors)
  └── Publish MODULE_STARTED / MODULE_FAILED

stop_module(module_id)
  ├── Call module.stop() with 10s timeout
  ├── Handle TimeoutError gracefully
  └── Update status

shutdown()
  ├── Stop all modules in reverse order (except self)
  ├── Set shutdown event
  └── Publish APP_SHUTDOWN
```

### 7. **Event Subscriptions** (legacy wiring)

```
wire() [idempotent - guarded by _wired flag]
  ├── InputReceived       → _on_input()
  ├── ResponseReady       → _on_response_ready()
  ├── EmotionChanged      → _on_emotion_changed()
  ├── SubsystemFailed     → _on_subsystem_failed()
  └── ShutdownRequested   → _on_shutdown_requested()
```

---

## Known Issues (Recently Fixed)

### ✅ **FIXED IN LATEST PATCH (18 issues)**

| Issue | Severity | Fix |
|-------|----------|-----|
| `asyncio.Event()` in `__init__` (event loop not yet active) | CRITICAL | Lazy init in `start()`/`run()` |
| `run_until_complete()` deadlock in sync `_show_status()` | CRITICAL | Made `_show_status()` async |
| Unreachable code after return in `_generate_compressed()` | HIGH | Removed dead code |
| Empty/None `user_input` crashes pipeline | HIGH | Early validation + error return |
| `router.route()` and `reasoner.reason()` NPE | HIGH | Try/except guards + fallback |
| `binary_vector.tolist()` crashes when None | HIGH | Safe type-aware conversion |
| `wire()` duplicate subscriptions on re-call | HIGH | Added `_wired` flag guard |
| `event.text` not validated as string | HIGH | Type checking at entry |
| Empty responses stored in memory | HIGH | Check before storing |
| `state.reset()` not error-checked | HIGH | Try/except wrapper |
| UTF-8 character splitting in memory truncation | HIGH | Encode/truncate/decode safely |
| `emotion_engine.process_user_input()` crashes | HIGH | Try/except + continue defaults |
| `personality` dict could be None | HIGH | Validate + default dict |
| `get_avatar_hint()` crashes | MEDIUM | Safe wrapper method `_safe_get_avatar_hint()` |
| Config extraction unsafe (nested dicts) | MEDIUM | Safe getter `_safe_get_config()` |
| Response validation missing | MEDIUM | Validate type + fallback |
| Compression state inconsistency | MEDIUM | Stricter state validation |
| Missing `Any` import | LOW | Added to typing imports |

---

## Remaining Risk Areas

### ⚠️ **Not Yet Fixed (Lower Priority)**

1. **Performance**: 10-second polling loop in `run()` is wasteful
   - Should use event-driven design instead of continuous polling

2. **Race Conditions**: Multiple async tasks call `request_stop()` without synchronization
   - Could set event multiple times (benign but inelegant)

3. **Module Ordering**: `start_all()` stops on first failure
   - Doesn't rollback already-started modules
   - No atomic guarantees

4. **Emotion Engine Fallback**: If `emotion_engine` is None, returns empty dict
   - Should have default emotional state template

5. **Bus Publishing**: No error handling if `bus.publish()` fails
   - Entire process fails silently with no feedback

6. **Unused Parameters**: `context` and `force_generation_mode` in `process_input()`
   - Dead API surface, confuses maintainers

7. **Config Type Safety**: No schema validation for runtime_config
   - Could accept wrong types without early detection

---

## Future Improvements

### Architecture
- [ ] **Event-Driven Loop**: Replace 10s polling with `asyncio.Event` for module health checks
- [ ] **Atomic Module Startup**: Implement rollback on `start_all()` failure
- [ ] **Schema Validation**: Use Pydantic or dataclass validators for runtime_config
- [ ] **Dependency Injection**: Formalize DI framework instead of ad-hoc property injection
- [ ] **Module Isolation**: Add context/namespace isolation between modules

### Reliability
- [ ] **Circuit Breaker**: Disable failing modules after N retries instead of infinite attempts
- [ ] **Bus Error Handling**: Log and report `bus.publish()` failures
- [ ] **Graceful Degradation**: Continue with reduced capabilities if optional modules fail
- [ ] **Telemetry**: Track generation time, error rates, module health over time
- [ ] **Distributed Tracing**: Add correlation IDs for request flow tracking

### Performance
- [ ] **Parallel Module Startup**: Start independent modules concurrently in `start_all()`
- [ ] **Response Caching**: Cache common intents (greeting, help, etc.)
- [ ] **Memory Pooling**: Pre-allocate emotional state dicts to reduce GC pressure
- [ ] **Compression Optimization**: Lazy-load compression model only when needed
- [ ] **Input Batching**: Queue multiple inputs and process in batches

### Developer Experience
- [ ] **Remove Unused Parameters**: Clean up `context` and `force_generation_mode`
- [ ] **Metrics Dashboard**: Real-time health/performance visualization
- [ ] **Debug Mode**: Add verbose logging option and request dump
- [ ] **Type Hints**: Add return type hints to all methods (currently partial)
- [ ] **Documentation**: Document event contract and ModuleContract interface

### Testing
- [ ] **Unit Tests**: Test each pipeline stage independently
- [ ] **Integration Tests**: Test emotion + routing + generation together
- [ ] **Chaos Tests**: Simulate module failures and verify recovery
- [ ] **Load Tests**: Measure throughput under high input volume
- [ ] **Benchmark**: Track generation time trends across releases

---

## Dependencies

### Internal
- `core.bus` → Event publisher/subscriber
- `core.contracts` → `ModuleContract`, `AIProvider`, etc.
- `core.events` → Event type definitions
- `core.brain.state` → `KitsuState`
- `core.brain.router` → `IntentRouter`
- `core.brain.binary_reasoner` → `BinaryReasoner`
- `core.compression.pipeline` → `CompressionPipeline`
- `core.compression.hybrid_generator` → `HybridGenerator`

### External
- `personality.emotion_engine` → EmotionEngine
- `personality.emotion_controller` → EmotionController
- `personality.kitsu_self` → KitsuSelf
- `personality.reaction_mapper` → ReactionMapper
- `memory.memory_manager` → MemoryManager
- `utils.llm_fallback_generator` → LLMFallback

### Standard Library
- `asyncio` → Event loop, tasks, events
- `logging` → Structured logging
- `dataclasses` → `@dataclass` for `ModuleStatus`

---

## Key Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|-----------|
| **Lazy asyncio.Event init** | Can't create Event outside event loop | Must check for None in multiple places |
| **Try/except everywhere** | Graceful degradation on any failure | Might hide bugs, verbose code |
| **Cascade fallback (FastBrain→SLM→LLM)** | Quality vs speed trade-off at runtime | Complex branching, hard to test |
| **10s health check polling** | Simple, predictable | Wasteful, high latency for failures |
| **Store everything in process_input result** | Complete metadata for debugging | Large return dict, couples layers |
| **MockState fallback** | Works when KitsuState import fails | Creates inconsistent behavior |
| **Legacy + Modern modules coexist** | Gradual migration path | Complexity, dual maintenance burden |

---

## File Statistics

- **Lines of Code**: ~930
- **Methods**: 28
- **Async Methods**: 16
- **Try/Except Blocks**: 20+
- **Event Subscriptions**: 5
- **AI Provider Chain Length**: 3 (FastBrain, SLM, LLM)
- **Initialization Steps**: 5 sequential async calls
- **State Machine States**: 4+ (idle, processing, complete, etc.)

---

## Quick Reference

### Starting the Orchestrator
```python
orch = Orchestrator(runtime_config=config_dict)
orch.fast_brain = FastBrain()
orch.llm = LLMProvider()
# ... inject other subsystems ...

await orch.start()
await orch.run()  # Blocks until shutdown
await orch.stop()
```

### Processing User Input Directly
```python
result = await orch.process_input("Hello!")
response = result["response"]
mood = result["mood"]
confidence = result["confidence"]
```

### Registering Modern Modules
```python
await orch.register(my_module)
await orch.start_module(my_module.module_id)
status = await orch.health_check()
```

### Graceful Shutdown
```python
orch.request_stop()
# Chat loop and main loop will exit cleanly
```

---

**Last Updated**: April 22, 2026  
**Patch Status**: 18 issues fixed, 7 remaining  
**Stability**: Production-ready with caveats (see Known Issues)
