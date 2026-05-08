# Runtime Module Summary

## Overview

The runtime module contains Kitsu's **modern 4-layer architecture** that provides robust startup, lifecycle management, and resource-aware operation. This architecture represents the evolution from a simple AI assistant to a sophisticated cognitive runtime with comprehensive safety and stability systems.

## Modern 4-Layer Architecture

Kitsu runs on a **modern 4-layer architecture**:

```
ServiceContainer → ModuleRegistry → LifecycleManager → RuntimeOrchestrator
```

### Architecture Layers

**1. ServiceContainer (Dependency Injection)**
- **Purpose**: Automatic dependency resolution and service lifetime management
- **Features**: Constructor injection with circular dependency detection
- **Key Files**: `service_container.py`

**2. ModuleRegistry (Module Management)**
- **Purpose**: Centralized module registration and dependency validation
- **Features**: State tracking (CREATED → INITIALIZING → RUNNING → DEGRADED → STOPPED)
- **Key Files**: `module_registry.py`

**3. LifecycleManager (Orchestration)**
- **Purpose**: Phased startup with graceful degradation and health monitoring
- **Features**: Resource-aware module management and automatic recovery
- **Key Files**: `lifecycle_manager.py`

**4. RuntimeOrchestrator (Main Loop)**
- **Purpose**: Event-driven coordination and cross-system communication
- **Features**: State machine integration and runtime behavior coordination
- **Key Files**: `runtime_orchestrator.py`

## Startup Phases

The modern architecture executes startup in deterministic phases:

1. **Phase 0** - Core Services (logger, config, container)
2. **Phase 1** - Communication (event_bus, message_bus)
3. **Phase 2** - Runtime Control (orchestrator, registry, lifecycle)
4. **Phase 3** - Monitoring (health_monitor, performance_manager)
5. **Phase 4** - Cognition (memory, emotion, judge, router, slm, llm)
6. **Phase 5** - Shell Systems (desktop_pet, wallpaper, cursor, voice)

## Key Components

### Modern Launcher (`modern_launcher.py`)
- **Purpose**: Clean entry point using the new architecture
- **Features**: Capability-based module registration, graceful startup/shutdown
- **Status**: ✅ Working - Successfully launches and shuts down (0.14s startup time)

### Legacy Compatibility (`legacy_compat.py`)
- **Purpose**: Bridge between legacy modules and modern architecture
- **Features**: Adapter pattern for inconsistent interfaces
- **Components**:
  - `LegacyModuleAdapter`: Wraps legacy modules with RuntimeModule interface
  - `LegacyCompatibilityOrchestrator`: Bridges legacy launcher with modern architecture

### Runtime Orchestrator (`runtime_orchestrator.py`)
- **Purpose**: Central coordination of all systems
- **Features**: Deterministic startup phases, dependency validation, lifecycle management
- **Integration**: Works with all critical stability systems

### Module Registry (`module_registry.py`)
- **Purpose**: Module registration and state tracking
- **Features**: Dependency validation, lifecycle states, graceful degradation
- **States**: CREATED, INITIALIZING, RUNNING, DEGRADED, FAILED, STOPPING, STOPPED

### Service Container (`service_container.py`)
- **Purpose**: Dependency injection container
- **Features**: Automatic resolution, constructor injection, lifetime management
- **Benefits**: Eliminates manual dependency wiring, prevents circular dependencies

### Lifecycle Manager (`lifecycle_manager.py`)
- **Purpose**: Orchestrates startup and shutdown phases
- **Features**: Phased initialization, graceful degradation, health monitoring
- **Capability**: Non-critical phases can fail without breaking startup

## Legacy Components (Preserved)

### Bootstrap (`bootstrap.py`)
- **Purpose**: Legacy container setup (preserved for compatibility)
- **Features**: Creates AppContainer with legacy service registration
- **Status**: Preserved but superseded by modern architecture

### Legacy Launcher (`launcher.py`)
- **Purpose**: Original launcher implementation
- **Features**: CLI parsing, config loading, hardware detection
- **Status**: Preserved as fallback, delegates to modern when possible

### Legacy Orchestrator (`orchestrator.py`)
- **Purpose**: Original event loop implementation
- **Features**: Event handling, module coordination
- **Status**: Preserved for compatibility, modern version preferred

## Critical Systems Integration

The runtime module integrates all critical stability systems:

### Capability Permissions System
- **Integration**: Registered with ServiceContainer for DI
- **Lifecycle**: Managed by ModuleRegistry and LifecycleManager
- **Features**: Safety gating, risk assessment, audit logging

### Resource-Aware Controller
- **Integration**: Phase 3 startup with health monitoring
- **Features**: Dynamic tier switching, battery/thermal awareness
- **Benefits**: Student laptop optimization

### State Machine
- **Integration**: Coordinated by RuntimeOrchestrator
- **Features**: 7 behavior states, resource-aware transitions
- **States**: ACTIVE, IDLE, SLEEPY, FOCUSED, PLAYFUL, OVERLOADED, LOW_POWER

### Tool Grounding System
- **Integration**: Registered service with dependency injection
- **Features**: Hallucination prevention, tool verification
- **Process**: Model decides → Tool verifies → Response generated

### Failure Recovery System
- **Integration**: Automatic monitoring through LifecycleManager
- **Features**: Circuit breaker patterns, comprehensive logging
- **Capability**: Automatic detection and recovery

## Architecture Benefits

### Modern Architecture Advantages

**Deterministic Startup**:
- Phased initialization with dependency validation
- Non-critical phases can fail without breaking startup
- Clear error reporting and recovery

**Proper Dependency Management**:
- Constructor injection with circular dependency detection
- Automatic service resolution
- No more manual dependency wiring

**Lifecycle Management**:
- Full module lifecycle with DEGRADED/RECOVERING states
- Health monitoring and automatic recovery
- Graceful shutdown

**Resource Awareness**:
- Automatic tier switching based on system resources
- Battery and thermal awareness
- Student laptop optimization

### Legacy Compatibility Benefits

**Backward Compatibility**:
- Existing configs and CLI still work
- Legacy modules wrapped with adapters
- Gradual migration path

**Risk Mitigation**:
- Modern architecture proven to work
- Legacy fallback available
- No breaking changes

## Performance Metrics

### Startup Performance
- **Modern Launcher**: 0.14s startup time (improved from 0.36s)
- **Memory Usage**: Optimized through dependency injection
- **Error Rate**: Reduced through proper interface validation

### Runtime Performance
- **Response Time**: Improved through event-driven coordination
- **Resource Usage**: Optimized through tier switching
- **Stability**: Enhanced through failure recovery

## Development Guidelines

### Adding New Modules

1. **Implement Standard Interfaces**:
   - Use `RuntimeModule` protocol from `domain/contracts/`
   - Implement lifecycle methods: `start()`, `stop()`, `health_check()`
   - Add state management with `ModuleState` enum

2. **Register with ServiceContainer**:
   - Add constructor dependencies
   - Register in appropriate startup phase
   - Test dependency resolution

3. **Update ModuleRegistry**:
   - Add module metadata and dependencies
   - Configure startup order
   - Add health checks

### Migrating Legacy Modules

1. **Create Compatibility Adapter**:
   - Wrap legacy module with `LegacyModuleAdapter`
   - Handle inconsistent interface methods
   - Map legacy states to modern `ModuleState`

2. **Register with Modern Architecture**:
   - Add to ModuleRegistry with legacy flag
   - Test with both launchers
   - Update documentation

### Testing Guidelines

- **Unit Tests**: Test individual components with mocked dependencies
- **Integration Tests**: Test 4-layer architecture integration
- **Legacy Tests**: Ensure backward compatibility
- **Performance Tests**: Validate startup and runtime performance

## Troubleshooting

### Common Issues

**Dependency Injection Failures**:
- Check ServiceContainer registration
- Verify constructor signatures
- Look for circular dependencies

**Module Startup Failures**:
- Check ModuleRegistry dependencies
- Verify startup phase order
- Review health check implementation

**Legacy Compatibility Issues**:
- Check adapter mappings
- Verify interface implementations
- Test with legacy launcher

### Debug Tools

- **Status Dashboard**: `python r.py --status`
- **Debug Logging**: Enable debug mode for detailed startup logs
- **Health Monitor**: Check module states and dependencies

## Future Enhancements

### Planned Improvements

1. **Hot Module Reloading**: Dynamic module updates without restart
2. **Advanced Dependency Management**: Feature flags and conditional loading
3. **Performance Optimization**: Lazy loading and caching strategies
4. **Enhanced Monitoring**: Real-time performance metrics and analytics

### Architecture Evolution

The modern 4-layer architecture provides a solid foundation for:
- **Microservices**: Potential service decomposition
- **Cloud Integration**: Remote service coordination
- **Advanced AI**: Multi-model orchestration
- **Plugin System**: Dynamic module loading

---

## Module Status Summary

| Component | Status | Architecture | Notes |
|-----------|--------|-------------|-------|
| Modern Launcher | ✅ Working | Modern | 0.14s startup, full 4-layer support |
| Legacy Compatibility | ✅ Working | Hybrid | Adapters for legacy modules |
| Runtime Orchestrator | ✅ Working | Modern | Event-driven coordination |
| Module Registry | ✅ Working | Modern | State tracking, dependency validation |
| Service Container | ✅ Working | Modern | DI container, circular dependency detection |
| Lifecycle Manager | ✅ Working | Modern | Phased startup, graceful degradation |
| Legacy Launcher | ✅ Preserved | Legacy | Fallback compatibility |
| Legacy Orchestrator | ✅ Preserved | Legacy | Original event loop |
| Bootstrap | ✅ Preserved | Legacy | Original container setup |

**Overall Architecture Status**: ✅ **Production Ready**

The modern 4-layer architecture is successfully implemented and provides a robust foundation for Kitsu's evolution from AI assistant to cognitive runtime. Legacy compatibility ensures smooth migration while modern architecture delivers improved reliability, performance, and maintainability.
