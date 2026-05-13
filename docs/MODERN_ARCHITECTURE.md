# Modern Kitsu Architecture

## Overview

Kitsu has been refactored to use a modern event-driven architecture that provides better separation of concerns, improved maintainability, and enhanced modularity.

## Architecture Diagram

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   User Input   │───▶│   InputMux   │───▶│   EventBus     │───▶│ InputManager │
│   (Text/Speech) │    │ (Sanity Layer)│    │   (Pub/Sub)    │    │ (Coordinator) │
└─────────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
                                                                   │
                                                                   ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│  Response      │◀───│  ChatApp     │◀───│  RESPONSE_READY │◀───│  AI Pipeline  │
│   Display      │    │   (Main UI)  │    │    (Event)      │    │ (SLM/LLM/etc)│
└─────────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
```

## Core Components

### 1. EventBus (`src/kitsu/core/event_bus.py`)

The central communication hub that enables decoupled, event-driven communication between components.

**Features:**
- Pub/sub pattern for loose coupling
- Async event handling
- Duplicate response prevention
- Comprehensive error handling

**Events:**
- `INPUT_RECEIVED`: Raw user input received
- `INPUT_NORMALIZED`: Input processed by InputMux
- `PREPROCESS_DONE`: Preprocessing completed
- `SLM_PATH`: Route to SLM module
- `RESPONSE_READY`: Final response ready for display

### 2. InputMux (`src/kitsu/modules/input_mux.py`)

The "Sanity Layer" that normalizes all input before it enters the AI pipeline.

**Responsibilities:**
- Text cleaning and normalization
- Input type classification (text/speech/command)
- Confidence scoring
- Metadata extraction

**Input Types:**
- `TEXT`: Regular text input
- `SPEECH`: Transcribed speech input
- `COMMAND`: System commands (starting with /)

### 3. InputManager (`src/kitsu/modules/input_manager.py`)

Coordinates the AI pipeline and routes events between modules.

**Responsibilities:**
- Route normalized input to appropriate AI modules
- Coordinate multi-tier processing
- Handle fallback scenarios
- Manage response lifecycle

### 4. ChatApp (`src/kitsu/main.py`)

The main user interface that handles user interaction and response display.

**Features:**
- Async input handling
- Request tracking with unique IDs
- Timeout protection
- Response formatting

## AI Pipeline

The modern system implements a multi-tier AI processing pipeline:

```
Input → Behavior Engine → FastBrain → SLM → LLM → Judge → Response
```

### Tiers

1. **FastBrain (Reflex)**: Quick, pre-trained responses
2. **SLM (Local Model)**: Qwen2.5-1.5B for balanced responses
3. **LLM (Fallback)**: Larger models for complex queries

### Judge Validation

All responses pass through a Judge module that evaluates:
- **In-character**: Response matches personality
- **Coherent**: Response makes logical sense
- **Factually safe**: Response doesn't contain harmful information

## Module System

### Auto-Registration

Modern modules automatically register themselves when imported:

```python
# Auto-import modules to register subscribers
import kitsu.modules.preprocess
import kitsu.modules.router
import kitsu.modules.reflex
import kitsu.modules.slm
import kitsu.modules.llm
import kitsu.modules.memory
import kitsu.modules.input_mux
import kitsu.modules.input_manager
```

### Module Structure

Each module follows this pattern:
```python
class ModuleName:
    def __init__(self):
        self.module_id = 'module.name'
    
    async def handle_event(self, ctx: RequestContext):
        # Process event
        await bus.emit("NEXT_EVENT", ctx)

# Auto-register
bus.subscribe("EVENT_TYPE", handle_event)
```

## Configuration

### Modern Configuration Files

- `data/config/modern_config.json`: Modern module settings
- `data/config/system_config.json`: System capabilities
- `data/config/user_profile.json`: User preferences
- `data/config/personality.json`: Personality settings
- `data/config/permissions.json`: Security permissions

### Event System Configuration

```json
{
  "event_system": {
    "bus_type": "kitsu.core.event_bus",
    "max_subscribers": 100,
    "timeout_ms": 5000
  },
  "pipeline": {
    "tiers": ["fast_brain", "slm", "llm"],
    "judge_validation": true,
    "behavior_gating": true
  }
}
```

## Usage

### Starting the Modern System

```bash
# Normal usage (modern system by default)
python r.py

# With debug logging
python r.py --debug

# First-time setup
python r.py --first-run
```

### Event Flow Example

1. User types "hello"
2. ChatApp creates RequestContext
3. EventBus emits `INPUT_RECEIVED`
4. InputMux normalizes input, emits `INPUT_NORMALIZED`
5. InputManager routes to SLM, emits `SLM_PATH`
6. SLM processes input, emits `RESPONSE_READY`
7. ChatApp displays response

## Migration from Legacy

### What Changed

- **Event-driven**: Replaced direct method calls with EventBus
- **Modular design**: Components are loosely coupled via events
- **Input normalization**: All input passes through InputMux
- **Modern configuration**: Separate configs for modern modules

### Compatibility

- Legacy system remains available as fallback
- Configuration files are compatible
- CLI interface unchanged
- Data formats preserved

### Benefits

- **Better testing**: Components can be tested in isolation
- **Easier debugging**: Event flow is traceable
- **Hot-swappable**: Modules can be replaced without system restart
- **Scalability**: Event system scales with feature additions

## Development

### Adding New Modules

1. Create module file in `src/kitsu/modules/`
2. Implement event handlers
3. Auto-register with EventBus
4. Add to main.py imports

### Event Handling Best Practices

- Use unique, descriptive event names
- Include RequestContext in all events
- Handle exceptions gracefully
- Use async/await for I/O operations

### Testing

```python
# Test module in isolation
import kitsu.modules.your_module
from kitsu.core.context import RequestContext

ctx = RequestContext(text="test input")
await bus.emit("TEST_EVENT", ctx)
```

## Troubleshooting

### Common Issues

1. **Module not loading**: Check import in main.py
2. **Event not received**: Verify subscription and event name
3. **No response**: Check AI pipeline configuration
4. **Configuration errors**: Validate JSON syntax

### Debug Tools

- `--debug` flag for verbose logging
- Event tracing in logs
- Module status reporting
- Configuration validation

## Future Enhancements

- Speech input integration
- Avatar expression events
- Memory system events
- Performance monitoring
- Plugin system
