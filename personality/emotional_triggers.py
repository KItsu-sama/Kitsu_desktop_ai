"""
personality/emotional_triggers.py

Configuration for emotional trigger processing.

Extracted hardcoded logic from EmotionEngine to improve maintainability.
"""

import random
from typing import Dict, List, Any

# Emotional trigger configuration
EMOTIONAL_TRIGGERS = {
    "positive_affection": {
        "keywords": ["love", "like", "awesome", "great"],
        "effects": {"trust": 0.1, "energy": 0.2},
        "emotions": ["happy", "fond", "excited"]
    },
    "negative_emotion": {
        "keywords": ["sad", "bad", "terrible", "awful"],
        "effects": {"trust": -0.05, "energy": -0.1},
        "emotions": ["sad", "concerned", "worried"]
    },
    "playful_interaction": {
        "keywords": ["play", "game", "fun"],
        "effects": {"energy": 0.3, "playfulness": 0.1},
        "emotions": ["playful", "excited", "joy"]
    },
    "questioning": {
        "keywords": ["why", "how", "what"],
        "condition": lambda text: "?" in text and any(word in text.lower() for word in ["why", "how", "what"]),
        "effects": {"curiosity": 0.1},
        "emotions": ["curious", "focused"]
    }
}

# Personality-based response modifiers
PERSONALITY_MODIFIERS = {
    "high_sass": {
        "condition": lambda traits: traits.get("sass_level", 0) > 0.5,
        "triggers": {
            "questioning": {"style_override": "sarcastic"}
        }
    },
    "high_energy": {
        "condition": lambda traits: traits.get("energy_level", 0) > 0.8,
        "mood_influence": {"flirty": 0.2}
    },
    "low_energy": {
        "condition": lambda traits: traits.get("energy_level", 0) < 0.3,
        "mood_influence": {"behave": 0.3}
    }
}


def detect_emotional_triggers(user_input: str) -> List[str]:
    """
    Detect emotional triggers in user input.
    
    Args:
        user_input: User's input text
        
    Returns:
        List of detected trigger names
    """
    input_lower = user_input.lower()
    detected_triggers = []
    
    for trigger_name, trigger_config in EMOTIONAL_TRIGGERS.items():
        keywords = trigger_config.get("keywords", [])
        
        # Check simple keyword match
        if any(keyword in input_lower for keyword in keywords):
            detected_triggers.append(trigger_name)
            continue
        
        # Check condition function if present
        condition = trigger_config.get("condition")
        if condition and condition(user_input):
            detected_triggers.append(trigger_name)
    
    return detected_triggers


def apply_trigger_effects(trigger_name: str, current_traits: Dict[str, float]) -> Dict[str, float]:
    """
    Apply effects of emotional trigger to personality traits.
    
    Args:
        trigger_name: Name of the trigger
        current_traits: Current personality traits
        
    Returns:
        Updated personality traits
    """
    if trigger_name not in EMOTIONAL_TRIGGERS:
        return current_traits
    
    effects = EMOTIONAL_TRIGGERS[trigger_name].get("effects", {})
    updated_traits = current_traits.copy()
    
    for trait, change in effects.items():
        current_value = updated_traits.get(trait, 0.0)
        updated_traits[trait] = max(0.0, min(1.0, current_value + change))
    
    return updated_traits


def get_trigger_emotions(trigger_name: str) -> List[str]:
    """
    Get emotions associated with a trigger.
    
    Args:
        trigger_name: Name of the trigger
        
    Returns:
        List of emotion names
    """
    return EMOTIONAL_TRIGGERS.get(trigger_name, {}).get("emotions", [])


def apply_personality_modifiers(
    current_mood: str, 
    current_style: str,
    personality_traits: Dict[str, float]
) -> tuple[str, str]:
    """
    Apply personality-based modifiers to mood and style.
    
    Args:
        current_mood: Current mood
        current_style: Current style
        personality_traits: Current personality traits
        
    Returns:
        Tuple of (mood, style) with modifiers applied
    """
    updated_mood = current_mood
    updated_style = current_style
    
    # Check personality modifiers
    for modifier_name, modifier_config in PERSONALITY_MODIFIERS.items():
        condition = modifier_config.get("condition")
        if condition and condition(personality_traits):
            # Apply mood influence
            mood_influence = modifier_config.get("mood_influence", {})
            for mood, strength in mood_influence.items():
                if random.random() < strength:
                    updated_mood = mood
                    break
            
            # Apply trigger-based style overrides
            triggers = modifier_config.get("triggers", {})
            # This would need context about current triggers
            # Simplified for now
    
    return updated_mood, updated_style
