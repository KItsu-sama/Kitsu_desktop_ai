"""
personality/signals.py

Prompt signal builder - converts personality vectors to natural language signals.

Transforms continuous personality vectors into structured prompt signals
that can be used by LLMs to generate contextually appropriate responses.

Key Features:
- Vector → natural language tone conversion
- Lightweight processing for low-spec systems
- Structured output for AI pipeline integration
- Maintains personality semantics in continuous space
"""

import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

from .vector import PersonalityVector

log = logging.getLogger(__name__)


@dataclass
class PromptSignal:
    """
    Structured prompt signal for LLM consumption.
    
    Contains all necessary information for generating personality-consistent responses.
    """
    # Core tone description
    tone: str
    
    # Behavioral parameters
    verbosity_target: int  # Target word count
    emoji_weight: float     # Emoji usage likelihood (0.0 - 1.0)
    
    # Stylistic elements
    formality: float       # Formality level (0.0 = casual, 1.0 = formal)
    energy_level: float    # Energy in response (0.0 - 1.0)
    
    # Emotional content
    warmth_expression: float  # How much warmth to express (0.0 - 1.0)
    edge_level: float       # Edge/sass level (0.0 - 1.0)
    
    # Raw vector for advanced processing
    raw_vector: Dict[str, float]
    
    # Metadata
    confidence: float      # How confident the signal is (0.0 - 1.0)
    complexity: str        # "simple", "moderate", "complex"


class PromptSignalBuilder:
    """
    Converts personality vectors to structured prompt signals.
    
    Analyzes vector dimensions and generates appropriate natural language
    descriptions and parameters for LLM prompt engineering.
    """
    
    def __init__(self):
        """Initialize prompt signal builder."""
        # Tone mapping thresholds
        self.tone_mappings = self._initialize_tone_mappings()
        
        # Verbosity mapping (vector verbosity → word count)
        self.verbosity_ranges = {
            'minimal': (0.0, 0.2, 5),      # Very brief
            'brief': (0.2, 0.4, 12),       # Short responses
            'moderate': (0.4, 0.7, 25),    # Normal length
            'verbose': (0.7, 0.9, 40),     # Detailed responses
            'extensive': (0.9, 1.0, 60)     # Very detailed
        }
        
        log.debug("PromptSignalBuilder initialized")
    
    def _initialize_tone_mappings(self) -> Dict[str, Tuple[float, float, str]]:
        """Initialize tone mapping based on vector combinations."""
        return {
            # Warm + gentle tones
            'sweet_caring': (0.7, 0.3, "Warm, caring, and gentle"),
            'affectionate': (0.8, 0.2, "Warm and affectionate"),
            'supportive': (0.7, 0.4, "Supportive and encouraging"),
            
            # Edgy/playful tones
            'playful_teasing': (0.5, 0.7, "Playful with light teasing"),
            'sassy': (0.4, 0.8, "Sassy and confident"),
            'mischievous': (0.6, 0.6, "Mischievous and playful"),
            
            # Professional/neutral tones
            'helpful': (0.6, 0.3, "Helpful and cooperative"),
            'direct': (0.4, 0.4, "Direct and straightforward"),
            'analytical': (0.3, 0.2, "Analytical and precise"),
            
            # Mysterious/complex tones
            'mysterious': (0.3, 0.5, "Mysterious and intriguing"),
            'enigmatic': (0.2, 0.6, "Enigmatic and subtle"),
            'calm_observant': (0.4, 0.3, "Calm and observant"),
            
            # High energy tones
            'energetic': (0.5, 0.5, "Energetic and enthusiastic"),
            'excited': (0.7, 0.4, "Excited and enthusiastic"),
            'bubbly': (0.8, 0.3, "Bubbly and cheerful"),
            
            # Low energy tones
            'gentle': (0.5, 0.2, "Gentle and soft-spoken"),
            'reserved': (0.3, 0.3, "Reserved and thoughtful"),
            'quiet': (0.2, 0.2, "Quiet and minimal")
        }
    
    def to_prompt_signal(self, vector: PersonalityVector) -> PromptSignal:
        """
        Convert personality vector to structured prompt signal.
        
        Args:
            vector: PersonalityVector to convert
            
        Returns:
            PromptSignal for LLM consumption
        """
        # Generate tone description
        tone = self._generate_tone_description(vector)
        
        # Calculate behavioral parameters
        verbosity_target = self._calculate_verbosity(vector)
        emoji_weight = self._calculate_emoji_weight(vector)
        
        # Determine stylistic elements
        formality = self._calculate_formality(vector)
        energy_level = vector.energy
        
        # Calculate emotional expression levels
        warmth_expression = vector.warmth * vector.expressiveness
        edge_level = vector.edge * vector.expressiveness
        
        # Determine complexity
        complexity = self._determine_complexity(vector)
        
        # Calculate confidence based on vector coherence
        confidence = self._calculate_confidence(vector)
        
        return PromptSignal(
            tone=tone,
            verbosity_target=verbosity_target,
            emoji_weight=emoji_weight,
            formality=formality,
            energy_level=energy_level,
            warmth_expression=warmth_expression,
            edge_level=edge_level,
            raw_vector=vector.to_dict(),
            confidence=confidence,
            complexity=complexity
        )
    
    def _generate_tone_description(self, vector: PersonalityVector) -> str:
        """
        Generate natural language tone description from vector.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            Natural language tone description
        """
        # Primary tone based on warmth and edge
        warmth = vector.warmth
        edge = vector.edge
        
        # Find closest tone mapping
        best_tone = "helpful"
        best_score = float('inf')
        
        for tone_name, (min_warmth, max_edge, description) in self.tone_mappings.items():
            # Calculate distance from this tone
            warmth_dist = abs(warmth - min_warmth)
            edge_dist = abs(edge - max_edge)
            total_dist = warmth_dist + edge_dist
            
            if total_dist < best_score:
                best_score = total_dist
                best_tone = description
        
        # Add modifiers based on other dimensions
        modifiers = []
        
        # Chaos modifier
        if vector.chaos > 0.7:
            modifiers.append("with unpredictable energy")
        elif vector.chaos > 0.5:
            modifiers.append("with playful spontaneity")
        
        # Energy modifier
        if vector.energy > 0.8:
            modifiers.append("and high energy")
        elif vector.energy < 0.3:
            modifiers.append("and calm demeanor")
        
        # Mystery modifier
        if vector.mystery > 0.7:
            modifiers.append("with an air of mystery")
        
        # Affection modifier
        if vector.affection > 0.7:
            modifiers.append("showing deep affection")
        
        # Combine base tone with modifiers
        if modifiers:
            return f"{best_tone}, {', '.join(modifiers)}"
        else:
            return best_tone
    
    def _calculate_verbosity(self, vector: PersonalityVector) -> int:
        """
        Calculate target word count based on verbosity dimension.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            Target word count
        """
        verbosity = vector.verbosity
        
        # Adjust based on focus (high focus = more concise)
        if vector.focus > 0.7:
            verbosity *= 0.7
        
        # Adjust based on energy (high energy = more talkative)
        if vector.energy > 0.7:
            verbosity *= 1.2
        
        # Find appropriate range
        for range_name, (min_val, max_val, word_count) in self.verbosity_ranges.items():
            if min_val <= verbosity < max_val:
                # Add some variation within range
                variation = (verbosity - min_val) / (max_val - min_val)
                return int(word_count * (0.8 + 0.4 * variation))
        
        # Default to moderate
        return 25
    
    def _calculate_emoji_weight(self, vector: PersonalityVector) -> float:
        """
        Calculate emoji usage likelihood.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            Emoji weight (0.0 - 1.0)
        """
        # Base emoji weight from expressiveness
        emoji_weight = vector.expressiveness * 0.6
        
        # Increase with warmth and affection
        emoji_weight += (vector.warmth + vector.affection) * 0.15
        
        # Decrease with edge and formality
        emoji_weight -= vector.edge * 0.2
        emoji_weight -= (1.0 - self._calculate_formality(vector)) * 0.1
        
        # Decrease with high focus (task mode)
        if vector.focus > 0.8:
            emoji_weight *= 0.3
        
        return max(0.0, min(1.0, emoji_weight))
    
    def _calculate_formality(self, vector: PersonalityVector) -> float:
        """
        Calculate formality level.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            Formality level (0.0 = casual, 1.0 = formal)
        """
        # Base formality from inverse of chaos and edge
        formality = (1.0 - vector.chaos) * 0.4
        formality += (1.0 - vector.edge) * 0.3
        
        # Increase with focus and mystery
        formality += vector.focus * 0.2
        formality += vector.mystery * 0.1
        
        return max(0.0, min(1.0, formality))
    
    def _determine_complexity(self, vector: PersonalityVector) -> str:
        """
        Determine response complexity based on vector dimensions.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            Complexity level: "simple", "moderate", or "complex"
        """
        # Complexity factors
        focus_factor = vector.focus
        mystery_factor = vector.mystery
        verbosity_factor = vector.verbosity
        
        # Calculate complexity score
        complexity_score = (focus_factor + mystery_factor + verbosity_factor) / 3.0
        
        if complexity_score < 0.4:
            return "simple"
        elif complexity_score < 0.7:
            return "moderate"
        else:
            return "complex"
    
    def _calculate_confidence(self, vector: PersonalityVector) -> float:
        """
        Calculate confidence in the signal based on vector coherence.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Check for conflicting signals
        conflicts = 0
        
        # High warmth with high edge is conflicting
        if vector.warmth > 0.7 and vector.edge > 0.7:
            conflicts += 1
        
        # High chaos with high focus is conflicting
        if vector.chaos > 0.7 and vector.focus > 0.7:
            conflicts += 1
        
        # High mystery with high expressiveness can be conflicting
        if vector.mystery > 0.8 and vector.expressiveness > 0.8:
            conflicts += 1
        
        # Calculate base confidence
        base_confidence = 1.0 - (conflicts * 0.2)
        
        # Reduce confidence for extreme values (might be unstable)
        extreme_count = sum(
            1 for val in vector.to_dict().values() 
            if val > 0.9 or val < 0.1
        )
        base_confidence -= extreme_count * 0.05
        
        return max(0.3, min(1.0, base_confidence))
    
    def get_llm_prompt_template(self, signal: PromptSignal) -> str:
        """
        Generate LLM prompt template from signal.
        
        Args:
            signal: PromptSignal to convert
            
        Returns:
            Prompt template string
        """
        template = f"""Respond with a {signal.complexity} message that is {signal.tone}.

Guidelines:
- Target approximately {signal.verbosity_target} words
- Energy level: {signal.energy_level:.0%}
- Formality: {signal.formality:.0%}
- Emoji usage likelihood: {signal.emoji_weight:.0%}
- Express warmth: {signal.warmth_expression:.0%}
- Edge/sass level: {signal.edge_level:.0%}

Maintain consistency with this personality throughout the response."""
        
        return template
    
    def signal_to_dict(self, signal: PromptSignal) -> Dict[str, Any]:
        """
        Convert PromptSignal to dictionary for serialization.
        
        Args:
            signal: PromptSignal to convert
            
        Returns:
            Dictionary representation
        """
        return {
            'tone': signal.tone,
            'verbosity_target': signal.verbosity_target,
            'emoji_weight': signal.emoji_weight,
            'formality': signal.formality,
            'energy_level': signal.energy_level,
            'warmth_expression': signal.warmth_expression,
            'edge_level': signal.edge_level,
            'raw_vector': signal.raw_vector,
            'confidence': signal.confidence,
            'complexity': signal.complexity
        }


# Convenience functions for standalone usage
def build_prompt_signal(vector: PersonalityVector) -> PromptSignal:
    """
    Convenience function to build prompt signal from vector.
    
    Args:
        vector: PersonalityVector
        
    Returns:
        PromptSignal for LLM consumption
    """
    builder = PromptSignalBuilder()
    return builder.to_prompt_signal(vector)


def get_llm_prompt(vector: PersonalityVector) -> str:
    """
    Convenience function to get complete LLM prompt from vector.
    
    Args:
        vector: PersonalityVector
        
    Returns:
        Complete LLM prompt template
    """
    builder = PromptSignalBuilder()
    signal = builder.to_prompt_signal(vector)
    return builder.get_llm_prompt_template(signal)
