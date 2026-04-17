# 🦊 Kitsu Runtime System — Implementation Tasks

**Last Updated:** 2026-04-17  
**Status:** Phase 1 - Critical Path

---

## 📊 Progress Overview

| Phase | Component | Status | Priority |
|-------|-----------|--------|----------|
| **CRITICAL PATH** | Boot Sequence | 40% | 🔴 P0 |
| **CRITICAL PATH** | Event Bus / Messaging | 60% | 🔴 P0 |
| **CRITICAL PATH** | AI Routing Pipeline | 10% | 🔴 P0 |
| Stretch | Resource Management | 20% | 🟡 P1 |
| Stretch | Permission Layer | 30% | 🟡 P1 |

---

## 🚀 Phase 1: Critical Path (Boot + Dispatch < 2s)

### Section 1.1: Boot Sequence

- [x] `launcher.py` — CLI entry point (60% done)
- [x] `bootstrap.py` — Container builder (50% done)
- [ ] **NEXT:** Complete hardware detection integration in `launcher.py`
  - Link `hw_detect.rs` binary  
  - Auto-detect CPU/RAM/GPU tier
  - Load matching profile (ultra_low.yaml | balanced.yaml | full.yaml)
- [ ] Refine `core/bus.py` — Add priority channels
  - System (highest)
  - AI (medium)
  - UI (lowest)
- [ ] **NEXT:** Implement `core/orchestrator.py` module startup sequence
  - Parallel boot for non-dependent modules
  - Graceful degradation on module failure
- [ ] Complete `app/main.py` — Main entry point

### Section 1.2: Event System

- [x] `core/events.py` — EventBus exists
- [x] `core/bus.py` — MessageBus exists  
- [ ] **NEXT:** Unify EventBus + MessageBus (or clarify separation)
- [ ] Add async pub/sub with priority dispatch
- [ ] Test latency < 1ms

### Section 1.3: Module Registration

- [ ] Startup order:
  1. Event Bus / Message Bus
  2. Hardware detection + Profile
  3. FastBrain (keep warm)
  4. Personality engine
  5. System gateway
  6. UI controller
  7. (SLM/LLM lazy load)

---

## 🧠 Phase 2: AI Pipeline (Routing Layer)

### Section 2.1: Input Multiplexing

- [ ] **NEXT:** Implement `multimodal/input_mux.py`
  - Normalize text input
  - Normalize speech → text (via ASR)
  - Output unified string

### Section 2.2: FastBrain Layer

- [ ] `ai/fast_brain/patterns.py` — Rule-based detection
  - Regex patterns (greetings, commands)
  - Spam detection
- [ ] `ai/fast_brain/markov.py` — Response generation
- [ ] `ai/fast_brain/intent_classifier.py` — Classify input
  - system_action, query, casual, learning
- [ ] `ai/fast_brain/engine.py` — Orchestrate pipeline

### Section 2.3: Routing Decision Tree

- [ ] **NEXT:** Implement `router/policy_router.py`
  - Simple (pattern matched) → FastBrain ✓
  - Moderate (intent unclear) → SLM
  - Complex (reasoning needed) → LLM
- [ ] Implement `router/strip_controller.py`
  - Enforce tier matrix (ultra_low | balanced | full)
  - Disable SLM/LLM/speech/vector if tier < required

### Section 2.4: SLM/LLM Layer

- [ ] `ai/slm/engine.py` — Load on demand, unload after N seconds idle
- [ ] `ai/llm/engine.py` — Lazy load after SLM timeout
- [ ] Template fallback system (`ai/slm/templates.py`)

### Section 2.5: Personality Injection

- [ ] `personality/engine.py` — Post-process responses
  - Apply tone (neutral | playful | sass)
  - Inject personality markers

---

## ⚡ Phase 3: Resource Management

- [ ] `core/performance_manager.py` — Lease system (CPU, RAM, GPU)
- [ ] `ui/shimeji/behavior.py` — Idle animations
  - 60s inactivity → wander/nap
  - 5min inactivity → hide/tray
- [ ] Auto-unload SLM/LLM on idle
- [ ] `ai/fast_brain/learning_loop.py` — Capture interactions
- [ ] `ai/fast_brain/trainer.py` — Rebuild models

---

## 🔐 Phase 4: Safety & Permissions

- [ ] `system/gateway.py` — Action validation
- [ ] `system/adapters/power.py` — System control actions
- [ ] `system/adapters/files.py` — File operations
- [ ] `system/loop_guard.py` — Detect + kill runaway loops

---

## 🧪 Phase 5: Testing

- [ ] Boot time < 2000ms
- [ ] FastBrain response < 10ms
- [ ] Routing decision < 20ms
- [ ] Memory profiling (idle footprint < 200MB)
- [ ] No overheating under sustained load

---

## 🎯 Quick Start (Next 3 Tasks)

1. **Link hardware detection** → Auto-select profile
2. **Implement input_mux.py** → Unify text/speech input
3. **Build policy_router.py** → Route to FastBrain/SLM/LLM

