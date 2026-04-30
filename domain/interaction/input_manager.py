"""
core/input_manager.py

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
from typing import Optional, Dict, Any

from runtime.bus import bus
from runtime.events import InputReceived, ResponseReady
from domain.contracts.contracts import AIProvider
from runtime.behavior_engine import BehaviorEngine, AttentionConfig

logger = logging.getLogger(__name__)


class InputManager:
    """
    Handles user input processing and AI pipeline routing.
    
    Coordinates behavior engine, AI providers (FastBrain/SLM/LLM),
    and response feeding back into learning systems.
    """
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self._chat_enabled: bool = True
        
        # Behavior engine for attention gating
        behavior_config = AttentionConfig(**orchestrator.core_config.get("attention", {}))
        self.behavior_engine = BehaviorEngine(behavior_config)
    
    async def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input through the complete AI pipeline.
        
        Args:
            user_input: Raw user input text
            
        Returns:
            Dict containing response and metadata
        """
        # Validate input
        if not user_input or not isinstance(user_input, str):
            raise ValueError("Invalid input")
        
        # Create input event
        input_event = InputReceived(text=user_input)
        
        # Process through behavior engine
        await self._handle_input(input_event)
        
        # Wait for response (synchronous for now)
        # In future, this could be made fully async with response events
        return {"status": "processed", "input": user_input}
    
    async def _handle_input(self, event: InputReceived) -> None:
        """
        Route input through behavior engine then AI pipeline.
        This is extracted from orchestrator._on_input()
        """
        # Get emotional state from EmotionManager (Single Source of Truth)
        emotion_state = self.orchestrator.emotion_manager.get_current_state() if self.orchestrator.emotion_manager else {}
        context = {
            "recent_inputs": getattr(self.orchestrator.core_memory, 'recent_memories', []) if self.orchestrator.core_memory else [],
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
            if self.orchestrator.avatar and behavior_decision.reaction_type:
                self.orchestrator.avatar.set_expression("neutral", "subtle", behavior_decision.reaction_type)
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
        if self.orchestrator.fast_brain and self.orchestrator.fast_brain.is_available():
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.orchestrator.fast_brain.query, event.text
                )
            except (RuntimeError, ValueError, TimeoutError, ConnectionError) as exc:
                logger.warning('FastBrain query failed: %s', exc)
                response = None
            
            if response is not None:
                if self.orchestrator.personality and isinstance(response, str):
                    try:
                        response = self.orchestrator.personality.decorate_response(response, source='fast_brain')
                    except Exception as exc:
                        logger.error('Personality injection failed: %s', exc)

                bus.publish(ResponseReady(
                    input_text=event.text,
                    response_text=response,
                    source="fast_brain",
                    confidence=1.0,
                ))
                return

        # SLM fallback - run in executor
        if self.orchestrator.slm and await self.orchestrator.slm.is_available():
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.orchestrator.slm.query, event.text
                )
            except Exception as exc:
                logger.warning('SLM query failed: %s', exc)
                response = None
            
            if response is not None:
                if self.orchestrator.personality and isinstance(response, str):
                    try:
                        response = self.orchestrator.personality.decorate_response(response, source='slm')
                    except Exception as exc:
                        logger.warning('Personality injection failed: %s', exc)

                bus.publish(ResponseReady(
                    input_text=event.text,
                    response_text=response,
                    source="slm",
                    confidence=0.75,
                ))
                return

        # LLM fallback - run in executor
        if self.orchestrator.llm and await self.orchestrator.llm.is_available():
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.orchestrator.llm.query, event.text
                )
            except Exception as exc:
                logger.warning('LLM query failed: %s', exc)
                response = None
            
            if response is not None:
                if self.orchestrator.personality and isinstance(response, str):
                    try:
                        response = self.orchestrator.personality.decorate_response(response, source='llm')
                    except Exception as exc:
                        logger.warning('Personality injection failed: %s', exc)

                bus.publish(ResponseReady(
                    input_text=event.text,
                    response_text=response,
                    source="llm",
                    confidence=0.9,
                ))
                return

        logger.warning("No AI provider could handle input: %r", event.text)
    
    def enable_chat(self) -> None:
        """Enable interactive chat mode."""
        self._chat_enabled = True
    
    def disable_chat(self) -> None:
        """Disable interactive chat mode."""
        self._chat_enabled = False
    
    @property
    def is_chat_enabled(self) -> bool:
        """Check if chat mode is enabled."""
        return self._chat_enabled
