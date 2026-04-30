---
title: Project Overview
tags: [architecture, overview, kitsu]
links: [[system-architecture], [ai-pipeline], [personality-system]]
created: 2026-04-27
updated: 2026-04-27
---

# Project Overview

## What is Kitsu?

Kitsu is a **local-first desktop AI companion** with a Shimeji-style presence, layered emotion system, and self-learning fast-response brain. She runs on any device from a weak CPU-only laptop up to a high-end workstation, adapting her capability profile to the hardware she runs on.

## Key Characteristics

- **Desktop overlay companion** — lives on your screen, reacts to what you do
- **Local AI** — no cloud required; all inference runs on your machine  
- **Self-learning system** — her fast-brain learns your patterns over time
- **Personality, not a chatbot** — emotion state shapes every response at every tier

## Architecture Philosophy

The system follows a **tiered capability approach** with graceful degradation:

1. **FastBrain** (always active) - Instant responses via Markov chains
2. **SLM** (style layer) - Personality shaping and reasoning
3. **LLM** (deep reasoning) - Complex queries when needed

## Core Design Principles

1. **FastBrain is ALWAYS active**
2. **Heavy models are OPTIONAL and unloadable**
3. **System must work offline at install**
4. **Every feature is permission-gated**
5. **Graceful degradation is mandatory**
6. **Emotion drives personality, not logic**
7. **Extensions are untrusted (must validate)**
8. **No lag on wake (instant FastBrain response)**

## Hardware Adaptation

| Tier | RAM | What runs | Profile |
|------|-----|-----------|---------|
| Micro | <2 GB | FastBrain + emotion templates only | `ultra_low` |
| Low | 2–4 GB | FastBrain + Micro-SLM + 2D avatar | `ultra_low` |
| Mid | 4–8 GB | FastBrain + Full SLM + 2D/3D toggle | `balanced` |
| High | 8+ GB | Everything including LLM | `full` |

## Related Documentation

- [[system-architecture]] - Detailed system design
- [[ai-pipeline]] - AI processing layers
- [[personality-system]] - Emotion and personality implementation
- [[desktop-companion]] - UI and desktop integration
- [[community-features]] - Plugin and mod system
