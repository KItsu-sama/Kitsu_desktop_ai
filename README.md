# Kitsu — Local Desktop AI Companion

Kitsu is a local-first desktop AI companion with a Shimeji-style presence, a layered emotion system, and a self-learning fast-response brain. Built for production-grade reliability, she runs on any device from a weak CPU-only laptop to a high-end workstation, automatically adapting her capability profile.

---

## Key Features

- **Desktop Overlay Companion**: Lives on your screen and reacts to your interactions.
- **Local-First AI**: No cloud required; all inference runs privately on your machine.
- **Self-Learning Core**: Her "Reflex" brain learns your patterns over time, responding to common inputs instantly using an O(1) SimHash cache.
- **Emotion-Driven Personality**: A 10-float vibe vector shapes every response, ensuring she feels like a character, not a chatbot.
- **Non-Blocking Architecture**: A robust asynchronous chat loop ensures the interface remains responsive during deep reasoning.

---

## AI Architecture

Kitsu utilizes a **Tiered Cascading Pipeline** driven by a central asynchronous `EventBus`.

### The Three Paths of Reasoning

1.  **Reflex (Base Layer)**:
    - Uses SimHash for instant cache lookups and Markov-based templates.
    - Latency: < 100ms.
2.  **SLM (Small Language Model)**:
    - Powered by Qwen2.5-1.5B Q4.
    - Handles casual conversation with high personality consistency.
    - Latency: < 500ms.
3.  **LLM (Deep Reasoning)**:
    - Engaged for complex tasks, analysis, and web search.
    - Includes a multi-step judging loop to ensure quality.
    - Latency: Variable (within budget).

### Quality Assurance
A dedicated **Judge** module analyzes every model-generated response for character consistency, coherence, and factual safety before it reaches the user.

---

## Getting Started

### Prerequisites
- Python 3.9+
- Recommended: 8GB RAM for SLM/LLM operation.

### Installation
```bash
pip install -e .
```

### Running the Chat Loop
Start the interactive CLI to chat with Kitsu:
```bash
python src/kitsu/main.py
```

---

## Project Layout

The project follows a production-grade `src` layout:

```text
kitsu-desktop-ai/
├── src/kitsu/              # Core Package Root
│   ├── core/               # Infrastructure (EventBus, RequestContext)
│   ├── modules/            # Processing Modules (SLM, LLM, Router, etc.)
│   ├── utils/              # Helpers (Timing, Budgets)
│   └── main.py             # CLI Entry Point
├── data/                   # Persistent State (Reflex Cache, Configs)
├── docs/                   # Documentation and Knowledge Base
└── pyproject.toml          # Package Metadata and Dependencies
```

---

## Configuration

Kitsu uses a tiered capability system. You can override settings in `pyproject.toml` or via environment variables.

| Tier   | RAM    | Profile      | Capability Profile                              |
|--------|--------|--------------|-------------------------------------------------|
| Micro  | <2 GB  | `ultra_low`  | Reflex + Templates only. No model inference.    |
| Low    | 2–4 GB | `low`        | Reflex + Micro-SLM. 2D avatar.                  |
| Mid    | 4–8 GB | `balanced`   | Full SLM + 2D/3D toggle.                        |
| High   | 8+ GB  | `full`       | SLM + LLM (Deep Reasoning). All features.       |

---

## License

See `LICENSE`. The core architecture, reflex systems, and modular framework are open-source. Model weights and specific character assets are subject to their respective licenses.
