"""
core/behavior_engine.py

BehaviorEngine = Personality-Driven Attention Gate

Responsibilities:
- Decide what action Kitsu should take (respond, react, idle, sleep)
- Compute attention scores to determine if Kitsu should engage
- Implement dynamic thresholds based on emotional state
- Select appropriate behavior type based on scoring

Non-responsibilities:
- State management (delegates to managers)
- Response generation (delegates to response_engine)
- File I/O
- Visual rendering
"""

import logging
import re
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

log = logging.getLogger(__name__)


class BehaviorType(Enum):
    """Types of behaviors Kitsu can perform."""
    RESPOND = "respond"           # Generate text response
    REACT = "react"               # Emotional reaction (blush, pout, etc.)
    IDLE = "idle"                 # Idle behavior
    CHECK_IN = "check_in"         # Check-in behavior (5 min idle)
    SLEEP = "sleep"               # Sleep mode (10 min idle)
    IGNORE = "ignore"             # Ignore input (selective ignoring)
    SYSTEM_COMMAND = "system_command"  # System command execution


class BehaviorDecision:
    """
    Result of behavior decision.
    
    Contains:
    - Behavior type
    - Context and metadata
    - Optional reaction type
    - Optional response requirements
    """
    
    def __init__(
        self,
        behavior_type: BehaviorType,
        context: Optional[Dict[str, Any]] = None,
        reaction_type: Optional[str] = None,
        response_required: bool = False,
        priority: int = 0
    ):
        self.behavior_type = behavior_type
        self.context = context or {}
        self.reaction_type = reaction_type
        self.response_required = response_required
        self.priority = priority  # Higher = more urgent


@dataclass
class AttentionConfig:
    """Configuration for attention scoring."""
    base_threshold: float = 0.5
    name_boost: float = 0.3
    question_boost: float = 0.2
    repeat_penalty: float = 0.3
    boredom_factor: float = 0.3
    energy_influence: float = 0.3


class BehaviorEngine:
    """
    Personality-Driven Attention Gate for Kitsu.
    
    This is PURE LOGIC - no state management, no I/O.
    Takes current state as input, returns behavior decision.
    Uses attention scoring to determine when Kitsu should respond.
    """
    
    def __init__(self, config: Optional[AttentionConfig] = None):
        """Initialize behavior engine."""
        self.config = config or AttentionConfig()
        self.triggers = self._load_triggers()
        # Load attention config from triggers if available
        self._load_attention_config()
        log.info("BehaviorEngine initialized as Attention Gate")
    
    def _load_attention_config(self) -> None:
        """Load attention configuration from triggers.json."""
        attention_config = self.triggers.get("attention", {})
        if attention_config:
            # Update config with values from triggers.json
            self.config.base_threshold = attention_config.get("base_threshold", self.config.base_threshold)
            self.config.name_boost = attention_config.get("name_boost", self.config.name_boost)
            self.config.question_boost = attention_config.get("question_boost", self.config.question_boost)
            self.config.repeat_penalty = attention_config.get("repeat_penalty", self.config.repeat_penalty)
            self.config.boredom_factor = attention_config.get("boredom_factor", self.config.boredom_factor)
            self.config.energy_influence = attention_config.get("energy_influence", self.config.energy_influence)
            log.debug("Loaded attention config from triggers.json")
    
    def decide_behavior(
        self,
        user_input: Optional[str] = None,
        emotion_state: Optional[Dict[str, Any]] = None,
        idle_state: Optional[Dict[str, Any]] = None,
        system_event: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> BehaviorDecision:
        """
        Decide what behavior Kitsu should perform.
        
        Args:
            user_input: User text input (if any)
            emotion_state: Current emotion state from emotion_manager
            idle_state: Current idle state from idle_manager
            system_event: System event (click, install, delete, notification)
            context: Additional context (conversation history, etc.)
        
        Returns:
            BehaviorDecision with behavior type and metadata
        """
        context = context or {}
        
        # Priority 1: System events (if not ignored)
        if system_event:
            decision = self._handle_system_event(system_event, emotion_state, context)
            if decision:
                return decision
        
        # Priority 2: Sleep mode
        if idle_state and idle_state.get("state") == "sleep":
            return BehaviorDecision(
                behavior_type=BehaviorType.SLEEP,
                context={"idle_time": idle_state.get("idle_time", 0)},
                priority=10
            )
        
        # Priority 3: Check-in behavior
        if idle_state and idle_state.get("state") == "check_in":
            return BehaviorDecision(
                behavior_type=BehaviorType.CHECK_IN,
                context={"idle_time": idle_state.get("idle_time", 0)},
                response_required=True,
                priority=8
            )
        
        # Priority 4: User input
        if user_input:
            return self._handle_user_input(user_input, emotion_state, context)
        
        # Priority 5: Idle behavior
        if idle_state and idle_state.get("state") == "idle":
            return BehaviorDecision(
                behavior_type=BehaviorType.IDLE,
                context={"idle_time": idle_state.get("idle_time", 0)},
                priority=1
            )
        
        # Default: idle
        return BehaviorDecision(
            behavior_type=BehaviorType.IDLE,
            priority=0
        )
    
    def _handle_user_input(
        self,
        user_input: str,
        emotion_state: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> BehaviorDecision:
        """
        Handle user text input using attention scoring.
        
        Args:
            user_input: User text input
            emotion_state: Current emotion state
            context: Additional context (recent_inputs, boredom_level, etc.)
        
        Returns:
            BehaviorDecision based on attention scoring
        """
        input_lower = user_input.lower().strip()
        
        # Check for commands (start with /) - always process
        if input_lower.startswith("/"):
            return BehaviorDecision(
                behavior_type=BehaviorType.SYSTEM_COMMAND,
                context={"command": user_input},
                priority=9
            )
        
        # Compute attention score
        attention_score = self._compute_attention_score(user_input, emotion_state, context)
        
        # Get dynamic threshold based on emotional state
        dynamic_threshold = self._compute_dynamic_threshold(emotion_state)
        
        # Log scoring for debugging
        log.debug(f"Attention score: {attention_score:.3f}, threshold: {dynamic_threshold:.3f}")
        
        # Check for emotional triggers first (can boost response)
        reaction = self._detect_emotional_trigger(user_input, emotion_state)
        
        # Behavior branching based on score
        if attention_score > dynamic_threshold:
            # High attention - full response
            if reaction:
                return BehaviorDecision(
                    behavior_type=BehaviorType.REACT,
                    reaction_type=reaction,
                    response_required=True,
                    context={
                        "trigger": user_input,
                        "attention_score": attention_score,
                        "threshold": dynamic_threshold
                    },
                    priority=7
                )
            else:
                return BehaviorDecision(
                    behavior_type=BehaviorType.RESPOND,
                    response_required=True,
                    context={
                        "input": user_input,
                        "attention_score": attention_score,
                        "threshold": dynamic_threshold
                    },
                    priority=5
                )
        elif attention_score > (dynamic_threshold * self.config.react_threshold_multiplier):
            # Medium attention - react only (subtle acknowledgment)
            return BehaviorDecision(
                behavior_type=BehaviorType.REACT,
                reaction_type=reaction or "glance",  # Default subtle reaction
                response_required=False,
                context={
                    "input": user_input,
                    "attention_score": attention_score,
                    "threshold": dynamic_threshold,
                    "subtle": True
                },
                priority=3
            )
        else:
            # Low attention - ignore
            return BehaviorDecision(
                behavior_type=BehaviorType.IGNORE,
                context={
                    "input": user_input,
                    "attention_score": attention_score,
                    "threshold": dynamic_threshold,
                    "reason": "low_attention"
                },
                priority=0
            )
    
    def _handle_system_event(
        self,
        system_event: Dict[str, Any],
        emotion_state: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Optional[BehaviorDecision]:
        """
        Handle system event (click, install, delete, notification) using external config.
        
        Args:
            system_event: System event data
            emotion_state: Current emotion state
            context: Additional context
        
        Returns:
            BehaviorDecision or None if event should be ignored
        """
        event_type = system_event.get("type")
        ignore_list = context.get("ignore_events", [])
        
        # Check if event should be ignored
        if event_type in ignore_list:
            return BehaviorDecision(
                behavior_type=BehaviorType.IGNORE,
                context={"event": system_event},
                priority=0
            )
        
        # Map event types to reactions using new triggers.json structure
        system_events = self.triggers.get("system_events", {})
        event_config = system_events.get(event_type)
        
        if event_config:
            reaction = event_config.get("reaction")
            priority = event_config.get("priority", 6)
            
            if reaction:
                return BehaviorDecision(
                    behavior_type=BehaviorType.REACT,
                    reaction_type=reaction,
                    context={"event": system_event},
                    priority=priority
                )
        
        # Default: ignore unknown events
        return None
    
    def _compute_attention_score(
        self,
        user_input: str,
        emotion_state: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> float:
        """
        Compute attention score for user input.
        
        Args:
            user_input: User text input
            emotion_state: Current emotion state
            context: Additional context (recent_inputs, boredom_level, etc.)
        
        Returns:
            Attention score between 0.0 and 1.0
        """
        score = 0.5  # Base score
        input_lower = user_input.lower().strip()
        
        # Use attention keywords from triggers.json
        attention_keywords = self.triggers.get("attention_keywords", {})
        names = attention_keywords.get("names", ["kitsu"])
        questions = attention_keywords.get("questions", [])
        
        # Boost for questions
        if self._is_question(user_input):
            score += self.config.question_boost
        
        # Boost for mentioning Kitsu by name variations
        if any(name in input_lower for name in names):
            score += self.config.name_boost
        
        # Boost based on energy level using energy_influence
        if emotion_state:
            energy = emotion_state.get("energy", 0.5)
            # Apply energy influence factor
            energy_modifier = (energy - 0.5) * self.config.energy_influence
            score += energy_modifier
            
            # Boost for high chaos personality traits (if chaos exists in emotion state)
            chaos = emotion_state.get("chaos", 0.0)
            if chaos > 0.6:
                score += self.config.energy_influence * 0.5  # Partial boost for chaos
        
        # Penalty for repetitive inputs (spam detection)
        recent_inputs = context.get("recent_inputs", [])
        if self._is_repetitive(user_input, recent_inputs):
            score -= self.config.repetition_penalty
        
        # Penalty for high boredom using boredom_factor
        boredom_level = context.get("boredom_level", 0.0)
        if boredom_level > 0.7:
            score -= self.config.boredom_factor * boredom_level
        
        # Clamp score between 0.0 and 1.0
        return max(0.0, min(1.0, score))
    
    def _compute_dynamic_threshold(
        self,
        emotion_state: Optional[Dict[str, Any]]
    ) -> float:
        """
        Compute dynamic threshold based on emotional state.
        
        Args:
            emotion_state: Current emotion state
        
        Returns:
            Dynamic threshold between 0.0 and 1.0
        """
        threshold = self.config.base_threshold
        
        if emotion_state:
            # Increase threshold if energy is low (harder to wake up)
            energy = emotion_state.get("energy", 0.5)
            if energy < 0.3:
                threshold += 0.2
            
            # Decrease threshold if chaos is high (more unpredictable/talkative)
            chaos = emotion_state.get("chaos", 0.0)
            if chaos > 0.6:
                threshold -= 0.15
        
        # Clamp threshold between 0.1 and 0.9
        return max(0.1, min(0.9, threshold))
    
    def _is_question(self, user_input: str) -> bool:
        """Check if input is a question."""
        return (
            user_input.strip().endswith("?") or
            any(word in user_input.lower() for word in ["what", "when", "where", "who", "why", "how", "is", "are", "do", "does", "can", "could", "would", "should"]) and
            "?" in user_input
        )
    
    def _is_repetitive(self, user_input: str, recent_inputs: List[str]) -> bool:
        """Check if input is repetitive (spam detection) using triggers.json config."""
        if not recent_inputs:
            return False
        
        # Get spam detection config from triggers.json
        spam_config = self.triggers.get("spam_detection", {})
        check_last_n = spam_config.get("check_last_n_inputs", 3)
        normalization_regex = spam_config.get("normalization_regex", "[^a-zA-Z0-9]")
        similarity_threshold = spam_config.get("similarity_threshold", 0.9)
        
        input_normalized = re.sub(normalization_regex, '', user_input.lower()).strip()
        
        # Check if similar to any of the last N inputs
        for recent_input in recent_inputs[-check_last_n:]:
            recent_normalized = re.sub(normalization_regex, '', recent_input.lower()).strip()
            
            # Simple similarity check (exact match for now, could be enhanced)
            if input_normalized == recent_normalized:
                return True
            
            # Could add more sophisticated similarity check here if needed
            # For now, just checking exact match after normalization
        
        return False
    
    def _load_triggers(self) -> Dict[str, Any]:
        """Load triggers from config file."""
        try:
            # Try to find config file in common locations
            config_paths = [
                os.path.join(os.path.dirname(__file__), "..", "shared", "triggers.json"),
                os.path.join(os.getcwd(), "config", "triggers.json"),
                "config/triggers.json"
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        triggers = json.load(f)
                        log.debug(f"Loaded triggers from {path}")
                        return triggers
            
            # Fallback to hardcoded triggers if config not found
            log.warning("Triggers config file not found, using fallback triggers")
            return self._get_fallback_triggers()
        except Exception as e:
            log.error(f"Failed to load triggers config: {e}")
            return self._get_fallback_triggers()
    
    def _get_fallback_triggers(self) -> Dict[str, Any]:
        """Fallback triggers if config loading fails."""
        return {
            "metadata": {
                "version": "3.0",
                "description": "Fallback triggers (clean production)"
            },
            "triggers": {
                "insulted": {
                    "keywords": ["stupid", "dumb", "bad", "wrong", "fail"],
                    "cooldown": 3.0,
                    "emotions": [{"name": "angry", "intensity": 0.9, "duration": 15}],
                    "reaction": {"high_edge": "glare", "default": "pout"}
                },
                "flustered": {
                    "keywords": ["cute", "pretty", "good", "nice", "love", "like"],
                    "cooldown": 4.0,
                    "emotions": [{"name": "flustered", "intensity": 0.9, "duration": 12}],
                    "reaction": {"default": "blush"}
                },
                "playful": {
                    "keywords": ["joke", "funny", "haha", "lol", "play"],
                    "cooldown": 2.0,
                    "emotions": [{"name": "playful", "intensity": 0.7, "duration": 8}],
                    "reaction": {"default": "giggle"}
                },
                "surprised": {
                    "keywords": ["wow", "whoa", "surprise", "shock"],
                    "cooldown": 3.0,
                    "emotions": [{"name": "excited", "intensity": 0.9, "duration": 12}],
                    "reaction": {"default": "jump"}
                }
            },
            "symbols": {
                "😊": "flustered",
                "😠": "insulted"
            },
            "attention": {
                "base_threshold": 0.5,
                "name_boost": 0.3,
                "question_boost": 0.2,
                "repeat_penalty": 0.3,
                "boredom_factor": 0.3,
                "energy_influence": 0.3
            },
            "attention_keywords": {
                "names": ["kitsu", "kitsu-chan", "kitsu-san"],
                "questions": ["?", "what", "when", "where", "who", "why", "how", "is", "are", "can", "could", "would"]
            },
            "spam_detection": {
                "check_last_n_inputs": 3,
                "normalization_regex": "[^a-zA-Z0-9]",
                "similarity_threshold": 0.9
            },
            "system_events": {
                "click": {"reaction": "jump", "priority": 3},
                "install": {"reaction": "giggle", "priority": 5},
                "delete": {"reaction": "pout", "priority": 9},
                "notification": {"reaction": "jump", "priority": 2}
            },
            "reactions": {
                "blush": {"animation": "blush_face"},
                "pout": {"animation": "pout_face"},
                "glare": {"animation": "angry_stare"},
                "giggle": {"animation": "happy_bounce"},
                "jump": {"animation": "surprised_jump"}
            }
        }
    
    def _detect_emotional_trigger(
        self,
        user_input: str,
        emotion_state: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Detect if user input triggers an emotional reaction using new triggers.json structure.
        
        Args:
            user_input: User text input
            emotion_state: Current emotion state
        
        Returns:
            Reaction type (blush, pout, glare, etc.) or None
        """
        input_lower = user_input.lower()
        
        # Check symbol triggers first
        symbols = self.triggers.get("symbols", {})
        for symbol, trigger_name in symbols.items():
            if symbol in user_input:
                trigger_config = self.triggers.get("triggers", {}).get(trigger_name, {})
                return self._get_reaction_from_trigger(trigger_config, emotion_state)
        
        # Check keyword triggers
        triggers = self.triggers.get("triggers", {})
        for trigger_name, trigger_config in triggers.items():
            keywords = trigger_config.get("keywords", [])
            
            # Check cooldown
            cooldown = trigger_config.get("cooldown", 0.0)
            if cooldown > 0:
                # Skip if on cooldown (would need state tracking for proper implementation)
                pass
            
            if any(keyword in input_lower for keyword in keywords):
                return self._get_reaction_from_trigger(trigger_config, emotion_state)
        
        return None
    
    def _get_reaction_from_trigger(
        self, 
        trigger_config: Dict[str, Any], 
        emotion_state: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Get appropriate reaction from trigger configuration based on emotion state.
        
        Args:
            trigger_config: Trigger configuration from triggers.json
            emotion_state: Current emotion state
        
        Returns:
            Reaction type or None
        """
        reactions = trigger_config.get("reaction", {})
        
        if isinstance(reactions, str):
            # Simple string reaction
            return reactions
        elif isinstance(reactions, dict):
            # Complex reaction with conditions
            if emotion_state:
                # Check for conditional reactions based on emotion state
                edge = emotion_state.get("edge", 0.0)
                if edge > 0.7 and "high_edge" in reactions:
                    return reactions["high_edge"]
            
            # Return default reaction if available
            return reactions.get("default")
        
        return None
    
    def should_respond(
        self,
        behavior_decision: BehaviorDecision,
        emotion_state: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if Kitsu should generate a text response.
        
        Args:
            behavior_decision: Behavior decision
            emotion_state: Current emotion state
        
        Returns:
            True if response should be generated
        """
        if behavior_decision.response_required:
            return True
        
        # Don't respond in sleep mode
        if behavior_decision.behavior_type == BehaviorType.SLEEP:
            return False
        
        # Don't respond to ignored events
        if behavior_decision.behavior_type == BehaviorType.IGNORE:
            return False
        
        # Respond to user input and check-ins
        return behavior_decision.behavior_type in {
            BehaviorType.RESPOND,
            BehaviorType.CHECK_IN
        }
    
    def get_behavior_priority(self, behavior_decision: BehaviorDecision) -> int:
        """
        Get priority of behavior decision.
        
        Args:
            behavior_decision: Behavior decision
        
        Returns:
            Priority value (higher = more urgent)
        """
        return behavior_decision.priority
