# Vector-Based Personality System

## Overview

The vector-based personality system replaces discrete personality states with continuous 10-dimensional vectors, enabling smooth, natural transitions and more nuanced emotional expression. This system maintains full backward compatibility with existing enums while providing a foundation for advanced AI behavior.

## Architecture

```text
Emotion Events → EmotionStack (existing) → PersonalityVector → 
Rule Engine (floats) → Emotional Inertia → Prompt Signal Builder → 
fastbrain → SLM → LLM pipeline
                                    ↓
                              Visual Output Adapters
```

## Core Components

### 1. PersonalityVector (`vector.py`)

10-dimensional continuous personality space:

**Core Affect (4 dimensions):**

- `warmth`: Emotional warmth vs coldness (0.0 = cold, 1.0 = warm)
- `edge`: Sharpness/sass vs gentleness (0.0 = gentle, 1.0 = edgy)  
- `chaos`: Unpredictability vs stability (0.0 = stable, 1.0 = chaotic)
- `energy`: Activity level vs passivity (0.0 = tired, 1.0 = energetic)

**Relational (2 dimensions):**

- `affection`: Caring vs detached (0.0 = distant, 1.0 = affectionate)
- `protectiveness`: Protective vs neutral (0.0 = neutral, 1.0 = protective)

**Cognitive (2 dimensions):**

- `focus`: Concentration vs distraction (0.0 = distracted, 1.0 = focused)
- `mystery`: Enigmatic vs straightforward (0.0 = direct, 1.0 = mysterious)

**Behavioral (2 dimensions):**

- `verbosity`: Talkativeness vs conciseness (0.0 = brief, 1.0 = verbose)
- `expressiveness`: Emotional expression vs restraint (0.0 = reserved, 1.0 = expressive)

### 2. Personality Presets (`presets.py`)

Maps existing enums to vector presets:

- **Mood Presets**: behave, mean, flirty, protective
- **Style Presets**: chaotic, sweet, cold, direct, sarcastic, playful, eerie
- **State Presets**: idle, active, sleep, normal, fox, glitch, analyst, submissive, detached
- **Role Presets**: default, caretaker, tutor, companion, observer

### 3. PersonalityBuilder (`builder.py`)

Converts emotion stacks to personality vectors:

- Weighted blending (not winner-takes-all)
- Emotion importance weighting
- Resistance-based modulation
- Role-based final adjustments

### 4. Emotional Inertia (`inertia.py`)

Provides smooth transitions:

- Physics-based velocity and acceleration
- Dimension-specific inertia factors
- Configurable damping and max velocity
- No randomness - fully deterministic

### 5. Vector Rule Engine (`rules.py`)

Float-based safety and behavioral rules:

- Continuous adjustments instead of state switching
- Threshold and combination conditions
- Safety constraint enforcement
- Validation and warnings

### 6. Prompt Signal Builder (`signals.py`)

Converts vectors to LLM-ready signals:

- Natural language tone descriptions
- Behavioral parameters (verbosity, emoji weight, formality)
- Complexity assessment
- Confidence scoring

### 7. Visual Adapters (`adapters.py`)

Maps vectors to visual parameters:

- **Avatar Adapter**: Facial expressions, body language, visual effects
- **Shimeji Adapter**: Movement behavior, interaction patterns, personality expression
- Pure data output (event-driven, no direct coupling)

### 8. Energy System (`energy.py`)

Manages energy cycles and decay:

- Time-based idle decay per dimension
- Sleep mode detection and triggers
- Energy recovery and fatigue tracking
- Natural energy simulation

## Key Features

### Smooth Transitions

- No more hard personality jumps
- Gradual evolution between states
- Configurable transition speeds
- Natural-feeling changes

### Weighted Blending

- Multiple emotions influence simultaneously
- Importance-based emotion weighting
- Resistance modulates new influences
- Deterministic, reproducible results

### Backward Compatibility

- All existing enums preserved
- Enums act as initializers, not final states
- Legacy mode mapping maintained
- Gradual migration path

### Safety Constraints

- Continuous-space safety rules
- Prevents conflicting personality traits
- Validation and warning system
- Clamp values, don't switch states

## Usage Examples

### Basic Personality Building

```python
from personality.vector import PersonalityVector
from personality.builder import PersonalityBuilder
from personality.presets import get_mood_preset

# Create emotion stack
emotion_stack = [
    {"name": "happy", "intensity": 0.7, "duration": 10.0},
    {"name": "affection", "intensity": 0.5, "duration": 8.0}
]

# Build personality vector
builder = PersonalityBuilder()
personality = builder.build_personality(emotion_stack, role="companion")
```

### Applying Emotional Inertia

```python
from personality.inertia import EmotionalInertia

inertia = EmotionalInertia(base_inertia=0.3)
smooth_personality = inertia.apply_inertia(target_vector)
```

### Generating Prompt Signals

```python
from personality.signals import build_prompt_signal

signal = build_prompt_signal(personality)
print(f"Tone: {signal.tone}")
print(f"Verbosity: {signal.verbosity_target} words")
print(f"Emoji weight: {signal.emoji_weight:.2f}")
```

### Visual Parameter Mapping

```python
from personality.adapters import to_avatar_params, to_shimeji_params

avatar_params = to_avatar_params(personality)
shimeji_params = to_shimeji_params(personality)
```

### Energy Management

```python
from personality.energy import EnergySystem

energy = EnergySystem()
decayed_personality = energy.apply_decay(personality)
energy.boost_energy(0.3)  # Immediate energy boost
```

## Configuration

### Inertia Settings

```python
inertia = EmotionalInertia(
    base_inertia=0.3,    # Resistance to change
    damping=0.8,          # Velocity damping
    max_velocity=0.1       # Maximum rate of change
)

# Dimension-specific inertia
inertia.set_dimension_inertia("warmth", 0.4)  # Warmth changes gradually
inertia.set_dimension_inertia("energy", 0.2)  # Energy can change quickly
```

### Energy Decay Rates

```python
energy = EnergySystem()
energy.set_decay_rates("energy", idle_rate=0.02, recovery_rate=0.05)
```

### Rule Engine

```python
from personality.rules import VectorRuleEngine, create_threshold_rule

engine = VectorRuleEngine()

# Add custom rule
custom_rule = create_threshold_rule(
    name="high_chaos_limit",
    priority=75,
    dimension="chaos",
    min_val=0.8,
    adjustments={"chaos": (0.0, 0.7)},
    description="Limit excessive chaos"
)
engine.add_rule(custom_rule)
```

## Testing

Run the complete test suite:

```bash
cd personality
python test_vector_system.py
```

The test demonstrates:

- Vector creation and operations
- Emotion stack processing
- Rule application and validation
- Smooth inertia transitions
- Prompt signal generation
- Visual parameter mapping
- Energy decay and recovery

## Migration Guide

### From Discrete States

1. Replace `Personality(mood, style, state, role)` with `PersonalityVector`
2. Use `PersonalityBuilder` instead of direct enum mapping
3. Apply `VectorRuleEngine` for safety constraints
4. Use `EmotionalInertia` for smooth transitions

### Integration Points

- **EmotionEngine**: Replace `update_personality()` with vector-based flow
- **LLM Integration**: Use `PromptSignalBuilder` output instead of discrete states
- **Visual Systems**: Use adapter outputs instead of state-based animations
- **Memory System**: Store vectors instead of state tuples

## Performance Considerations

### Low-Spec Optimization

- Vector operations are lightweight (O(1) per dimension)
- Minimal memory footprint (10 floats per personality)
- No complex calculations in main loop
- Configurable update frequencies

### CPU Usage

- Basic vector math: ~0.1ms per update
- Rule engine: ~0.5ms per pass (typically 1-2 passes)
- Inertia system: ~0.2ms per transition
- Total: <1ms per personality update

## Future Enhancements

### Machine Learning Integration

- Vector space suitable for ML training
- Emotion pattern recognition
- Personalized adaptation learning
- Predictive personality modeling

### Advanced Visual Systems

- More sophisticated avatar animations
- Context-aware expression mapping
- Multi-character personality interactions
- Environmental response systems

### Extended Dimensions

- Cultural adaptation dimensions
- Temporal mood tracking
- Social context awareness
- Long-term personality evolution

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure proper path setup for relative imports
2. **Syntax Errors**: Check for balanced parentheses in vector operations
3. **Performance**: Monitor rule engine pass counts and inertia complexity
4. **Validation**: Use rule engine validation to catch unsafe combinations

### Debug Tools

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check rule application
engine = get_rule_engine()
applicable = engine.get_applicable_rules(vector)
warnings = engine.validate_vector(vector)

# Monitor inertia transitions
inertia = EmotionalInertia()
transition_info = inertia.get_transition_info()
```

## Architecture Benefits

### Over Discrete States

- **Smooth Transitions**: No jarring personality jumps
- **Nuanced Expression**: Infinite personality combinations
- **Natural Evolution**: Continuous personality development
- **Better AI Integration**: Vector space maps well to ML models

### Maintained Compatibility

- **Enum Preservation**: Existing code continues to work
- **Gradual Migration**: Can adopt incrementally
- **Legacy Support**: Old and new systems can coexist
- **Clear Upgrade Path**: Well-documented transition process

This vector-based system provides a solid foundation for advanced AI personality while maintaining the simplicity and reliability of the existing architecture.
