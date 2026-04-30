"""
Policy Router: Route normalized input to FastBrain, SLM, or LLM based on complexity.

Decision Tree:
  Input → Pattern match (FastBrain) → Intent classification → Route decision
    - Simple (pattern match) → FastBrain (< 10ms)
    - Moderate (routine query) → SLM (< 500ms)
    - Complex (reasoning needed) → LLM (< 5s)

Design:
  - Uses strip_controller to enforce tier constraints
  - Gracefully downgrades on lower hardware tiers
  - No direct calls — all routing via Event Bus
  - Priority: Speed > Intelligence
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from domain.contracts.contracts import ModuleContract
from runtime.events import EventBus, EventType, EventPayload
from runtime.strip_controller import StripController

logger = logging.getLogger('kitsu.router.policy_router')


class RoutingTarget(Enum):
    """Target AI layer for this input."""
    FASTBRAIN = 'fastbrain'
    SLM = 'slm'
    LLM = 'llm'
    TEMPLATE = 'template'  # Fallback static response


@dataclass
class RoutingDecision:
    """Result of routing analysis."""
    target: RoutingTarget
    confidence: float
    reason: str
    complexity_score: float  # 0.0 (trivial) → 1.0 (complex)
    estimated_latency_ms: float


class PolicyRouter(ModuleContract):
    """
    Route normalized inputs to the appropriate intelligence layer.
    
    Responsibilities:
    - Analyze input complexity
    - Apply policy constraints (device tier)
    - Select optimal target (FastBrain → SLM → LLM)
    - Emit routing decision through Event Bus
    - Gracefully degrade on resource constraints
    """

    module_id = 'router.policy_router'
    required_flags = []

    def __init__(self, event_bus: EventBus, strip_controller: StripController) -> None:
        self.event_bus = event_bus
        self.strip = strip_controller
        
        # Compile common patterns for quick matching
        self._greeting_patterns = self._compile_patterns([
            r'^(hi|hello|hey|yo|greetings)',
            r'(how are you|how\'s it going|what\'s up)',
        ])
        
        self._command_patterns = self._compile_patterns([
            r'^/(help|exit|quit|restart)',
            r'^(open|close|launch|run)\s+\w+',
        ])
        
        self._question_patterns = self._compile_patterns([
            r'^(what|where|when|who|why|how)',
            r'(\?$)',  # ends with ?
        ])

    async def start(self) -> bool:
        """Initialize router."""
        logger.info('PolicyRouter started')
        return True

    async def stop(self) -> bool:
        """Cleanup."""
        return True

    async def health_check(self):
        """Report router health."""
        from runtime.health import HealthStatus
        return HealthStatus(
            module_id=self.module_id,
            ok=True,
            latency_ms=0.0
        )

    @staticmethod
    def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
        """Compile regex patterns with case-insensitive flag."""
        return [re.compile(pat, re.IGNORECASE) for pat in patterns]

    def _match_patterns(self, text: str, patterns: list[re.Pattern]) -> bool:
        """Check if text matches any pattern."""
        return any(pat.search(text) for pat in patterns)

    def _analyze_complexity(self, content: str) -> float:
        """
        Score input complexity on 0.0 (trivial) → 1.0 (complex).
        
        Factors:
        - Length (longer → more complex)
        - Vocabulary (rare words → more complex)
        - Sentence structure (nested → more complex)
        """
        length_score = min(1.0, len(content.split()) / 30.0)  # 30 words = moderately complex
        
        # Rough vocabulary check: presence of uncommon words
        rare_word_markers = [
            'utilize', 'implement', 'analyze', 'furthermore', 'however',
            'consequently', 'regarding', 'consider', 'evaluate', 'optimize'
        ]
        vocab_score = sum(1 for marker in rare_word_markers if marker in content.lower()) / 5.0
        vocab_score = min(1.0, vocab_score)
        
        # Nested structure check (parentheses, multiple clauses)
        structure_score = min(1.0, (content.count('(') + content.count(',')) / 4.0)
        
        # Average the three factors
        complexity = (length_score * 0.4 + vocab_score * 0.3 + structure_score * 0.3)
        return min(1.0, complexity)

    async def analyze(self, content: str, input_type: str = 'text') -> RoutingDecision:
        """
        Analyze input and produce routing decision.
        
        Args:
            content: Normalized input text
            input_type: 'text', 'speech', 'command'
        
        Returns:
            RoutingDecision with target and reasoning
        """
        # Early exit: empty input
        if not content or not content.strip():
            return RoutingDecision(
                target=RoutingTarget.TEMPLATE,
                confidence=0.5,
                reason='Empty input detected',
                complexity_score=0.0,
                estimated_latency_ms=10
            )

        # Pattern matching layer: FastBrain candidates
        if self._match_patterns(content, self._greeting_patterns):
            return RoutingDecision(
                target=await self.strip.enforce(RoutingTarget.FASTBRAIN),
                confidence=0.95,
                reason='Greeting pattern matched',
                complexity_score=0.1,
                estimated_latency_ms=5
            )

        if self._match_patterns(content, self._command_patterns):
            return RoutingDecision(
                target=await self.strip.enforce(RoutingTarget.FASTBRAIN),
                confidence=0.9,
                reason='Command pattern matched',
                complexity_score=0.2,
                estimated_latency_ms=8
            )

        # Complexity-based routing
        complexity = self._analyze_complexity(content)

        # Low complexity → FastBrain
        if complexity < 0.3:
            return RoutingDecision(
                target=await self.strip.enforce(RoutingTarget.FASTBRAIN),
                confidence=0.8,
                reason=f'Low complexity (score={complexity:.2f})',
                complexity_score=complexity,
                estimated_latency_ms=10
            )

        # Medium complexity → SLM
        if complexity < 0.65:
            default_target = RoutingTarget.SLM
            enforced = await self.strip.enforce(default_target)
            
            # On ultra_low tier, SLM unavailable → downgrade to FastBrain
            if enforced != default_target:
                reason = f'Medium complexity, but SLM unavailable on tier; downgrading to {enforced.value}'
            else:
                reason = f'Medium complexity (score={complexity:.2f})'
            
            return RoutingDecision(
                target=enforced,
                confidence=0.7,
                reason=reason,
                complexity_score=complexity,
                estimated_latency_ms=300
            )

        # High complexity → LLM
        default_target = RoutingTarget.LLM
        enforced = await self.strip.enforce(default_target)
        
        if enforced != default_target:
            reason = f'High complexity, but LLM unavailable on tier; downgrading to {enforced.value}'
        else:
            reason = f'High complexity (score={complexity:.2f})'
        
        return RoutingDecision(
            target=enforced,
            confidence=0.6,
            reason=reason,
            complexity_score=complexity,
            estimated_latency_ms=3000
        )

    async def route(self, content: str, input_type: str = 'text', metadata: dict[str, Any] | None = None) -> Optional[RoutingDecision]:
        """
        Analyze and emit routing decision.
        
        Public API: Called by main input handler after normalization.
        
        Args:
            content: Normalized input text
            input_type: Classification (text, speech, command)
            metadata: Optional context (user_id, session_id, etc.)
        
        Returns:
            RoutingDecision if successful, None on error
        """
        try:
            decision = await self.analyze(content, input_type)
            
            # Emit routing decision through Event Bus
            self.event_bus.emit(
                EventType.ROUTING_DECISION,
                EventPayload(
                    source=self.module_id,
                    data={
                        'target': decision.target.value,
                        'confidence': decision.confidence,
                        'reason': decision.reason,
                        'complexity_score': decision.complexity_score,
                        'estimated_latency_ms': decision.estimated_latency_ms,
                        'content_preview': content[:100],
                        'metadata': metadata or {}
                    }
                )
            )
            
            logger.debug(
                'Routed to %s (conf=%.2f, complexity=%.2f): %s',
                decision.target.value,
                decision.confidence,
                decision.complexity_score,
                decision.reason
            )
            
            return decision
        except Exception:
            logger.exception('Routing analysis failed')
            return None


# Singleton instance
_policy_router: Optional[PolicyRouter] = None


async def get_policy_router(
    event_bus: EventBus,
    strip_controller: StripController
) -> PolicyRouter:
    """Get or create singleton PolicyRouter."""
    global _policy_router
    if _policy_router is None:
        _policy_router = PolicyRouter(event_bus=event_bus, strip_controller=strip_controller)
    return _policy_router
