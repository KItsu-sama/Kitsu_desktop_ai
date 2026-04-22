# Kitsu — System Architecture Overview

Kitsu is a local-first desktop AI companion with a Shimeji-style presence, layered emotion system, and self-learning fast-response brain.

## Core Architecture

### Brain Stack (Inference Pipeline)
**FastBrain → SLM → LLM**

- **FastBrain**: Binary + Markov Chain + Huffman Tree for instant responses
- **SLM**: Style-shaping small language model for personality
- **LLM**: Deep reasoning for complex queries

### Emotion System
- **Mood** (Primary): behave, mean, flirty, protective
- **Style** (Expression): chaotic, sweet, cold, direct, sarcastic, playful, eerie
- **State** (Micro-behavior): normal, fox, glitch, analyst, submissive, detached

### Capability Tiers
| Tier | RAM | What runs | Profile |
|------|-----|-----------|---------|
| Micro | <2 GB | FastBrain + emotion templates | `ultra_low` |
| Low | 2–4 GB | FastBrain + Micro-SLM + 2D avatar | `ultra_low` |
| Mid | 4–8 GB | FastBrain + Full SLM + 2D/3D toggle | `balanced` |
| High | 8+ GB | Everything including LLM | `full` |

## System Navigation

### Core System Architecture
- [[Kitsu_Overview]] - Complete system documentation
- [[Kitsu_GitNexus_Guide]] - Code intelligence and navigation

### Core Infrastructure
- [[02_core/Kitsu_Orchestrator]] - Event routing and execution paths
- [[02_core/Kitsu_EventBus]] - Inter-module communication

### Modules & Features
- [[03_modules/Kitsu_EmotionEngine]] - Emotion processing and personality
- [[03_modules/Kitsu_QuizSystem]] - Automatic quiz solving

### Memory & Learning
- [[04_memory]] - FastBrain, episodic, and vector memory systems

### Knowledge Base
- [[05_knowledge]] - Extracted concepts and simplified documentation

### Reference Documentation
- [[90_references/llama_cpp/_Summary]] - LLM inference engine
- [[90_references/open_llm_vtuber/_Summary]] - VTuber framework concepts
- [[90_references/tauri/_Summary]] - Desktop application framework
- [[90_references/legacy_kitsu/_Summary]] - Historical architecture and designs

### Project Meta
- [[99_meta/Kitsu_Implementation_Tasks]] - Development roadmap
- [[99_meta/Kitsu_Phase1_Summary]] - Phase 1 completion report
- [[99_meta/Kitsu_Legacy_Refactor_Summary]] - Architecture refactoring notes

## Key Design Principles

1. **FastBrain is ALWAYS active** - Instant responses guaranteed
2. **Heavy models are OPTIONAL and unloadable** - Graceful degradation
3. **System must work offline at install** - No cloud dependencies
4. **Every feature is permission-gated** - Security first
5. **Emotion drives personality, not logic** - Character consistency
6. **Extensions are untrusted** - Must validate and sandbox

## Technology Stack

**Kitsu = Open_LLM_VTuber + Tauri + Shimeji + Desktop_Local**

- **Open_LLM_VTuber**: AI personality and emotion system
- **Tauri**: Desktop app framework with Rust backend
- **Shimeji**: Desktop overlay companion physics
- **Desktop Local**: Offline-first, permission-gated system

## Development Phases

| Phase | Focus | Milestone |
|-------|-------|-----------|
| 0 | `app/`, `core/`, `config/` | Skeleton boots, flags work |
| 1 | `ai/fast_brain/`, `personality/` | FastBrain learns, emotion runs |
| 2 | `ui/avatar/`, `memory/` | 2D avatar reacts to emotion |
| 3 | `ui/shimeji/`, `system/` | Shimeji on desktop, OS actions |
| 4 | `ai/slm/`, `ai/llm/` | Full intelligence layer |
| 5 | `src-tauri/`, `modules/` | Desktop shell + browser extension |
| 6 | `multimodal/`, training | Voice, LoRA fine-tuning |
| 7 | `data/mods/`, community shop | Mod ecosystem opens |
