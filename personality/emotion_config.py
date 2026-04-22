"""
config/personality_config.py

Canonical personality system configuration for Kitsu.
This file defines the authoritative mood, style, state, and role values used across the system.

Three-Layer Architecture:
- mood: Primary emotional axis (intent toward user)
- style: Expression overlay (delivery method) 
- state: Micro-behavior layer (quirks/persona)
- role: Behavioral overlay (contextual purpose)

Total combinations: 4 moods × 7 styles × 6 states × 5 roles = 8,400 personality states

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
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any, Callable, List
from enum import StrEnum

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

# ============================================================================
# Emotion → Mood Mapping - COMPREHENSIVE MERGE
# ============================================================================

EMOTION_TO_MOOD = {
    # Legacy mappings
    "happy": "behave",
    "sad": "protective",
    "angry": "mean",
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
    "bored": "behave",  # Added
    "indifferent": "behave",
    "surprised": "behave",  # Added
    "confused": "behave"
}

# ============================================================================
# Emotion → Style Mapping - COMPREHENSIVE MERGE
# ============================================================================

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
    "playful": "chaotic",
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
def fix_mean_cold(p):
    p.style = "sarcastic"
    return p

def rule_protective_cold(p): return p.mood == "protective" and p.style == "cold"
def fix_protective_cold(p):
    p.style = "direct"
    return p

def rule_gentle_mean(p): return p.state == "submissive" and p.mood == "mean"  # Fixed: "gentle" not in VALID_STATES, using "submissive" as closest
def fix_gentle_mean(p):
    p.mood = "behave"
    return p

def rule_observer_chaotic(p): return p.role == "observer" and p.style == "chaotic"
def fix_observer_chaotic(p):
    p.style = "cold"
    return p

def rule_glitch_tutor(p): return p.state == "glitch" and p.role == "tutor"
def fix_glitch_tutor(p):
    p.state = "analyst"
    return p

def rule_caretaker_mean(p): return p.role == "caretaker" and p.mood == "mean"
def fix_caretaker_mean(p):
    p.mood = "behave"  # Caretaker should be supportive, not mean
    return p

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
    from dataclasses import asdict
    
    for _ in range(max_passes):
        changed = False
        modified_attributes = set()  # Track modified attributes to prevent re-modification
        
        for rule in sorted(RULES, key=lambda r: -r.priority):
            if rule.condition(p):
                before = asdict(p)
                p = rule.action(p)
                after = asdict(p)
                
                # Identify changed attributes
                changed_attrs = {attr for attr in ['mood', 'style', 'state', 'role'] if before.get(attr) != after.get(attr)}
                
                # Only apply if none of the changed attributes have been modified before
                if not changed_attrs & modified_attributes:
                    modified_attributes.update(changed_attrs)
                    if before != after:
                        changed = True
                else:
                    # Revert the change to prevent oscillation
                    p = Personality(**before)
        
        if not changed:
            break
    
    return p

# ============================================================================
# VALIDATION
# ============================================================================

def validate_full_personality(p: Personality) -> Tuple[bool, Optional[str]]:
    if p.mood not in VALID_MOODS:
        return False, f"Invalid mood: {p.mood}"
    if p.style not in VALID_STYLES:
        return False, f"Invalid style: {p.style}"
    if p.state not in VALID_STATES:
        return False, f"Invalid state: {p.state}"
    if p.role not in VALID_ROLES:
        return False, f"Invalid role: {p.role}"
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