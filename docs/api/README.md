# Kitsu API Documentation

## Overview

This section contains comprehensive API documentation for Kitsu's modern 4-layer architecture and critical systems. The APIs are designed to provide both internal module interfaces and external integration points.

## Architecture APIs

### Modern 4-Layer Architecture APIs

The modern 4-layer architecture provides standardized interfaces for all system components:

#### ServiceContainer API
- **Purpose**: Dependency injection and service management
- **Key Methods**:
  - `register(service_class, instance=None, singleton=False)`
  - `get(service_class)` - Automatic dependency resolution
  - `create(service_class, **kwargs)` - Create with dependencies

#### ModuleRegistry API
- **Purpose**: Module registration and lifecycle management
- **Key Methods**:
  - `register_module(module_class, metadata)`
  - `get_module_state(module_name)`
  - `get_all_states()`
  - `validate_dependencies()`

#### LifecycleManager API
- **Purpose**: Phased startup and shutdown orchestration
- **Key Methods**:
  - `startup_phases()` - Execute deterministic startup
  - `shutdown_phases()` - Graceful shutdown
  - `get_current_phase()`
  - `is_phase_complete(phase)`

#### RuntimeOrchestrator API
- **Purpose**: Event-driven coordination and runtime behavior
- **Key Methods**:
  - `start()` - Start main event loop
  - `stop()` - Stop gracefully
  - `get_system_status()` - Comprehensive status
  - `handle_event(event)` - Process system events

### Critical Systems APIs

#### Capability Permissions System API

**Location**: `domain/capabilities/capability_manager.py`

```python
# Permission checking
has_permission = CAPABILITY_MANAGER.check_permission(
    Capability.READ_FILES,
    requested_by="file_manager",
    reason="User requested file listing",
    scope="/Downloads"
)

# Granting permissions
CAPABILITY_MANAGER.grant_permanent(Capability.READ_FILES)
CAPABILITY_MANAGER.grant_temporary(Capability.WRITE_FILES, duration=300)

# Audit trail
audit_log = CAPABILITY_MANAGER.get_audit_log(limit=50)
```

**Capabilities Enum**:
- `READ_FILES` - File system read access
- `WRITE_FILES` - File system write access
- `DELETE_FILES` - File deletion operations
- `SYSTEM_SETTINGS` - System configuration changes
- `DESKTOP_AUTOMATION` - Desktop control operations
- `NETWORK_REQUESTS` - Network access
- `AUDIO_RECORDING` - Microphone access

**Permission Levels**:
- `DENIED` - Never allowed
- `PROMPT` - Ask user each time
- `TEMPORARY` - Granted for limited duration
- `GRANTED` - Permanent permission

#### Resource-Aware Controller API

**Location**: `domain/inference/resource_controller.py`

```python
# Get current system status
status = RESOURCE_CONTROLLER.get_system_status()
print(f"Inference Tier: {status['tiers']['inference']}")
print(f"Render Tier: {status['tiers']['render']}")

# Force tier changes
RESOURCE_CONTROLLER.force_inference_tier(InferenceTier.SLM)
RESOURCE_CONTROLLER.force_render_tier(RenderTier.CHIBI_2D)

# Monitor performance
metrics = RESOURCE_CONTROLLER.get_performance_metrics()
```

**Inference Tiers**:
- `LLM` - Full language model (high resource usage)
- `SLM` - Small language model (medium resource usage)
- `REFLEX` - Fast responses only (low resource usage)

**Render Tiers**:
- `FULL_3D` - Full 3D avatar rendering
- `CHIBI_2D` - 2D chibi avatar
- `MINIMAL` - Minimal visual representation

#### State Machine API

**Location**: `domain/state/behavior_state_machine.py`

```python
# Get current state
current_state = BEHAVIOR_STATE_MACHINE.get_current_state()

# Force state transition
BEHAVIOR_STATE_MACHINE.force_state(BehaviorState.PLAYFUL)

# Get state history
history = BEHAVIOR_STATE_MACHINE.get_state_history(limit=10)

# Check transition rules
can_transition = BEHAVIOR_STATE_MACHINE.can_transition_to(
    BehaviorState.FOCUSED
)
```

**Behavior States**:
- `ACTIVE` - Full responsiveness, high resource usage
- `IDLE` - Low activity, responsive when needed
- `SLEEPY` - Very low activity, minimal responses
- `FOCUSED` - Task-oriented, reduced interruptions
- `PLAYFUL` - High animation, expressive behavior
- `OVERLOADED` - System stressed, minimal features
- `LOW_POWER` - Battery saving mode

#### Tool Grounding System API

**Location**: `domain/grounding/tool_grounding.py`

```python
# Ground a user request
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

# Get statistics
stats = TOOL_GROUNDING_SYSTEM.get_statistics()
print(f"Success Rate: {stats['success_rate']:.2%}")
```

**Grounding Types**:
- `FILE_SYSTEM` - File system operations
- `SYSTEM_INFO` - System information retrieval
- `NETWORK` - Network operations
- `DESKTOP` - Desktop interactions
- `MEMORY` - Memory operations

**Verification Status**:
- `VERIFIED` - Tool successfully verified information
- `FAILED` - Tool verification failed
- `PARTIAL` - Partial verification
- `DENIED` - Access denied
- `ERROR` - Tool error occurred

#### Failure Recovery System API

**Location**: `domain/core/failure_recovery.py`

```python
# Manual recovery trigger
await FAILURE_RECOVERY.handle_failure(
    category=FailureCategory.MEMORY,
    severity=FailureSeverity.HIGH,
    context="Memory allocation failed"
)

# Get recovery statistics
stats = FAILURE_RECOVERY.get_recovery_statistics()

# Configure recovery rules
FAILURE_RECOVERY.add_recovery_rule(
    trigger_condition=lambda: memory_usage > 90,
    recovery_action="clear_cache",
    max_attempts=3
)
```

**Failure Categories**:
- `MEMORY` - Memory allocation failures
- `CPU` - CPU overload conditions
- `MODEL` - AI model failures
- `NETWORK` - Network connectivity issues
- `FILESYSTEM` - File system errors
- `PERMISSION` - Permission denied errors
- `DEPENDENCY` - Dependency resolution failures
- `TIMEOUT` - Operation timeouts

## Integration APIs

### Desktop Integration API

**Location**: `interfaces/desktop/`

```python
# Desktop automation (requires permission)
if CAPABILITY_MANAGER.check_permission(Capability.DESKTOP_AUTOMATION):
    desktop_controller.move_window(window_id, x, y)
    desktop_controller.set_wallpaper(image_path)

# System information
system_info = desktop_gateway.get_system_info()
battery_info = desktop_gateway.get_battery_status()
```

### AI Pipeline API

**Location**: `domain/ai/`

```python
# FastBrain (instant responses)
response = FAST_BRAIN_PROVIDER.generate_response("hello")
if response:
    print(response.text)  # Instant response

# SLM (styled reasoning)
response = await SLM_PROVIDER.generate_response(
    "How are you today?",
    personality="playful"
)

# LLM (complex reasoning)
response = await LLM_PROVIDER.generate_response(
    "Explain quantum computing",
    context=conversation_history
)
```

### Personality System API

**Location**: `domain/personality/`

```python
# Get current emotional state
emotion_state = EMOTION_ENGINE.get_current_state()
print(f"Emotion: {emotion_state.emotion}")
print(f"Intensity: {emotion_state.intensity}")

# Trigger emotional response
EMOTION_ENGINE.process_user_interaction(
    interaction_type="headpat",
    intensity=0.8
)

# Get personality mapping
personality = PERSONALITY_mapper.get_current_personality()
print(f"Mood: {personality.mood}")
print(f"Style: {personality.style}")
```

## External APIs

### REST API

**Base URL**: `http://localhost:8080/api/v1`

#### Authentication
All API calls require authentication token:
```http
Authorization: Bearer <token>
```

#### Endpoints

**System Status**
```http
GET /api/v1/status
```
Returns comprehensive system status including all critical systems.

**Module Control**
```http
POST /api/v1/modules/{module_name}/start
POST /api/v1/modules/{module_name}/stop
GET /api/v1/modules/{module_name}/status
```

**Configuration**
```http
GET /api/v1/config
PUT /api/v1/config
PATCH /api/v1/config/{section}
```

**AI Interaction**
```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "Hello Kitsu!",
  "context": "casual"
}
```

**Personality**
```http
GET /api/v1/personality/current
POST /api/v1/personality/trigger
Content-Type: application/json

{
  "emotion": "happy",
  "intensity": 0.8,
  "source": "user_interaction"
}
```

### WebSocket API

**Endpoint**: `ws://localhost:8080/ws`

#### Events
- `status_update` - System status changes
- `emotion_changed` - Emotional state updates
- `module_status` - Module lifecycle events
- `resource_alert` - Resource usage warnings
- `user_message` - Real-time user messages

#### Example WebSocket Client
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

// Send user message
ws.send(JSON.stringify({
    type: 'user_message',
    message: 'Hello Kitsu!'
}));
```

## Development APIs

### Testing API

**Location**: `tests/api/`

```python
# Mock service container for testing
mock_container = MockServiceContainer()
mock_container.register(MockResourceController)

# Test module lifecycle
test_module = TestModule()
lifecycle_manager = LifecycleManager(mock_container)
await lifecycle_manager.start_module(test_module)

# Assert module state
assert test_module.get_state() == ModuleState.RUNNING
```

### Debug API

**Location**: `runtime/debug/`

```python
# Enable debug mode
DEBUG_MODE.enable()

# Get debug information
debug_info = DEBUG_MODE.get_system_debug_info()
print(f"Registered Services: {debug_info['services']}")
print(f"Module States: {debug_info['modules']}")

# Performance profiling
with DEBUG_MODE.profile("operation_name"):
    # Code to profile
    pass

# Get performance report
report = DEBUG_MODE.get_performance_report()
```

## API Versioning

### Version Strategy
- **Major Version**: Breaking changes to API structure
- **Minor Version**: New features, backward compatible
- **Patch Version**: Bug fixes, security updates

### Current Version: **v1.0.0**

### Version Compatibility
- **v1.x**: Stable API with backward compatibility
- **v0.x**: Development versions, may break compatibility

### Deprecation Policy
- **6 months** notice for breaking changes
- **12 months** support for deprecated APIs
- **Automatic migration** tools when possible

## Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Insufficient permissions for this operation",
    "details": {
      "required_capability": "DELETE_FILES",
      "current_level": "PROMPT"
    },
    "timestamp": "2026-05-08T10:34:00Z",
    "request_id": "req_123456"
  }
}
```

### Error Codes
- `PERMISSION_DENIED` - Insufficient permissions
- `RESOURCE_UNAVAILABLE` - Resource not available
- `MODULE_FAILED` - Module operation failed
- `INVALID_REQUEST` - Malformed request
- `RATE_LIMITED` - Too many requests
- `SYSTEM_ERROR` - Internal system error

## Rate Limiting

### Default Limits
- **REST API**: 100 requests per minute
- **WebSocket**: 10 messages per second
- **File Operations**: 10 operations per minute
- **AI Requests**: 20 requests per minute

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Security

### Authentication Methods
- **API Keys**: For external integrations
- **JWT Tokens**: For web applications
- **Session Tokens**: For desktop applications

### Permission Model
All API calls are gated through the capability permissions system. See the Capability Permissions System API for details.

### Data Protection
- **Encryption**: All sensitive data encrypted at rest
- **Transport**: HTTPS/WSS required for production
- **Audit**: All API calls logged for security review

## Examples

### Complete API Integration Example

```python
import asyncio
import aiohttp
from kitsu_api import KitsuClient

async def main():
    # Initialize client
    client = KitsuClient(
        base_url="http://localhost:8080",
        api_key="your-api-key"
    )
    
    # Get system status
    status = await client.get_status()
    print(f"System Status: {status['overall']}")
    
    # Send message
    response = await client.send_message("Hello Kitsu!")
    print(f"Response: {response['text']}")
    
    # Check emotional state
    emotion = await client.get_emotion_state()
    print(f"Current Emotion: {emotion['emotion']}")
    
    # Trigger happy emotion
    await client.trigger_emotion("happy", 0.8)

if __name__ == "__main__":
    asyncio.run(main())
```

### WebSocket Integration Example

```javascript
class KitsuWebSocket {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.handlers = {};
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('Connected to Kitsu WebSocket');
            this.send({type: 'subscribe', events: ['emotion_changed', 'status_update']});
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleEvent(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }
    
    handleEvent(data) {
        const handler = this.handlers[data.type];
        if (handler) {
            handler(data);
        }
    }
    
    on(eventType, handler) {
        this.handlers[eventType] = handler;
    }
}

// Usage
const kitsu = new KitsuWebSocket('ws://localhost:8080/ws');
kitsu.connect();

kitsu.on('emotion_changed', (data) => {
    console.log('Emotion changed:', data.emotion);
});

kitsu.on('status_update', (data) => {
    console.log('Status update:', data.status);
});
```

## Support

### Documentation
- **API Reference**: Detailed endpoint documentation
- **Code Examples**: Integration examples in multiple languages
- **Tutorials**: Step-by-step integration guides

### Community
- **GitHub Discussions**: API questions and discussions
- **Discord**: Real-time support and community help
- **Issue Tracker**: Bug reports and feature requests

### Getting Help
- **API Status**: Check status at `http://localhost:8080/api/v1/status`
- **Debug Mode**: Enable debug logging for troubleshooting
- **Health Check**: Monitor system health and performance

---

**API Version**: v1.0.0  
**Last Updated**: 2026-05-08  
**Compatibility**: Kitsu Desktop AI v2.0+
