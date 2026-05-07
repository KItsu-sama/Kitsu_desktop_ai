import numpy as np
from typing import List, Dict
from .emotion_config import Personality, Mood, Style, State, Role

# 10-dim: [warmth, edge, chaos, energy, affection, protectiveness, focus, mystery, verbosity, expressiveness]
BASIS_MAP = {
    # --- Moods (The Core Intent) ---
    Mood.BEHAVE:     [0.6, 0.2, 0.2, 0.5, 0.4, 0.5, 0.7, 0.2, 0.5, 0.5],
    Mood.MEAN:       [0.3, 0.8, 0.6, 0.7, 0.2, 0.1, 0.5, 0.4, 0.6, 0.8],
    Mood.FLIRTY:     [0.8, 0.4, 0.5, 0.6, 0.9, 0.3, 0.4, 0.6, 0.7, 0.9],
    Mood.PROTECTIVE: [0.7, 0.5, 0.1, 0.6, 0.8, 1.0, 0.8, 0.3, 0.5, 0.4],

    # --- Styles (The Expression) ---
    Style.CHAOTIC:   [0.5, 0.5, 1.0, 0.9, 0.4, 0.2, 0.2, 0.5, 0.9, 1.0],
    Style.SWEET:     [1.0, 0.0, 0.1, 0.4, 0.9, 0.5, 0.5, 0.2, 0.6, 0.7],
    Style.COLD:      [0.1, 0.7, 0.0, 0.3, 0.1, 0.2, 0.9, 0.8, 0.3, 0.2],
    Style.DIRECT:    [0.4, 0.5, 0.0, 0.4, 0.2, 0.3, 1.0, 0.1, 0.1, 0.1],
    Style.SARCASTIC: [0.4, 0.9, 0.4, 0.6, 0.3, 0.2, 0.6, 0.5, 0.7, 0.8],
    
    # --- States (The Quirk/Physicality) ---
    State.FOX:       [0.6, 0.4, 0.8, 0.8, 0.5, 0.4, 0.4, 0.6, 0.6, 0.9],
    State.GLITCH:    [0.3, 0.6, 1.0, 0.9, 0.2, 0.1, 0.1, 0.9, 0.8, 0.7],
    State.ANALYST:   [0.3, 0.3, 0.0, 0.5, 0.2, 0.4, 1.0, 0.5, 0.9, 0.3],
}

def calculate_vibe_vector(p: Personality) -> List[float]:
    """
    Collapses the 4-layer personality into a single 10-dim vibe vector.
    """
    components = []
    
    # Safely get vectors for each layer
    for val in [p.mood, p.style, p.state]:
        if val in BASIS_MAP:
            components.append(BASIS_MAP[val])
            
    if not components:
        return [0.5] * 10 # Default neutral
        
    # Calculate mean across all active components
    vibe = np.mean(components, axis=0)
    
    # Apply Role modifiers (Role doesn't have its own vector, it scales others)
    if p.role == Role.CARETAKER:
        vibe[0] *= 1.2 # Boost warmth
        vibe[5] *= 1.3 # Boost protectiveness
    elif p.role == Role.OBSERVER:
        vibe[8] *= 0.5 # Reduce verbosity
        vibe[9] *= 0.5 # Reduce expressiveness

    return [round(float(x), 2) for x in np.clip(vibe, 0, 1)]