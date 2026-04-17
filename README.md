# Kitsu — local desktop AI companion

Kitsu (Kisu) is a local-first desktop AI companion with a Shimeji-style presence,
a layered emotion system, and a self-learning fast-response brain. She runs on any
device from a weak CPU-only laptop up to a high-end workstation, adapting her
capability profile to the hardware she runs on.

---

## What Kisu is

- A **desktop overlay companion** — lives on your screen, reacts to what you do
- A **local AI** — no cloud required; all inference runs on your machine
- A **self-learning system** — her fast-brain learns your patterns over time,
  responding to common inputs instantly without ever touching a model
- A **personality, not a chatbot** — emotion state shapes every response at every tier

---

## Architecture overview

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

The FastBrain learning loop is the core mechanism: every response generated anywhere
in the pipeline is fed back in, making the Markov chain more confident on that path
so the next identical or similar input never needs to escalate.

---

## Project layout

```
Kitsu_ai/
├── app/            Startup sequencing — entry point, launcher, bootstrap
├── core/           Runtime infrastructure — event bus, orchestrator, contracts
├── config/         Capability flags, YAML schemas, hardware profiles
├── ai/
│   ├── fast_brain/ Markov chain, Huffman compression, learning loop
│   ├── slm/        Style-shaping small language model layer
│   └── llm/        Full LLM bridge (local GGUF or API)
├── personality/    Emotion engine, mood/style/state system, triggers
├── memory/         Short-term, episodic, vector, and preference stores
├── router/         Policy router, strip controller, complexity scorer
├── system/         Capability gateway, permission manager, OS adapters
├── ui/             Avatar controller, shimeji physics, overlay HUD
├── multimodal/     Voice input (ASR), voice output (TTS)
├── modules/        Plugin loader, quiz solver, community mod API
├── data/           Config data files — these ARE the mod API
├── src-tauri/      Rust backend + frontend (desktop shell)
├── infra/          Logging, metrics, tracing
└── tests/          Unit, integration, performance tests
```

---

## Capability tiers

Kisu detects your hardware on first launch and selects a profile automatically.
You can override it in settings.

| Tier   | RAM    | What runs                              | Profile         |
|--------|--------|----------------------------------------|-----------------|
| Micro  | <2 GB  | FastBrain + emotion templates only     | `ultra_low`     |
| Low    | 2–4 GB | FastBrain + Micro-SLM + 2D avatar      | `ultra_low`     |
| Mid    | 4–8 GB | FastBrain + Full SLM + 2D/3D toggle    | `balanced`      |
| High   | 8+ GB  | Everything including LLM               | `full`          |

At every tier, the emotion system runs and Kisu has a personality.
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

```
main.py
  └── launcher.py
        ├── 1. logging online
        ├── 2. validate config schema
        ├── 3. load defaults.yaml
        ├── 4. overlay active profile
        ├── 5. detect hardware tier (via Tauri IPC)
        ├── 6. set capability flags
        ├── 7. LOCK flags ← read-only from here
        ├── 8. bootstrap.py (wire subsystems)
        └── 9. orchestrator.run() (event loop)
```

Steps 1–7 failing causes an immediate clean exit with a clear error message.
Steps 8–9 failing triggers degraded mode — Kisu still runs at a lower tier.

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

**Import discipline** — modules only import "downward":
- `core/` never imports from `ai/`, `personality/`, or `ui/`
- `config/` imports nothing from the project
- `core/events.py` and `core/contracts.py` import nothing from the project
- Cross-module communication goes through `core/bus.py` (EventBus)

**Capability gateway** — all system actions (file access, OS control, automation)
must pass through `system/gateway.py`. No module calls OS APIs directly.

**Data files are the mod API** — everything in `data/` is a versioned JSON file
that community mods can override. Never hardcode values that belong in `data/`.

**FastBrain is always hot** — even in sleep mode, the FastBrain stays loaded.
SLM and LLM unload after 5 minutes idle. FastBrain never unloads.

**Emotion is always on** — even with no avatar and no SLM, the emotion engine
runs and shapes template selection. This is what makes ultra-low mode feel
like Kisu, not a generic chatbot.

**Null implementations, not flag checks** — every optional subsystem has a null
implementation that satisfies its contract. Call sites never do `if USE_SLM:`.
The null SLM just returns `None` and the router handles it.

---

## Permissions

Kisu requests permissions by category, not per-feature:

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