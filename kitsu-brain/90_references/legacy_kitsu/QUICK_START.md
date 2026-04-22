# Kitsu AI - Quick Start Guide

## Overview

Kitsu is an advanced AI companion with sophisticated personality modeling, emotion processing, and machine learning capabilities. This guide will get you up and running quickly.

## System Requirements

- **Python**: 3.8 or higher
- **Memory**: 8GB RAM minimum (16GB+ recommended for ML features)
- **Storage**: 10GB free space for models and data
- **GPU**: Optional but recommended for ML training

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/kitsu-ai/kitsu.git
cd kitsu
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Basic installation
pip install -e .

# With development tools
pip install -e ".[dev]"

# With desktop UI
pip install -e ".[desktop]"

# With voice features
pip install -e ".[voice]"

# With web interface
pip install -e ".[web]"
```

## First Run

### Quick Start

```bash
python launcher.py
```

The first run will:
1. Detect your system capabilities
2. Run the setup wizard
3. Download required models
4. Create configuration files
5. Start the Kitsu interface

### Setup Wizard

The setup wizard will guide you through:
- **Personality Configuration**: Choose Kitsu's personality traits
- **Model Selection**: Select LLM models (Ollama, LoRA, or character models)
- **Interface Choice**: Terminal, desktop, or web interface
- **Feature Enablement**: Voice, gestures, integrations

## Basic Usage

### Terminal Interface

```bash
# Start terminal interface
python launcher.py --ui terminal

# Example interactions
Hello Kitsu!                    # Basic greeting
/kitsu mood playful             # Change mood
/kitsu stats                   # View status
/help                          # Show commands
```

### Desktop Interface

```bash
# Start desktop app
python launcher.py --ui desktop

# Features:
- Rich GUI with avatar
- Mouse gesture support
- Voice interaction
- System tray integration
```

### Web Interface

```bash
# Start web server
python launcher.py --ui web --port 8080

# Access at http://localhost:8080
```

## Configuration

### Personality Settings

Edit `data/config/personality.json`:

```json
{
  "base_personality": {
    "mood": "behave",
    "style": "chaotic",
    "traits": {
      "playfulness": 0.8,
      "curiosity": 0.9,
      "empathy": 0.7
    }
  },
  "emotional_range": {
    "happiness": 0.9,
    "excitement": 0.8,
    "affection": 0.7
  }
}
```

### Model Configuration

Edit `data/config/system_config.json`:

```json
{
  "llm": {
    "model": "kitsu_character",
    "temperature": 0.8,
    "is_character_model": true
  },
  "compression": {
    "enabled": true,
    "bitstream_width": 256,
    "binary_output_dim": 64
  }
}
```

## Advanced Features

### Binary Compression Pipeline

Kitsu's advanced ML pipeline compresses conversations for efficiency:

```python
# Enable compression in config
"compression": {
  "enabled": true,
  "markov_order": 2,
  "online_threshold": 100
}
```

### Multi-Candidate Generation

Generate and rank multiple responses:

```python
"candidate_generation": {
  "enabled": true,
  "num_candidates": 4,
  "ranking_method": "binary_reasoning"
}
```

### Vector Memory System

Store and retrieve conversations using vector similarity:

```python
"memory": {
  "vector_memory": {
    "enabled": true,
    "max_entries": 1000,
    "similarity_threshold": 0.7
  }
}
```

## Voice Setup

### Windows

```bash
# Install voice dependencies
pip install -e ".[voice]"

# Configure microphone
python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
```

### macOS/Linux

```bash
# Install system dependencies
# macOS: brew install portaudio
# Ubuntu: sudo apt-get install portaudio19-dev

# Install Python packages
pip install -e ".[voice]"
```

## Model Management

### Download Models

```bash
# Download character model
python scripts/download_model.py kitsu_character

# Download base model for LoRA
python scripts/download_model.py TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

### Train Custom Models

```bash
# Train compression pipeline
python scripts/train_compression.py

# Train LoRA adapter
python scripts/train_lora.py --base-model TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Reinstall dependencies
pip install -e .
```

**Model Loading Issues:**
```bash
# Check model paths
python scripts/check_models.py

# Re-download models
python scripts/download_model.py --force
```

**Memory Issues:**
```bash
# Reduce model size
# Edit config: "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Disable compression
"compression": {"enabled": false}
```

### Debug Mode

```bash
# Enable debug logging
python launcher.py --debug

# Check system status
python scripts/system_check.py
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=.
```

### Code Quality

```bash
# Format code
black .
isort .

# Type checking
mypy .

# Linting
flake8 .
```

## Next Steps

- **Documentation**: Read the [Architecture Guide](ARCHITECTURE_PROPOSAL.md)
- **API Reference**: Check the [ML System Guide](ML_System.md)
- **Examples**: See `examples/` directory
- **Community**: Join our Discord server

## Support

- **Issues**: [GitHub Issues](https://github.com/kitsu-ai/kitsu/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kitsu-ai/kitsu/discussions)
- **Documentation**: [Full Docs](https://kitsu-ai.github.io/docs)

---

*Enjoy your AI companion journey with Kitsu! 🦊*
