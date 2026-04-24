# Emotion System

This document describes Kitsu's emotion system, how it maps emotional signals to personality state, and where the configuration lives in the codebase.

## Overview

Kitsu uses a layered emotion system to shape behavior and response style.

Primary goals:
- Track active emotions over time
- Convert emotion signals into a mood and expression style
- Apply safe, personality-driven behavior rules
- Support triggers, reactions, and personality overlays

## Architecture

The emotion system is built around a two-layer personality architecture plus a micro-behavior state layer:

1. Mood (primary axis)
   - `behave`
   - `mean`
   - `flirty`
   - `protective`

2. Style (expression overlay)
   - `chaotic`
   - `sweet`
   - `cold`
   - `direct`
   - `sarcastic`
   - `playful`
   - `eerie`

3. State (micro-behavior)
   - `normal`
   - `fox`
   - `glitch`
   - `analyst`
   - `submissive`
   - `detached`

The active mood + style determine Kitsu's personality when producing output, while the state layer adds fine-grained expression behavior.

## Core files

- `core/config/personality_config.py`
  - Defines the authoritative mood/style values used by `manager/emotion_manager.py`
  - Contains emotion → mood/style maps and style rules

- `core/personality/emotion_config.py`
  - Defines emotion system configuration for `core/personality/emotion_engine.py`
  - Adds additional state mappings, safety guidance, legacy compatibility, and role overlay metadata

- `core/personality/emotion_engine.py`
  - Manages emotion stack, decay, and personality mapping in the core personality layer
  - Integrates with `KitsuSelf` and trigger management

- `manager/emotion_manager.py`
  - Provides a manager variant of the emotion lifecycle
  - Uses `EmotionState`, `EmotionEntry`, and `EmotionStack` data structures

- `core/personality/emotion_model.py`
  - Defines pure data structures for emotion entries, stacks, and exported state

- `core/personality/trigger_manager.py`
  - Manages triggers that fire emotion effects based on events

- `core/personality/reaction_mapper.py`
  - Maps gestures, emojis, and system events to emotional reactions

## Emotion stack and decay

The emotion system is stack-based:
- Emotions are pushed onto a stack with `name`, `intensity`, `timestamp`, and `expire`
- Active emotions decay over time
- The dominant emotion is calculated by weighted score after decay
- Intensity and persistence control how long emotions influence mood/style

This makes Kitsu behave naturally:
- strong emotions shift mood quickly
- weaker emotions fade gradually
- multiple emotions can coexist and influence the resulting state

## Emotion → mood/style/state mapping

The emotion config maps raw emotion names to behavior layers.

### Mood mapping

Examples:
- `angry`, `irritated`, `offended` → `mean`
- `love`, `affection`, `flattered` → `flirty`
- `protective`, `defensive`, `concerned` → `protective`
- `neutral`, `happy`, `calm` → `behave`

### Style mapping

Examples:
- `hurt`, `betrayed`, `ashamed` → `cold`
- `sad`, `fear`, `anxiety`, `lonely` → `direct`
- `excited`, `playful`, `teasing` → `chaotic`
- `sarcastic`, `witty`, `ironic` → `sarcastic`
- `eerie`, `mysterious` → `eerie`
- Default `happy` / `content` / `neutral` → `sweet`

### State mapping

Examples:
- Playful emotions like `playful`, `teasing`, `excited` → `fox`
- Confused or overwhelmed emotions → `glitch`
- Curious or analytical emotions → `analyst`
- Hurt, embarrassed, lonely → `submissive`
- Cold, distant emotions → `detached`

## Special behavior rules

`core/personality/emotion_config.py` defines additional behavior layers:

- `STYLE_RULES` control limits such as word count, emoji usage, and repetition
- `STYLE_QUIRKS` inject optional character flavor for certain styles
- `MOOD_CONSTRAINTS` add safety restrictions for moods like `flirty` and `mean`
- `UNSAFE_COMBINATIONS` suggest safe conversions when mood/style combinations are undesirable
- `ROLE_STYLE_MODIFIERS` let non-emotional roles like `caretaker` or `observer` bias the tone

## Runtime flow

A typical emotion flow is:

1. Event or user input produces an emotion signal
2. The system pushes an emotion onto the stack
3. The manager/engine calculates the dominant emotion after decay
4. The emotion maps to a mood and style
5. The translator layer uses the current mood/style/state to shape output
6. Triggers and reactions may fire additional emotion changes

## Integration points

- `core/translator/llm_translator.py`
  - Uses current emotion state to build prompt instructions
  - Logs `Current emotion: ...` along with intensity

- `core/personality/kitsu_self.py`
  - Exposes emotional expression for UI/voice systems
  - Reads current state from the emotion engine

- `core/personality/reaction_definitions.py`
  - Maps emotional triggers to reaction names used by the UI or response generator

## Extending the emotion system

To add a new emotion or adjust behavior:

1. Add the emotion to the appropriate mapping in `core/config/personality_config.py` or `core/personality/emotion_config.py`
2. Update `MOOD_DESCRIPTIONS`, `STYLE_DESCRIPTIONS`, or `STATE_DESCRIPTIONS` if needed
3. Add or adjust rules in `STYLE_RULES` for the new style
4. If adding triggers, update `core/personality/trigger_manager.py` or `data/triggers.json`
5. Validate with `validate_mood()` / `validate_style()` helpers

## Notes

- The system is intentionally separated between configuration and runtime logic.
- `core/personality/emotion_model.py` contains pure data structures and should remain logic-free.
- The emotion system supports both direct behavior mapping and character-flavor overlays, making it easy to tune personality without changing core response generation.
