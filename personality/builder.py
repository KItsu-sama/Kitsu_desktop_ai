"""
personality/builder.py

PersonalityBuilder - Converts emotion stack to continuous personality vectors.

Replaces discrete state selection with weighted blending from EmotionStack.
Preserves existing architecture while changing output to continuous signals.

Key Features:
- Weighted blending (not winner-takes-all)
- Deterministic behavior
- Emotion intensity weighting
- Resistance-based modulation
- Smooth transitions between states
"""
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .vector import PersonalityVector, create_neutral_vector
from .presets import (
    get_mood_preset, get_style_preset, get_state_preset, get_role_preset,
    blend_personality_presets
)
from .emotion_config import EMOTION_TO_MOOD, EMOTION_TO_STYLE, EMOTION_TO_STATE

log = logging.getLogger(__name__)


@dataclass
class EmotionWeight:
    """Represents an emotion with its weight for blending."""
    name: str
    weight: float
    intensity: float
    mood: str
    style: str
    state: str


class PersonalityBuilder:
    """
    Builds continuous personality vectors from emotion stacks.
    
    Replaces discrete mood/style/state selection with weighted blending
    of personality presets based on emotion intensities.
    
    Architecture:
    EmotionStack → Weight Analysis → Preset Blending → PersonalityVector
    """
    
    def __init__(self):
        """Initialize personality builder."""
        self.previous_vector: Optional[PersonalityVector] = None
        self.inertia_factor: float = 0.3  # Emotional inertia strength
        
        # Emotion importance weights (higher = more influence)
        self.emotion_importance = {
            # High importance emotions
            "love": 1.5, "angry": 1.4, "betrayed": 1.3, "joy": 1.3,
            "excited": 1.2, "protective": 1.2, "fear": 1.2,
            
            # Medium importance emotions
            "happy": 1.0, "sad": 1.0, "offended": 1.0, "frustrated": 1.0,
            "affection": 1.0, "concerned": 1.0, "teasing": 1.0,
            
            # Low importance emotions
            "neutral": 0.5, "calm": 0.5, "content": 0.5, "bored": 0.5,
            "confused": 0.7, "surprised": 0.8, "curious": 0.8
        }
    
    def build_personality(self, emotion_stack: List[Dict[str, Any]], 
                        resistance: float = 0.0,
                        role: str = "default",
                        apply_inertia: bool = True) -> PersonalityVector:
        """
        Build personality vector from emotion stack.
        
        Args:
            emotion_stack: List of emotion dicts with name, intensity, age
            resistance: Current resistance level (0.0 - 1.0)
            role: Current role for role-based modulation
            apply_inertia: Whether to apply emotional inertia
            
        Returns:
            Blended PersonalityVector
        """
        if not emotion_stack:
            result = get_role_preset(role)
            if apply_inertia and self.previous_vector:
                result = self._apply_inertia(result, self.previous_vector)
            return result
        
        # Analyze emotions and calculate weights
        emotion_weights = self._analyze_emotions(emotion_stack, resistance)
        
        if not emotion_weights:
            result = get_role_preset(role)
            if apply_inertia and self.previous_vector:
                result = self._apply_inertia(result, self.previous_vector)
            return result
        
        # Build personality from weighted emotions
        result = self._build_from_emotions(emotion_weights, role)
        
        # Apply emotional inertia
        if apply_inertia and self.previous_vector:
            result = self._apply_inertia(result, self.previous_vector)
        
        # Store for next iteration
        self.previous_vector = result.copy()
        
        return result
    
    def _analyze_emotions(self, emotion_stack: List[Dict[str, Any]], 
                        resistance: float) -> List[EmotionWeight]:
        """
        Analyze emotion stack and calculate weights for blending.
        
        Args:
            emotion_stack: List of emotion data
            resistance: Current resistance level
            
        Returns:
            List of EmotionWeight objects sorted by weight
        """
        emotion_weights = []
        current_time = emotion_stack[0].get("current_time", 0) if emotion_stack else 0
        
        for emotion_data in emotion_stack:
            name = emotion_data.get("name", "neutral")
            intensity = emotion_data.get("intensity", 0.0)
            timestamp = emotion_data.get("timestamp", current_time)
            expire = emotion_data.get("expire", current_time + 5.0)
            
            # Skip expired emotions
            if expire <= current_time:
                continue
            
            # Calculate age-based decay
            age = current_time - timestamp
            decay_factor = max(0.0, 1.0 - age * 0.01)  # 1% decay per second
            
            # Apply resistance (reduces influence of new emotions)
            resistance_factor = 1.0 - (resistance * 0.5)
            
            # Calculate final weight
            base_weight = intensity * decay_factor * resistance_factor
            
            # Apply emotion importance multiplier
            importance = self.emotion_importance.get(name, 1.0)
            final_weight = base_weight * importance
            
            # Get mapped personality dimensions
            mood = EMOTION_TO_MOOD.get(name, "behave")
            style = EMOTION_TO_STYLE.get(name, "sweet")
            state = EMOTION_TO_STATE.get(name, "normal")
            
            emotion_weights.append(EmotionWeight(
                name=name,
                weight=final_weight,
                intensity=intensity,
                mood=mood,
                style=style,
                state=state
            ))
        
        # Sort by weight (highest first)
        emotion_weights.sort(key=lambda ew: ew.weight, reverse=True)
        
        return emotion_weights
    
    def _build_from_emotions(self, emotion_weights: List[EmotionWeight], 
                           role: str) -> PersonalityVector:
        """
        Build personality vector from weighted emotions.
        
        Uses weighted blending of presets rather than winner-takes-all.
        
        Args:
            emotion_weights: List of weighted emotions
            role: Current role for role-based modulation
            
        Returns:
            Blended PersonalityVector
        """
        if not emotion_weights:
            return get_role_preset(role)
        
        # Collect all preset vectors
        mood_vectors = []
        style_vectors = []
        state_vectors = []
        mood_weights = []
        style_weights = []
        state_weights = []
        
        # Group emotions by mapped dimensions
        for ew in emotion_weights:
            # Add mood preset
            if ew.mood:
                mood_vectors.append(get_mood_preset(ew.mood))
                mood_weights.append(ew.weight)
            
            # Add style preset
            if ew.style:
                style_vectors.append(get_style_preset(ew.style))
                style_weights.append(ew.weight)
            
            # Add state preset
            if ew.state:
                state_vectors.append(get_state_preset(ew.state))
                state_weights.append(ew.weight)
        
        # Create weighted averages for each dimension
        result = create_neutral_vector()
        
        # Blend mood vectors (40% influence)
        if mood_vectors:
            mood_result = self._weighted_average(mood_vectors, mood_weights)
            result = result.blend(mood_result, 0.4)
        
        # Blend style vectors (35% influence)
        if style_vectors:
            style_result = self._weighted_average(style_vectors, style_weights)
            result = result.blend(style_result, 0.35)
        
        # Blend state vectors (20% influence)
        if state_vectors:
            state_result = self._weighted_average(state_vectors, state_weights)
            result = result.blend(state_result, 0.2)
        
        # Apply role modulation (5% influence)
        role_vector = get_role_preset(role)
        result = result.blend(role_vector, 0.05)
        
        return result
    
    def _weighted_average(self, vectors: List[PersonalityVector], 
                        weights: List[float]) -> PersonalityVector:
        """
        Calculate weighted average of personality vectors.
        
        Args:
            vectors: List of PersonalityVector objects
            weights: Corresponding weights
            
        Returns:
            Weighted average PersonalityVector
        """
        if not vectors or not weights:
            return create_neutral_vector()
        
        if len(vectors) != len(weights):
            log.warning("Vector and weight length mismatch in weighted_average")
            return create_neutral_vector()
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return create_neutral_vector()
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Calculate weighted average for each dimension
        result_values = {}
        
        # Get all field names from PersonalityVector
        field_names = vectors[0].__dataclass_fields__.keys()
        
        for field_name in field_names:
            weighted_sum = 0.0
            for vector, weight in zip(vectors, normalized_weights):
                weighted_sum += getattr(vector, field_name) * weight
            result_values[field_name] = weighted_sum
        
        return PersonalityVector(**result_values)
    
    def _apply_inertia(self, current: PersonalityVector, 
                      previous: PersonalityVector) -> PersonalityVector:
        """
        Apply emotional inertia for smooth transitions.
        
        Args:
            current: Newly calculated personality vector
            previous: Previous personality vector
            
        Returns:
            Personality vector with inertia applied
        """
        # Blend previous state into current state
        inertia_applied = current.blend(previous, self.inertia_factor)
        
        log.debug(f"Applied inertia: factor={self.inertia_factor}")
        
        return inertia_applied
    
    def set_inertia_factor(self, factor: float):
        """
        Set emotional inertia factor.
        
        Args:
            factor: Inertia strength (0.0 = no inertia, 1.0 = fully inertial)
        """
        self.inertia_factor = max(0.0, min(1.0, factor))
        log.debug(f"Inertia factor set to: {self.inertia_factor}")
    
    def get_dominant_emotions(self, emotion_stack: List[Dict[str, Any]], 
                           top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Get top N dominant emotions from stack.
        
        Args:
            emotion_stack: List of emotion data
            top_n: Number of top emotions to return
            
        Returns:
            List of (emotion_name, weight) tuples
        """
        emotion_weights = self._analyze_emotions(emotion_stack, 0.0)
        
        return [(ew.name, ew.weight) for ew in emotion_weights[:top_n]]
    
    def get_emotion_influence(self, emotion_stack: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Get influence breakdown by emotion type.
        
        Args:
            emotion_stack: List of emotion data
            
        Returns:
            Dictionary mapping emotion names to influence weights
        """
        emotion_weights = self._analyze_emotions(emotion_stack, 0.0)
        
        return {ew.name: ew.weight for ew in emotion_weights}
    
    def reset_inertia(self):
        """Reset emotional inertia (clear previous vector)."""
        self.previous_vector = None
        log.debug("Emotional inertia reset")
    
    def get_transition_smoothness(self, current: PersonalityVector, 
                               target: PersonalityVector) -> float:
        """
        Calculate how smooth a transition would be.
        
        Args:
            current: Current personality vector
            target: Target personality vector
            
        Returns:
            Smoothness score (0.0 = abrupt, 1.0 = very smooth)
        """
        distance = current.distance_to(target)
        max_distance = math.sqrt(10)  # Maximum possible distance in 10D space
        
        # Convert distance to smoothness (inverse relationship)
        smoothness = 1.0 - (distance / max_distance)
        return max(0.0, smoothness)


# Utility function for standalone usage
def build_personality_from_emotions(emotion_stack: List[Dict[str, Any]], 
                                  role: str = "default",
                                  inertia_factor: float = 0.3) -> PersonalityVector:
    """
    Convenience function to build personality from emotions.
    
    Args:
        emotion_stack: List of emotion data
        role: Current role
        inertia_factor: Emotional inertia strength
        
    Returns:
        Blended PersonalityVector
    """
    builder = PersonalityBuilder()
    builder.set_inertia_factor(inertia_factor)
    return builder.build_personality(emotion_stack, role=role)
