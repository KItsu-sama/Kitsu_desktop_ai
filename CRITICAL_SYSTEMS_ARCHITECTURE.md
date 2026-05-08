# Critical Systems Architecture

This document describes Kitsu's critical systems architecture that ensures safety, intelligence, and efficiency while maintaining the "alive" feeling through the modern 4-layer architecture.

## Overview

Kitsu has evolved beyond a simple AI assistant into a sophisticated **cognitive runtime** that requires:

1. **Safety** - Capability sandboxing prevents dangerous operations
2. **Intelligence** - Attention engine and tool grounding prevent hallucinations  
3. **Efficiency** - Resource-aware controller adapts to student laptops
4. **Life-like behavior** - State machine provides structured behavior states
5. **Energy awareness** - Budget system balances performance with battery life
6. **Robust operation** - 4-layer architecture ensures reliable startup and lifecycle management

## Modern 4-Layer Integration

The critical systems are integrated through the **modern 4-layer architecture**:

```
ServiceContainer → ModuleRegistry → LifecycleManager → RuntimeOrchestrator
```

### Architecture Integration

- **ServiceContainer**: Provides dependency injection for all critical systems
- **ModuleRegistry**: Manages lifecycle and dependencies of safety systems
- **LifecycleManager**: Orchestrates startup phases with graceful degradation
- **RuntimeOrchestrator**: Coordinates cross-system communication and monitoring

## Core Systems

### 1. Capability Sandbox System (`domain/capabilities/`)

**Purpose**: Prevent dangerous operations by requiring explicit permission.

**Key Components**:
- `CapabilityManager` - Central permission controller
- `Capability` enum - Defines dangerous operations (file access, desktop control, etc.)
- `PermissionLevel` - DENIED, PROMPT, TEMPORARY, GRANTED
- `AuditEntry` - Comprehensive audit logging

**Features**:
- Permission prompts with scope limits
- Temporary grants with expiration
- Risk assessment and auto-grant rules
- Comprehensive audit trail

**Example Usage**:
```python
from domain.capabilities import CAPABILITY_MANAGER, Capability

# Check permission before file operation
if CAPABILITY_MANAGER.check_permission(
    Capability.READ_FILES, 
    requested_by="file_manager",
    reason="User requested file listing",
    scope="/Downloads"
):
    # Proceed with file operation
    pass
```

### 2. Attention Engine (`domain/attention/`)

**Purpose**: Makes Kitsu feel "alive" by dynamically scoring and prioritizing events.

**Key Components**:
- `AttentionManager` - Central attention controller
- `AttentionEvent` - Events with novelty, emotional weight, urgency
- `AttentionType` - USER_INPUT, NOTIFICATION, DESKTOP_EVENT, etc.
- `UrgencyLevel` - LOW, NORMAL, HIGH, CRITICAL

**Features**:
- Dynamic scoring: `attention_score = novelty + emotional_weight + urgency`
- Boredom detection and idle behavior triggering
- Focus management and interruption handling
- Environmental awareness (music, desktop events)

**Example Usage**:
```python
from domain.attention import ATTENTION_MANAGER, AttentionType, UrgencyLevel

# Trigger emotional attention event
ATTENTION_MANAGER.trigger_emotional_event("happy", 0.8, source="user_compliment")

# Check if should interrupt current task
if ATTENTION_MANAGER.should_interrupt(current_task_priority=0.5):
    # Handle interruption
    pass
```

### 3. State Machine Layer (`domain/state/`)

**Purpose**: Provides structured behavior states for consistent, efficient operation.

**Key Components**:
- `BehaviorStateMachine` - State transition controller
- `BehaviorState` - ACTIVE, IDLE, SLEEPY, FOCUSED, PLAYFUL, OVERLOADED, LOW_POWER
- `StateConfig` - Resource allocation per state
- `StateTransitionRule` - Conditional state changes

**Features**:
- Seven behavior states with different resource profiles
- Smooth transitions and conditional rules
- Resource-aware state selection
- History tracking and analytics

**State Characteristics**:
- **ACTIVE**: Full responsiveness, high resource usage
- **IDLE**: Low activity, responsive when needed
- **SLEEPY**: Very low activity, minimal responses
- **FOCUSED**: Task-oriented, reduced interruptions
- **PLAYFUL**: High animation, expressive behavior
- **OVERLOADED**: System stressed, minimal features
- **LOW_POWER**: Battery saving mode

### 4. Resource-Aware Inference Controller (`domain/inference/`)

**Purpose**: Dynamically adapts to system resources for student laptop compatibility.

**Key Components**:
- `ResourceController` - System resource monitor
- `InferenceTier` - LLM → SLM → REFLEX
- `RenderTier` - 3D → 2D → CHIBI → MINIMAL
- `SystemMetrics` - CPU, memory, battery, thermal monitoring

**Features**:
- Automatic tier switching based on resources
- Battery and thermal awareness
- Performance monitoring and optimization
- Student laptop optimization

**Tier Switching Logic**:
```python
# High system load + low battery → REFLEX + MINIMAL
if system_load > 80% or battery < 20%:
    inference_tier = InferenceTier.REFLEX
    render_tier = RenderTier.MINIMAL

# Good conditions → LLM + FULL_3D  
elif system_load < 40% and battery > 50%:
    inference_tier = InferenceTier.LLM
    render_tier = RenderTier.FULL_3D
```

### 5. Tool Grounding System (`domain/grounding/`)

**Purpose**: The REAL hallucination solution - models don't invent, tools verify.

**Key Components**:
- `ToolGroundingSystem` - Central grounding controller
- `GroundingType` - FILE_SYSTEM, SYSTEM_INFO, NETWORK, etc.
- `VerificationStatus` - VERIFIED, FAILED, PARTIAL, DENIED
- `GroundedResponse` - Response generated from verified data

**Process Flow**:
1. Model decides what information is needed
2. Tool verifies and retrieves actual data
3. Response generated from tool output
4. Confidence score based on verification success

**Example Usage**:
```python
from domain.grounding import TOOL_GROUNDING_SYSTEM

# Ground user query to prevent hallucinations
results = TOOL_GROUNDING_SYSTEM.ground_request(
    request_id="query_001",
    query="What files are in Downloads?",
    source="user_query"
)

# Generate grounded response
response = TOOL_GROUNDING_SYSTEM.generate_grounded_response(
    original_query="What files are in Downloads?",
    model_response="There are files in Downloads.",
    grounding_results=results
)
```

### 6. Energy Budget System (`shared/budgets.py`)

**Purpose**: Balances performance with battery life for mobile efficiency.

**Key Components**:
- `BudgetManager` - Central budget controller
- `BudgetType` - LATENCY, ENERGY, CPU, MEMORY, NETWORK, ANIMATION
- `EnergyBudget` - Specialized energy management
- `BudgetState` - Current usage and status

**Features**:
- Real-time budget monitoring
- Automatic budget adjustments
- Energy-aware resource allocation
- Performance optimization

**Energy Budget Logic**:
```python
# Calculate energy budget factor (0.0 - 1.0)
if battery < 10%:
    energy_factor = 0.2  # Minimal power
elif battery < 30%:
    energy_factor = 0.5  # Reduced power
elif thermal_critical:
    energy_factor = 0.4  # Thermal throttling
else:
    energy_factor = 1.0  # Full power
```

## Integration: KitsuOrchestrator (`domain/core/`)

The `KitsuOrchestrator` is the central brain that coordinates all systems through the **modern 4-layer architecture**:

### System Integration Flow

1. **User Input** → Attention Engine → State Machine
2. **State Changes** → Resource Controller → Budget Manager  
3. **Budget Alerts** → Resource Controller → Inference/Render Tiers
4. **Capability Requests** → Safety Check → Permission Grant/Deny
5. **Model Responses** → Tool Grounding → Verified Output

### 4-Layer Architecture Benefits

**ServiceContainer Integration**:
- Automatic dependency resolution for all critical systems
- Constructor injection with circular dependency detection
- Service lifetime management

**ModuleRegistry Integration**:
- Centralized registration of all safety and stability systems
- Dependency validation and state tracking
- Graceful degradation when systems fail

**LifecycleManager Integration**:
- Phased startup with critical system initialization
- Health monitoring and automatic recovery
- Resource-aware module management

**RuntimeOrchestrator Integration**:
- Event-driven coordination between all critical systems
- Cross-system communication and state synchronization
- Real-time monitoring and adaptation

### Key Integrations

- **Attention → State Machine**: Emotional triggers update behavior state
- **Resource → State Machine**: CPU/memory/battery affect state transitions
- **Budget → Resource**: Energy limits force lower inference/render tiers
- **State → Budget**: LOW_POWER state enables energy saving
- **Capability → Safety**: All dangerous operations require permission
- **4-Layer → Critical Systems**: Architecture provides robust foundation for all safety features

## Safety Features

### Multi-Layer Safety

1. **Capability Sandbox**: Explicit permission required for dangerous operations
2. **Tool Grounding**: Models cannot invent information - must verify with tools
3. **State Protection**: Critical states (OVERLOADED, SLEEPY) disable risky features
4. **Budget Limits**: Resource exhaustion triggers automatic degradation
5. **Audit Trail**: All operations logged for security review

### Permission Levels

- **DENIED**: Never allowed
- **PROMPT**: Ask user each time
- **TEMPORARY**: Granted for limited duration (auto-expire)
- **GRANTED**: Permanent permission

### Risk Assessment

Each capability has a risk score (0.0 - 1.0):
- **High Risk** (0.8): DELETE_FILES, SHUTDOWN_PC, SYSTEM_SETTINGS
- **Medium Risk** (0.5): WRITE_FILES, CONTROL_WINDOWS, DESKTOP_AUTOMATION  
- **Low Risk** (0.2): READ_FILES, WEB_SEARCH, NETWORK_REQUESTS

## Performance Optimization

### Student Laptop Focus

The system is specifically optimized for student laptops:

1. **Automatic Tier Switching**: LLM → SLM → REFLEX based on resources
2. **Render Adaptation**: 3D → 2D → CHIBI → MINIMAL based on performance
3. **Battery Awareness**: Reduces activity when battery low
4. **Thermal Throttling**: Prevents overheating on sustained use
5. **Memory Management**: Automatic cleanup and cache management

### Resource Allocation

Each behavior state has specific resource budgets:
- **ACTIVE**: 80% CPU, 70% memory, 60 FPS animations
- **IDLE**: 30% CPU, 30% memory, 15 FPS animations  
- **LOW_POWER**: 20% CPU, 20% memory, 8 FPS animations

## Usage Examples

### Basic Setup

```python
from domain.core import KITSU_ORCHESTRATOR

# Start the orchestrator
await KITSU_ORCHESTRATOR.start()

# Process user request
response = KITSU_ORCHESTRATOR.process_user_request(
    "What files are in my Downloads folder?"
)

print(f"Response: {response['response']}")
print(f"Confidence: {response['confidence']}")
print(f"Sources: {response['sources']}")
```

### Monitoring System Status

```python
# Get detailed system status
status = KITSU_ORCHESTRATOR.get_detailed_status()

print(f"System Health: {status['orchestrator']['healthy']}")
print(f"Safety Level: {status['orchestrator']['safety_level']}")
print(f"Performance Mode: {status['orchestrator']['performance_mode']}")
print(f"Current State: {status['state_machine']['current_state']['current_state']}")
print(f"Energy Factor: {status['budgets']['energy_factor']}")
```

### Custom Capability Check

```python
from domain.capabilities import CAPABILITY_MANAGER, Capability

# Check if desktop automation is allowed
if CAPABILITY_MANAGER.check_permission(
    Capability.DESKTOP_AUTOMATION,
    requested_by="automation_module",
    reason="User requested window management",
    scope="current_window"
):
    # Perform desktop automation
    pass
else:
    # Handle permission denied
    pass
```

## Configuration

### System Configuration

All systems use sensible defaults but can be configured:

```python
# Configure capability permissions
CAPABILITY_MANAGER.grant_permanent(Capability.READ_FILES)
CAPABILITY_MANAGER.grant_temporary(Capability.WRITE_FILES, duration=300)

# Configure state machine
BEHAVIOR_STATE_MACHINE.force_state(BehaviorState.PLAYFUL)

# Configure resource controller
RESOURCE_CONTROLLER.force_inference_tier(InferenceTier.SLM)
RESOURCE_CONTROLLER.force_render_tier(RenderTier.CHIBI_2D)
```

### Budget Configuration

```python
# Adjust budget limits
BUDGET_MANAGER.limits[BudgetType.CPU].max_value = 60.0  # 60% CPU max
BUDGET_MANAGER.limits[BudgetType.MEMORY].max_value = 50.0  # 50% memory max
```

## Monitoring and Debugging

### Audit Logs

All capability usage is logged:
```python
# Get capability audit log
audit_log = CAPABILITY_MANAGER.get_audit_log(limit=50)
for entry in audit_log:
    print(f"{entry['capability']} by {entry['requested_by']} -> {entry['granted']}")
```

### Performance Metrics

```python
# Get grounding system statistics
stats = TOOL_GROUNDING_SYSTEM.get_statistics()
print(f"Success Rate: {stats['success_rate']:.2%}")
print(f"Average Confidence: {stats['average_confidence']:.2f}")

# Get resource controller status
resource_status = RESOURCE_CONTROLLER.get_system_status()
print(f"Current Inference Tier: {resource_status['tiers']['inference']}")
print(f"Current Render Tier: {resource_status['tiers']['render']}")
```

## Future Enhancements

### Planned Features

1. **Machine Learning**: Learn user patterns for better state prediction
2. **Advanced Grounding**: More sophisticated tool verification
3. **Network Awareness**: Adapt based on network quality and cost
4. **Multi-Modal**: Integrate vision and audio grounding
5. **Cloud Integration**: Offload processing when resources available

### Extensibility

The architecture is designed for extensibility:

- **New Capabilities**: Add to `Capability` enum
- **New Attention Types**: Extend `AttentionType` enum  
- **New Behavior States**: Add to `BehaviorState` enum
- **New Grounding Tools**: Register with `ToolGroundingSystem`
- **New Budget Types**: Add to `BudgetType` enum

## Architecture Evolution

### From Legacy to Modern

Kitsu has evolved from a traditional AI assistant to a **modern cognitive runtime**:

**Legacy Architecture**:
- Simple startup sequence
- Manual dependency management
- Basic error handling
- Monolithic system design

**Modern 4-Layer Architecture**:
- Deterministic phased startup
- Automatic dependency injection
- Comprehensive failure recovery
- Modular, extensible design

### Benefits of Modern Architecture

**For Critical Systems**:
1. **Reliable Startup**: Phased initialization ensures all safety systems are properly loaded
2. **Dependency Management**: Automatic resolution prevents configuration errors
3. **Health Monitoring**: Continuous monitoring of all critical systems
4. **Graceful Degradation**: System continues operating even if some components fail
5. **Recovery Mechanisms**: Automatic detection and recovery from failures

**For Development**:
1. **Clear Separation**: Each layer has distinct responsibilities
2. **Testability**: Individual components can be tested in isolation
3. **Extensibility**: New safety systems can be easily added
4. **Maintainability**: Modular design makes updates safer

## Conclusion

This critical systems architecture, built on the **modern 4-layer foundation**, ensures Kitsu remains:

- **Safe**: Capability sandboxing prevents dangerous operations
- **Intelligent**: Attention engine and tool grounding prevent hallucinations
- **Efficient**: Resource-aware controller adapts to any hardware
- **Alive**: State machine provides life-like, responsive behavior
- **Mobile**: Energy budget system optimizes for battery life
- **Robust**: 4-layer architecture provides reliable operation and recovery

The clean shell architecture with the `KitsuOrchestrator` at its core, built on the modern 4-layer foundation, provides a robust, scalable, and maintainable platform for future development while maintaining the balance between sophistication and safety that makes Kitsu unique.
