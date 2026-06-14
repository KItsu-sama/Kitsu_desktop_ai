# Kitsu Development Guide

## Getting Started

### Development Environment

1. **Python Requirements:**
   - Python 3.8+ (3.10+ recommended)
   - pip package manager
   - Git for version control

2. **Clone Repository:**
   ```bash
   git clone <repository-url>
   cd kitsu_desktop_ai
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run First-Time Setup:**
   ```bash
   python r.py --first-run
   ```

### Project Structure

```
kitsu_desktop_ai/
├── src/kitsu/                 # Modern system
│   ├── core/                   # Core components
│   │   ├── event_bus.py        # Event system
│   │   └── context.py          # Request context
│   ├── modules/                # Modern modules
│   │   ├── input_mux.py        # Input normalization
│   │   ├── input_manager.py    # Pipeline coordinator
│   │   ├── slm.py              # Local language model
│   │   ├── llm.py              # Large language model
│   │   ├── memory.py           # Memory system
│   │   └── judge.py            # Response validation
│   ├── main.py                 # Modern chat app
│   ├── launcher.py             # Modern launcher
│   └── first_run.py            # Modern first-run
├── runtime/                     # Modern runtime architecture
│   ├── core/                   # Runtime core services
│   ├── launchers/              # Startup and bootstrap code
│   ├── config/                 # Runtime configuration and profiles
│   └── docs/                   # Runtime documentation
├── scripts/                    # Setup scripts
│   ├── first_run.py            # Legacy first-run
│   └── setup_wizard.py         # Setup wizard
├── docs/                       # Documentation
├── data/                       # Runtime data
└── r.py                        # Main entry point
```

## Architecture

### Modern Event-Driven System

The modern system uses an event-driven architecture with these key components:

#### EventBus (`application/core/event_bus.py`)

Central communication hub implementing pub/sub pattern.

```python
from kitsu.core.event_bus import bus, RequestContext

# Emit event
await bus.emit("EVENT_NAME", request_context)

# Subscribe to event
bus.subscribe("EVENT_NAME", handler_function)
```

#### RequestContext (`application/core/context.py`)

Standardized request context passed through the pipeline.

```python
ctx = RequestContext(
    text="user input",
    original_text="raw input",
    vibe=[0.1, 0.5, 0.2, ...],
    mode="chat"
)
```

### Module Development

#### Creating a New Module

1. **Create module file** in `src/kitsu/modules/`:

```python
"""
Custom Module - Description of what this module does.
"""

import logging
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

logger = logging.getLogger(__name__)

class CustomModule:
    """Custom module implementation."""
    
    def __init__(self):
        self.module_id = 'custom.module'
        self._initialized = False
    
    async def process_event(self, ctx: RequestContext):
        """Handle incoming events."""
        try:
            # Your processing logic here
            result = self.process_input(ctx.text)
            
            # Update context with result
            ctx.response = result
            
            # Emit next event
            await bus.emit("CUSTOM_RESPONSE", ctx)
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            ctx.response = "Sorry, I encountered an error."
            await bus.emit("RESPONSE_READY", ctx)
    
    def process_input(self, text: str) -> str:
        """Your custom processing logic."""
        # Implement your logic here
        return f"Custom response to: {text}"

# Auto-register module
custom_module = CustomModule()

# Subscribe to events
async def on_custom_trigger(ctx: RequestContext):
    """Handle trigger events."""
    await custom_module.process_event(ctx)

bus.subscribe("CUSTOM_TRIGGER", on_custom_trigger)
logger.info("CustomModule registered")
```

2. **Import in main app** (`src/kitsu/main.py`):

```python
# Add to auto-imports
import kitsu.modules.custom
```

#### Module Best Practices

1. **Error Handling:** Always wrap processing in try/catch
2. **Logging:** Use structured logging with appropriate levels
3. **Event Names:** Use descriptive, unique event names
4. **Context:** Always pass RequestContext through events
5. **Async:** Use async/await for I/O operations

#### Module Registration Pattern

```python
# 1. Create module instance
module_instance = YourModule()

# 2. Create event handler
async def handle_event(ctx: RequestContext):
    await module_instance.process(ctx)

# 3. Subscribe to events
bus.subscribe("TRIGGER_EVENT", handle_event)

# 4. Log registration
logger.info("YourModule registered")
```

## Event System

### Event Flow

```
User Input → INPUT_RECEIVED → INPUT_NORMALIZED → AI_PROCESSING → RESPONSE_READY
```

### Standard Events

- `INPUT_RECEIVED`: Raw user input received
- `INPUT_NORMALIZED`: Input processed by InputMux
- `PREPROCESS_DONE`: Preprocessing completed
- `SLM_PATH`: Route to SLM module
- `LLM_PATH`: Route to LLM module
- `RESPONSE_READY`: Final response ready

### Custom Events

Create custom events for module communication:

```python
# Emit custom event
await bus.emit("CUSTOM_EVENT", ctx)

# Handle custom event
bus.subscribe("CUSTOM_EVENT", custom_handler)
```

## Configuration

### Configuration Files

#### Modern Configuration (`data/config/modern_config.json`)

```json
{
  "modules": {
    "input_mux": {"enabled": true},
    "input_manager": {"enabled": true},
    "slm": {"enabled": true, "model": "Qwen2.5-1.5B"},
    "llm": {"enabled": true, "fallback": true},
    "memory": {"enabled": true},
    "judge": {"enabled": true},
    "custom_module": {"enabled": true, "setting": "value"}
  },
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

#### Module Configuration

Access configuration in your module:

```python
import json
from pathlib import Path

def load_config():
    config_path = Path("data/config/modern_config.json")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

config = load_config()
module_config = config.get("modules", {}).get("your_module", {})
```

## Testing

### Unit Testing

Create tests for your modules:

```python
import unittest
import asyncio
from kitsu.core.context import RequestContext
from kitsu.modules.your_module import YourModule

class TestYourModule(unittest.TestCase):
    def setUp(self):
        self.module = YourModule()
    
    async def test_processing(self):
        ctx = RequestContext(text="test input")
        await self.module.process_event(ctx)
        self.assertIsNotNone(ctx.response)
    
    def test_sync_wrapper(self):
        asyncio.run(self.test_processing())

if __name__ == "__main__":
    unittest.main()
```

### Integration Testing

Test the full event flow:

```python
import asyncio
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

async def test_event_flow():
    # Create test context
    ctx = RequestContext(text="hello")
    
    # Track events
    events_received = []
    
    def event_handler(event_ctx):
        events_received.append(event_ctx.text)
    
    # Subscribe to events
    bus.subscribe("TEST_EVENT", event_handler)
    
    # Emit test event
    await bus.emit("TEST_EVENT", ctx)
    
    # Verify event was received
    assert len(events_received) > 0
    print("✅ Event flow test passed")

# Run test
asyncio.run(test_event_flow())
```

### Debug Testing

Use debug mode for detailed logging:

```bash
python r.py --debug
```

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/new-module

# Develop your module
# Edit src/kitsu/modules/your_module.py

# Test your changes
python r.py --debug

# Run tests
python -m pytest tests/

# Commit changes
git add .
git commit -m "Add new module"
git push origin feature/new-module
```

### 2. Debugging

#### Debug Logging

```python
import logging
logger = logging.getLogger(__name__)

def debug_function():
    logger.debug("Starting function")
    # Your code
    logger.info("Function completed")
    logger.error("Error occurred", exc_info=True)
```

#### Event Tracing

```python
# Add event tracing
async def traced_handler(ctx: RequestContext):
    logger.info(f"Processing event: {ctx.text[:50]}...")
    result = await actual_handler(ctx)
    logger.info(f"Event processed: {result[:50]}...")
    return result
```

### 3. Performance Monitoring

#### Timing Events

```python
import time

async def timed_handler(ctx: RequestContext):
    start_time = time.time()
    
    # Process event
    result = await process_event(ctx)
    
    end_time = time.time()
    logger.info(f"Event processed in {end_time - start_time:.2f}s")
    
    return result
```

#### Memory Monitoring

```python
import psutil
import os

def log_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
```

## Code Style

### Python Style Guide

Follow PEP 8 with these additional guidelines:

1. **Imports:** Group imports by type
2. **Logging:** Use structured logging
3. **Async:** Use async/await consistently
4. **Error Handling:** Always handle exceptions
5. **Documentation:** Document all public functions

### Example

```python
"""
Module description.

This module provides functionality for...
"""

import asyncio
import logging
from typing import Optional

from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

logger = logging.getLogger(__name__)

class ExampleClass:
    """Example class implementation."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize the example class.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._initialized = False
    
    async def process_input(self, text: str) -> str:
        """Process input text.
        
        Args:
            text: Input text to process
            
        Returns:
            Processed text
            
        Raises:
            ValueError: If input is invalid
        """
        try:
            if not text or not text.strip():
                raise ValueError("Input cannot be empty")
            
            # Processing logic
            result = text.strip().title()
            
            logger.debug(f"Processed input: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            raise
```

## Contributing

### Pull Request Process

1. **Fork** the repository
2. **Create** feature branch
3. **Develop** your feature
4. **Test** thoroughly
5. **Document** changes
6. **Submit** pull request

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included
- [ ] Documentation is updated
- [ ] No breaking changes
- [ ] Performance impact considered
- [ ] Security implications reviewed

### Release Process

1. **Update** version numbers
2. **Update** CHANGELOG.md
3. **Tag** release
4. **Create** release notes
5. **Deploy** to distribution

## Troubleshooting

### Common Development Issues

#### Module Not Loading

```bash
# Check if module is imported
grep -r "your_module" src/kitsu/main.py

# Check for syntax errors
python -m py_compile src/kitsu/modules/your_module.py
```

#### Events Not Working

```python
# Debug event subscription
import kitsu.core.event_bus as eb
print(f"Subscribers: {len(eb.bus.subscribers)}")

# Test event emission
async def test_event():
    ctx = RequestContext(text="test")
    await eb.bus.emit("TEST_EVENT", ctx)

asyncio.run(test_event())
```

#### Configuration Issues

```python
# Validate configuration
import json
from pathlib import Path

config_path = Path("data/config/modern_config.json")
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
        print(json.dumps(config, indent=2))
```

### Performance Issues

#### Memory Leaks

```python
# Monitor memory usage
import psutil
import time

def monitor_memory():
    process = psutil.Process()
    while True:
        memory = process.memory_info().rss / 1024 / 1024
        print(f"Memory: {memory:.2f} MB")
        time.sleep(5)

# Run in separate thread
import threading
threading.Thread(target=monitor_memory, daemon=True).start()
```

#### Event Bottlenecks

```python
# Profile event handling
import cProfile
import pstats

def profile_events():
    pr = cProfile.Profile()
    pr.enable()
    
    # Run your event processing
    asyncio.run(test_event_flow())
    
    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    stats.print_stats(10)

profile_events()
```

## Resources

### Documentation

- [Modern Architecture](MODERN_ARCHITECTURE.md)
- [User Guide](USER_GUIDE.md)
- [API Reference](API_REFERENCE.md)

### Tools

- **Python Debugger:** `python -m pdb your_script.py`
- **Memory Profiler:** `python -m memory_profiler your_script.py`
- **Line Profiler:** `kernprof -l -v your_script.py`

### Community

- **GitHub Issues:** Report bugs and request features
- **Discussions:** Ask questions and share ideas
- **Wiki:** Community-maintained documentation
