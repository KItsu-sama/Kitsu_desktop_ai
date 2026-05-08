---
tags: [architecture, design, system-overview, documentation]
aliases: ["System Architecture", "Kitsu Design"]
project: Kitsu Desktop AI
type: documentation
created: 2026-04-27
modified: 2026-04-27
---

# System Design Document

## Executive Summary

Kitsu is a modular, local-first AI companion system designed for desktop integration with adaptive capability tiers. The system uses a layered architecture with clear separation of concerns, event-driven communication, and graceful degradation based on available hardware resources.

## Design Principles

### 1. Local-First Architecture
- All core functionality works offline
- No cloud dependencies for basic operations
- User data remains on local device

### 2. Capability-Based Design
- Features enabled/disabled based on hardware detection
- Graceful degradation for low-end systems
- User override options for capability settings

### 3. Event-Driven Communication
- Loose coupling between modules
- Central EventBus for all inter-module communication
- Asynchronous message passing

### 4. Permission-Gated Security
- Category-based permission system
- Explicit user consent for dangerous operations
- Session-based permission management

## System Architecture

### Core Components

#### Application Layer
- **Orchestrator**: Main application lifecycle management
- **EventBus**: Central communication hub
- **Contracts**: Interface definitions and data structures

#### AI Pipeline
- **FastBrain**: Pattern-based instant responses
- **SLM**: Personality-shaped conversation
- **LLM**: Deep reasoning for complex queries
- **Policy Router**: Intent classification and routing

#### Personality System
- **Emotion Engine**: Mood/style/state management
- **Memory Manager**: Episodic and semantic memory
- **Reaction Mapper**: Personality-driven response selection

#### Desktop Integration
- **Avatar Controller**: 2D/3D character rendering
- **Shimeji Physics**: Desktop overlay behavior
- **System Gateway**: OS-level interaction permissions

### Module Organization

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
└── docs/                # Documentation
    ├── notes/           # Atomic knowledge notes
    ├── architecture/    # System design docs
    ├── api/            # API documentation
    └── guides/         # Tutorials and how-tos
```

## Data Flow

### User Input Processing

1. **Input Reception** - Desktop controller receives user input
2. **Intent Classification** - Policy router analyzes input complexity
3. **Tier Selection** - System selects appropriate AI layer
4. **Response Generation** - Selected AI layer processes input
5. **Emotion Integration** - Emotion engine shapes response
6. **Output Delivery** - Response delivered via appropriate channel

### Learning Loop

1. **Pattern Extraction** - FastBrain extracts response patterns
2. **Feedback Integration** - User reactions fed back to system
3. **Model Adaptation** - Response patterns updated based on usage
4. **Memory Consolidation** - Important interactions stored in memory

## Security Model

### Permission Categories

| Category | Examples | Risk Level | Default |
|----------|----------|------------|---------|
| filesystem | File read/write | High | Off |
| display | Wallpaper, cursor | Low | On |
| system | Sleep, shutdown | High | Off |
| browser | Tab manipulation | Medium | Off |
| network | Web search | Medium | On |
| audio | Microphone, TTS | Medium | Off |
| automation | Keyboard/mouse | Critical | Off |

### Safety Mechanisms

- **Explicit Confirmation**: Dangerous actions require user confirmation
- **Cooldown Periods**: Rate limiting for sensitive operations
- **Kill Switch**: Emergency stop for automation features
- **Session Permissions**: Time-limited permission grants

## Performance Strategy

### Hardware Adaptation

The system automatically detects hardware capabilities and adjusts feature set:

- **Micro Tier** (<2GB RAM): FastBrain only, basic templates
- **Low Tier** (2-4GB RAM): FastBrain + SLM, 2D avatar
- **Mid Tier** (4-8GB RAM): FastBrain + SLM, 2D/3D toggle
- **High Tier** (8GB+ RAM): Full feature set including LLM

### Resource Management

- **Dynamic Loading**: Models loaded/unloaded based on usage
- **Memory Optimization**: Efficient data structures and caching
- **Background Processing**: Non-blocking operations where possible

## Integration Points

### Desktop Shell Integration
- Tauri-based desktop application
- System tray integration
- Wallpaper and cursor control
- Overlay rendering

### Browser Extension (Optional)
- Web page interaction
- Quiz automation
- Tab management
- WebSocket communication with core app

### Community Plugin System
- Plugin loader with sandboxing
- API for community extensions
- Asset sharing platform
- Version compatibility management

## Development Guidelines

### Code Organization
- Feature-based modules, not file-type grouping
- Clear dependency hierarchy (core → modules → shared)
- Interface-driven development

### Testing Strategy
- Unit tests for core components
- Integration tests for module interactions
- Performance tests for AI pipeline
- Security tests for permission system

### Documentation Requirements
- Every module has corresponding documentation
- Bidirectional linking between code and docs
- Atomic notes for specific concepts
- API documentation for all public interfaces

## Future Extensibility

### Planned Features
- Voice input/output integration
- Advanced learning algorithms
- Multi-language support
- Cloud synchronization (optional)

### Extension Points
- Custom AI model integration
- Additional personality profiles
- New desktop interaction modes
- Enhanced community features

## Conclusion

The Kitsu system architecture provides a solid foundation for a local-first AI companion with adaptive capabilities, strong security, and extensible design. The modular nature allows for incremental development and easy maintenance while the event-driven communication ensures loose coupling and flexibility.

The design prioritizes user privacy, performance, and customization while maintaining a consistent and engaging user experience across different hardware capabilities.
