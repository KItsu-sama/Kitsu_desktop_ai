"""
FastBrain Pattern Detection: Regex/rule-based ultra-fast responses.

Flow:
  Input → Pattern matching → Intent classification → Template response

Design:
  - All patterns compiled at startup (< 50ms overhead)
  - Zero ML overhead — pure regex/logic + fuzzy matching
  - Latency target: < 5ms pattern matching
  - Covers: greetings, commands, spam, common queries
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional

from domain.contracts.contracts import ModuleContract
from runtime.events import EventBus, EventType, EventPayload

logger = logging.getLogger('kitsu.ai.fast_brain.patterns')


class PatternIntentType(Enum):
    """Intent categories detected by pattern matching."""
    GREETING = 'greeting'
    FAREWELL = 'farewell'
    COMMAND = 'command'
    QUESTION = 'question'
    STATEMENT = 'statement'
    SPAM = 'spam'
    UNKNOWN = 'unknown'


@dataclass
class PatternMatch:
    """Result of pattern matching."""
    matched: bool
    intent: PatternIntentType
    confidence: float  # 0.0 → 1.0
    response: Optional[str] = None
    pattern_name: str = 'none'
    captured_data: dict = None  # e.g., {'command': 'open', 'target': 'notepad'}

    def __post_init__(self):
        if self.captured_data is None:
            self.captured_data = {}


class PatternDetector(ModuleContract):
    """
    Rule-based pattern detection for FastBrain quick responses.
    
    Responsibilities:
    - Compile regex patterns efficiently
    - Match against common intents
    - Extract parameters from commands
    - Detect spam/noise
    - Report confidence scores
    """
    
    module_id = 'ai.fast_brain.patterns'
    required_flags = []

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        """Initialize pattern detector with compiled patterns."""
        self.event_bus = event_bus
        self._patterns = self._compile_patterns()
        self._exact_responses = self._compile_exact_responses()
        self._fuzzy_threshold = 0.8
        logger.info('PatternDetector initialized with patterns')

    async def start(self) -> bool:
        """Start pattern detector."""
        logger.info('PatternDetector started')
        return True

    async def stop(self) -> bool:
        """Clean up."""
        return True

    async def health_check(self):
        """Report detector health."""
        from runtime.health import HealthStatus
        return HealthStatus(
            module_id=self.module_id,
            ok=True,
            latency_ms=0.0,
            details={'pattern_count': sum(len(p) for p in self._patterns.values())}
        )

    def _compile_exact_responses(self) -> dict[str, str]:
        """
        Compile exact match patterns with direct responses.
        
        Returns:
            Dict mapping exact phrases to responses
        """
        return {
            "help": "I can help you with various things! Try asking me questions or giving commands.",
            "hi": "Hai!",
            "hello": "Hello there!",
            "hey": "Hey!",
            "sup": "What's up!",
            "yo": "Yo!",
            "bye": "Goodbye!",
            "goodbye": "See you later!",
            "thanks": "You're welcome!",
            "thank you": "Happy to help!",
            "sorry": "No worries!",
            "yes": "Great!",
            "yeah": "Awesome!",
            "no": "Okay, noted.",
            "nope": "Alright.",
            "!help": "Available commands: !help, !time, !date, !status",
            "!status": "I'm doing well!",
            "/help": "Use /help for command list, or just ask me anything!",
            "debug": "[DEBUG MODE] Pattern detector online"
        }

    def _compile_patterns(self) -> dict[str, list[tuple[str, re.Pattern, PatternIntentType]]]:
        """
        Compile all regex patterns into structured groups.
        
        Returns:
            Dict mapping pattern category to list of (name, compiled_regex, intent_type)
        """
        CASE_INSENSITIVE = re.IGNORECASE | re.UNICODE

        patterns = {
            'greetings': [
                ('simple_hi', re.compile(r'^(hi|hello|hey|yo|greetings|hola|sup)s?!*$', CASE_INSENSITIVE), PatternIntentType.GREETING),
                ('how_are_you', re.compile(r'(how are you|how\'s it going|what\'s (up|good)|how\'s your day)', CASE_INSENSITIVE), PatternIntentType.GREETING),
                ('good_time_of_day', re.compile(r'(good morning|good afternoon|good evening|good night)', CASE_INSENSITIVE), PatternIntentType.GREETING),
                ('nice_to_meet', re.compile(r'(nice to (meet|see)|pleasure to|glad to (meet|see))', CASE_INSENSITIVE), PatternIntentType.GREETING),
                ('casual_hello', re.compile(r'^(hai|haii|heeyo|heyo)s?!*$', CASE_INSENSITIVE), PatternIntentType.GREETING),
            ],
            'farewells': [
                ('bye', re.compile(r'^(bye|goodbye|see you|farewell|cya|see ya|later|gtg)s?!*$', CASE_INSENSITIVE), PatternIntentType.FAREWELL),
                ('later', re.compile(r'(see you (later|soon)|talk (to you )?soon|catch you|until (next|later))', CASE_INSENSITIVE), PatternIntentType.FAREWELL),
                ('thanks_bye', re.compile(r'(thanks?.*bye|bye.*thanks?)', CASE_INSENSITIVE), PatternIntentType.FAREWELL),
            ],
            'commands': [
                ('help', re.compile(r'^(@help|/help|help|!help|what can you do)', CASE_INSENSITIVE), PatternIntentType.COMMAND),
                ('exit', re.compile(r'^(quit|exit|close|stop|gtfo|logout|shutdown)$', CASE_INSENSITIVE), PatternIntentType.COMMAND),
                ('clear', re.compile(r'^(clear|cls|reset|wipe memory|forget)$', CASE_INSENSITIVE), PatternIntentType.COMMAND),
                ('open_app', re.compile(r'^(open|launch|run|start|execute)\s+(\w+)', CASE_INSENSITIVE), PatternIntentType.COMMAND),
                ('system_info', re.compile(r'(system info|stats|my computer|specs|hardware|performance)', CASE_INSENSITIVE), PatternIntentType.COMMAND),
            ],
            'questions': [
                ('open_question', re.compile(r'^(what|where|when|who|why|how|can you|could you|will you).*\?$', CASE_INSENSITIVE), PatternIntentType.QUESTION),
                ('yes_no_question', re.compile(r'^(do|does|did|will|would|should|is|are|am|have|has)\s+.*\?$', CASE_INSENSITIVE), PatternIntentType.QUESTION),
                ('interrogative_word', re.compile(r'^(which|whose|what time|how many|how much|how long).*\?$', CASE_INSENSITIVE), PatternIntentType.QUESTION),
            ],
            'spam': [
                ('repeated_chars', re.compile(r'(.)\1{4,}'), PatternIntentType.SPAM),  # aaaaa
                ('repeated_words', re.compile(r'\b(\w+)\s+(?:\1\s+){2,}', CASE_INSENSITIVE), PatternIntentType.SPAM),
                ('excessive_punctuation', re.compile(r'[!?]{3,}'), PatternIntentType.SPAM),
                ('gibberish', re.compile(r'^[bcdfghjklmnpqrstvwxyz]{10,}$', CASE_INSENSITIVE), PatternIntentType.SPAM),
            ],
        }

        return patterns

    def detect(self, text: str) -> PatternMatch:
        """
        Detect intent and matching pattern.
        
        Args:
            text: User input (normalized)
        
        Returns:
            PatternMatch with matched intent and confidence
        """
        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Check spam first (lowest latency rejection)
        spam_match = self._check_spam(text_stripped)
        if spam_match.matched:
            return spam_match

        # Check exact matches (fastest positive match)
        if text_lower in self._exact_responses:
            return PatternMatch(
                matched=True,
                intent=PatternIntentType.GREETING,  # or determine dynamically
                confidence=0.95,
                response=self._exact_responses[text_lower],
                pattern_name='exact_match'
            )

        # Check regex patterns in priority order
        priority_order = ['greetings', 'farewells', 'commands', 'questions']
        
        for category in priority_order:
            patterns = self._patterns.get(category, [])
            for pattern_name, regex, intent_type in patterns:
                match_obj = regex.search(text_stripped)
                if match_obj:
                    confidence = 0.92 if category in ['greetings', 'farewells'] else 0.85
                    
                    # Extract command parameters if applicable
                    captured_data = {}
                    if intent_type == PatternIntentType.COMMAND and 'open_app' in pattern_name:
                        groups = match_obj.groups()
                        if len(groups) >= 2:
                            captured_data = {'action': groups[0], 'target': groups[1]}
                    
                    return PatternMatch(
                        matched=True,
                        intent=intent_type,
                        confidence=confidence,
                        pattern_name=pattern_name,
                        captured_data=captured_data
                    )

        # Try fuzzy matching as fallback
        fuzzy_match = self._fuzzy_match(text_lower)
        if fuzzy_match:
            return fuzzy_match

        # No pattern matched
        return PatternMatch(
            matched=False,
            intent=PatternIntentType.UNKNOWN,
            confidence=0.0,
            pattern_name='none'
        )

    def _check_spam(self, text: str) -> PatternMatch:
        """Check if input is spam/noise."""
        spam_patterns = self._patterns.get('spam', [])
        for pattern_name, regex, _ in spam_patterns:
            if regex.search(text):
                return PatternMatch(
                    matched=True,
                    intent=PatternIntentType.SPAM,
                    confidence=0.9,
                    pattern_name=pattern_name
                )
        return PatternMatch(
            matched=False,
            intent=PatternIntentType.UNKNOWN,
            confidence=0.0
        )

    def _fuzzy_match(self, text_lower: str) -> Optional[PatternMatch]:
        """Try fuzzy matching against exact responses."""
        best_match = None
        best_score = 0.0

        for pattern, response in self._exact_responses.items():
            score = SequenceMatcher(None, text_lower, pattern.lower()).ratio()
            if score > best_score and score >= self._fuzzy_threshold:
                best_score = score
                best_match = PatternMatch(
                    matched=True,
                    intent=PatternIntentType.GREETING,
                    confidence=score,
                    response=response,
                    pattern_name='fuzzy_match'
                )

        return best_match

    def extract_parameters(self, text: str, intent: PatternIntentType) -> dict[str, str]:
        """Extract structured parameters from matched text."""
        params = {}

        if intent == PatternIntentType.COMMAND:
            cmd_match = re.match(r'^(open|launch|run|start|close|quit)\s+(.+)$', text, re.IGNORECASE)
            if cmd_match:
                params['verb'] = cmd_match.group(1).lower()
                params['object'] = cmd_match.group(2).lower()

        elif intent == PatternIntentType.QUESTION:
            if text.lower().startswith(('what', 'who', 'when', 'where', 'why')):
                params['qtype'] = 'open'
            elif text.lower().startswith(('do', 'does', 'did', 'will', 'is', 'are')):
                params['qtype'] = 'yes_no'
            else:
                params['qtype'] = 'other'

        return params

    async def emit_match(self, match: PatternMatch, original_text: str) -> None:
        """Emit pattern match event through Event Bus."""
        if self.event_bus:
            try:
                self.event_bus.emit(
                    EventType.AI_REQUEST,
                    EventPayload(
                        source=self.module_id,
                        data={
                            'intent': match.intent.value,
                            'confidence': match.confidence,
                            'pattern': match.pattern_name,
                            'content': original_text,
                            'response': match.response,
                        }
                    )
                )
            except Exception:
                logger.exception('Failed to emit pattern match event')


# Singleton instance
_detector: Optional[PatternDetector] = None


def get_pattern_detector(event_bus: Optional[EventBus] = None) -> PatternDetector:
    """Get or create singleton PatternDetector."""
    global _detector
    if _detector is None:
        _detector = PatternDetector(event_bus=event_bus)
    return _detector