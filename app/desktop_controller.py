"""
app/desktop_controller.py

DesktopController — Subsystem Orchestrator for Kitsu Desktop AI

Responsibilities (orchestration only):
- Bridge KitsuEngine (core) with desktop output modules (Avatar, Voice, Toybox)
- Coordinate desktop integration events (mouse gestures, system events)
- Route response data to appropriate subsystems via unified dispatch
- Manage async lifecycle of all subsystems
- Trigger ML compression pipeline updates after interactions

Non-responsibilities:
- Core logic (→ core/orchestrator.py)
- Personality or emotion decisions (→ core/personality/)
- Memory operations (→ core/memory/)
- Command handling (→ ui/commands/command_router.py)
"""

import asyncio
import logging
import time
from typing import Optional, Any, Dict, List
from dataclasses import dataclass

# Import contracts for type safety
from core.contracts import (
    AvatarContract,
    TTSProvider,
    ASRProvider,
    MemoryStoreContract,
    EmotionProvider
)

log = logging.getLogger("desktop_controller")


class ResponseHistoryWrapper:
    """Wrapper to make MemoryManager compatible with command router expectations."""

    def __init__(self, memory_manager):
        self.memory = memory_manager

    def rate_response(self, response_id=None, rating: int = 5, rater: str = "user", comment: str = None):
        return self.memory.rate_response(response_id, rating, rater, comment)

    def last_response_for_user(self, user: str = "default"):
        if hasattr(self.memory, "_response_history") and self.memory._response_history:
            return self.memory._response_history[-1]
        return None


class DesktopController:
    """
    Subsystem Orchestrator for desktop companion features.

    Bridges the KitsuEngine (core) with desktop output modules (Avatar, Voice, Toybox).
    Routes all responses through a unified dispatch pipeline and manages async lifecycle
    of all subsystems with explicit initialization patterns.

    All decision logic is delegated to the core engine.
    """

    def __init__(self, engine: Any, runtime_config: Dict[str, Any]) -> None:
        self.engine = engine
        self.config = runtime_config

        # Subsystem handles — populated during explicit initialization
        self.desktop_integration: Optional[Any] = None
        self.avatar_system: Optional[AvatarContract] = None
        self.voice_system: Optional[Any] = None  # Could be TTSProvider, ASRProvider, or combined
        self.toybox: Optional[Any] = None
        self.training_system: Optional[Any] = None

        # Track last interaction for rating and compression
        self._last_user_input: Optional[str] = None
        self._last_state_dict: Optional[Dict] = None
        self._last_binary_features: Optional[Dict] = None
        self._last_response: Optional[Dict] = None
        
        # Auto-prompt setting
        self._auto_prompt_enabled: bool = False

        self.running: bool = False

    # =========================================================================
    # Property Pass-Through Pattern
    # =========================================================================

    @property
    def emotion_engine(self) -> Optional[EmotionProvider]:
        """Access to engine's emotion engine through controller interface."""
        return self.engine.emotion_engine if self.engine else None

    @property
    def memory(self) -> Optional[MemoryStoreContract]:
        """Access to engine's memory system through controller interface."""
        return self.engine.memory if self.engine else None

    @property
    def personality_vector(self) -> Optional[Any]:
        """Access to engine's personality vector through controller interface."""
        return getattr(self.engine, 'personality_vector', None) if self.engine else None

    @property
    def llm(self) -> Optional[Any]:
        """Access to engine's LLM controller through controller interface."""
        if self.engine is None:
            return None
        return getattr(self.engine, "llm_controller", self.engine)

    @property
    def response_history(self) -> Optional['ResponseHistoryWrapper']:
        """Access to response history for command router compatibility."""
        if self.engine and self.engine.memory:
            return ResponseHistoryWrapper(self.engine.memory)
        return None

    # =========================================================================
    # Async Lifecycle Management
    # =========================================================================

    async def initialize(self) -> None:
        """
        Initialize all subsystems with explicit async lifecycle management.
        Each subsystem is protected by configuration guards.
        """
        log.info("Initializing DesktopController subsystems...")

        # Core desktop integration (always enabled if available)
        await self._init_desktop_integration()

        # Optional subsystems based on configuration
        if self.config.get("enable_avatar"):
            await self._init_avatar_system()

        if self.config.get("enable_tts") or self.config.get("enable_stt"):
            await self._init_voice_system()

        if self.config.get("enable_toybox"):
            await self._init_toybox()

        if self.config.get("enable_training"):
            self._init_training_system()

        log.info("DesktopController subsystems initialized")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all subsystems in reverse order.
        """
        log.info("DesktopController shutting down...")

        # Shutdown subsystems in reverse dependency order
        shutdown_tasks = []

        if self.voice_system:
            shutdown_tasks.append(self._shutdown_voice_system())

        if self.desktop_integration:
            shutdown_tasks.append(self._shutdown_desktop_integration())

        if self.avatar_system:
            shutdown_tasks.append(self._shutdown_avatar_system())

        if self.toybox:
            shutdown_tasks.append(self._shutdown_toybox())

        # Execute shutdowns concurrently with error handling
        if shutdown_tasks:
            results = await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    subsystem = ["voice", "desktop", "avatar", "toybox"][i]
                    log.warning(f"{subsystem} system shutdown error: {result}")

        # Finally shutdown the core engine
        if self.engine:
            await self.engine.shutdown()

        self.running = False
        log.info("DesktopController shut down")

    # =========================================================================
    # Explicit Subsystem Initialization
    # =========================================================================

    async def _init_desktop_integration(self) -> None:
        """Initialize desktop integration system."""
        try:
            from desktop_app.desktop_integration import DesktopIntegration, EventType, GestureType

            self.desktop_integration = DesktopIntegration()

            # Register event handlers
            for event_type in EventType:
                self.desktop_integration.register_event_handler(event_type, self._handle_system_event)

            for gesture_type in GestureType:
                self.desktop_integration.register_gesture_handler(gesture_type, self._handle_gesture)

            await self.desktop_integration.start()
            log.info("Desktop integration initialized")

        except ImportError:
            log.warning("DesktopIntegration not available — skipping")
        except Exception as e:
            log.error(f"Desktop integration init failed: {e}")

    async def _init_avatar_system(self) -> None:
        """Initialize avatar system if enabled."""
        try:
            from desktop_app.avatar_system import AvatarSystem
            self.avatar_system = AvatarSystem(
                assets_dir="assets/models/kitsu",
                config=self.config,
            )
            await self.avatar_system.initialize()
            log.info("Avatar system initialized")
        except ImportError:
            log.warning("AvatarSystem not available — skipping")
        except Exception as e:
            log.error(f"Avatar system init failed: {e}")

    async def _init_voice_system(self) -> None:
        """Initialize voice system (TTS/STT) if enabled."""
        try:
            from voice.voice_system import VoiceSystem
            self.voice_system = VoiceSystem(
                enable_tts=self.config.get("enable_tts", False),
                enable_stt=self.config.get("enable_stt", False),
                on_speech_input=self._handle_voice_input,
            )
            await self.voice_system.initialize()
            log.info("Voice system initialized")
        except ImportError:
            log.warning("VoiceSystem not available — skipping")
        except Exception as e:
            log.error(f"Voice system init failed: {e}")

    async def _init_toybox(self) -> None:
        """Initialize toybox/mini-games system if enabled."""
        try:
            from toybox.mini_games import MiniGames
            self.toybox = MiniGames(engine=self.engine)
            log.info("Toybox initialized")
        except ImportError:
            log.warning("Toybox not available — skipping")
        except Exception as e:
            log.error(f"Toybox init failed: {e}")

    def _init_training_system(self) -> None:
        """Initialize training system if enabled."""
        try:
            from core.learning.micro_trainer import MicroTrainer
            self.training_system = MicroTrainer()
            log.info("Training system initialized")
        except Exception as e:
            log.warning(f"Training system init failed (non-critical): {e}")

    # =========================================================================
    # Subsystem Shutdown Helpers
    # =========================================================================

    async def _shutdown_voice_system(self) -> None:
        """Shutdown voice system."""
        try:
            await self.voice_system.stop()
        except Exception as e:
            log.warning(f"Voice system shutdown error: {e}")

    async def _shutdown_desktop_integration(self) -> None:
        """Shutdown desktop integration."""
        try:
            await self.desktop_integration.stop()
        except Exception as e:
            log.warning(f"Desktop integration shutdown error: {e}")

    async def _shutdown_avatar_system(self) -> None:
        """Shutdown avatar system."""
        try:
            if hasattr(self.avatar_system, 'stop'):
                await self.avatar_system.stop()
        except Exception as e:
            log.warning(f"Avatar system shutdown error: {e}")

    async def _shutdown_toybox(self) -> None:
        """Shutdown toybox system."""
        try:
            if hasattr(self.toybox, 'stop'):
                await self.toybox.stop()
        except Exception as e:
            log.warning(f"Toybox shutdown error: {e}")

    # =========================================================================
    # Public Interface
    # =========================================================================

    async def process_input(
        self,
        user_input: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process user input through core engine and dispatch response.

        After getting the response, triggers an online update on the
        compression pipeline so encoder frequencies and NN weights
        stay current without needing explicit retraining.
        """
        response = await self.engine.process_input(user_input, context)

        # Store for rating passthrough and compression
        self._last_user_input = user_input
        self._last_state_dict = self.engine.state.to_dict() if self.engine.state else None
        self._last_binary_features = response.get("binary_features")
        self._last_response = response

        # Add to memory history for command compatibility
        if self.engine.memory:
            self.engine.memory.add_response(user_input, response.get("response", ""))

        # Log interaction to legacy training system
        if self.training_system:
            try:
                self.training_system.log_interaction(
                    user_input=user_input,
                    response=response.get("response", ""),
                    mood=response.get("mood", "behave"),
                    style=response.get("style", "chaotic"),
                    emotion=response.get("emotion", "neutral"),
                )
            except Exception as e:
                log.debug(f"Training system log failed (non-critical): {e}")

        # Online update to compression pipeline (no rating yet — neutral update)
        await self._compression_online_update(user_input, rating=None)

        # Unified response dispatch
        await self._dispatch_response(response)
        return response

    async def rate_last_response(self, rating: int) -> str:
        """
        Rate the last response (1–5).

        Routes to:
          1. Memory manager (existing behaviour)
          2. Compression pipeline online_update with rating-scaled lr
        """
        if rating < 1 or rating > 5:
            return "Rating must be between 1 and 5"

        # Memory manager rating
        if self.engine.memory and hasattr(self.engine.memory, "rate_response"):
            try:
                self.engine.memory.rate_response(rating=rating)
            except Exception as e:
                log.debug(f"Memory rate_response failed: {e}")

        # Compression pipeline online update with rating signal
        await self._compression_online_update(
            user_input=self._last_user_input or "",
            rating=rating,
        )

        log.info(f"Response rated {rating}/5")
        return f"Response rated {rating}/5"

    # =========================================================================
    # ML Compression Pipeline Integration
    # =========================================================================

    async def _compression_online_update(
        self,
        user_input: str,
        rating: Optional[int],
    ) -> None:
        """
        Trigger an online update on the compression pipeline.
        Safe to call even if pipeline is not ready.
        """
        if not user_input:
            return

        compression = getattr(self.engine, "compression", None)
        if compression is None:
            return

        try:
            rebuilt = compression.online_update(
                text=user_input,
                state_dict=self._last_state_dict,
                binary_features=self._last_binary_features,
                rating=rating,
            )
            if rebuilt:
                log.info("Compression encoder rebuilt after online update")
                # Mark engine as ready if it wasn't already
                self.engine._compression_ready = compression.encoder._is_built
        except Exception as e:
            log.debug(f"Compression online update failed (non-critical): {e}")

    # =========================================================================
    # Event Handlers (Route to Engine)
    # =========================================================================

    async def _handle_gesture(self, gesture) -> None:
        """Handle mouse gesture events by routing to engine."""
        log.debug(f"Gesture received: {gesture.gesture_type.value}")
        try:
            response = await self.engine.process_gesture(
                gesture_type=gesture.gesture_type,
                x=gesture.x,
                y=gesture.y,
                intensity=getattr(gesture, "pressure", 0.5),
            )
            if response:
                await self._dispatch_response(response)
        except Exception as e:
            log.error(f"Gesture handling error: {e}")

    async def _handle_system_event(self, event) -> None:
        """Handle system events by routing to engine."""
        log.debug(f"System event: {event.event_type.value}")
        try:
            response = await self.engine.process_system_event(
                event_type=event.event_type.value,
                payload=event.data,
            )
            if response:
                await self._dispatch_response(response)
        except Exception as e:
            log.error(f"System event handling error: {e}")

    async def _handle_voice_input(self, transcript: str) -> None:
        """Handle voice input by routing to engine."""
        if not transcript.strip():
            return
        log.debug(f"Voice input: {transcript!r}")
        try:
            response = await self.engine.process_input(user_input=transcript)
            if response:
                await self._dispatch_response(response)
        except Exception as e:
            log.error(f"Voice input handling error: {e}")

    # =========================================================================
    # Unified Response Dispatch
    # =========================================================================

    async def _dispatch_response(self, response: Dict[str, Any]) -> None:
        """
        Unified response routing to appropriate output subsystems.
        
        Routes:
          - Text → VoiceSystem (if active)
          - Emotion → AvatarSystem (if active)
          - Auto-prompt → Console (if enabled)
          - Debug log → Console (if debug mode)
        """
        # Text routing to voice system
        if self.voice_system and response.get("text"):
            try:
                await self.voice_system.speak(response["text"])
            except Exception as e:
                log.warning(f"TTS speak failed: {e}")

        # Emotion routing to avatar system
        if self.avatar_system and response.get("emotion"):
            try:
                await self.avatar_system.set_emotion(response["emotion"])
            except Exception as e:
                log.warning(f"Avatar emotion update failed: {e}")

        # Auto-prompt routing
        if self._auto_prompt_enabled:
            await self._dispatch_auto_prompt(response)

        # Debug log routing
        debug_enabled = (
            self.config.get("debug_mode") or 
            (hasattr(self.engine, 'runtime_config') and self.engine.runtime_config.get("debug_mode"))
        )
        if debug_enabled and response.get("debug_log"):
            log.debug(f"\n{response['debug_log']}")
            # Also display to user in terminal
            print(f"\n🔢 Binary Debug Log:\n{response['debug_log']}\n")

    async def _dispatch_auto_prompt(self, response: Dict[str, Any]) -> None:
        """Extract and display auto-prompt information."""
        try:
            # Get the actual prompt that was used for the last response
            prompt_data = None
            
            # Method 1: Try to get from engine state
            if hasattr(self.engine, 'state') and self.engine.state:
                state = self.engine.state
                if hasattr(state, 'llm_prompt'):
                    prompt_data = getattr(state, 'llm_prompt', None)
                    if prompt_data:
                        state_dict = state.to_dict()
                        prompt_data = {
                            "prompt": prompt_data,
                            "mood": state_dict.get('mood', '?'),
                            "style": state_dict.get('style', '?'),
                            "emotion": state_dict.get('dominant_emotion', '?'),
                            "user_input": state_dict.get('user_input', 'N/A')
                        }
            
            # Method 2: Try to get from compression pipeline directly
            if not prompt_data and hasattr(self.engine, 'compression') and self.engine.compression:
                comp = self.engine.compression
                # Look for stored prompt in various possible locations
                if hasattr(comp, '_last_prompt'):
                    prompt_data = comp._last_prompt
                elif hasattr(comp, 'last_prompt'):
                    prompt_data = comp.last_prompt
                elif hasattr(comp, 'current_prompt'):
                    prompt_data = comp.current_prompt
            
            # Method 3: Fallback to last user input + response
            if not prompt_data and self._last_user_input:
                user_input = self._last_user_input
                response_text = self._last_response.get('response', '') if self._last_response else ''
                mood = self._last_response.get('mood', '?') if self._last_response else '?'
                style = self._last_response.get('style', '?') if self._last_response else '?'
                
                prompt_data = {
                    "prompt": (
                        f"Last interaction:\n"
                        f"User: {user_input}\n"
                        f"Kitsu Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}\n"
                        f"Mood: {mood}, Style: {style}"
                    ),
                    "mood": mood,
                    "style": style,
                    "emotion": self._last_response.get('emotion', '?') if self._last_response else '?',
                    "user_input": user_input
                }
            
            if prompt_data:
                # Handle both string and dict prompt_data
                if isinstance(prompt_data, str):
                    prompt_text = prompt_data
                    prompt_display = {
                        "mood": self._last_response.get('mood', '?') if self._last_response else '?',
                        "style": self._last_response.get('style', '?') if self._last_response else '?',
                        "emotion": self._last_response.get('emotion', '?') if self._last_response else '?',
                        "user_input": self._last_user_input or 'N/A'
                    }
                else:
                    prompt_display = prompt_data
                    prompt_text = prompt_data.get('prompt', '')
                
                prompt_output = (
                    "\n" + "=" * 50 + "\n📝 AUTO PROMPT\n" + "=" * 50 + "\n\n"
                    f"🎭 Mood: {prompt_display.get('mood','?')}\n"
                    f"✨ Style: {prompt_display.get('style','?')}\n"
                    f"😊 Emotion: {prompt_display.get('emotion','?')}\n"
                    f"👤 Input: {prompt_display.get('user_input','N/A')}\n"
                    + "-" * 50 + "\n📄 PROMPT:\n" + "-" * 50 + "\n\n"
                )
                if len(prompt_text) > 1000:
                    prompt_output += prompt_text[:1000] + f"\n\n[... truncated, full length: {len(prompt_text)} chars]"
                else:
                    prompt_output += prompt_text
                prompt_output += "\n" + "=" * 50 + "\n"
                print(prompt_output)
        except Exception as e:
            log.debug(f"Auto-prompt display failed: {e}")

    # =========================================================================
    # Toybox Interface
    # =========================================================================

    async def launch_game(self, game_id: str, **kwargs) -> Any:
        """Launch a mini-game through the toybox system."""
        if not self.toybox:
            log.warning("Toybox not initialized")
            return None
        try:
            return await self.toybox.launch(game_id, **kwargs)
        except Exception as e:
            log.error(f"Failed to launch game '{game_id}': {e}")
            return None
