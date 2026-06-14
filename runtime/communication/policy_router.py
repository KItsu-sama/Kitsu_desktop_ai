"""
# runtime/communication/policy_router.py

Policy Router: Route normalized input to FastBrain, SLM, or LLM based on complexity.

Decision Tree:
  Input → SimHash cache check → Pattern match → Intent classification → Route decision
    - Cache hit → FastBrain (< 5ms)
    - Simple (pattern match) → FastBrain (< 10ms)
    - Moderate (routine query) → SLM (< 500ms)
    - Complex (reasoning needed) → LLM (< 5s)

Design:
  - Uses SimHash from preprocess for instant cache hits
  - Voice input complexity multiplier (speech = simpler)
  - StripController enforces tier constraints
  - Gracefully downgrades on lower hardware tiers
  - No direct calls — all routing via Event Bus
  - Priority: Speed > Intelligence
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from rich.logging import RichHandler

from domain.contracts.contracts import ModuleContract
from runtime.events import EventBus, EventType, EventPayload
from runtime.strip_controller import StripController

# Configure logger with rich formatting
logger = logging.getLogger('kitsu.router.policy_router')
logger.addHandler(RichHandler(rich_tracebacks=True))
logger.setLevel(logging.DEBUG)


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
    simhash_cache_hit: bool = False  # New: cache hit indicator


class PolicyRouter(ModuleContract):
    """
    Intelligent routing with SimHash cache + voice optimization.
    
    Flow:
    1. SimHash cache check (instant FastBrain)
    2. Pattern matching (greetings/commands)
    3. Complexity analysis + voice boost
    4. Hardware-aware tier enforcement
    """

    module_id = 'router.policy_router'
    required_flags = []

    def __init__(self, event_bus: EventBus, strip_controller: StripController) -> None:
        self.event_bus = event_bus
        self.strip = strip_controller
        
        # FastBrain cache (simhash → response) - populated by reflex module
        self.fastbrain_cache: Dict[str, bool] = {}
        
        # Compile common patterns for quick matching (~1ms)
        self._greeting_patterns = self._compile_patterns([
            r'^(hi|hello|hey|yo|greetings|good\s*(morning|afternoon|evening))',
            r'(how are you|how\'s it going|what\'s up|howdy)',
        ])
        
        self._command_patterns = self._compile_patterns([
            r'^/(help|exit|quit|restart|clear|history|h)',
            r'^(open|close|launch|run|start|stop)\s+\w+',
            r'^(list|show|display)\s+(files|apps|tasks)',
        ])
        
        self._question_patterns = self._compile_patterns([
            r'^(what|where|when|who|why|how)\b',
            r'(\?$)',  # ends with question mark
        ])

    async def start(self) -> bool:
        """Initialize router and sync cache."""
        logger.info('🚀 PolicyRouter started with SimHash caching')
        await self._sync_cache()
        return True

    async def stop(self) -> bool:
        """Cleanup."""
        logger.info('🛑 PolicyRouter stopped')
        return True

    async def health_check(self):
        """Report router health with cache stats."""
        from runtime.health import HealthStatus
        cache_hit_rate = (
            sum(1 for v in self.fastbrain_cache.values() if v) 
            / max(len(self.fastbrain_cache), 1)
        )
        return HealthStatus(
            module_id=self.module_id,
            ok=True,
            latency_ms=0.0,
            details={
                'cache_size': len(self.fastbrain_cache),
                'cache_hit_rate': f"{cache_hit_rate:.1%}"
            }
        )

    async def _sync_cache(self) -> None:
        """Sync FastBrain cache from shared storage."""
        # TODO: Load from Redis/memcached/shared dict
        # For now, empty cache - populated by reflex hits
        logger.debug("Cache sync complete (empty - will populate from reflex hits)")

    @staticmethod
    def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
        """Compile regex patterns with case-insensitive flag."""
        return [re.compile(pat, re.IGNORECASE) for pat in patterns]

    def _match_patterns(self, text: str, patterns: list[re.Pattern]) -> bool:
        """Check if text matches any pattern."""
        return any(pat.search(text) for pat in patterns)

    def _analyze_complexity(self, content: str, input_type: str) -> float:
        """
        Score input complexity with VOICE BOOST.
        
        Voice inputs get 20% complexity reduction (less precise).
        """
        start_time = time.perf_counter()
        
        # Base complexity factors
        length_score = min(1.0, len(content.split()) / 30.0)
        
        # Vocabulary rarity
        rare_word_markers = {
            'utilize', 'implement', 'analyze', 'furthermore', 'however',
            'consequently', 'regarding', 'consider', 'evaluate', 'optimize',
            'algorithm', 'parameter', 'framework', 'integrate', 'leverage'
        }
        vocab_score = sum(1 for marker in rare_word_markers if marker in content.lower()) / 5.0
        
        # Structure complexity
        structure_score = min(1.0, (content.count('(') + content.count('[') + content.count(',')) / 4.0)
        
        # Weighted average
        complexity = (length_score * 0.4 + vocab_score * 0.3 + structure_score * 0.3)
        
        # VOICE INPUT BOOST: Speech is less precise → lower complexity
        if input_type == 'speech':
            complexity *= 0.8
            logger.debug("🔊 Voice input: complexity reduced by 20%")
        
        complexity = min(1.0, max(0.0, complexity))
        
        analysis_time = (time.perf_counter() - start_time) * 1000
        logger.debug(f"[POLICY] Complexity: {complexity:.2f} (len={length_score:.2f}, vocab={vocab_score:.2f}, struct={structure_score:.2f}) in {analysis_time:.1f}μs")
        
        return complexity

    def _check_simhash_cache(self, simhash: str) -> bool:
        """Check if SimHash exists in FastBrain cache."""
        if simhash in self.fastbrain_cache:
            logger.debug(f"💾 SimHash CACHE HIT: {simhash[:16]}...")
            return True
        return False

    async def analyze(
        self, 
        content: str, 
        simhash: str, 
        input_type: str = 'text'
    ) -> RoutingDecision:
        """
        Analyze input with SimHash cache + voice boost.
        
        Args:
            content: Normalized input text
            simhash: Pre-computed SimHash from preprocess
            input_type: 'text', 'speech', 'command'
        """
        start_time = time.perf_counter()
        logger.debug(f"[POLICY] Analyzing: '{content[:50]}{'...' if len(content) > 50 else ''}' | simhash={simhash[:16]} | type={input_type}")
        
        # 1. SIMHASH CACHE CHECK - Instant FastBrain
        if self._check_simhash_cache(simhash):
            analysis_time = (time.perf_counter() - start_time) * 1000
            return RoutingDecision(
                target=await self.strip.enforce(RoutingTarget.FASTBRAIN),
                confidence=1.0,
                reason='SimHash cache hit',
                complexity_score=0.0,
                estimated_latency_ms=2,
                simhash_cache_hit=True
            )

        # 2. PATTERN MATCHING - FastBrain candidates
        if self._match_patterns(content, self._greeting_patterns):
            analysis_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"[POLICY] Greeting pattern ✓ in {analysis_time:.1f}ms")
            return RoutingDecision(
                target=await self.strip.enforce(RoutingTarget.FASTBRAIN),
                confidence=0.95,
                reason='Greeting pattern matched',
                complexity_score=0.1,
                estimated_latency_ms=5,
                simhash_cache_hit=False
            )

        if self._match_patterns(content, self._command_patterns):
            analysis_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"[POLICY] Command pattern ✓ in {analysis_time:.1f}ms")
            return RoutingDecision(
                target=await self.strip.enforce(RoutingTarget.FASTBRAIN),
                confidence=0.9,
                reason='Command pattern matched',
                complexity_score=0.2,
                estimated_latency_ms=8,
                simhash_cache_hit=False
            )

        # 3. COMPLEXITY ANALYSIS with VOICE BOOST
        complexity = self._analyze_complexity(content, input_type)

        # Low complexity → FastBrain
        if complexity < 0.3:
            analysis_time = (time.perf_counter() - start_time) * 1000
            return RoutingDecision(
                target=await self.strip.enforce(RoutingTarget.FASTBRAIN),
                confidence=0.8,
                reason=f'Low complexity (score={complexity:.2f})',
                complexity_score=complexity,
                estimated_latency_ms=10,
                simhash_cache_hit=False
            )

        # Medium complexity → SLM (with tier downgrade)
        if complexity < 0.65:
            default_target = RoutingTarget.SLM
            enforced = await self.strip.enforce(default_target)
            
            reason = (
                f'Medium complexity (score={complexity:.2f})'
                if enforced == default_target 
                else f'Medium complexity, SLM unavailable → {enforced.value}'
            )
            
            analysis_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"[POLICY] Medium ({complexity:.2f}) → {enforced.value} in {analysis_time:.1f}ms")
            return RoutingDecision(
                target=enforced,
                confidence=0.7,
                reason=reason,
                complexity_score=complexity,
                estimated_latency_ms=300,
                simhash_cache_hit=False
            )

        # High complexity → LLM (with tier downgrade)
        default_target = RoutingTarget.LLM
        enforced = await self.strip.enforce(default_target)
        
        reason = (
            f'High complexity (score={complexity:.2f})'
            if enforced == default_target 
            else f'High complexity, LLM unavailable → {enforced.value}'
        )
        
        analysis_time = (time.perf_counter() - start_time) * 1000
        logger.debug(f"[POLICY] High ({complexity:.2f}) → {enforced.value} in {analysis_time:.1f}ms")
        return RoutingDecision(
            target=enforced,
            confidence=0.6,
            reason=reason,
            complexity_score=complexity,
            estimated_latency_ms=3000,
            simhash_cache_hit=False
        )

    async def route(
        self, 
        content: str, 
        simhash: str, 
        input_type: str = 'text', 
        metadata: Dict[str, Any] | None = None
    ) -> Optional[RoutingDecision]:
        """
        Public API: Analyze + emit routing decision.
        
        Expects preprocess.simhash in context.
        """
        start_time = time.perf_counter()
        
        try:
            decision = await self.analyze(content, simhash, input_type)
            
            # Emit via EventBus
            emit_start = time.perf_counter()
            await self.event_bus.emit(
                EventType.ROUTING_DECISION,
                EventPayload(
                    source=self.module_id,
                    data={
                        'target': decision.target.value,
                        'confidence': decision.confidence,
                        'reason': decision.reason,
                        'complexity_score': decision.complexity_score,
                        'estimated_latency_ms': decision.estimated_latency_ms,
                        'simhash_cache_hit': decision.simhash_cache_hit,
                        'simhash': simhash[:16],
                        'content_preview': content[:100],
                        'input_type': input_type,
                        'metadata': metadata or {}
                    }
                )
            )
            emit_time = (time.perf_counter() - emit_start) * 1000
            
            total_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"🎯 ROUTE: {decision.target.value} | conf={decision.confidence:.1f} | complexity={decision.complexity_score:.2f} | {total_time:.1f}ms")
            
            return decision
        except Exception:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.exception(f'[POLICY] Routing failed after {total_time:.1f}ms')
            return None

    def update_cache(self, simhash: str, cache_hit: bool = True) -> None:
        """Update FastBrain cache (called by reflex module)."""
        self.fastbrain_cache[simhash] = cache_hit
        if len(self.fastbrain_cache) > 10000:  # LRU eviction
            # TODO: Implement proper LRU
            pass
        logger.debug(f"💾 Cache updated: {simhash[:16]} → {cache_hit}")


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
        # Subscribe to cache updates from reflex
        await event_bus.subscribe("CACHE_HIT", _policy_router.update_cache)
    return _policy_router