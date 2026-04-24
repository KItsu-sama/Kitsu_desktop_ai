"""
core/personality/emotion_controller.py

High-level controller for emotional system integration.
Coordinates between EmotionEngine, ReactionMapper, AvatarSystem, and DesktopIntegration.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from personality.emotion_engine import EmotionEngine
from personality.kitsu_self import KitsuSelf
from personality.reaction_mapper import ReactionMapper, InteractionType

log = logging.getLogger(__name__)


@dataclass
class EmotionalResponse:
    """Complete emotional response package"""
    emotion: str
    intensity: float
    mood: str
    style: str
    animation: str
    voice_modulation: Dict[str, float]
    text_response: Optional[str] = None
    duration: float = 5.0


class EmotionController:
    """
    High-level emotional system controller.
    
    Coordinates:
    - EmotionEngine for emotional state management
    - ReactionMapper for interaction→emotion mapping
    - AvatarSystem for visual feedback
    - Voice system for audio feedback
    - Memory system for learning
    """
    
    def __init__(
        self,
        emotion_engine: EmotionEngine,
        kitsu_self: KitsuSelf,
        reaction_mapper: ReactionMapper,
        avatar_system=None,  # Optional avatar system
        voice_system=None,   # Optional voice system
        memory_manager=None  # Optional memory manager
    ):
        self.emotion_engine = emotion_engine
        self.kitsu_self = kitsu_self
        self.reaction_mapper = reaction_mapper
        self.avatar_system = avatar_system
        self.voice_system = voice_system
        self.memory_manager = memory_manager
        
        # Response queue for coordinated reactions
        self.response_queue: asyncio.Queue = asyncio.Queue()
        
        # Background processing task
        self.processing_task = None
        
        log.info("EmotionController initialized")
    
    async def start(self) -> None:
        """Start emotion controller background processing"""
        self.processing_task = asyncio.create_task(self._process_responses())
        log.info("EmotionController started")
    
    async def stop(self) -> None:
        """Stop emotion controller"""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        log.info("EmotionController stopped")
    
    # =========================================================================
    # Interaction Processing
    # =========================================================================
    
    async def handle_mouse_gesture(
        self,
        gesture_type: InteractionType,
        x: float,
        y: float,
        intensity: float = 0.5
    ) -> EmotionalResponse:
        """
        Handle mouse gesture interaction.
        
        Args:
            gesture_type: Type of gesture
            x: Mouse X position
            y: Mouse Y position
            intensity: Gesture intensity
            
        Returns:
            Complete emotional response
        """
        log.debug(f"Handling gesture: {gesture_type.value} at ({x}, {y})")
        
        # Map gesture to emotional reaction
        reaction = self.reaction_mapper.map_gesture(gesture_type)
        
        # Plan reaction sequence
        sequence = self.reaction_mapper.plan_reaction_sequence(
            gesture_type,
            self.emotion_engine.mood,
            self.emotion_engine.style
        )
        
        # Apply emotions to engine
        for step in sequence:
            self.emotion_engine.set_emotion(
                step["emotion"],
                intensity * reaction["intensity"],
                step["duration"]
            )
        
        # Fire triggers
        for trigger in reaction["triggers"]:
            self.emotion_engine.fire_trigger(trigger)
        
        # Update mood/style if specified
        if reaction["mood_shift"]:
            self.emotion_engine.set_mood(reaction["mood_shift"], duration=60.0)
        if reaction["style_shift"]:
            self.emotion_engine.set_style(reaction["style_shift"])
        
        # Generate complete response
        response = await self._generate_response(reaction, gesture_type.value)
        
        # Queue for coordinated execution
        await self.response_queue.put(response)
        
        return response
    
    async def handle_emoji(self, emoji: str, intensity: float = 0.5) -> EmotionalResponse:
        """
        Handle emoji interaction.
        
        Args:
            emoji: Emoji character
            intensity: Emoji intensity
            
        Returns:
            Complete emotional response
        """
        log.debug(f"Handling emoji: {emoji}")
        
        # Map emoji to reaction
        reaction = self.reaction_mapper.map_emoji(emoji)
        
        # Set emotion
        self.emotion_engine.set_emotion(
            reaction["emotion"],
            intensity * reaction["intensity"],
            duration=5.0
        )
        
        # Generate response
        response = await self._generate_response(reaction, f"emoji:{emoji}")
        
        # Queue for execution
        await self.response_queue.put(response)
        
        return response
    
    async def handle_system_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Optional[EmotionalResponse]:
        """
        Handle system event.
        
        Args:
            event_type: System event type
            event_data: Event data
            
        Returns:
            Emotional response or None if no reaction
        """
        log.debug(f"Handling system event: {event_type}")
        
        # Map system event to reaction
        reaction = self.reaction_mapper.map_system_event(event_type)
        
        # Set emotion with lower priority (system events are less important)
        self.emotion_engine.set_emotion(
            reaction["emotion"],
            reaction["intensity"] * 0.5,  # Reduce intensity for system events
            duration=reaction["duration"]
        )
        
        # Generate response
        response = await self._generate_response(reaction, f"system:{event_type}")
        
        # Queue for execution
        await self.response_queue.put(response)
        
        return response
    
    async def handle_idle_timeout(self, idle_minutes: int) -> EmotionalResponse:
        """
        Handle idle timeout.
        
        Args:
            idle_minutes: Minutes of inactivity
            
        Returns:
            Complete emotional response
        """
        log.debug(f"Handling idle timeout: {idle_minutes} minutes")
        
        # Get idle reaction
        reaction = self.reaction_mapper.get_idle_reactions(idle_minutes)
        
        if reaction["type"] == "sleep_mode":
            # Hide avatar and set sleep state
            if self.avatar_system:
                self.avatar_system.set_state("sleeping")
            self.emotion_engine.hide()
        elif reaction["type"] == "check_in":
            # Brief check-in animation
            self.emotion_engine.set_emotion("curious", 0.3, duration=3.0)
            if self.avatar_system:
                self.avatar_system.play_animation("peek")
        
        # Generate response
        response = await self._generate_response(reaction, f"idle:{idle_minutes}")
        
        return response
    
    # =========================================================================
    # Response Generation
    # =========================================================================
    
    async def _generate_response(
        self,
        reaction: Dict[str, Any],
        source: str
    ) -> EmotionalResponse:
        """
        Generate complete emotional response.
        
        Args:
            reaction: Reaction mapping data
            source: Source of interaction
            
        Returns:
            Complete emotional response
        """
        # Get current emotional state
        emotional_state = self.emotion_engine.get_emotional_state()
        
        # Determine animation
        animation = reaction.get("animation", "idle")
        if self.avatar_system:
            # Map emotion to animation if not specified
            if not animation or animation == "idle":
                animation = self.emotion_engine.get_avatar_hint()
        
        # Voice modulation
        voice_modulation = {
            "pitch": reaction.get("voice_pitch", 1.0),
            "speed": 1.0,
            "volume": 1.0
        }
        
        # Adjust voice based on emotion
        emotion = emotional_state["dominant_emotion"]
        if emotion == "happy":
            voice_modulation["pitch"] *= 1.2
            voice_modulation["speed"] *= 1.1
        elif emotion == "sad":
            voice_modulation["pitch"] *= 0.8
            voice_modulation["speed"] *= 0.9
        elif emotion == "angry":
            voice_modulation["pitch"] *= 1.1
            voice_modulation["volume"] *= 1.2
        elif emotion == "flirty":
            voice_modulation["pitch"] *= 1.3
        
        # Generate text response if needed
        text_response = reaction.get("message")
        if not text_response and source.startswith("emoji:"):
            text_response = await self._generate_emoji_response(source.split(":")[1])
        
        return EmotionalResponse(
            emotion=emotional_state["dominant_emotion"],
            intensity=emotional_state["confidence"],
            mood=self.emotion_engine.mood,
            style=self.emotion_engine.style,
            animation=animation,
            voice_modulation=voice_modulation,
            text_response=text_response,
            duration=reaction.get("duration", 5.0)
        )
    
    async def _generate_emoji_response(self, emoji: str) -> str:
        """
        Generate text response to emoji.
        
        Args:
            emoji: Emoji character
            
        Returns:
            Text response
        """
        # This would use the LLM to generate appropriate responses
        emoji_responses = {
            "🥰": ["Aww, you're making me blush! 🦊", "Hehe, that's sweet!"],
            "😡": ["Hey! What did I do? 😤", "Why the angry face?"],
            "😭": ["Don't cry! I'm here! 🤗", "What's wrong? Let me help!"],
            "😏": ["What's that look for? 😏", "Planning something mischievous?"]
        }
        
        import random
        responses = emoji_responses.get(emoji, ["Interesting emoji!"])
        return random.choice(responses)
    
    # =========================================================================
    # Response Execution
    # =========================================================================
    
    async def _process_responses(self) -> None:
        """Background task to process queued responses"""
        log.info("Starting response processing loop")
        
        while True:
            try:
                # Get next response
                response = await self.response_queue.get()
                
                # Execute all components simultaneously
                tasks = []
                
                # Avatar animation
                if self.avatar_system and response.animation:
                    tasks.append(asyncio.create_task(
                        self._execute_avatar_animation(response)
                    ))
                
                # Voice response
                if self.voice_system and response.text_response:
                    tasks.append(asyncio.create_task(
                        self._execute_voice_response(response)
                    ))
                
                # Memory update
                if self.memory_manager:
                    tasks.append(asyncio.create_task(
                        self._update_memory(response)
                    ))
                
                # Wait for all to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait for response duration
                await asyncio.sleep(response.duration)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error processing response: {e}")
    
    async def _execute_avatar_animation(self, response: EmotionalResponse) -> None:
        """Execute avatar animation"""
        try:
            if self.avatar_system:
                self.avatar_system.play_emotion_animation(
                    response.emotion,
                    response.intensity
                )
        except Exception as e:
            log.error(f"Avatar animation error: {e}")
    
    async def _execute_voice_response(self, response: EmotionalResponse) -> None:
        """Execute voice response"""
        try:
            if self.voice_system and response.text_response:
                await self.voice_system.speak(
                    response.text_response,
                    pitch=response.voice_modulation["pitch"],
                    speed=response.voice_modulation["speed"],
                    volume=response.voice_modulation["volume"]
                )
        except Exception as e:
            log.error(f"Voice response error: {e}")
    
    async def _update_memory(self, response: EmotionalResponse) -> None:
        """Update memory with interaction"""
        try:
            if self.memory_manager:
                # Store interaction in memory
                interaction_data = {
                    "type": "emotional_response",
                    "emotion": response.emotion,
                    "intensity": response.intensity,
                    "mood": response.mood,
                    "style": response.style,
                    "timestamp": time.time()
                }
                
                # This would use the memory manager's API
                # await self.memory_manager.store_interaction(interaction_data)
        except Exception as e:
            log.error(f"Memory update error: {e}")
    
    # =========================================================================
    # Manual Controls
    # =========================================================================
    
    async def trigger_emotion(self, emotion: str, intensity: float = 0.5) -> None:
        """
        Manually trigger an emotion.
        
        Args:
            emotion: Emotion name
            intensity: Emotion intensity
        """
        self.emotion_engine.set_emotion(emotion, intensity, duration=5.0)
        
        # Generate and queue response
        response = EmotionalResponse(
            emotion=emotion,
            intensity=intensity,
            mood=self.emotion_engine.mood,
            style=self.emotion_engine.style,
            animation=self.emotion_engine.get_avatar_hint(),
            voice_modulation={"pitch": 1.0, "speed": 1.0, "volume": 1.0},
            duration=5.0
        )
        
        await self.response_queue.put(response)
    
    def get_emotional_state(self) -> Dict[str, Any]:
        """Get current emotional state"""
        return {
            "emotion_engine": self.emotion_engine.get_state_dict(),
            "kitsu_self": self.kitsu_self.export_state(),
            "queue_size": self.response_queue.qsize()
        }
