---
title: Developer Onboarding Guide
tags: [development, onboarding, setup]
links: [[project-overview], [system-architecture], [development-workflow]]
created: 2026-04-27
updated: 2026-04-27
---

# Developer Onboarding Guide

## Welcome to Kitsu Development

This guide will help you get started with contributing to the Kitsu desktop AI companion project.

## Prerequisites

### Required Software
- **Python 3.8+** - Core runtime environment
- **Node.js 16+** - Frontend development (Tauri)
- **Rust 1.70+** - Backend development (Tauri)
- **Git** - Version control

### Recommended Tools
- **VS Code** - Primary development environment
- **Obsidian** - Documentation and knowledge management
- **Docker** - Containerized development (optional)

## Project Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/kitsu-desktop-ai.git
cd kitsu-desktop-ai
```

### 2. Environment Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Development Environment

```bash
# Install Tauri dependencies
cd src-tauri
cargo install tauri-cli
cd ..

# Setup development configuration
python scripts/setup_dev.py
```

## Project Structure Overview

```
project-root/
├── src/                    # Core system components
│   ├── application.py      # Main orchestrator
│   ├── bus.py             # EventBus implementation
│   ├── contracts.py       # Interface definitions
│   └── gateway.py         # Security and permissions
├── modules/               # Feature-based modules
│   ├── ai_pipeline/       # AI processing layers
│   ├── personality_system/ # Emotion and memory
│   ├── desktop_companion/ # UI and desktop integration
│   └── community_features/ # Plugins and extensions
├── shared/               # Shared utilities
│   ├── config/           # Configuration management
│   ├── utils/            # Common utilities
│   └── data/            # Data files and schemas
├── docs/                # Documentation (Obsidian-ready)
│   ├── notes/           # Atomic knowledge notes
│   ├── architecture/    # System design docs
│   ├── api/            # API documentation
│   └── guides/         # Tutorials and how-tos
└── tests/              # Test suites
```

## Development Workflow

### 1. Understanding the Architecture

Before diving into code, read these key documents:

- [[project-overview]] - High-level system understanding
- [[system-architecture]] - Detailed system design
- [[ai-pipeline]] - AI processing flow
- [[development-workflow]] - Coding guidelines

### 2. Setting Up Your Development Environment

#### IDE Configuration
Install these VS Code extensions:
- Python
- Rust
- Tauri
- Obsidian (for documentation)

#### Documentation Setup
1. Install Obsidian
2. Open the `docs/` folder as an Obsidian vault
3. Enable community plugins for better navigation

### 3. Running the Application

#### Development Mode
```bash
# Start the development server
python src/main.py --dev

# Or with Tauri
npm run tauri dev
```

#### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/test_ai_pipeline.py
```

## Key Concepts

### 1. Capability Tiers
The system adapts to hardware capabilities:
- **Ultra Low** - FastBrain only
- **Balanced** - FastBrain + SLM
- **Full** - All features including LLM

### 2. Event-Driven Architecture
All modules communicate through the central EventBus:
```python
# Emit an event
event_bus.emit("emotion_changed", data)

# Listen for events
@event_bus.on("user_input")
def handle_input(data):
    # Process input
```

### 3. Permission System
All system actions require permissions:
```python
# Check permission before action
if gateway.check_permission("filesystem", "read", path):
    # Perform file operation
```

## Coding Guidelines

### 1. Module Organization
- Feature-based modules, not file-type grouping
- Clear dependency hierarchy
- Interface-driven development

### 2. Import Discipline
```python
# Good - clear dependency hierarchy
from src.application import Orchestrator
from modules.ai_pipeline.fast_brain import FastBrain

# Bad - circular dependencies
from modules.desktop_companion.avatar import Avatar
from src.contracts import ResponseContract
```

### 3. Error Handling
```python
# Use proper error handling
try:
    result = process_input(user_input)
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    return ErrorResponse(str(e))
```

### 4. Documentation
Every module must have:
- Overview documentation
- API documentation
- Usage examples
- Bidirectional links to code

## Common Development Tasks

### 1. Adding a New AI Layer
1. Create module in `modules/ai_pipeline/`
2. Implement required interfaces from `src/contracts.py`
3. Add configuration in `shared/config/`
4. Write tests in `tests/`
5. Update documentation

### 2. Adding Desktop Features
1. Create module in `modules/desktop_companion/`
2. Implement permission checks via `src/gateway.py`
3. Add UI components if needed
4. Update system architecture docs

### 3. Extending Personality System
1. Modify modules in `modules/personality_system/`
2. Update emotion configuration
3. Add new personality traits
4. Document changes

## Testing Strategy

### 1. Unit Tests
- Test individual components
- Mock external dependencies
- Focus on business logic

### 2. Integration Tests
- Test module interactions
- Use test fixtures for setup
- Verify event flow

### 3. Performance Tests
- Test AI pipeline performance
- Memory usage validation
- Response time measurement

## Debugging

### 1. Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning condition")
logger.error("Error occurred")
```

### 2. Development Tools
- Use VS Code debugger for Python
- Rust debugger for backend
- Browser dev tools for frontend

### 3. Common Issues
- **Import errors** - Check PYTHONPATH
- **Permission denied** - Verify gateway configuration
- **Model loading failures** - Check hardware capabilities

## Contributing Guidelines

### 1. Code Review Process
- All changes require PR review
- Two reviewers for core changes
- Security review for permission changes

### 2. Documentation Requirements
- Update relevant docs
- Add links to new code
- Update API documentation

### 3. Testing Requirements
- Add tests for new features
- Ensure all tests pass
- Performance impact assessment

## Getting Help

### 1. Documentation
- Check `docs/notes/` for specific concepts
- Review `docs/architecture/` for system design
- Consult `docs/api/` for interface details

### 2. Community
- GitHub discussions for questions
- Discord server for real-time help
- Weekly developer meetings

### 3. Code Examples
Check the `examples/` directory for:
- Common patterns
- Module implementations
- Integration examples

## Next Steps

1. Read through the linked documentation
2. Set up your development environment
3. Run the application in development mode
4. Explore the codebase
5. Pick a good first issue from GitHub
6. Make your first contribution!

Welcome to the Kitsu development team! 🦊
