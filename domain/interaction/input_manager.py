"""
domain/interaction/input_manager.py

Input processing and routing manager.
Extracted from orchestrator.py to follow Single Responsibility Principle.

Responsibilities:
- Process user input through AI pipeline
- Route through FastBrain → SLM → LLM
- Handle behavior engine decisions
- Feed responses back into learning systems

Non-responsibilities:
- Application lifecycle (→ application.py)
- Health monitoring (→ system_monitor.py)
- Module management (→ orchestrator.py)
- UI rendering (→ interfaces)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Dict, Any

from typing import TYPE_CHECKING
from domain.contracts.contracts import AIProvider

if TYPE_CHECKING:
    from kitsu.core.context import RequestContext
    from runtime.systems.behavior_engine import BehaviorEngine, AttentionConfig

logger = logging.getLogger(__name__)


class InputManager:
    """
    Handles user input processing and AI pipeline routing.
    
    Coordinates behavior engine, AI providers (FastBrain/SLM/LLM),
    and response feeding back into learning systems.
    """
    
    def __init__(self, message_bus, emotion_manager=None, core_memory=None, llm_fallback=None, 
                 slm=None, judge=None, fast_brain=None, core_config=None):
        self.message_bus = message_bus
        self.emotion_manager = emotion_manager
        self.core_memory = core_memory
        self.llm_fallback = llm_fallback
        self.slm = slm
        self.judge = judge
        self.fast_brain = fast_brain
        self.core_config = core_config or {}
        
        # Lazy imports to avoid circular imports
        self._bus = None
        self._behavior_engine = None
    
    @property
    def bus(self):
        """Lazy import of event bus to avoid circular imports."""
        if self._bus is None:
            from kitsu.core.event_bus import bus
            self._bus = bus
        return self._bus
    
    @property
    def behavior_engine(self):
        """Lazy import of behavior engine to avoid circular imports."""
        if self._behavior_engine is None:
            from runtime.systems.behavior_engine import BehaviorEngine, AttentionConfig
            behavior_config = AttentionConfig(
                max_attention=100.0,
                decay_rate=0.1,
                boost_factor=1.5
            )
            self._behavior_engine = BehaviorEngine(behavior_config)
        return self._behavior_engine
    
    async def on_user_input(self, ctx) -> None:
        """
        Handle normalized input from InputMux via Event Bus.
        
        This is the new entry point - replaces direct process_input calls.
        """
        start_time = time.perf_counter()
        
        try:
            # Extract content from RequestContext
            user_input = ctx.text
            if not user_input.strip():
                return
            
            logger.debug(f"[INPUT_MANAGER] Processing input: '{user_input}' (len={len(user_input)})")
            
            # Process through the multi-tier AI pipeline
            result = await self.process_input(user_input)
            
            # Publish response for UI components
            await self.bus.emit("RESPONSE_READY", {
                'input_text': user_input,
                'response_text': result.get('response', ''),
                'source': result.get('source', 'input_manager'),
                'confidence': result.get('confidence', 0.8),
            })
            
            processing_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"[INPUT_MANAGER] Processing completed in {processing_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"Error processing USER_INPUT event: {e}")
    
    async def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input through the multi-tier AI pipeline.
        
        Args:
            user_input: Raw user input text
            
        Returns:
            Dict containing response and metadata compatible with legacy UI
        """
        start_time = time.perf_counter()
        logger.debug(f"[INPUT_MANAGER] Starting pipeline for: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")
        
        # Validate input
        if not user_input or not isinstance(user_input, str):
            return self._create_error_response("Invalid input")
        
        # Create request context
        ctx = RequestContext(
            text=user_input,
            vibe=self._get_vibe_vector(),
            mode='chat'
        )
        logger.debug(f"[INPUT_MANAGER] Context created: mode={ctx.mode}, vibe={ctx.vibe}")
        
        # Process through behavior engine first
        behavior_start = time.perf_counter()
        behavior_result = await self._process_behavior_engine(ctx)
        behavior_time = (time.perf_counter() - behavior_start) * 1000
        logger.debug(f"[INPUT_MANAGER] Behavior engine: {behavior_time:.1f}ms")
        
        if behavior_result is not None:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"[INPUT_MANAGER] Pipeline completed (behavior handled): {total_time:.1f}ms")
            return behavior_result
        
        # Multi-tier AI pipeline: FastBrain → SLM → LLM
        pipeline_start = time.perf_counter()
        response_text, source, confidence = await self._process_tiered_pipeline(ctx)
        pipeline_time = (time.perf_counter() - pipeline_start) * 1000
        logger.debug(f"[INPUT_MANAGER] AI pipeline: {pipeline_time:.1f}ms, source={source}, confidence={confidence:.2f}")
        
        # Get emotional state for expression
        emotion_state = self.emotion_manager.get_current_state() if self.emotion_manager else {}
        mood = emotion_state.get("mood", "neutral")
        emotion = emotion_state.get("dominant_emotion", "neutral")
        logger.debug(f"[INPUT_MANAGER] Emotional state: mood={mood}, emotion={emotion}")
        
        total_time = (time.perf_counter() - start_time) * 1000
        logger.debug(f"[INPUT_MANAGER] Total pipeline time: {total_time:.1f}ms")
        
        return {
            "response": response_text,
            "text": response_text,
            "emotional_state": emotion_state,
            "mood": mood,
            "style": emotion_state.get("style", "normal"),
            "emotion": emotion,
            "expression": self._determine_expression(emotion_state),
            "confidence": confidence,
            "source": source,
            "generation_metadata": {
                "pipeline": "fast_brain_slm_llm",
                "behavior_engine": True,
                "tier_used": source
            },
            "generation_time": total_time / 1000,
            "routing": {"intent": "processed"},
            "binary_features": {},
            "debug_log": None,
            "binary_vector": None,
            "memory_references": [],
            "avatar_hint": self._get_avatar_hint(emotion_state),
            "voice_params": self._get_voice_params(emotion_state)
        }
    
    async def _handle_input(self, event: InputReceived) -> None:
        """
        Route input through behavior engine then AI pipeline.
        This is extracted from orchestrator._on_input()
        """
        # Get emotional state from EmotionManager (Single Source of Truth)
        emotion_state = self.emotion_manager.get_current_state() if self.emotion_manager else {}
        context = {
            "recent_inputs": getattr(self.core_memory, 'recent_memories', []) if self.core_memory else [],
            "boredom_level": emotion_state.get("resistance", 0.0) if emotion_state else 0.0
        }
        
        # Use behavior engine to decide what to do
        behavior_decision = self.behavior_engine.decide_behavior(
            user_input=event.text,
            emotion_state=emotion_state,
            context=context
        )
        
        # Log behavior decision for debugging
        logger.debug(f"Behavior decision: {behavior_decision.behavior_type.value}, "
                   f"score: {behavior_decision.context.get('attention_score', 'N/A')}")
        
        # Handle IGNORE behavior - don't process further
        if behavior_decision.behavior_type.value == "ignore":
            logger.debug(f"Ignoring input: {event.text[:50]}...")
            return
        
        # Handle REACT behavior (subtle acknowledgment)
        if behavior_decision.behavior_type.value == "react" and not behavior_decision.response_required:
            # Trigger subtle reaction without text response
            # Note: Avatar access would need to be passed in if needed
            logger.debug(f"Subtle reaction: {behavior_decision.reaction_type}")
            return
        
        # Process RESPOND and other behaviors through AI pipeline
        if behavior_decision.response_required or behavior_decision.behavior_type.value in ["respond", "check_in"]:
            await self._process_through_ai_pipeline(event)
    
    async def _process_through_ai_pipeline(self, event: InputReceived) -> None:
        """
        Process input through FastBrain → SLM → LLM pipeline.
        Extracted from orchestrator._on_input()
        """
        # FastBrain first - run in executor to prevent blocking
        # Note: FastBrain access would need to be passed in if needed
        # For now, skip FastBrain as we don't have direct access
        fast_brain = None  # Would be passed in constructor if needed
        if fast_brain and fast_brain.is_available():
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, fast_brain.query, event.text
                )
            except (RuntimeError, ValueError, TimeoutError, ConnectionError) as exc:
                logger.warning('FastBrain query failed: %s', exc)
                response = None
            
            if response is not None:
                # Note: Personality access would need to be passed in if needed
                if isinstance(response, str):
                    try:
                        # response = personality.decorate_response(response, source='fast_brain')
                        pass  # Skip personality injection for now
                    except Exception as exc:
                        logger.error('Personality injection failed: %s', exc)

                await self.bus.emit("RESPONSE_READY", {
                    'input_text': event.text,
                    'response_text': response,
                    'source': "fast_brain",
                    'confidence': 1.0,
                })
                return

        # SLM fallback - run in executor
        # Note: SLM access would need to be passed in if needed
        slm = None  # Would be passed in constructor if needed
        if slm and await slm.is_available():
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, slm.query, event.text
                )
            except Exception as exc:
                logger.warning('SLM query failed: %s', exc)
                response = None
            
            if response is not None:
                # Note: Personality access would need to be passed in if needed
                if isinstance(response, str):
                    try:
                        # response = personality.decorate_response(response, source='slm')
                        pass  # Skip personality injection for now
                    except Exception as exc:
                        logger.warning('Personality injection failed: %s', exc)

                await self.bus.emit("RESPONSE_READY", {
                    'input_text': event.text,
                    'response_text': response,
                    'source': "slm",
                    'confidence': 0.75,
                })
                return

        # LLM fallback - run in executor
        # Note: LLM access would need to be passed in if needed
        llm = None  # Would be passed in constructor if needed
        if llm and await llm.is_available():
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, llm.query, event.text
                )
            except Exception as exc:
                logger.warning('LLM query failed: %s', exc)
                response = None
            
            if response is not None:
                # Note: Personality access would need to be passed in if needed
                if isinstance(response, str):
                    try:
                        # response = personality.decorate_response(response, source='llm')
                        pass  # Skip personality injection for now
                    except Exception as exc:
                        logger.warning('Personality injection failed: %s', exc)

                await self.bus.emit("RESPONSE_READY", {
                    'input_text': event.text,
                    'response_text': response,
                    'source': "llm",
                    'confidence': 0.5,
                })
                return

        logger.warning("No AI provider could handle input: %r", event.text)
    
    def enable_chat(self) -> None:
        """Enable interactive chat mode."""
        self._chat_enabled = True
    
    def disable_chat(self) -> None:
        """Disable interactive chat mode."""
        self._chat_enabled = False
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            "response": f"Error: {error_message}",
            "text": f"Error: {error_message}",
            "emotional_state": {},
            "mood": "neutral",
            "style": "normal",
            "emotion": "neutral",
            "expression": "neutral",
            "confidence": 0.0,
            "source": "input_manager",
            "generation_metadata": {"error": error_message},
            "generation_time": 0.0,
            "routing": {"intent": "error"},
            "binary_features": {},
            "debug_log": None,
            "binary_vector": None,
            "memory_references": [],
            "avatar_hint": None,
            "voice_params": {}
        }
    
    async def _get_response_sync(self, user_input: str) -> str:
        """
        Simplified synchronous response getter.
        In a full implementation, this would wait for ResponseReady events.
        """
        # For now, use a simple fallback response
        # In the full implementation, this would integrate with the AI pipeline
        try:
            # Try to get response from llm_fallback
            if self.llm_fallback:
                return self.llm_fallback.generate(
                    mood="friendly",
                    style="sweet", 
                    cause="chat_input",
                    raw_input=user_input
                )
        except Exception as e:
            logger.warning(f"Failed to get AI response: {e}")
        
        # Ultimate fallback
        return f"I understand you said: {user_input}"
    
    def _determine_expression(self, emotion_state: Dict[str, Any]) -> str:
        """Determine facial expression based on emotional state."""
        mood = emotion_state.get("mood", "neutral")
        emotion = emotion_state.get("dominant_emotion", "neutral")
        
        # Simple mapping - could be enhanced
        if mood == "happy" or emotion == "joy":
            return "smile"
        elif mood == "sad" or emotion == "sadness":
            return "sad"
        elif mood == "angry" or emotion == "anger":
            return "angry"
        elif mood == "surprised" or emotion == "surprise":
            return "surprised"
        else:
            return "neutral"
    
    def _get_avatar_hint(self, emotion_state: Dict[str, Any]) -> Optional[str]:
        """Get avatar hint based on emotional state."""
        mood = emotion_state.get("mood", "neutral")
        
        # Simple mood-to-hint mapping
        hints = {
            "happy": "tail_wag",
            "sad": "ears_down",
            "angry": "growl",
            "surprised": "perk_ears",
            "neutral": "idle"
        }
        
        return hints.get(mood, "idle")
    
    def _get_voice_params(self, emotion_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get voice parameters based on emotional state."""
        mood = emotion_state.get("mood", "neutral")
        
        # Simple mood-to-voice mapping
        params = {
            "happy": {"pitch": 1.1, "speed": 1.0, "energy": 0.9},
            "sad": {"pitch": 0.9, "speed": 0.8, "energy": 0.5},
            "angry": {"pitch": 1.2, "speed": 1.1, "energy": 1.0},
            "surprised": {"pitch": 1.3, "speed": 1.2, "energy": 0.8},
            "neutral": {"pitch": 1.0, "speed": 1.0, "energy": 0.7}
        }
        
        return params.get(mood, params["neutral"])
    
    def _get_vibe_vector(self) -> list[float]:
        """Get current vibe vector from emotion state."""
        if not self.emotion_manager:
            return [0.5, 0.5, 0.5]  # Default neutral
        
        emotion_state = self.emotion_manager.get_current_state()
        # Simplified vibe vector: [warmth, energy, creativity]
        warmth = emotion_state.get("warmth", 0.5)
        energy = emotion_state.get("energy", 0.5) 
        creativity = emotion_state.get("creativity", 0.5)
        return [warmth, energy, creativity]
    
    async def _process_behavior_engine(self, ctx: RequestContext) -> Optional[Dict[str, Any]]:
        """
        Process input through behavior engine for attention gating.
        
        Returns None if processing should continue, or response dict if behavior handled it.
        """
        # Get emotional state from EmotionManager (Single Source of Truth)
        emotion_state = self.emotion_manager.get_current_state() if self.emotion_manager else {}
        context = {
            "recent_inputs": getattr(self.core_memory, 'recent_memories', []) if self.core_memory else [],
            "boredom_level": emotion_state.get("resistance", 0.0) if emotion_state else 0.0
        }
        
        # Use behavior engine to decide what to do
        behavior_decision = self.behavior_engine.decide_behavior(
            user_input=ctx.text,
            emotion_state=emotion_state,
            context=context
        )
        
        # Handle IGNORE behavior - don't process further
        if behavior_decision.behavior_type.value == "ignore":
            logger.debug(f"Ignoring input: {ctx.text[:50]}...")
            return self._create_behavior_response("ignored", "Input ignored due to attention gating")
        
        # Handle REACT behavior (subtle acknowledgment)
        if behavior_decision.behavior_type.value == "react" and not behavior_decision.response_required:
            logger.debug(f"Subtle reaction: {behavior_decision.reaction_type}")
            return self._create_behavior_response("react", f"Subtle reaction: {behavior_decision.reaction_type}")
        
        # Continue processing for RESPOND and other behaviors
        return None
    
    def _create_behavior_response(self, behavior_type: str, message: str) -> Dict[str, Any]:
        """Create a response for behavior engine actions."""
        return {
            "response": message,
            "text": message,
            "emotional_state": {},
            "mood": "neutral",
            "style": "normal", 
            "emotion": "neutral",
            "expression": "neutral",
            "confidence": 0.5,
            "source": "behavior_engine",
            "generation_metadata": {"behavior_type": behavior_type},
            "generation_time": 0.01,
            "routing": {"intent": "behavior_response"},
            "binary_features": {},
            "debug_log": None,
            "binary_vector": None,
            "memory_references": [],
            "avatar_hint": None,
            "voice_params": {}
        }
    
    async def _process_tiered_pipeline(self, ctx: RequestContext) -> tuple[str, str, float]:
        """
        Process input through multi-tier AI pipeline: FastBrain → SLM → LLM.
        
        Returns:
            (response_text, source, confidence) tuple
        """
        logger.debug(f"[INPUT_MANAGER] Starting tiered pipeline for: '{ctx.text}'")
        
        # Tier 1: FastBrain (Reflex)
        if self.fast_brain and hasattr(self.fast_brain, 'is_available') and self.fast_brain.is_available():
            try:
                fastbrain_start = time.perf_counter()
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.fast_brain.query, ctx.text
                )
                fastbrain_time = (time.perf_counter() - fastbrain_start) * 1000
                
                if response and self._judge_response(response, ctx):
                    logger.debug(f"[INPUT_MANAGER] FastBrain success: {fastbrain_time:.1f}ms")
                    return response, "fast_brain", 1.0
                else:
                    logger.debug(f"[INPUT_MANAGER] FastBrain rejected: {fastbrain_time:.1f}ms")
            except Exception as e:
                logger.warning(f"FastBrain query failed: {e}")
        
        # Tier 2: SLM (Local Qwen)
        if self.slm and ctx.within_budget():
            try:
                slm_start = time.perf_counter()
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.slm.query, ctx.text
                )
                slm_time = (time.perf_counter() - slm_start) * 1000
                
                if response and self._judge_response(response, ctx):
                    logger.debug(f"[INPUT_MANAGER] SLM success: {slm_time:.1f}ms")
                    return response, "slm", 0.8
                else:
                    logger.debug(f"[INPUT_MANAGER] SLM rejected: {slm_time:.1f}ms")
            except Exception as e:
                logger.warning(f"SLM query failed: {e}")
        
        # Tier 3: LLM Fallback
        if self.llm_fallback:
            try:
                llm_start = time.perf_counter()
                response = self.llm_fallback.generate(
                    mood="friendly",
                    style="sweet",
                    cause="chat_input",
                    raw_input=ctx.text
                )
                llm_time = (time.perf_counter() - llm_start) * 1000
                
                if response:
                    logger.debug(f"[INPUT_MANAGER] LLM fallback success: {llm_time:.1f}ms")
                    return response, "llm_fallback", 0.6
                else:
                    logger.debug(f"[INPUT_MANAGER] LLM fallback failed: {llm_time:.1f}ms")
            except Exception as e:
                logger.warning(f"LLM fallback failed: {e}")
        
        # Ultimate fallback
        fallback_msg = f"I understand you said: {ctx.text}"
        logger.warning("[INPUT_MANAGER] All AI tiers failed, using ultimate fallback")
        return fallback_msg, "fallback", 0.3
    
    def _judge_response(self, response: str, ctx: RequestContext) -> bool:
        """
        Judge response quality using the Judge module.
        
        Returns True if response passes quality threshold.
        """
        if not self.judge:
            return True  # No judge = accept all
        
        try:
            # Import judge if available
            from src.kitsu.modules.judge import judge_response
            judge_result = judge_response(ctx, response)
            confidence = judge_result.confidence(ctx.mode)
            
            # Accept if confidence meets threshold
            threshold = 0.65  # Configurable threshold
            return confidence >= threshold
            
        except Exception as e:
            logger.warning(f"Judge evaluation failed: {e}")
            return True  # Accept on judge failure
    
    @property
    def is_chat_enabled(self) -> bool:
        """Check if chat mode is enabled."""
        return self._chat_enabled
