"""
FastBrain Engine: Orchestrate pattern → intent → generation pipeline.

Flow:
  Input → Pattern match → Intent classification → Response generation
  
  - Patterns: 0-5ms (exact/regex/fuzzy matching)
  - Intent:   0-5ms (heuristic classification)
  - Response: 5-20ms (caching, Markov, templates)
  - Latency target: < 10ms

Design:
  - Stateful for boredom/spam detection
  - Emits responses through Event Bus
  - Integrates learning loop for personalization
  - Falls back to SLM/LLM on uncertainty
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

from runtime.communication.bus import MessageBus
from domain.contracts.contracts import ModuleContract
from runtime.communication.events import EventBus, EventType, EventPayload
from domain.ai.fast_brain.patterns import get_pattern_detector, PatternIntentType
from domain.ai.fast_brain.intent_classifier import get_intent_classifier, Intent
from .cache_store import get_cached_response, add_to_cache, get_spam_response , conversation_cache


logger = logging.getLogger('kitsu.ai.fast_brain.engine')


@dataclass
class FastBrainResponse:
    """Response from FastBrain engine."""
    text: str
    generation_mode: str  # "pattern", "intent", "markov", "cached", "llm_fallback"
    intent: Optional[str] = None
    confidence: float = 0.9
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FastBrainEngine(ModuleContract):
    """
    FastBrain orchestrates rapid-response intelligence pipeline.
    
    Responsibilities:
    - Pattern matching (0-5ms)
    - Intent classification (0-5ms)
    - Response generation/selection (5-20ms)
    - Spam/boredom detection
    - Learning loop integration
    - Fallback routing to SLM/LLM
    """
    
    module_id = 'ai.fast_brain.engine'
    required_flags = ['use_fast_brain']

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.pattern_detector = get_pattern_detector(event_bus)
        self.intent_classifier = get_intent_classifier(event_bus)
        
        # State tracking
        self.boredom_timer = 0.0
        self.spam_timer = 0.0
        self.last_interaction_time = time.time()
        
        # Thresholds
        self.boredom_threshold = 300.0  # 5 minutes
        self.spam_threshold = 10.0      # 10 seconds
    
    async def start(self) -> bool:
        """Start FastBrain engine."""
        try:
            # Initialize subcomponents
            await self.pattern_detector.start()
            await self.intent_classifier.start()
            logger.info('FastBrainEngine started')
            return True
        except Exception:
            logger.exception('Failed to start FastBrainEngine')
            return False

    async def stop(self) -> bool:
        """Shutdown FastBrain engine."""
        try:
            await self.pattern_detector.stop()
            await self.intent_classifier.stop()
            logger.info('FastBrainEngine stopped')
            return True
        except Exception:
            logger.exception('Error stopping FastBrainEngine')
            return False

    async def health_check(self):
        """Report engine health."""
        from runtime.health import HealthStatus
        try:
            pattern_health = await self.pattern_detector.health_check()
            classifier_health = await self.intent_classifier.health_check()
            
            ok = pattern_health.ok and classifier_health.ok
            
            return HealthStatus(
                module_id=self.module_id,
                ok=ok,
                latency_ms=0.0,
                details={
                    'pattern_detector': pattern_health.ok,
                    'intent_classifier': classifier_health.ok,
                }
            )
        except Exception:
            logger.exception('Health check failed')
            return HealthStatus(
                module_id=self.module_id,
                ok=False,
                latency_ms=0.0
            )
    
    async def process_input(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user input through the Fast Brain pipeline.
        
        Args:
            user_input: Raw user input
            context: Additional context
            
        Returns:
            Response dictionary with metadata
        """
        context = context or {}
        start_time = time.time()
        logger.debug(f"[FASTBRAIN] Processing input: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")
        
        # Update timers
        current_time = time.time()
        time_since_last = current_time - self.last_interaction_time
        self.last_interaction_time = current_time
        
        # Update boredom timer
        if time_since_last > 60:  # Reset if gap > 1 minute
            self.boredom_timer = 0.0
        else:
            self.boredom_timer += time_since_last
        
        logger.debug(f"[FASTBRAIN] Timers: boredom={self.boredom_timer:.1f}s, spam={self.spam_timer:.1f}s")
        
        # Step 1: Check cache for exact matches (0ms response)
        cache_start = time.time()
        cached_response = get_cached_response(user_input)
        cache_time = (time.time() - cache_start) * 1000
        
        if cached_response:
            logger.debug(f"[FASTBRAIN] Cache hit in {cache_time:.1f}ms")
            return self._create_response(
                cached_response,
                "cache_hit",
                start_time,
                {"cache_hit": True}
            )
        
        # Step 2: Check for spam
        spam_start = time.time()
        is_spam, spam_prob = self._check_spam(user_input)
        spam_time = (time.time() - spam_start) * 1000
        
        if is_spam:
            spam_response = get_spam_response(user_input)
            self.spam_timer += 1.0
            
            logger.debug(f"[FASTBRAIN] Spam detected ({spam_prob:.2f}) in {spam_time:.1f}ms")
            
            # Signal emotion engine for spam detection
            self._signal_emotion_engine("spam_detected", {"spam_probability": spam_prob})
            
            return self._create_response(
                spam_response,
                "spam_deflect",
                start_time,
                {"spam": True, "spam_probability": spam_prob}
            )
        
        # Reset spam timer if not spam
        self.spam_timer = max(0.0, self.spam_timer - 0.5)
        
        # Step 3: Try pattern matching (fast hardcoded responses)
        pattern_start = time.time()
        pattern_response = get_fast_response(user_input)
        pattern_time = (time.time() - pattern_start) * 1000
        
        if pattern_response:
            logger.debug(f"[FASTBRAIN] Pattern match in {pattern_time:.1f}ms")
            
            response = self._create_response(
                pattern_response,
                "pattern_match",
                start_time,
                {"pattern_matched": True}
            )
            
            # Add to cache
            add_to_cache(user_input, pattern_response)
            
            # Learn from this interaction
            add_learning_example(user_input, pattern_response, quality=0.8)
            
            return response
        
        # Step 4: Intent classification
        intent_start = time.time()
        intent, confidence = classify_intent(user_input)
        intent_time = (time.time() - intent_start) * 1000
        logger.debug(f"[FASTBRAIN] Intent classification: {intent.value} ({confidence:.2f}) in {intent_time:.1f}ms")
        
        # If system control, route to gateway
        if intent == Intent.SYSTEM_CONTROL:
            return self._route_to_gateway(user_input, intent, confidence, start_time)
        
        # Step 5: Try Markov generation for conversational intents
        if intent in {Intent.CONVERSATIONAL, Intent.EMOTIONAL, Intent.GREETING} and confidence > 0.6:
            markov_start = time.time()
            markov_response = generate_markov_response(user_input)
            markov_time = (time.time() - markov_start) * 1000
            
            if markov_response:
                logger.debug(f"[FASTBRAIN] Markov generation in {markov_time:.1f}ms")
                
                response = self._create_response(
                    markov_response,
                    "markov_generated",
                    start_time,
                    {"intent": intent.value, "confidence": confidence, "markov": True}
                )
                
                # Add to cache
                add_to_cache(user_input, markov_response)
                
                # Learn from this
                add_learning_example(user_input, markov_response, quality=0.7)
                
                return response
        
        # Step 6: Fallback to SLM/LLM
        return self._fallback_to_slm(user_input, intent, confidence, start_time, context)
    
    def _check_spam(self, user_input: str) -> Tuple[bool, float]:
        """
        Check if input is spam using multiple methods.
        
        Args:
            user_input: User input
            
        Returns:
            (is_spam, probability)
        """
        # Cache-based spam check
        cache_spam = cache_check_spam(user_input)
        
        # Markov-based spam probability
        markov_spam_prob = get_spam_probability(user_input)
        
        # Timer-based spam
        timer_spam = self.spam_timer > self.spam_threshold
        
        # Combine probabilities
        spam_prob = max(cache_spam * 0.5, markov_spam_prob, timer_spam * 0.3)
        
        is_spam = spam_prob > 0.7
        return is_spam, spam_prob
    
    def _route_to_gateway(self, user_input: str, intent: Intent, confidence: float, start_time: float) -> Dict[str, Any]:
        """Route system control commands to gateway."""
        # For now, return a placeholder response
        # In full implementation, this would call the system gateway
        response_text = f"System command recognized: {user_input}"
        
        return self._create_response(
            response_text,
            "gateway_routed",
            start_time,
            {"intent": intent.value, "confidence": confidence, "gateway": True}
        )
    
    def _fallback_to_slm(self, user_input: str, intent: Intent, confidence: float, start_time: float, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to SLM/LLM for complex queries."""
        # Placeholder - in real implementation, this would call the LLM
        response_text = f"I need to think about that... (LLM call would happen here)"
        
        return self._create_response(
            response_text,
            "llm_fallback",
            start_time,
            {"intent": intent.value, "confidence": confidence, "llm": True}
        )
    
    def _create_response(self, text: str, generation_mode: str, start_time: float, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create standardized response dictionary."""
        processing_time = time.time() - start_time
        
        response = {
            "text": text,
            "generation_mode": generation_mode,
            "processing_time": processing_time,
            "boredom_level": min(1.0, self.boredom_timer / self.boredom_threshold),
            "spam_level": min(1.0, self.spam_timer / self.spam_threshold),
        }
        
        if metadata:
            response.update(metadata)
        
        logger.debug(f"[FASTBRAIN] Response created: {generation_mode} in {processing_time*1000:.1f}ms")
        
        return response
    
    def _signal_emotion_engine(self, event: str, data: Dict[str, Any]) -> None:
        """Signal the emotion engine about events."""
        # Placeholder - in real implementation, this would emit events
        # to the personality/emotion_engine.py
        log.debug(f"Emotion signal: {event} with data {data}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "boredom_timer": self.boredom_timer,
            "spam_timer": self.spam_timer,
            "last_interaction_time": self.last_interaction_time,
            "boredom_threshold": self.boredom_threshold,
            "spam_threshold": self.spam_threshold,
        }


# Global instance
fast_brain_engine = FastBrainEngine(MessageBus())


async def process_user_input(user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process user input through the Fast Brain engine.
    
    Args:
        user_input: User input
        context: Additional context
        
    Returns:
        Response dictionary
    """
    return await fast_brain_engine.process_input(user_input, context)
