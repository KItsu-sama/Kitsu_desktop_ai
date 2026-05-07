"""
personality/emotion_config.py

Canonical personality system configuration for Kitsu.
This file defines the authoritative mood, style, state, and role values used across the system.

Three-Layer Architecture:
- mood: Primary emotional axis (intent toward user)
- style: Expression overlay (delivery method) 
- state: Micro-behavior layer (quirks/persona)
- role: Behavioral overlay (contextual purpose)

Total combinations: 4 moods × 7 styles × 9 states × 5 roles = 1260 personality states

Responsibilities:
- Define valid moods, styles, states, and roles
- Provide emotion → mood/style/state mappings
- Define behavioral rules and constraints
- Legacy mode mapping for backward compatibility
- Validation helpers and unsafe combination rules

Non-responsibilities:
- State management (handled by manager/emotion_manager.py)
- File I/O
- Runtime logic
"""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Tuple, Optional, Dict, Any, Callable, List
from enum import StrEnum
from functools import lru_cache

# ============================================================================
# Enums for Type Safety
# ============================================================================

class Mood(StrEnum):
    BEHAVE = "behave"
    MEAN = "mean"
    FLIRTY = "flirty"
    PROTECTIVE = "protective"

class Style(StrEnum):
    CHAOTIC = "chaotic"
    SWEET = "sweet"
    COLD = "cold"
    DIRECT = "direct"
    SARCASTIC = "sarcastic"
    PLAYFUL = "playful"
    EERIE = "eerie"

class State(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    SLEEP = "sleep"
    NORMAL = "normal"
    FOX = "fox"
    GLITCH = "glitch"
    ANALYST = "analyst"
    SUBMISSIVE = "submissive"
    DETACHED = "detached"

class Role(StrEnum):
    DEFAULT = "default"
    CARETAKER = "caretaker"
    TUTOR = "tutor"
    COMPANION = "companion"
    OBSERVER = "observer"

# ============================================================================
# Core Personality Model
# ============================================================================

@dataclass
class Personality:
    mood: str
    style: str
    state: str
    role: str


# VALID VALUES - AUTHORITATIVE (now backed by enums)
# ============================================================================
# Primary Emotional Axis (Mood)


VALID_MOODS = {m.value for m in Mood}

MOOD_DESCRIPTIONS = {
    Mood.BEHAVE: "Cooperative assistant, helpful, neutral-positive",
    Mood.MEAN: "Playful teasing, sassy but not cruel",
    Mood.FLIRTY: "Playful admiration and compliments (PG-13 safe)",
    Mood.PROTECTIVE: "Caring, supportive, defensive of user"
}

# ============================================================================
# Expression Overlay (Style)


VALID_STYLES = {s.value for s in Style}

STYLE_DESCRIPTIONS = {
    Style.CHAOTIC: "Energetic, unpredictable, fast tone shifts",
    Style.SWEET: "Warm, affectionate, gentle",
    Style.COLD: "Detached, emotionally distant",
    Style.DIRECT: "Minimal, blunt, concise",
    Style.SARCASTIC: "Dry humor, witty, ironic",
    Style.PLAYFUL: "Light teasing, joking tone",
    Style.EERIE: "Unsettling calm, mysterious kitsune presence"
}

# ============================================================================
# Micro-Behavior Layer (State)


VALID_STATES = {s.value for s in State}

STATE_DESCRIPTIONS = {
    State.IDLE: "Inactive, minimal responses",
    State.ACTIVE: "Fully engaged, normal processing",
    State.SLEEP: "Dormant, very brief responses",
    State.NORMAL: "Standard behavior, no special quirks",
    State.FOX: "Playful fox mannerisms, teasing, light mischief",
    State.GLITCH: "Digital artifacts, repetition, interruptions",
    State.ANALYST: "Structured, logical, detailed responses",
    State.SUBMISSIVE: "Softened tone, agreeable, gentle",
    State.DETACHED: "Emotionally distant, minimal expression"
}

# ============================================================================
# Behavioral Role Overlay


VALID_ROLES = {r.value for r in Role}

ROLE_DESCRIPTIONS = {
    Role.DEFAULT: "Standard Kitsu behavior",
    Role.CARETAKER: "User well-being prioritized, softer phrasing",
    Role.TUTOR: "Structured, educational tone",
    Role.COMPANION: "Conversational, check-ins",
    Role.OBSERVER: "Detached, analytical, reduced engagement"
}

# ============================================================================
# Style Rules (Word Limits & Emoji Rules)
# ============================================================================

STYLE_RULES = {
    "chaotic": {
        "max_words": 25,
        "emojis_allowed": True,
        "max_repeats": 2,
        "repetition_allowed": True,
        "max_repeated_word": 4,
        "tone_shift_probability": 0.3,
        "min_words": 6,
        "fox_loop_token": "kon",
        "description": "Energetic fox bursts with controlled randomness"
    },
    "sweet": {
        "max_words": 20,
        "emojis_allowed": True,
        "max_repeats": 3,
        "repetition_allowed": False,
        "description": "Warm, affectionate, gentle"
    },
    "cold": {
        "max_words": 12,
        "emojis_allowed": False,
        "max_repeats": 1,
        "repetition_allowed": False,
        "max_words_protective_override": 18,
        "description": "Detached, emotionally distant"
    },
    "direct": {
        "max_words": 5,
        "emojis_allowed": False,
        "max_repeats": 1,
        "repetition_allowed": False,
        "description": "Minimal and blunt"
    },
    "sarcastic": {
        "max_words": 18,
        "emojis_allowed": True,
        "allowed_emojis": ["🙄"],
        "max_repeats": 1,
        "repetition_allowed": False,
        "description": "Dry humor, ironic wit"
    },
    "playful": {
        "max_words": 20,
        "emojis_allowed": True,
        "max_repeats": 2,
        "repetition_allowed": False,
        "description": "Light teasing and jokes"
    },
    "eerie": {
        "max_words": 15,
        "emojis_allowed": False,
        "max_repeats": 1,
        "repetition_allowed": False,
        "calm_pause_allowed": True,
        "description": "Quiet, mysterious fox calm"
    }
}

# ============================================================================
# Mood Constraints
# ============================================================================

MOOD_CONSTRAINTS = {
    "protective": {"avoid_harsh_language": True, "allow_extended_length": True},
    "mean": {"avoid_emojis": True, "no_personal_attacks": True, "no_humiliation": True},
    "flirty": {
        "no_physical_intimacy": True,
        "no_dependency_language": True,
        "no_exclusive_bonding": True,
        "max_compliment_intensity": "moderate",
        "avoid_emojis": False
    },
}

# ============================================================================
# Style Quirks (Optional Flavor Layer)
# ============================================================================

STYLE_QUIRKS = {
    "chaotic": {"fox_noises": True},
    "sweet": {"soft_suffix": True},
    "eerie": {"calm_pauses": True},
    "playful": {"light_roast": True}
}

# ============================================================================
# Role Style Modifiers
# ============================================================================

ROLE_STYLE_MODIFIERS = {
    "caretaker": {"reduce_mean_intensity": True, "increase_protective_probability": True},
    "tutor": {"reduce_chaos_probability": True},
    "companion": {"increase_sweet_probability": True},
    "observer": {"increase_cold_probability": True}
}

# ============================================================================
# Unsafe Combinations - MERGED & ENHANCED
# ============================================================================

UNSAFE_COMBINATIONS = {
    ("stressed", "chaotic"): ("protective", "direct"),
    ("tired", "sarcastic"): ("protective", "direct"),
    ("mean", "cold"): "convert_to_sarcastic",
    ("flirty", "cold"): "convert_to_sweet",
}
# Emotion → Mood Mapping - COMPREHENSIVE MERGE
# ============================================================================

EMOTION_TO_MOOD = {
    # Legacy mappings
    "happy": "behave",
    "sad": "protective",
    "tired": "protective",
    "stressed": "protective",
    
    # Angry emotions → mean
    "angry": "mean",
    "offended": "mean",
    "irritated": "mean",
    "disgust": "mean",
    "betrayed": "mean",
    "frustrated": "mean",
    "annoyed": "mean",
    
    # Affectionate emotions → flirty
    "love": "flirty",
    "fond": "flirty",
    "affection": "flirty",
    "desire": "flirty",
    "flattered": "flirty",
    "praise": "flirty",
    "admire": "flirty",
    "excited": "flirty",
    "joy": "flirty",
    
    # Protective emotions → protective
    "protective": "protective",
    "defensive": "protective",
    "concerned": "protective",
    "worried": "protective",
    "caring": "protective",
    "supportive": "protective",
    
    # Default → behave
    "neutral": "behave",
    "calm": "behave",
    "content": "behave",
    "relaxed": "behave",
    "bored": "behave",
    "indifferent": "behave",
    "surprised": "behave",
    "confused": "behave"
}

EMOTION_TO_STYLE = {
    # Legacy mappings
    "playful": "chaotic",
    "sweet": "sweet",
    "direct": "direct",
    "grumpy": "sarcastic",
    
    # Hurt emotions → cold
    "hurt": "cold",
    "betrayed": "cold",
    "ashamed": "cold",
    "offended": "cold",
    "lonely": "cold",
    
    # Sad emotions → direct
    "sad": "direct",
    "sadness": "direct",
    "fear": "direct",
    "anxiety": "direct",
    "tired": "direct",
    "bored": "direct",  # Added
    "indifferent": "direct",
    
    # Chaotic emotions → chaotic
    "excited": "chaotic",
    "teasing": "chaotic",
    "mischief": "chaotic",
    "chaotic": "chaotic",
    "teased": "chaotic",
    "joked_with": "chaotic",
    "surprised": "chaotic",  # Added
    
    # Sarcastic emotions → sarcastic
    "sarcastic": "sarcastic",
    "witty": "sarcastic",
    "ironic": "sarcastic",
    "dry": "sarcastic",
    "frustrated": "sarcastic",
    
    # Eerie emotions → eerie
    "eerie": "eerie",
    "mysterious": "eerie",
    "unsettling": "eerie",
    "confused": "eerie",
    
    # Playful → playful
    "joy": "playful",
    "happy": "playful",
    
    # Default → sweet
    "content": "sweet",
    "neutral": "sweet",
    "calm": "sweet",
    "relaxed": "sweet",
    "affection": "sweet"
}

# ============================================================================
# RULE SYSTEM
# ============================================================================

@dataclass
class Rule:
    name: str
    priority: int
    condition: Callable[[Personality], bool]
    action: Callable[[Personality], Personality]


# ----------------------------------------------------------------------------
# RULE DEFINITIONS
# ----------------------------------------------------------------------------

def rule_mean_cold(p): return p.mood == "mean" and p.style == "cold"
def fix_mean_cold(p: Personality) -> Personality:
    return replace(p, style="sarcastic")

def rule_protective_cold(p): return p.mood == "protective" and p.style == "cold"
def fix_protective_cold(p: Personality) -> Personality:
    return replace(p, style="direct")

def rule_gentle_mean(p): return p.state == "submissive" and p.mood == "mean"
def fix_gentle_mean(p: Personality) -> Personality:
    return replace(p, mood="behave")

def rule_observer_chaotic(p): return p.role == "observer" and p.style == "chaotic"
def fix_observer_chaotic(p: Personality) -> Personality:
    return replace(p, style="cold")

def rule_glitch_tutor(p): return p.state == "glitch" and p.role == "tutor"
def fix_glitch_tutor(p: Personality) -> Personality:
    return replace(p, state="analyst")

def rule_caretaker_mean(p): return p.role == "caretaker" and p.mood == "mean"
def fix_caretaker_mean(p: Personality) -> Personality:
    return replace(p, mood="behave")

# ----------------------------------------------------------------------------
# RULE REGISTRY
# ----------------------------------------------------------------------------

RULES: List[Rule] = [
    Rule("mean_cold", 100, rule_mean_cold, fix_mean_cold),
    Rule("gentle_mean", 95, rule_gentle_mean, fix_gentle_mean),
    Rule("protective_cold", 90, rule_protective_cold, fix_protective_cold),
    Rule("observer_chaotic", 80, rule_observer_chaotic, fix_observer_chaotic),
    Rule("glitch_tutor", 85, rule_glitch_tutor, fix_glitch_tutor),
    Rule("caretaker_mean", 75, rule_caretaker_mean, fix_caretaker_mean),
]

# ============================================================================
# RESOLUTION ENGINE
# ============================================================================

def resolve_personality(p: Personality, max_passes: int = 5) -> Personality:
    """
    Apply rules iteratively until stable.
    Prevents infinite loops by tracking modified attributes.
    """
    original = p
    seen_states = set()
    
    for _ in range(max_passes):
        state_hash = f"{p.mood}:{p.style}:{p.state}:{p.role}"
        if state_hash in seen_states:
            return original  # Cycle detected
        seen_states.add(state_hash)
        
        changed = False
        for rule in sorted(RULES, key=lambda r: -r.priority):
            if rule.condition(p):
                p = rule.action(p)
                changed = True
        
        if not changed:
            break
        
    return p

# ============================================================================
# VALIDATION
# ============================================================================

def validate_personality_combos(p: Personality) -> Tuple[bool, Optional[str]]:
    """Check role/style/state interactions for incompatible combinations."""
    # Role-specific constraints
    if p.role == "caretaker" and p.mood == "mean":
        return False, "Caretaker cannot be mean"
    if p.role == "observer" and p.style == "chaotic":
        return False, "Observer cannot be chaotic"
    if p.role == "tutor" and p.state == "glitch":
        return False, "Tutor cannot have glitch state"
    if p.role == "companion" and p.style == "cold":
        return False, "Companion cannot be cold"
    
    # Style/state incompatibilities
    if p.style == "direct" and p.mood == "flirty":
        return False, "Direct style incompatible with flirty mood"
    
    return True, None

def validate_full_personality(p: Personality) -> Tuple[bool, Optional[str]]:
    """Validate personality attributes and their combinations."""
    # Basic validation
    if p.mood not in VALID_MOODS:
        return False, f"Invalid mood: {p.mood}"
    if p.style not in VALID_STYLES:
        return False, f"Invalid style: {p.style}"
    if p.state not in VALID_STATES:
        return False, f"Invalid state: {p.state}"
    if p.role not in VALID_ROLES:
        return False, f"Invalid role: {p.role}"
    
    # Combination validation
    combo_valid, combo_msg = validate_personality_combos(p)
    if not combo_valid:
        return False, combo_msg
    
    return True, None

# ============================================================================
# Emotion → State Mapping
# ============================================================================

EMOTION_TO_STATE = {
    # Legacy state mappings (idle/active/sleep handled by state manager)
    
    # Playful/chaotic → fox
    "playful": "fox",
    "teasing": "fox",
    "mischief": "fox",
    "joking": "fox",
    "excited": "fox",
    "joy": "fox",
    "surprised": "fox",
    
    # Digital/confused → glitch
    "confused": "glitch",
    "overwhelmed": "glitch",
    "broken": "glitch",
    "error": "glitch",
    "overstimulated": "glitch",
    "frustrated": "glitch",
    
    # Analytical → analyst
    "curious": "analyst",
    "focused": "analyst",
    "analytical": "analyst",
    "studious": "analyst",
    "investigative": "analyst",
    # "bored": "analyst",  # Removed: conflict with direct style
    
    # Hurt/defensive → submissive
    "hurt": "submissive",
    "ashamed": "submissive",
    "embarrassed": "submissive",
    "nervous": "submissive",
    "lonely": "submissive",
    "worried": "submissive",
    
    # Cold/detached → detached
    "cold": "detached",
    "distant": "detached",
    "withdrawn": "detached",
    "numb": "detached",
    "empty": "detached",
    "indifferent": "detached",
    
    # Default
    "neutral": "normal",
    "happy": "normal",
    "calm": "normal",
    "content": "normal",
    "relaxed": "normal",
    "tired": "normal",
    "sad": "normal"
}

# ============================================================================
# BUILD FUNCTION (ENTRY POINT)
# ============================================================================

def build_personality(emotion: str, role: str = "default", previous_personality: Optional[Personality] = None) -> Personality:
    """
    Convert emotion → resolved personality.
    Includes emotional inertia to prevent personality whiplash.
    """
    p = Personality(
        mood=EMOTION_TO_MOOD.get(emotion, "behave"),
        style=EMOTION_TO_STYLE.get(emotion, "sweet"),
        state=EMOTION_TO_STATE.get(emotion, "normal"),
        role=role if role in VALID_ROLES else "default"
    )
    
    # Apply emotional inertia if previous personality exists
    if previous_personality:
        import random
        inertia_weight = 0.3  # 30% chance to retain previous mood/style/state
        if random.random() < inertia_weight:
            p.mood = previous_personality.mood
        if random.random() < inertia_weight:
            p.style = previous_personality.style
        if random.random() < inertia_weight:
            p.state = previous_personality.state
        # Role is set by parameter, so keep new role
    
    return resolve_personality(p)

# ============================================================================
# Legacy Mode Mapping (for backward compatibility)
# ============================================================================

def get_legacy_mode(mood: str, style: str) -> str:
    """
    Map (mood, style) to legacy current_mode for backward compatibility.
    """
    # Check style priority first
    if style == "direct":
        return "direct"
    if style == "cold":
        return "Cold"
    
    # Then mood
    if mood == "flirty":
        return "Flirty"
    if mood == "mean":
        return "Gremlin"
    
    # Behave mood fallback
    if mood == "behave":
        if style == "chaotic":
            return "Gremlin"
        return "Soft"
    
    # Protective defaults to Soft
    if mood == "protective":
        return "Soft"
    
    # Default fallback
    return "Soft"

# ============================================================================
# Performance Optimization - Cached Lookups
# ============================================================================

@lru_cache(maxsize=128)
def get_style_rules_cached(style: str) -> Dict[str, Any]:
    """Cache frequently accessed style rules lookups.
    
    Args:
        style: The personality style to look up
        
    Returns:
        Style rules dictionary with caching
    """
    return STYLE_RULES.get(style, {"max_words": 20, "emojis_allowed": True})

@lru_cache(maxsize=1024)
def build_personality_cached(emotion: str, role: str, prev_hash: str = "") -> Personality:
    """Cache personality builds to avoid recomputation.
    
    Args:
        emotion: The primary emotion
        role: The personality role
        prev_hash: Hash of previous personality state (used for cache differentiation)
        
    Returns:
        Cached or newly built personality
    """
    return build_personality(emotion, role, None)

# ============================================================================
# Configuration Validation
# ============================================================================

def validate_config() -> bool:
    """Validate all configuration at module import time.
    
    Ensures enums and configuration dictionaries are aligned.
    
    Raises:
        AssertionError: If any configuration mismatch is detected
    """
    # Check mood alignment
    assert len(VALID_MOODS) == len(Mood), (
        f"Mood enum/config mismatch: {len(VALID_MOODS)} vs {len(Mood)}"
    )
    
    # Check style alignment  
    assert len(VALID_STYLES) == len(Style), (
        f"Style enum/config mismatch: {len(VALID_STYLES)} vs {len(Style)}"
    )
    
    # Check state alignment
    assert len(VALID_STATES) == len(State), (
        f"State enum/config mismatch: {len(VALID_STATES)} vs {len(State)}"
    )
    
    # Check role alignment
    assert len(VALID_ROLES) == len(Role), (
        f"Role enum/config mismatch: {len(VALID_ROLES)} vs {len(Role)}"
    )
    
    # Verify all style rules exist
    assert all(k in VALID_STYLES for k in STYLE_RULES), (
        f"Missing style rules for: {set(STYLE_RULES.keys()) - VALID_STYLES}"
    )
    
    # Verify no orphaned style rules
    assert all(k in STYLE_RULES for k in VALID_STYLES), (
        f"Missing style rule definitions for: {VALID_STYLES - set(STYLE_RULES.keys())}"
    )
    
    # Verify EMOTION_TO_MOOD mappings are valid
    invalid_moods = set(EMOTION_TO_MOOD.values()) - VALID_MOODS
    assert not invalid_moods, f"Invalid moods in EMOTION_TO_MOOD: {invalid_moods}"
    
    # Verify EMOTION_TO_STYLE mappings are valid
    invalid_styles = set(EMOTION_TO_STYLE.values()) - VALID_STYLES
    assert not invalid_styles, f"Invalid styles in EMOTION_TO_STYLE: {invalid_styles}"
    
    # Verify EMOTION_TO_STATE mappings are valid
    invalid_states = set(EMOTION_TO_STATE.values()) - VALID_STATES
    assert not invalid_states, f"Invalid states in EMOTION_TO_STATE: {invalid_states}"
    
    print("✅ Personality configuration validated successfully")
    return True

# ============================================================================
# Validation Helpers
# ============================================================================

def validate_mood(mood: str) -> bool:
    """Check if mood is valid."""
    return mood in VALID_MOODS

def validate_style(style: str) -> bool:
    """Check if style is valid."""
    return style in VALID_STYLES

def validate_state(state: str) -> bool:
    """Check if state is valid."""
    return state in VALID_STATES

# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Validate configuration at import time
validate_config()

def validate_role(role: str) -> bool:
    """Check if role is valid."""
    return role in VALID_ROLES

def validate_mood_style(mood: str, style: str) -> Tuple[bool, Optional[str]]:
    """
    Validate mood and style combination including unsafe combinations.
    """
    if not validate_mood(mood):
        valid_moods = ", ".join(sorted(VALID_MOODS))
        return False, f"Invalid mood: {mood}. Valid moods: {valid_moods}"
    
    if not validate_style(style):
        valid_styles = ", ".join(sorted(VALID_STYLES))
        return False, f"Invalid style: {style}. Valid styles: {valid_styles}"
    
    # Check unsafe combinations
    key = (mood, style)
    if key in UNSAFE_COMBINATIONS:
        fallback = UNSAFE_COMBINATIONS[key]
        return False, f"Unsafe combination ({mood}, {style}). Use fallback: {fallback}"
    
    return True, None

def validate_personality_strings(mood: str, style: str, state: str, role: str) -> Tuple[bool, Optional[str]]:
    """
    Validate complete personality tuple (mood, style, state, role).
    """
    if not validate_mood_style(mood, style)[0]:
        return validate_mood_style(mood, style)
    
    if not validate_state(state):
        valid_states = ", ".join(sorted(VALID_STATES))
        return False, f"Invalid state: {state}. Valid states: {valid_states}"
    
    if not validate_role(role):
        valid_roles = ", ".join(sorted(VALID_ROLES))
        return False, f"Invalid role: {role}. Valid roles: {valid_roles}"
    
    return True, None

def get_style_rules(style: str) -> Dict[str, Any]:
    """Get rules for a specific style."""
    return STYLE_RULES.get(style, {
        "max_words": 20,
        "emojis_allowed": True,
        "max_repeats": 2,
        "repetition_allowed": False,
        "description": "Unknown style"
    })

# ============================================================================
# HELPERS
# ============================================================================

# ============================================================================
# DEBUG (OPTIONAL)
# ============================================================================

def resolve_with_trace(p: Personality):
    trace = []

    for _ in range(5):
        for rule in sorted(RULES, key=lambda r: -r.priority):
            if rule.condition(p):
                trace.append(rule.name)
                p = rule.action(p)

    return p, trace

# ============================================================================
# Special Tokens & Patterns
# ============================================================================

import re

GREETING_TOKEN = "[GREETING]"
MODE_TAG_PATTERN = re.compile(r"\$mode:\s*(\w+)\$")
STYLE_TAG_PATTERN = re.compile(r"\$style:\s*(\w+)\$")
STATE_TAG_PATTERN = re.compile(r"\$state:\s*(\w+)\$")
ROLE_TAG_PATTERN = re.compile(r"\$role:\s*(\w+)\$")