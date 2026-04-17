"""
FastBrain Intent Classifier: Semantic intent detection for routing.

Role: Classify user intent (greeting, question, command, system_control, etc.)
for proper response generation routing.

Design:
  - Fast heuristic-based classification (< 5ms)
  - No ML overhead
  - Integrates with ModuleContract for proper module lifecycle
  - Emits intent classification through Event Bus
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional

from core.contracts import ModuleContract
from core.events import EventBus, EventType, EventPayload

logger = logging.getLogger('kitsu.ai.fast_brain.intent_classifier')


class Intent(Enum):
    """Enumeration of possible user intents."""
    GREETING = "greeting"
    FAREWELL = "farewell"
    QUESTION = "question"
    COMMAND = "command"
    EMOTIONAL = "emotional"
    CONVERSATIONAL = "conversational"
    SYSTEM_CONTROL = "system_control"
    QUIZ_HELP = "quiz_help"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of intent classification."""
    intent: Intent
    confidence: float  # 0.0 → 1.0
    category: str  # for grouping


class IntentClassifier(ModuleContract):
    """
    Classify user input into intents for routing and response generation.
    
    Responsibilities:
    - Heuristic-based intent detection (no ML)
    - Route to appropriate handler
    - Emit classification results through Event Bus
    - Handle system control requests specially
    """
    
    module_id = 'ai.fast_brain.intent_classifier'
    required_flags = []

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        # Intent patterns with associated regexes
        self.intent_patterns = {
            Intent.GREETING: [
                r'^(hi|hello|hey|hai|heyo|sup|yo|howdy)\s*!*$',
                r'^good\s+(morning|afternoon|evening|day)$',
                r'^(what\'?s?\s+up|what\'?s?\s+happening)$',
            ],
            Intent.FAREWELL: [
                r'^(bye|goodbye|see\s+ya|later|cya|farewell|see you)\s*$',
                r'^(talk\s+to\s+you\s+soon|catch you (later|soon))\s*$',
                r'^(goodbye|till next time)\s*$',
            ],
            Intent.QUESTION: [
                r'\?$',  # Ends with question mark
                r'^(what|how|when|where|why|who|which|whose)\s+',
                r'^(can\s+you|could\s+you|would\s+you|do\s+you)\s+',
                r'^(tell\s+me|explain|describe)\s+',
                r'^(is\s+|are\s+|does\s+|do\s+|did\s+|was\s+|were\s+)',
            ],
            Intent.COMMAND: [
                r'^[!/]',  # Starts with command prefix
                r'^(please|help\s+me|set|change|toggle|enable|disable)\s+',
                r'^(show|hide|create|delete|start|stop|restart)\s+',
                r'^(run|execute|do)\s+',
            ],
            Intent.EMOTIONAL: [
                r'^(i\s+(feel|am|\'?m)|i\'?m\s+(feeling|so))\s+',
                r'^(i\s+(love|hate|like|dislike))\s+',
                r'^(thank\s+you|thanks|sorry|apologize)\s*$',
                r'^(goodbye|bye|see\s+ya|later|cya)\s*$',
            ],
            Intent.CONVERSATIONAL: [
                r'^(yeah|yes|yep|sure|okay|ok|alright|nope|nah)\s*$',
                r'^(that\'?s?\s+)?(good|bad|nice|cool|awesome|terrible)\s*$',
                r'^(i\s+(think|guess|suppose|believe))\s+',
                r'^(maybe|perhaps|actually|well)\s+',
            ],
            Intent.SYSTEM_CONTROL: [
                r'^(shutdown|restart|exit|quit|close)\s*$',
                r'^(system|config|settings|preferences)\s+',
                r'^(enable|disable)\s+(debug|logging|safe\s+mode)\s*$',
                r'^(switch|change)\s+(profile|mode)\s+',
            ],
            Intent.QUIZ_HELP: [
                r'^(quiz|question|answer|help\s+with)\s+',
                r'^(solve|answer)\s+(this|that|it)\s+',
                r'^(what\s+is|how\s+to|explain)\s+',
            ],
        }
        
        # Confidence thresholds for each intent
        self.confidence_thresholds = {
            Intent.GREETING: 0.7,
            Intent.FAREWELL: 0.7,
            Intent.QUESTION: 0.6,
            Intent.COMMAND: 0.8,
            Intent.EMOTIONAL: 0.7,
            Intent.CONVERSATIONAL: 0.5,
            Intent.SYSTEM_CONTROL: 0.9,
            Intent.QUIZ_HELP: 0.7,
        }
    
    def classify_intent(self, user_input: str) -> Tuple[Intent, float]:
        """
        Classify the intent of user input.
        
        Args:
            user_input: Raw user input string
            
        Returns:
            Tuple of (Intent, confidence_score)
        """
        if not user_input or not user_input.strip():
            return Intent.UNKNOWN, 0.0
        
        text = user_input.lower().strip()
        intent_scores = {}
        
        # Calculate scores for each intent
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.0
                    matches += 1
            
            # Normalize by number of patterns
            if patterns:
                score = score / len(patterns)
            
            # Boost score for multiple matches
            if matches > 1:
                score *= 1.2
            
            intent_scores[intent] = min(score, 1.0)
        
        # Find the highest scoring intent
        if not intent_scores:
            return Intent.UNKNOWN, 0.0
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]
        
        # Apply minimum confidence threshold
        threshold = self.confidence_thresholds.get(best_intent, 0.5)
        if confidence < threshold:
            return Intent.UNKNOWN, confidence
        
        return best_intent, confidence
    
    def is_system_control(self, intent: Intent) -> bool:
        """Check if intent requires system-level routing."""
        return intent == Intent.SYSTEM_CONTROL
    
    def requires_gateway(self, intent: Intent) -> bool:
        """Check if intent should be routed directly to gateway."""
        return intent in {Intent.SYSTEM_CONTROL, Intent.COMMAND}

    async def start(self) -> bool:
        """Start intent classifier."""
        logger.info('IntentClassifier started')
        return True

    async def stop(self) -> bool:
        """Clean up."""
        return True

    async def health_check(self):
        """Report classifier health."""
        from core.health import HealthStatus
        return HealthStatus(
            module_id=self.module_id,
            ok=True,
            latency_ms=0.0,
            details={'pattern_count': sum(len(p) for p in self.intent_patterns.values())}
        )

    async def classify(self, user_input: str) -> ClassificationResult:
        """
        Classify intent and emit event through Event Bus.
        
        Args:
            user_input: User input to classify
        
        Returns:
            ClassificationResult with intent and confidence
        """
        intent, confidence = self.classify_intent(user_input)
        
        # Categorize intent
        if intent in {Intent.GREETING, Intent.FAREWELL, Intent.EMOTIONAL}:
            category = 'affective'
        elif intent == Intent.SYSTEM_CONTROL:
            category = 'system'
        elif intent == Intent.COMMAND:
            category = 'action'
        elif intent == Intent.QUESTION:
            category = 'inquiry'
        else:
            category = 'general'
        
        result = ClassificationResult(
            intent=intent,
            confidence=confidence,
            category=category
        )
        
        # Emit through Event Bus
        if self.event_bus:
            try:
                self.event_bus.emit(
                    EventType.AI_REQUEST,
                    EventPayload(
                        source=self.module_id,
                        data={
                            'intent': intent.value,
                            'confidence': confidence,
                            'category': category,
                            'content': user_input[:100],
                        }
                    )
                )
            except Exception:
                logger.exception('Failed to emit intent classification event')
        
        logger.debug(
            'Classified intent: %s (conf=%.2f, category=%s)',
            intent.value,
            confidence,
            category
        )
        
        return result


# Singleton instance
_classifier: Optional[IntentClassifier] = None


def get_intent_classifier(event_bus: Optional[EventBus] = None) -> IntentClassifier:
    """Get or create singleton IntentClassifier."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier(event_bus=event_bus)
    return _classifier