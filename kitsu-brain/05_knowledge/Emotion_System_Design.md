# Emotion System Design

## Concept Explanation
Kitsu's emotion system uses a three-layer model for personality expression:

**Mood (Primary Layer)**
- Core emotional states: behave, mean, flirty, protective
- Long-term emotional disposition
- Influences all responses

**Style (Expression Layer)**
- Communication patterns: chaotic, sweet, cold, direct, sarcastic, playful, eerie
- Determines tone and delivery style
- Controls emoji usage and response length

**State (Micro-behavior Layer)**
- Behavioral modes: normal, fox, glitch, analyst, submissive, detached
- Situational behavior adjustments
- Triggers specific animation sets

## How it applies to Kitsu
- **Personality consistency**: Emotions shape every response at every tier
- **Dynamic behavior**: Real-time emotion changes based on interactions
- **Visual feedback**: Emotions drive avatar expressions and animations
- **Safety system**: Prevents unsafe emotion combinations

## Key Implementation Details
- Emotions stored in decaying stack (recent emotions fade over time)
- Dominant emotion determines: `emotion → mood + style + state`
- Supports triggers (events that cause emotion changes)
- Supports reactions (emotion responses to stimuli)
- Personality overlays can modify base emotion rules

## Integration Points
- Receives events from EventBus
- Sends emotion state to UI/avatar system
- Influences response generation in all AI layers
- Persists emotion state between sessions
- Interacts with permission system for safety

## Limitations
- Requires careful balancing to avoid personality instability
- Complex state management increases debugging difficulty
- Performance overhead of emotion processing
- Risk of emotion loops or stuck states
