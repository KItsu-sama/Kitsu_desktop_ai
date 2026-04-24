"""
personality/adapters.py

Visual output adapters for avatar and shimeji systems.

Converts personality vectors to visual parameters for different output systems.
Provides pure data output without direct coupling to rendering systems.

Key Features:
- Avatar animation parameter mapping
- Shimeji behavior parameter mapping
- Event-driven architecture (no direct coupling)
- Smooth transitions for visual changes
"""

import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .vector import PersonalityVector

log = logging.getLogger(__name__)


@dataclass
class AvatarParams:
    """Parameters for avatar rendering system."""
    
    # Facial expressions
    eye_openness: float          # 0.0 = closed, 1.0 = fully open
    smile_intensity: float       # 0.0 = neutral, 1.0 = big smile
    brow_position: float         # 0.0 = relaxed, 1.0 = furrowed
    
    # Body language
    posture: float              # 0.0 = slumped, 1.0 = upright
    animation_speed: float      # 0.0 = slow, 1.0 = fast
    movement_range: float       # 0.0 = minimal, 1.0 = expressive
    
    # Visual effects
    glow_intensity: float       # 0.0 = none, 1.0 = bright glow
    particle_effects: float     # 0.0 = none, 1.0 = many particles
    color_temperature: float    # 0.0 = cool, 1.0 = warm
    
    # Interaction cues
    proximity_radius: float     # 0.0 = close, 1.0 = distant
    responsiveness: float       # 0.0 = slow, 1.0 = quick reactions
    
    # Metadata
    animation_state: str        # Current animation state name
    transition_speed: float    # Speed of transitions between states


@dataclass
class ShimejiParams:
    """Parameters for shimeji desktop companion system."""
    
    # Movement behavior
    movement_speed: float       # 0.0 = stationary, 1.0 = very active
    jump_frequency: float      # 0.0 = never, 1.0 = constantly
    wander_radius: float       # 0.0 = small area, 1.0 = full screen
    
    # Interaction behavior
    interaction_frequency: float  # 0.0 = rarely, 1.0 = frequently
    approach_distance: float      # 0.0 = stays distant, 1.0 = gets close
    attention_duration: float    # 0.0 = brief, 1.0 = prolonged
    
    # Visual behavior
    pose_variety: float       # 0.0 = repetitive, 1.0 = varied poses
    expression_changes: float  # 0.0 = static, 1.0 = frequent changes
    idle_animations: float    # 0.0 = minimal, 1.0 = many idle behaviors
    
    # Personality expression
    playfulness: float        # 0.0 = serious, 1.0 = very playful
    curiosity: float         # 0.0 = indifferent, 1.0 = very curious
    mischievousness: float   # 0.0 = well-behaved, 1.0 = troublemaker
    
    # Environmental interaction
    object_interaction: float # 0.0 = ignores objects, 1.0 = plays with everything
    window_climbing: float   # 0.0 = stays on desktop, 1.0 = climbs windows
    
    # Metadata
    behavior_state: str       # Current behavior state
    activity_level: str      # "sleeping", "idle", "active", "hyper"


class VisualAdapter(ABC):
    """Base class for visual output adapters."""
    
    @abstractmethod
    def to_params(self, vector: PersonalityVector) -> Any:
        """Convert personality vector to system-specific parameters."""
        pass
    
    @abstractmethod
    def get_transition_params(self, current: Any, target: Any, 
                           progress: float) -> Any:
        """Get interpolated parameters for smooth transitions."""
        pass


class AvatarAdapter(VisualAdapter):
    """
    Adapter for avatar rendering system.
    
    Maps personality dimensions to avatar visual parameters.
    Focuses on facial expressions, body language, and visual effects.
    """
    
    def __init__(self):
        """Initialize avatar adapter."""
        # Animation state mappings based on vector combinations
        self.state_mappings = self._initialize_state_mappings()
        log.debug("AvatarAdapter initialized")
    
    def _initialize_state_mappings(self) -> Dict[str, Tuple[float, float, float, float]]:
        """Initialize animation state mappings."""
        return {
            'idle_sleeping': (0.1, 0.0, 0.1, 0.1),     # low energy, low everything
            'idle_calm': (0.5, 0.2, 0.3, 0.3),         # moderate, calm
            'idle_playful': (0.7, 0.6, 0.4, 0.6),       # high energy, playful
            'active_focused': (0.6, 0.3, 0.7, 0.5),      # focused, moderate energy
            'active_excited': (0.9, 0.8, 0.3, 0.8),      # very excited
            'social_affectionate': (0.8, 0.7, 0.2, 0.7),  # warm, affectionate
            'social_teasing': (0.6, 0.5, 0.6, 0.7),      # teasing, playful
            'protective': (0.7, 0.4, 0.2, 0.6),         # caring, protective
            'mysterious': (0.4, 0.2, 0.8, 0.5)          # mysterious, subtle
        }
    
    def to_params(self, vector: PersonalityVector) -> AvatarParams:
        """
        Convert personality vector to avatar parameters.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            AvatarParams for rendering system
        """
        # Facial expressions
        eye_openness = self._calculate_eye_openness(vector)
        smile_intensity = self._calculate_smile_intensity(vector)
        brow_position = self._calculate_brow_position(vector)
        
        # Body language
        posture = self._calculate_posture(vector)
        animation_speed = vector.energy
        movement_range = vector.expressiveness
        
        # Visual effects
        glow_intensity = self._calculate_glow_intensity(vector)
        particle_effects = vector.chaos * vector.energy
        color_temperature = vector.warmth
        
        # Interaction cues
        proximity_radius = 1.0 - vector.affection  # More affection = closer
        responsiveness = vector.energy * vector.focus
        
        # Determine animation state
        animation_state = self._determine_animation_state(vector)
        transition_speed = 0.3 + (vector.energy * 0.5)
        
        return AvatarParams(
            eye_openness=eye_openness,
            smile_intensity=smile_intensity,
            brow_position=brow_position,
            posture=posture,
            animation_speed=animation_speed,
            movement_range=movement_range,
            glow_intensity=glow_intensity,
            particle_effects=particle_effects,
            color_temperature=color_temperature,
            proximity_radius=proximity_radius,
            responsiveness=responsiveness,
            animation_state=animation_state,
            transition_speed=transition_speed
        )
    
    def _calculate_eye_openness(self, vector: PersonalityVector) -> float:
        """Calculate eye openness based on energy and focus."""
        base_openness = 0.3 + (vector.energy * 0.5)
        
        # Adjust for focus (high focus = more alert eyes)
        if vector.focus > 0.7:
            base_openness += 0.2
        
        # Adjust for mystery (high mystery = slightly narrowed eyes)
        if vector.mystery > 0.6:
            base_openness -= 0.1
        
        return max(0.1, min(1.0, base_openness))
    
    def _calculate_smile_intensity(self, vector: PersonalityVector) -> float:
        """Calculate smile intensity based on warmth and affection."""
        base_smile = (vector.warmth + vector.affection) / 2.0
        
        # Modify with expressiveness
        smile = base_smile * vector.expressiveness
        
        # Reduce with high edge (sass overrides smile)
        if vector.edge > 0.6:
            smile *= (1.0 - vector.edge * 0.3)
        
        return max(0.0, min(1.0, smile))
    
    def _calculate_brow_position(self, vector: PersonalityVector) -> float:
        """Calculate brow position based on edge and focus."""
        # High edge = furrowed brows
        brow_furrow = vector.edge * 0.7
        
        # High focus = slightly furrowed (concentration)
        focus_furrow = vector.focus * 0.3
        
        # High warmth = relaxed brows
        warmth_relax = (1.0 - vector.warmth) * 0.2
        
        return max(0.0, min(1.0, brow_furrow + focus_furrow - warmth_relax))
    
    def _calculate_posture(self, vector: PersonalityVector) -> float:
        """Calculate posture based on energy and protectiveness."""
        # Base posture from energy
        base_posture = 0.3 + (vector.energy * 0.5)
        
        # Protectiveness = more upright posture
        if vector.protectiveness > 0.6:
            base_posture += 0.2
        
        # High chaos = more dynamic posture
        if vector.chaos > 0.7:
            base_posture = min(1.0, base_posture + 0.1)
        
        return max(0.1, min(1.0, base_posture))
    
    def _calculate_glow_intensity(self, vector: PersonalityVector) -> float:
        """Calculate glow intensity based on energy and mystery."""
        # Base glow from energy
        base_glow = vector.energy * 0.6
        
        # Mystery adds ethereal glow
        mystery_glow = vector.mystery * 0.4
        
        # Affection adds warm glow
        affection_glow = vector.affection * 0.3
        
        return max(0.0, min(1.0, base_glow + mystery_glow + affection_glow))
    
    def _determine_animation_state(self, vector: PersonalityVector) -> str:
        """Determine appropriate animation state from vector."""
        # Find closest state mapping
        best_state = 'idle_calm'
        best_distance = float('inf')
        
        for state_name, (energy, warmth, mystery, chaos) in self.state_mappings.items():
            distance = (
                abs(vector.energy - energy) +
                abs(vector.warmth - warmth) +
                abs(vector.mystery - mystery) +
                abs(vector.chaos - chaos)
            )
            
            if distance < best_distance:
                best_distance = distance
                best_state = state_name
        
        return best_state
    
    def get_transition_params(self, current: AvatarParams, target: AvatarParams, 
                           progress: float) -> AvatarParams:
        """Get interpolated avatar parameters for smooth transitions."""
        progress = max(0.0, min(1.0, progress))
        
        return AvatarParams(
            eye_openness=current.eye_openness + (target.eye_openness - current.eye_openness) * progress,
            smile_intensity=current.smile_intensity + (target.smile_intensity - current.smile_intensity) * progress,
            brow_position=current.brow_position + (target.brow_position - current.brow_position) * progress,
            posture=current.posture + (target.posture - current.posture) * progress,
            animation_speed=current.animation_speed + (target.animation_speed - current.animation_speed) * progress,
            movement_range=current.movement_range + (target.movement_range - current.movement_range) * progress,
            glow_intensity=current.glow_intensity + (target.glow_intensity - current.glow_intensity) * progress,
            particle_effects=current.particle_effects + (target.particle_effects - current.particle_effects) * progress,
            color_temperature=current.color_temperature + (target.color_temperature - current.color_temperature) * progress,
            proximity_radius=current.proximity_radius + (target.proximity_radius - current.proximity_radius) * progress,
            responsiveness=current.responsiveness + (target.responsiveness - current.responsiveness) * progress,
            animation_state=target.animation_state,  # Use target state immediately
            transition_speed=current.transition_speed + (target.transition_speed - current.transition_speed) * progress
        )


class ShimejiAdapter(VisualAdapter):
    """
    Adapter for shimeji desktop companion system.
    
    Maps personality dimensions to shimeji behavior parameters.
    Focuses on movement, interaction, and personality expression.
    """
    
    def __init__(self):
        """Initialize shimeji adapter."""
        self.behavior_states = self._initialize_behavior_states()
        log.debug("ShimejiAdapter initialized")
    
    def _initialize_behavior_states(self) -> Dict[str, Dict[str, float]]:
        """Initialize behavior state definitions."""
        return {
            'sleeping': {
                'movement_speed': 0.0, 'interaction_frequency': 0.0,
                'playfulness': 0.0, 'activity_level': 0.0
            },
            'idle': {
                'movement_speed': 0.2, 'interaction_frequency': 0.1,
                'playfulness': 0.2, 'activity_level': 0.2
            },
            'curious': {
                'movement_speed': 0.5, 'interaction_frequency': 0.4,
                'playfulness': 0.4, 'activity_level': 0.5
            },
            'playful': {
                'movement_speed': 0.8, 'interaction_frequency': 0.7,
                'playfulness': 0.9, 'activity_level': 0.8
            },
            'hyper': {
                'movement_speed': 1.0, 'interaction_frequency': 0.9,
                'playfulness': 1.0, 'activity_level': 1.0
            }
        }
    
    def to_params(self, vector: PersonalityVector) -> ShimejiParams:
        """
        Convert personality vector to shimeji parameters.
        
        Args:
            vector: PersonalityVector
            
        Returns:
            ShimejiParams for behavior system
        """
        # Movement behavior
        movement_speed = self._calculate_movement_speed(vector)
        jump_frequency = vector.energy * vector.chaos
        wander_radius = vector.chaos * 0.8
        
        # Interaction behavior
        interaction_frequency = self._calculate_interaction_frequency(vector)
        approach_distance = vector.affection
        attention_duration = vector.focus
        
        # Visual behavior
        pose_variety = vector.expressiveness
        expression_changes = vector.expressiveness * vector.energy
        idle_animations = (1.0 - vector.focus) * vector.energy
        
        # Personality expression
        playfulness = (vector.energy + vector.chaos) / 2.0
        curiosity = vector.mystery * vector.energy
        mischievousness = vector.chaos * vector.edge
        
        # Environmental interaction
        object_interaction = vector.chaos * vector.energy
        window_climbing = vector.chaos * 0.7
        
        # Determine behavior state
        behavior_state = self._determine_behavior_state(vector)
        activity_level = self._determine_activity_level(vector)
        
        return ShimejiParams(
            movement_speed=movement_speed,
            jump_frequency=jump_frequency,
            wander_radius=wander_radius,
            interaction_frequency=interaction_frequency,
            approach_distance=approach_distance,
            attention_duration=attention_duration,
            pose_variety=pose_variety,
            expression_changes=expression_changes,
            idle_animations=idle_animations,
            playfulness=playfulness,
            curiosity=curiosity,
            mischievousness=mischievousness,
            object_interaction=object_interaction,
            window_climbing=window_climbing,
            behavior_state=behavior_state,
            activity_level=activity_level
        )
    
    def _calculate_movement_speed(self, vector: PersonalityVector) -> float:
        """Calculate movement speed from energy and chaos."""
        base_speed = vector.energy * 0.7
        chaos_boost = vector.chaos * 0.3
        
        # High focus reduces movement speed
        focus_reduction = (1.0 - vector.focus) * 0.2
        
        return max(0.0, min(1.0, base_speed + chaos_boost + focus_reduction))
    
    def _calculate_interaction_frequency(self, vector: PersonalityVector) -> float:
        """Calculate interaction frequency from multiple dimensions."""
        # Base from affection and energy
        base_frequency = (vector.affection + vector.energy) / 2.0
        
        # Expressiveness increases interaction
        expressiveness_boost = vector.expressiveness * 0.3
        
        # High mystery reduces interaction slightly
        mystery_reduction = vector.mystery * 0.1
        
        return max(0.0, min(1.0, base_frequency + expressiveness_boost - mystery_reduction))
    
    def _determine_behavior_state(self, vector: PersonalityVector) -> str:
        """Determine appropriate behavior state."""
        # Low energy = sleeping
        if vector.energy < 0.2:
            return 'sleeping'
        
        # High energy and chaos = hyper
        if vector.energy > 0.8 and vector.chaos > 0.6:
            return 'hyper'
        
        # High energy and playfulness = playful
        if vector.energy > 0.6 and (vector.chaos > 0.4 or vector.edge > 0.5):
            return 'playful'
        
        # High mystery and energy = curious
        if vector.mystery > 0.6 and vector.energy > 0.4:
            return 'curious'
        
        # Default to idle
        return 'idle'
    
    def _determine_activity_level(self, vector: PersonalityVector) -> str:
        """Determine activity level category."""
        activity_score = (vector.energy + vector.chaos + vector.expressiveness) / 3.0
        
        if activity_score < 0.3:
            return 'sleeping'
        elif activity_score < 0.5:
            return 'idle'
        elif activity_score < 0.7:
            return 'active'
        else:
            return 'hyper'
    
    def get_transition_params(self, current: ShimejiParams, target: ShimejiParams, 
                           progress: float) -> ShimejiParams:
        """Get interpolated shimeji parameters for smooth transitions."""
        progress = max(0.0, min(1.0, progress))
        
        return ShimejiParams(
            movement_speed=current.movement_speed + (target.movement_speed - current.movement_speed) * progress,
            jump_frequency=current.jump_frequency + (target.jump_frequency - current.jump_frequency) * progress,
            wander_radius=current.wander_radius + (target.wander_radius - current.wander_radius) * progress,
            interaction_frequency=current.interaction_frequency + (target.interaction_frequency - current.interaction_frequency) * progress,
            approach_distance=current.approach_distance + (target.approach_distance - current.approach_distance) * progress,
            attention_duration=current.attention_duration + (target.attention_duration - current.attention_duration) * progress,
            pose_variety=current.pose_variety + (target.pose_variety - current.pose_variety) * progress,
            expression_changes=current.expression_changes + (target.expression_changes - current.expression_changes) * progress,
            idle_animations=current.idle_animations + (target.idle_animations - current.idle_animations) * progress,
            playfulness=current.playfulness + (target.playfulness - current.playfulness) * progress,
            curiosity=current.curiosity + (target.curiosity - current.curiosity) * progress,
            mischievousness=current.mischievousness + (target.mischievousness - current.mischievousness) * progress,
            object_interaction=current.object_interaction + (target.object_interaction - current.object_interaction) * progress,
            window_climbing=current.window_climbing + (target.window_climbing - current.window_climbing) * progress,
            behavior_state=target.behavior_state,  # Use target state immediately
            activity_level=target.activity_level
        )


# Convenience functions for standalone usage
def to_avatar_params(vector: PersonalityVector) -> Dict[str, Any]:
    """
    Convert personality vector to avatar parameters.
    
    Args:
        vector: PersonalityVector
        
    Returns:
        Dictionary of avatar parameters
    """
    adapter = AvatarAdapter()
    params = adapter.to_params(vector)
    
    return {
        'eye_openness': params.eye_openness,
        'smile_intensity': params.smile_intensity,
        'brow_position': params.brow_position,
        'posture': params.posture,
        'animation_speed': params.animation_speed,
        'movement_range': params.movement_range,
        'glow_intensity': params.glow_intensity,
        'particle_effects': params.particle_effects,
        'color_temperature': params.color_temperature,
        'proximity_radius': params.proximity_radius,
        'responsiveness': params.responsiveness,
        'animation_state': params.animation_state,
        'transition_speed': params.transition_speed
    }


def to_shimeji_params(vector: PersonalityVector) -> Dict[str, Any]:
    """
    Convert personality vector to shimeji parameters.
    
    Args:
        vector: PersonalityVector
        
    Returns:
        Dictionary of shimeji parameters
    """
    adapter = ShimejiAdapter()
    params = adapter.to_params(vector)
    
    return {
        'movement_speed': params.movement_speed,
        'jump_frequency': params.jump_frequency,
        'wander_radius': params.wander_radius,
        'interaction_frequency': params.interaction_frequency,
        'approach_distance': params.approach_distance,
        'attention_duration': params.attention_duration,
        'pose_variety': params.pose_variety,
        'expression_changes': params.expression_changes,
        'idle_animations': params.idle_animations,
        'playfulness': params.playfulness,
        'curiosity': params.curiosity,
        'mischievousness': params.mischievousness,
        'object_interaction': params.object_interaction,
        'window_climbing': params.window_climbing,
        'behavior_state': params.behavior_state,
        'activity_level': params.activity_level
    }
