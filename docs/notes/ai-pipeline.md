---
title: AI Pipeline
tags: [ai, pipeline, fastbrain, slm, llm]
links: [[project-overview], [system-architecture], [fastbrain-system], [emotion-system]]
created: 2026-04-27
updated: 2026-04-27
---

# AI Pipeline

## Overview

The AI pipeline follows a **tiered processing approach** with FastBrain → SLM → LLM layers, ensuring instant responses while maintaining depth when needed.

## Processing Flow

```
User Input
    │
    ▼
┌─────────────┐     always-on, learns from every response
│  FastBrain  │◄────────────────────────────────────────┐
│ (Markov +   │                                         │
│  Huffman)   │──► known input? respond instantly       │
└──────┬──────┘                                         │
       │ unknown                                        │
       ▼                                                │
┌─────────────┐                                         │
│ PolicyRouter │──► classify intent                      │
└──────┬──────┘                                         │
       │                                                │
  ┌────┴─────────────────┐                              │
  │                      │                              │
  ▼                      ▼                              │
┌──────┐           ┌──────────┐                         │
│ SLM  │           │   LLM    │                         │
│(fox  │           │(thinking)│                         │
│style)│           └──────────┘                         │
└──┬───┘                 │                              │
   └──────────┬──────────┘                              │
              ▼                                         │
    ┌──────────────────┐                                │
    │  EmotionEngine   │ shapes every response          │
    └────────┬─────────┘                                │
             │                                          │
             ▼                                          │
    final response ─────────────────────────────────────┘
             │          fed back into FastBrain
             ▼
         User + Avatar
```

## FastBrain Layer

### Purpose
- **Instant responses** (0ms latency)
- **Pattern recognition** for common inputs
- **Self-learning** through usage feedback

### Implementation
- **Markov chains** for sequence prediction
- **Huffman compression** for efficient storage
- **Frequency scoring**: `score = frequency × recency`

### Capabilities
- Common inputs (greetings, repeated phrases)
- Spam detection
- Template-based responses
- Learning loop with confirmed outputs

## SLM Layer (Small Language Model)

### Purpose
- **Personality shaping** with fox-like tone
- **Lightweight reasoning** for normal conversation
- **Style consistency** across responses

### Features
- Context-aware responses
- Personality injection
- Resource-efficient operation
- Offline capability

## LLM Layer (Large Language Model)

### Purpose
- **Deep reasoning** for complex queries
- **Web search integration**
- **Analysis and synthesis**

### Usage Conditions
- Complex queries only
- On-demand loading/unloading
- API or local GGUF support
- Resource-intensive operations

## Policy Router

### Function
- **Intent classification** and routing
- **Complexity scoring** for tier selection
- **Resource management** and optimization

### Decision Logic
```python
def route_input(user_input, context):
    if fastbrain.has_pattern(user_input):
        return "fastbrain"
    
    complexity = calculate_complexity(user_input)
    if complexity < threshold:
        return "slm"
    else:
        return "llm"
```

## Postprocessing

### Response Ranking
- Multiple candidate generation
- Quality scoring and ranking
- Safety filtering
- Personality alignment

### Safety Systems
- Content filtering
- Response validation
- Emotion appropriateness checks

## Learning Integration

### FastBrain Learning
- Pattern extraction from confirmed responses
- Automatic promotion of frequent inputs
- Feedback loop from all layers

### Model Adaptation
- User preference learning
- Response quality improvement
- Personality refinement

## Performance Optimization

### Resource Management
- Dynamic model loading
- Memory-efficient caching
- Background preloading

### Latency Optimization
- Parallel processing where possible
- Response streaming
- Early termination for simple queries

## Configuration

### Tier Selection
```yaml
profiles:
  ultra_low:
    use_fastbrain: true
    use_slm: false
    use_llm: false
  
  balanced:
    use_fastbrain: true
    use_slm: true
    use_llm: false
  
  full:
    use_fastbrain: true
    use_slm: true
    use_llm: true
```

### Model Parameters
- Context window sizes
- Temperature settings
- Response length limits
- Timeout configurations

## Related Documentation

- [[fastbrain-system]] - FastBrain implementation details
- [[slm-implementation]] - Small language model details
- [[llm-integration]] - Large language model bridge
- [[emotion-system]] - Emotion processing integration
- [[learning-systems]] - Adaptive learning mechanisms
