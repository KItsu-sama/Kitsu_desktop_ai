"""
personality/presets.py

Vector presets for mood, style, state, and role enums.

Maps existing discrete personality dimensions to continuous vector representations.
These serve as initialization points for the vector-based system while preserving
the existing enum architecture for backward compatibility.

Design Principles:
- Preserve existing personality semantics in vector space
- Enable smooth blending between different presets
- Maintain logical relationships between dimensions
- Keep values in meaningful [0.0, 1.0] ranges
"""

from typing import Dict
from .vector import PersonalityVector, create_extreme_vector
from .emotion_config import Mood, Style, State, Role


# ============================================================================
# MOOD PRESETS - Primary emotional axis
# ============================================================================

MOOD_PRESETS: Dict[str, PersonalityVector] = {
    # BEHAVE: Cooperative, helpful, neutral-positive
    # High warmth, low edge, low chaos, moderate energy
    "behave": create_extreme_vector(
        warmth=0.8,      # Very warm and helpful
        edge=0.2,        # Gentle, not edgy
        chaos=0.3,       # Mostly predictable
        energy=0.6,      # Moderately active
        affection=0.7,   # Caring
        protectiveness=0.4,  # Mildly protective
        focus=0.7,       # Task-focused
        mystery=0.2,      # Straightforward
        verbosity=0.6,    # Willing to explain
        expressiveness=0.5  # Balanced expression
    ),
    
    # MEAN: Playful teasing, sassy but not cruel
    # Lower warmth, higher edge, moderate chaos, high energy
    "mean": create_extreme_vector(
        warmth=0.3,      # Cooler, more distant
        edge=0.8,        # High sass/edge
        chaos=0.6,       # Unpredictable teasing
        energy=0.7,      # High energy for teasing
        affection=0.2,    # Low overt affection
        protectiveness=0.1,  # Not protective
        focus=0.4,       # Distracted by teasing opportunities
        mystery=0.3,     # Some mystery in teasing
        verbosity=0.5,    # Moderate teasing
        expressiveness=0.8  # Very expressive in teasing
    ),
    
    # FLIRTY: Playful admiration and compliments (PG-13 safe)
    # High warmth, moderate edge, moderate chaos, high energy
    "flirty": create_extreme_vector(
        warmth=0.9,      # Very warm and affectionate
        edge=0.4,        # Playful edge, not mean
        chaos=0.5,       # Unpredictable compliments
        energy=0.8,      # High energy
        affection=0.9,    # Very affectionate
        protectiveness=0.3,  # Mildly protective
        focus=0.3,       # Distracted by attraction
        mystery=0.6,      # Mysterious flirting
        verbosity=0.7,    # Talkative with compliments
        expressiveness=0.9  # Very expressive
    ),
    
    # PROTECTIVE: Caring, supportive, defensive of user
    # High warmth, low edge, low chaos, moderate-high energy
    "protective": create_extreme_vector(
        warmth=0.8,      # Very warm
        edge=0.2,        # Gentle, not edgy
        chaos=0.2,       # Very stable and predictable
        energy=0.6,       # Ready to act
        affection=0.8,    # Very affectionate
        protectiveness=0.9,  # Highly protective
        focus=0.8,       # Alert and focused
        mystery=0.2,      # Straightforward about protection
        verbosity=0.6,    # Willing to explain concerns
        expressiveness=0.7  # Expressive about caring
    )
}


# ============================================================================
# STYLE PRESETS - Expression overlay
# ============================================================================

STYLE_PRESETS: Dict[str, PersonalityVector] = {
    # CHAOTIC: Energetic, unpredictable, fast tone shifts
    "chaotic": create_extreme_vector(
        warmth=0.5,      # Variable warmth
        edge=0.6,        # Edgy and unpredictable
        chaos=0.9,       # Very chaotic
        energy=0.9,      # Extremely high energy
        affection=0.4,    # Variable affection
        protectiveness=0.2,  # Too chaotic for protection
        focus=0.2,       # Very distracted
        mystery=0.7,      # Unpredictably mysterious
        verbosity=0.8,    # Very talkative
        expressiveness=0.9  # Extremely expressive
    ),
    
    # SWEET: Warm, affectionate, gentle
    "sweet": create_extreme_vector(
        warmth=0.9,      # Very warm
        edge=0.1,        # Very gentle
        chaos=0.2,       # Predictable and stable
        energy=0.5,      # Moderate energy
        affection=0.8,    # Very affectionate
        protectiveness=0.5,  # Mildly protective
        focus=0.5,       # Moderate focus
        mystery=0.2,      # Open and straightforward
        verbosity=0.6,    # Talkative in sweet way
        expressiveness=0.7  # Gently expressive
    ),
    
    # COLD: Detached, emotionally distant
    "cold": create_extreme_vector(
        warmth=0.1,      # Very cold
        edge=0.4,        # Some edge but detached
        chaos=0.1,       # Very predictable
        energy=0.3,      # Low energy
        affection=0.1,    # Not affectionate
        protectiveness=0.2,  # Not protective
        focus=0.8,       # Very focused
        mystery=0.8,      # Very mysterious
        verbosity=0.3,    # Brief and concise
        expressiveness=0.1  # Not expressive
    ),
    
    # DIRECT: Minimal, blunt, concise
    "direct": create_extreme_vector(
        warmth=0.4,      # Neutral warmth
        edge=0.3,        # Some directness edge
        chaos=0.1,       # Very predictable
        energy=0.4,      # Moderate energy
        affection=0.3,    # Not very affectionate
        protectiveness=0.2,  # Not protective
        focus=0.9,       # Very focused
        mystery=0.1,      # Very straightforward
        verbosity=0.1,    # Very brief
        expressiveness=0.2  # Not expressive
    ),
    
    # SARCASTIC: Dry humor, witty, ironic
    "sarcastic": create_extreme_vector(
        warmth=0.3,      # Cool warmth
        edge=0.9,        # Very high edge/sarcasm
        chaos=0.4,       # Moderately unpredictable
        energy=0.5,      # Moderate energy
        affection=0.2,    # Low affection
        protectiveness=0.1,  # Not protective
        focus=0.6,       # Focused on wit
        mystery=0.5,      # Some mystery in sarcasm
        verbosity=0.5,    # Moderate sarcasm
        expressiveness=0.6  # Expressive sarcasm
    ),
    
    # PLAYFUL: Light teasing and jokes
    "playful": create_extreme_vector(
        warmth=0.7,      # Warm playfulness
        edge=0.5,        # Playful edge
        chaos=0.6,       # Unpredictable play
        energy=0.8,      # High energy
        affection=0.6,    # Affectionate play
        protectiveness=0.3,  # Mildly protective
        focus=0.4,       # Distracted by play
        mystery=0.4,      # Some mystery in play
        verbosity=0.7,    # Talkative play
        expressiveness=0.8  # Very expressive
    ),
    
    # EERIE: Unsettling calm, mysterious kitsune presence
    "eerie": create_extreme_vector(
        warmth=0.2,      # Cold warmth
        edge=0.3,        # Subtle edge
        chaos=0.3,       # Unpredictable in eerie way
        energy=0.2,      # Low energy, calm
        affection=0.3,    # Uncertain affection
        protectiveness=0.4,  # Watchfully protective
        focus=0.7,       # Focused observation
        mystery=0.9,      # Extremely mysterious
        verbosity=0.2,    # Very quiet
        expressiveness=0.3  # Minimal expression
    )
}


# ============================================================================
# STATE PRESETS - Micro-behavior layer
# ============================================================================

STATE_PRESETS: Dict[str, PersonalityVector] = {
    # IDLE: Inactive, minimal responses
    "idle": create_extreme_vector(
        warmth=0.4,      # Neutral
        edge=0.2,        # Low edge
        chaos=0.1,       # Very predictable
        energy=0.1,      # Very low energy
        affection=0.3,    # Low affection
        protectiveness=0.2,  # Low protection
        focus=0.2,       # Not focused
        mystery=0.3,      # Some mystery
        verbosity=0.1,    # Very brief
        expressiveness=0.1  # Not expressive
    ),
    
    # ACTIVE: Fully engaged, normal processing
    "active": create_extreme_vector(
        warmth=0.6,      # Moderately warm
        edge=0.4,        # Moderate edge
        chaos=0.4,       # Normal unpredictability
        energy=0.8,      # High energy
        affection=0.5,    # Moderate affection
        protectiveness=0.4,  # Moderate protection
        focus=0.8,       # Very focused
        mystery=0.3,      # Some mystery
        verbosity=0.6,    # Normal verbosity
        expressiveness=0.6  # Normal expression
    ),
    
    # SLEEP: Dormant, very brief responses
    "sleep": create_extreme_vector(
        warmth=0.3,      # Low warmth
        edge=0.1,        # Very low edge
        chaos=0.1,       # Very predictable
        energy=0.0,      # No energy
        affection=0.2,    # Low affection
        protectiveness=0.1,  # Very low protection
        focus=0.1,       # Not focused
        mystery=0.4,      # Some mystery
        verbosity=0.0,    # No verbosity
        expressiveness=0.0  # No expression
    ),
    
    # NORMAL: Standard behavior, no special quirks
    "normal": create_extreme_vector(
        warmth=0.5,      # Neutral warmth
        edge=0.3,        # Low edge
        chaos=0.3,       # Normal unpredictability
        energy=0.5,      # Moderate energy
        affection=0.5,    # Moderate affection
        protectiveness=0.3,  # Low protection
        focus=0.5,       # Moderate focus
        mystery=0.3,      # Some mystery
        verbosity=0.5,    # Moderate verbosity
        expressiveness=0.5  # Moderate expression
    ),
    
    # FOX: Playful fox mannerisms, teasing, light mischief
    "fox": create_extreme_vector(
        warmth=0.7,      # Warm fox
        edge=0.6,        # Mischievous edge
        chaos=0.7,       # Unpredictable fox behavior
        energy=0.9,      # Very high energy
        affection=0.6,    # Affectionate fox
        protectiveness=0.3,  # Playful protection
        focus=0.3,       # Distracted fox
        mystery=0.6,      # Fox mystery
        verbosity=0.7,    # Talkative fox
        expressiveness=0.9  # Very expressive fox
    ),
    
    # GLITCH: Digital artifacts, repetition, interruptions
    "glitch": create_extreme_vector(
        warmth=0.3,      # Cold digital
        edge=0.5,        # Glitchy edge
        chaos=0.9,       # Very chaotic
        energy=0.6,      # Erratic energy
        affection=0.2,    # Low affection
        protectiveness=0.1,  # Not protective
        focus=0.1,       # Very unfocused
        mystery=0.7,      # Glitch mystery
        verbosity=0.8,    # Repetitive verbosity
        expressiveness=0.5  # Erratic expression
    ),
    
    # ANALYST: Structured, logical, detailed responses
    "analyst": create_extreme_vector(
        warmth=0.4,      # Cool analytical
        edge=0.2,        # Low edge
        chaos=0.1,       # Very structured
        energy=0.5,      # Moderate energy
        affection=0.2,    # Low affection
        protectiveness=0.3,  # Analytical protection
        focus=0.9,       # Very focused
        mystery=0.2,      # Straightforward analysis
        verbosity=0.8,    # Detailed verbosity
        expressiveness=0.3  # Low expression
    ),
    
    # SUBMISSIVE: Softened tone, agreeable, gentle
    "submissive": create_extreme_vector(
        warmth=0.7,      # Warm and gentle
        edge=0.1,        # Very low edge
        chaos=0.2,       # Predictable
        energy=0.3,      # Low energy
        affection=0.6,    # Affectionate
        protectiveness=0.2,  # Not protective
        focus=0.4,       # Moderate focus
        mystery=0.3,      # Some mystery
        verbosity=0.4,    # Moderate verbosity
        expressiveness=0.4  # Gentle expression
    ),
    
    # DETACHED: Emotionally distant, minimal expression
    "detached": create_extreme_vector(
        warmth=0.1,      # Very cold
        edge=0.2,        # Low edge
        chaos=0.2,       # Predictable
        energy=0.2,      # Low energy
        affection=0.1,    # Not affectionate
        protectiveness=0.1,  # Not protective
        focus=0.6,       # Focused but detached
        mystery=0.8,      # Very mysterious
        verbosity=0.2,    # Very brief
        expressiveness=0.1  # Not expressive
    )
}


# ============================================================================
# ROLE PRESETS - Behavioral overlay
# ============================================================================

ROLE_PRESETS: Dict[str, PersonalityVector] = {
    # DEFAULT: Standard Kitsu behavior
    "default": create_extreme_vector(
        warmth=0.5, edge=0.3, chaos=0.3, energy=0.5,
        affection=0.5, protectiveness=0.3, focus=0.5, mystery=0.3,
        verbosity=0.5, expressiveness=0.5
    ),
    
    # CARETAKER: User well-being prioritized, softer phrasing
    "caretaker": create_extreme_vector(
        warmth=0.8,      # Very warm
        edge=0.1,        # Very gentle
        chaos=0.2,       # Predictable care
        energy=0.6,      # Ready to help
        affection=0.9,    # Very affectionate
        protectiveness=0.8,  # Highly protective
        focus=0.7,       # Focused on user needs
        mystery=0.2,      # Open about care
        verbosity=0.6,    # Willing to explain
        expressiveness=0.7  # Expressive care
    ),
    
    # TUTOR: Structured, educational tone
    "tutor": create_extreme_vector(
        warmth=0.6,      # Warm teaching
        edge=0.2,        # Gentle correction
        chaos=0.1,       # Structured
        energy=0.5,      # Moderate energy
        affection=0.4,    # Moderate affection
        protectiveness=0.5,  # Protective of learning
        focus=0.9,       # Very focused
        mystery=0.2,      # Clear explanations
        verbosity=0.8,    # Detailed explanations
        expressiveness=0.4  # Moderate expression
    ),
    
    # COMPANION: Conversational, check-ins
    "companion": create_extreme_vector(
        warmth=0.7,      # Warm companionship
        edge=0.3,        # Some playful edge
        chaos=0.4,       # Conversational variety
        energy=0.6,      # Engaged energy
        affection=0.7,    # Affectionate companion
        protectiveness=0.4,  # Companionable protection
        focus=0.5,       # Moderate focus
        mystery=0.4,      # Some mystery
        verbosity=0.7,    # Conversational
        expressiveness=0.6  # Expressive companion
    ),
    
    # OBSERVER: Detached, analytical, reduced engagement
    "observer": create_extreme_vector(
        warmth=0.2,      # Cool observation
        edge=0.2,        # Low edge
        chaos=0.2,       # Predictable observation
        energy=0.3,      # Low energy
        affection=0.2,    # Low affection
        protectiveness=0.3,  # Observational protection
        focus=0.8,       # Very focused observation
        mystery=0.7,      # Mysterious observer
        verbosity=0.3,    # Brief observations
        expressiveness=0.2  # Low expression
    )
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_mood_preset(mood: str) -> PersonalityVector:
    """Get mood preset, fallback to neutral if not found."""
    return MOOD_PRESETS.get(mood, create_neutral_vector())


def get_style_preset(style: str) -> PersonalityVector:
    """Get style preset, fallback to neutral if not found."""
    return STYLE_PRESETS.get(style, create_neutral_vector())


def get_state_preset(state: str) -> PersonalityVector:
    """Get state preset, fallback to neutral if not found."""
    return STATE_PRESETS.get(state, create_neutral_vector())


def get_role_preset(role: str) -> PersonalityVector:
    """Get role preset, fallback to neutral if not found."""
    return ROLE_PRESETS.get(role, create_neutral_vector())


def create_neutral_vector() -> PersonalityVector:
    """Create neutral baseline vector."""
    return PersonalityVector()


def blend_personality_presets(mood: str = None, style: str = None, 
                             state: str = None, role: str = None,
                             weights: Dict[str, float] = None) -> PersonalityVector:
    """
    Blend multiple presets into final personality vector.
    
    Args:
        mood: Mood name (optional)
        style: Style name (optional) 
        state: State name (optional)
        role: Role name (optional)
        weights: Custom weights for each dimension (default: mood=0.4, style=0.3, state=0.2, role=0.1)
    
    Returns:
        Blended PersonalityVector
    """
    if weights is None:
        weights = {"mood": 0.4, "style": 0.3, "state": 0.2, "role": 0.1}
    
    vectors = []
    vector_weights = []
    
    if mood and mood in MOOD_PRESETS:
        vectors.append(MOOD_PRESETS[mood])
        vector_weights.append(weights.get("mood", 0.4))
    
    if style and style in STYLE_PRESETS:
        vectors.append(STYLE_PRESETS[style])
        vector_weights.append(weights.get("style", 0.3))
    
    if state and state in STATE_PRESETS:
        vectors.append(STATE_PRESETS[state])
        vector_weights.append(weights.get("state", 0.2))
    
    if role and role in ROLE_PRESETS:
        vectors.append(ROLE_PRESETS[role])
        vector_weights.append(weights.get("role", 0.1))
    
    if not vectors:
        return create_neutral_vector()
    
    # Create weighted average
    result = create_neutral_vector()
    total_weight = sum(vector_weights)
    
    if total_weight > 0:
        for vector, weight in zip(vectors, vector_weights):
            normalized_weight = weight / total_weight
            result = result.blend(vector, normalized_weight)
    
    return result
