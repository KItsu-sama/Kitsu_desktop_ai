"""
personality/vector.py

Core PersonalityVector dataclass for the hybrid vector-based personality system.

This module defines the 10-dimensional personality vector that replaces discrete 
personality states with continuous signals for smoother, more natural transitions.

Architecture:
- Core affect: warmth, edge, chaos, energy
- Relational: affection, protectiveness  
- Cognitive: focus, mystery
- Behavioral: verbosity, expressiveness

All values are clamped to [0.0, 1.0] and support weighted blending.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import math


@dataclass
class PersonalityVector:
    """
    10-dimensional continuous personality vector.
    
    Replaces discrete mood/style/state/role tuples with smooth, blendable values.
    All dimensions are normalized to [0.0, 1.0].
    
    Core Affect (4 dimensions):
    - warmth: Emotional warmth vs coldness (0.0 = cold, 1.0 = warm)
    - edge: Sharpness/sass vs gentleness (0.0 = gentle, 1.0 = edgy)
    - chaos: Unpredictability vs stability (0.0 = stable, 1.0 = chaotic)
    - energy: Activity level vs passivity (0.0 = tired, 1.0 = energetic)
    
    Relational (2 dimensions):
    - affection: Caring vs detached (0.0 = distant, 1.0 = affectionate)
    - protectiveness: Protective vs neutral (0.0 = neutral, 1.0 = protective)
    
    Cognitive (2 dimensions):
    - focus: Concentration vs distraction (0.0 = distracted, 1.0 = focused)
    - mystery: Enigmatic vs straightforward (0.0 = direct, 1.0 = mysterious)
    
    Behavioral (2 dimensions):
    - verbosity: Talkativeness vs conciseness (0.0 = brief, 1.0 = verbose)
    - expressiveness: Emotional expression vs restraint (0.0 = reserved, 1.0 = expressive)
    """
    
    # Core affect
    warmth: float = 0.5
    edge: float = 0.5
    chaos: float = 0.5
    energy: float = 0.5
    
    # Relational
    affection: float = 0.5
    protectiveness: float = 0.5
    
    # Cognitive
    focus: float = 0.5
    mystery: float = 0.5
    
    # Behavioral
    verbosity: float = 0.5
    expressiveness: float = 0.5
    
    def __post_init__(self):
        """Clamp all values to [0.0, 1.0] range."""
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            clamped_value = max(0.0, min(1.0, float(value)))
            setattr(self, field_name, clamped_value)
    
    def blend(self, other: 'PersonalityVector', weight: float) -> 'PersonalityVector':
        """
        Blend this vector with another using weighted interpolation.
        
        Args:
            other: Another PersonalityVector to blend with
            weight: Blend weight (0.0 = keep self, 1.0 = use other)
            
        Returns:
            New PersonalityVector with blended values
        """
        weight = max(0.0, min(1.0, float(weight)))
        
        blended_values = {}
        for field_name in self.__dataclass_fields__:
            self_value = getattr(self, field_name)
            other_value = getattr(other, field_name)
            blended_values[field_name] = self_value * (1.0 - weight) + other_value * weight
        
        return PersonalityVector(**blended_values)
    
    def weighted_average(self, vectors: List['PersonalityVector'], weights: List[float]) -> 'PersonalityVector':
        """
        Compute weighted average with multiple vectors.
        
        Args:
            vectors: List of PersonalityVectors to average
            weights: Corresponding weights (must sum to 1.0)
            
        Returns:
            New PersonalityVector with weighted average values
        """
        if not vectors or not weights or len(vectors) != len(weights):
            return PersonalityVector()
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return PersonalityVector()
        weights = [w / total_weight for w in weights]
        
        averaged_values = {}
        for field_name in self.__dataclass_fields__:
            weighted_sum = sum(
                getattr(vec, field_name) * weight 
                for vec, weight in zip(vectors, weights)
            )
            averaged_values[field_name] = weighted_sum
        
        return PersonalityVector(**averaged_values)
    
    def distance_to(self, other: 'PersonalityVector') -> float:
        """
        Calculate Euclidean distance to another vector.
        
        Args:
            other: Another PersonalityVector
            
        Returns:
            Euclidean distance (0.0 = identical, higher = more different)
        """
        squared_diffs = []
        for field_name in self.__dataclass_fields__:
            diff = getattr(self, field_name) - getattr(other, field_name)
            squared_diffs.append(diff * diff)
        
        return math.sqrt(sum(squared_diffs))
    
    def magnitude(self) -> float:
        """
        Calculate vector magnitude (length from origin).
        
        Returns:
            Euclidean magnitude
        """
        squared_values = []
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            squared_values.append(value * value)
        
        return math.sqrt(sum(squared_values))
    
    def normalize(self) -> 'PersonalityVector':
        """
        Normalize vector to unit magnitude while preserving direction.
        
        Returns:
            Normalized PersonalityVector
        """
        mag = self.magnitude()
        if mag == 0:
            return PersonalityVector()
        
        normalized_values = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            normalized_values[field_name] = value / mag
        
        return PersonalityVector(**normalized_values)
    
    def lerp(self, other: 'PersonalityVector', t: float) -> 'PersonalityVector':
        """
        Linear interpolation between this vector and another.
        
        Args:
            other: Target vector
            t: Interpolation parameter (0.0 = self, 1.0 = other)
            
        Returns:
            Interpolated PersonalityVector
        """
        t = max(0.0, min(1.0, float(t)))
        return self.blend(other, t)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary representation."""
        return {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityVector':
        """Create from dictionary, ignoring unknown keys."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered_data = {
            k: v for k, v in data.items() 
            if k in valid_fields
        }
        return cls(**filtered_data)
    
    def copy(self) -> 'PersonalityVector':
        """Create a deep copy of this vector."""
        return PersonalityVector(**self.to_dict())
    
    def __str__(self) -> str:
        """String representation with key values."""
        key_dims = ['warmth', 'edge', 'chaos', 'energy', 'affection']
        key_values = [f"{k}={getattr(self, k):.2f}" for k in key_dims]
        return f"PersonalityVector({', '.join(key_values)})"
    
    def __repr__(self) -> str:
        """Full representation."""
        values = [f"{k}={getattr(self, k):.3f}" for k in self.__dataclass_fields__]
        return f"PersonalityVector({', '.join(values)})"


# Utility functions for vector operations
def create_zero_vector() -> PersonalityVector:
    """Create a vector with all values at 0.0."""
    return PersonalityVector(
        warmth=0.0, edge=0.0, chaos=0.0, energy=0.0,
        affection=0.0, protectiveness=0.0,
        focus=0.0, mystery=0.0,
        verbosity=0.0, expressiveness=0.0
    )


def create_neutral_vector() -> PersonalityVector:
    """Create a vector with all values at 0.5 (neutral baseline)."""
    return PersonalityVector()


def create_extreme_vector(warmth: float = 0.5, edge: float = 0.5, chaos: float = 0.5, 
                        energy: float = 0.5, affection: float = 0.5, 
                        protectiveness: float = 0.5, focus: float = 0.5, 
                        mystery: float = 0.5, verbosity: float = 0.5, 
                        expressiveness: float = 0.5) -> PersonalityVector:
    """
    Create a vector with specific values, useful for presets.
    All parameters are clamped to [0.0, 1.0].
    """
    return PersonalityVector(
        warmth=warmth, edge=edge, chaos=chaos, energy=energy,
        affection=affection, protectiveness=protectiveness,
        focus=focus, mystery=mystery,
        verbosity=verbosity, expressiveness=expressiveness
    )
