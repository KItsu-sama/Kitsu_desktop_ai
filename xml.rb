# High-Level Runtime Flow

```text
┌─────────────┐                              ┌────────────────────┐
│   ChatApp   │                              │      EventBus      │
└──────┬──────┘                              └─────────┬──────────┘
       │                                               │
       │  ctx = RequestContext(id="abc123")            │
       │──────────────────────────────────────────────>│
       │                                               │
       │                           emit("INPUT_RECEIVED", ctx)
       │                                               │
       │                           handlers = [
       │                             input_mux,
       │                             preprocess,
       │                             router,
       │                             reflex
       │                           ]
       │                                               │
       │<──────────── async pipeline execution ───────>│
       │                                               │
       │                     gather([...]) concurrent execution
       │                                               │
       │                     input_mux
       │                     └─ normalize input
       │                        → INPUT_RECEIVED
       │
       │                     preprocess
       │                     └─ SimHash + vibe analysis
       │                        → PREPROCESS_DONE
       │
       │                     router
       │                     └─ route selection
       │                        → REFLEX_PATH
       │
       │                     reflex
       │                     └─ generate response
       │                        → RESPONSE_READY
       │
       │<──────────────────── future resolved ─────────│
       │
await future
       │
       ▼
"display response"
```

---

# Detailed Request Lifecycle

```text
┌─────────────┐        ┌────────────────────┐        ┌────────────────────┐
│   ChatApp   │        │      EventBus      │        │   RequestContext   │
└──────┬──────┘        └─────────┬──────────┘        └─────────┬──────────┘
       │                          │                             │
       │ ctx = RequestContext()   │                             │
       │─────────────────────────>│                             │
       │                          │                             │
       │                          │                             │  CREATED
       │                          │                             │
       │                          │ input_mux(ctx)              │
       │                          │────────────────────────────>│
       │                          │ ctx.text = normalized       │
       │                          │ emit("INPUT_RECEIVED")      │
       │                          │                             │  PROCESSING
       │                          │
       │                          │ preprocess(ctx)
       │                          │────────────────────────────>│
       │                          │ ctx.simhash = 0x1234
       │                          │ ctx.vibe = [0.8, 0.2, ...]
       │                          │ emit("PREPROCESS_DONE")
       │                          │                             │  ANALYZED
       │                          │
       │                          │ router(ctx)
       │                          │────────────────────────────>│
       │                          │ ctx.route = "REFLEX"
       │                          │ emit("REFLEX_PATH")
       │                          │                             │  ROUTED
       │                          │
       │                          │ reflex(ctx)
       │                          │────────────────────────────>│
       │                          │ ctx.response = "Hey!"
       │                          │ emit("RESPONSE_READY")
       │                          │                             │  RESPONDED ✓
       │                          │
       │ _on_response_ready(ctx)  │
       │<─────────────────────────│
       │ future.set_result(ctx)   │
       ▼                          ▼
 response returned          pipeline complete
```

---

# Bootstrap & Initialization Flow

```text
r.py
 └─ parse CLI args
      ↓
launcher.py
      ↓
first_run.py (only if setup required)
      ↓
detect hardware capabilities
      ↓
generate profile.json
      ↓
CapabilityFlags.from_profile(profile_data)
      ↓
set feature flags:
    use_slm = True   (8GB+ RAM)
    use_llm = False  (<16GB)
      ↓
flags.lock() 🔒
      ↓
StripController(flags)
      ↓
PolicyRouter uses enforced capability tiers
```

---

# Hardware-Aware Intelligence Tiering

## Low-End Device (4GB RAM Laptop)

```text
User Input
    ↓
PolicyRouter
    ↓
┌──────────────────────────────────────┐
│ "hello"          → FASTBRAIN ✓       │
│ "math problem"   → SLM ✓             │
│ "PhD thesis"     → LLM ❌            │
│                     fallback → SLM ✓ │
└──────────────────────────────────────┘
```

### Result

* FastBrain always available
* SLM available within memory budget
* LLM automatically blocked

---

## High-End Device (16GB Desktop)

```text
User Input
    ↓
PolicyRouter
    ↓
┌──────────────────────────────────┐
│ FASTBRAIN ✓                      │
│ SLM ✓                            │
│ LLM ✓                            │
└──────────────────────────────────┘
```

### Result

Full intelligence stack enabled.

---

# PolicyRouter + StripController Enforcement

```python
# Input:
"solve integral calculus"

PolicyRouter:
    RoutingDecision(
        target = LLM,
        confidence = 0.60,
        expected_latency = 3000ms
    )

StripController.enforce(LLM):

    ultra_low:
        LLM → SLM → FastBrain
        latency ≈ 15ms

    balanced:
        LLM → SLM
        latency ≈ 300ms

    full:
        LLM allowed directly
        latency ≈ 3s
```

---

# Null Implementation Pattern

```python
# modules/slm.py

if FLAGS.use_slm:

    class SLM:
        async def generate(ctx):
            ...

else:

    class SLM:
        async def generate(ctx):
            raise NotImplementedError()
```

### Why This Helps

* Keeps architecture stable across hardware tiers
* Avoids conditional imports everywhere
* Allows graceful degradation
* Simplifies dependency management

---

# Complete System Architecture

```text
r.py
  ↓
launcher.py
  ↓
main.py
  ↓
EventBus Pipeline
  ↓
stdin
  ↓
RAW_INPUT
  ↓
InputMux
  ↓
INPUT_RECEIVED
  ↓
Preprocess
  ↓
Router
  ↓
┌───────────────────────────────┐
│ REFLEX │ SLM │ LLM │ TOOLS    │
└───────────────────────────────┘
  ↓
Judge
  ↓
RESPONSE_READY
  ↓
ChatApp Future Resolution
  ↓
display response
  ↓
RESPONSE_SENT
  ↓
Memory.learn() (async / non-blocking)
```

---

# Example Runtime Timeline (≈83ms)

```text
User types:
    "hello"

0ms
 └─ ChatApp creates RequestContext

1ms
 └─ EventBus.emit("INPUT_RECEIVED")

2ms
 └─ input_mux
      RAW_INPUT → normalized text

7ms
 └─ preprocess
      SimHash + vibe embedding

9ms
 └─ router
      complexity = 0.1
      route = REFLEX

15ms
 └─ reflex
      cache hit
      response = "Hey! 😊"

16ms
 └─ future.set_result(ctx)

16ms
 └─ response displayed to user

20ms
 └─ Memory.learn()
      async background learning
```

---

# Core Design Principles

| Principle                  | Purpose                               |
| -------------------------- | ------------------------------------- |
| Event-driven architecture  | Decouples modules cleanly             |
| RequestContext             | Shared mutable state across pipeline  |
| PolicyRouter               | Chooses intelligence tier dynamically |
| StripController            | Enforces hardware limits safely       |
| Async EventBus             | Concurrent low-latency execution      |
| Null Implementations       | Stable architecture across profiles   |
| Background Memory Learning | No response blocking                  |
| CapabilityFlags            | Centralized hardware feature control  |

---

# Overall Architecture Philosophy

```text
Fast when possible.
Smart when allowed.
Graceful when limited.
Always responsive.
```
