# Kitsu AI User Guide

## Quick Start

### Installation

1. Clone the repository
2. Run first-time setup:
   ```bash
   python r.py --first-run
   ```
3. Start Kitsu:
   ```bash
   python r.py
   ```

### Basic Usage

```
🦊 You: hello
Kitsu: I am a kitsu fox with vibe 0.10,0.50,0.20... You said: hello.

🦊 You: /help
Kitsu: Available commands:
  help    - Show this help message
  status  - Show system status
  quit    - Exit the application
```

## Features

### Modern Event-Driven Architecture

Kitsu uses a modern event-driven system that processes your input through multiple layers:

1. **InputMux (Sanity Layer)**: Normalizes and cleans your input
2. **EventBus**: Routes events between components
3. **AI Pipeline**: Multi-tier processing (FastBrain → SLM → LLM)
4. **Judge Validation**: Ensures response quality
5. **Response Display**: Shows formatted responses

### AI Pipeline

The system uses a sophisticated multi-tier AI pipeline:

- **FastBrain**: Quick reflex responses for common queries
- **SLM (Local Model)**: Qwen2.5-1.5B for balanced, intelligent responses
- **LLM (Fallback)**: Larger models for complex queries
- **Judge Module**: Validates responses for character consistency and safety

### Memory System

Kitsu remembers your conversations and builds context over time. The memory system tracks:
- Conversation history
- User preferences
- Emotional context
- Interaction patterns

## Configuration

### First-Run Setup

The first time you run Kitsu, you'll be guided through setup:

```
🦊 KITSU MODERN FIRST RUN INITIALIZATION
📊 Detecting system capabilities...
⚙️  Running setup wizard...
```

### Personality Settings

Configure Kitsu's personality:

```json
{
  "personality": {
    "default_mood": "behave",
    "default_style": "chaotic",
    "enable_sass": true,
    "emotion_decay_rate": 0.1,
    "emotion_threshold": 0.3,
    "max_stack_size": 5
  }
}
```

**Moods:**
- `behave`: Cooperative and helpful
- `flirty`: Affectionate and playful
- `mean`: Teasing and sassy
- `protective`: Caring and defensive

**Styles:**
- `chaotic`: Energetic and unpredictable
- `sweet`: Warm and gentle
- `cold`: Emotionally distant
- `direct`: Minimal and blunt
- `sarcastic`: Dry humor
- `playful`: Light teasing
- `eerie`: Mysterious

### Runtime Configuration

```json
{
  "runtime": {
    "mode": "text",
    "model": "kitsu:character",
    "temperature": 0.8,
    "streaming": true,
    "greet_on_startup": true,
    "enable_tts": false,
    "enable_stt": false,
    "enable_avatar": false,
    "memory_max_history": 200
  }
}
```

## Commands

### System Commands

- `/help` - Show available commands
- `/status` - Display system status
- `/quit` or `/exit` - Exit Kitsu
- `/mood <mood>` - Change current mood
- `/style <style>` - Change expression style

### Examples

```
🦊 You: /mood flirty
Kitsu: *switches to flirty mood* Hey there~ How can I help you today? 😉

🦊 You: /style sweet
Kitsu: *adopts a gentle tone* I'm here to help with kindness and care.

🦊 You: /status
Kitsu: System Status:
  Modules: 8 registered
  Legacy OK: True
  Engine OK: True
  Overall OK: True
```

## Input Types

### Text Input

Regular text conversation:
```
🦊 You: Tell me about yourself
Kitsu: I'm Kitsu, a friendly AI fox assistant! I love chatting and helping people.
```

### Commands

System commands start with `/`:
```
🦊 You: /help
Kitsu: Available commands: help, status, quit...
```

### Questions

Ask questions naturally:
```
🦊 You: What's the weather like?
Kitsu: I don't have access to current weather data, but I can help you with many other things!
```

## Advanced Features

### Behavior Gating

Kitsu's behavior engine can choose to ignore or respond differently based on:
- Input content
- Current mood
- Conversation context
- User preferences

### Emotion System

Kitsu maintains an emotional state that affects responses:
- Emotions decay over time
- Multiple emotions can stack
- User input influences emotional changes
- Personality settings govern emotion thresholds

### Multi-Modal Input (Future)

The system is designed to support:
- Speech input via STT
- Gesture input
- File uploads
- Image processing

## Troubleshooting

### Common Issues

**Kitsu doesn't respond:**
- Check if the system is running (`python r.py --debug`)
- Verify configuration files exist
- Check logs for error messages

**Responses seem generic:**
- Try changing mood/style
- Check personality configuration
- Ensure AI models are loaded

**Memory not working:**
- Verify memory directory exists
- Check memory configuration
- Ensure conversation history is being saved

### Debug Mode

Run with debug logging for detailed information:
```bash
python r.py --debug
```

### Reset Configuration

If you need to reset settings:
```bash
python r.py --first-run
```

Or completely reset:
```bash
python src/kitsu/first_run.py --reset
```

## Data and Privacy

### Data Storage

Kitsu stores data in the `data/` directory:
- `data/config/` - Configuration files
- `data/memory/` - Conversation memory
- `data/logs/` - Application logs
- `data/learning/` - Training data

### Privacy

- All data is stored locally
- No data is sent to external servers
- You can delete data files at any time
- Configuration can be adjusted for privacy preferences

### Permissions

Control what Kitsu can access:
```json
{
  "permissions": {
    "browser_hooks": false,
    "system_control": false,
    "file_access": false,
    "safe_mode": true,
    "can_train": false,
    "can_modify_memory": true
  }
}
```

## Performance

### System Requirements

**Minimum:**
- Python 3.8+
- 4GB RAM
- 2GB free disk space

**Recommended:**
- Python 3.10+
- 8GB RAM
- 5GB free disk space
- GPU support (optional)

### Optimization Tips

- Use appropriate model for your hardware
- Enable/disable features based on needs
- Monitor memory usage with `/status`
- Adjust temperature for response variety

### Models

Available AI models:
- **Kitsu:Character** (recommended) - Optimized for character interaction
- **TinyLlama 1.1B** - Fastest, good for low-end systems
- **Gemma 2B** - Balanced performance
- **Qwen 1.8B** - Smarter, requires more resources

## Development

### Extending Kitsu

Add custom modules by creating files in `src/kitsu/modules/`:
```python
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

async def handle_custom_event(ctx: RequestContext):
    # Your custom logic
    await bus.emit("CUSTOM_RESPONSE", ctx)

bus.subscribe("CUSTOM_EVENT", handle_custom_event)
```

### Configuration

Edit configuration files in `data/config/`:
- `modern_config.json` - Module settings
- `personality.json` - Personality parameters
- `runtime.json` - Runtime options

### Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Test with both modern and legacy systems

## Support

### Getting Help

- Check this guide first
- Run with `--debug` for detailed logs
- Review configuration files
- Check the GitHub issues

### Reporting Issues

When reporting issues, include:
- Python version
- Operating system
- Error messages
- Configuration (if relevant)
- Steps to reproduce

### Community

Join the community for:
- Feature requests
- Bug reports
- Configuration help
- Development discussions
