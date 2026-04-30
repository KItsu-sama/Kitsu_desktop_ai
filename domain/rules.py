"""
personality/rules.py

Vector-based rule engine for personality modulation.

Replaces discrete state switching rules with continuous float-based adjustments.
Rules now modify personality vector dimensions rather than switching between states.

Key Changes:
- Rules operate on float values, not discrete states
- Clamp values instead of switching states
- Preserve safety constraints in continuous space
- Support gradual adjustments and thresholds
"""

import logging
from typing import Dict, List, Callable, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .vector import PersonalityVector
from .presets import get_mood_preset, get_style_preset

log = logging.getLogger(__name__)


@dataclass
class VectorRule:
    """
    A rule that modifies personality vector dimensions.
    
    Replaces discrete state changes with continuous adjustments.
    """
    name: str
    priority: int
    condition: Callable[[PersonalityVector], bool]
    adjustments: Dict[str, Tuple[float, float]]  # dimension -> (min, max)
    description: str = ""


class RuleCondition(ABC):
    """Base class for rule conditions."""
    
    @abstractmethod
    def evaluate(self, vector: PersonalityVector) -> bool:
        """Evaluate condition against personality vector."""
        pass


class ThresholdCondition(RuleCondition):
    """Condition based on dimension thresholds."""
    
    def __init__(self, dimension: str, min_val: float = 0.0, max_val: float = 1.0):
        self.dimension = dimension
        self.min_val = min_val
        self.max_val = max_val
    
    def evaluate(self, vector: PersonalityVector) -> bool:
        value = getattr(vector, self.dimension, 0.5)
        return self.min_val <= value <= self.max_val


class CombinationCondition(RuleCondition):
    """Condition based on multiple dimension combinations."""
    
    def __init__(self, conditions: List[Tuple[str, float, str]], 
                 operator: str = "and"):
        """
        Initialize combination condition.
        
        Args:
            conditions: List of (dimension, value, operator) tuples
            operator: "and" or "or" for combining conditions
        """
        self.conditions = conditions
        self.operator = operator.lower()
    
    def evaluate(self, vector: PersonalityVector) -> bool:
        results = []
        
        for dimension, value, op in self.conditions:
            current_val = getattr(vector, dimension, 0.5)
            
            if op == ">":
                results.append(current_val > value)
            elif op == "<":
                results.append(current_val < value)
            elif op == ">=":
                results.append(current_val >= value)
            elif op == "<=":
                results.append(current_val <= value)
            elif op == "==":
                results.append(abs(current_val - value) < 0.1)
            else:
                results.append(False)
        
        if self.operator == "and":
            return all(results)
        elif self.operator == "or":
            return any(results)
        else:
            return False


class VectorRuleEngine:
    """
    Rule engine that applies continuous adjustments to personality vectors.
    
    Instead of switching between discrete states, applies gradual adjustments
    to vector dimensions while respecting safety constraints.
    """
    
    def __init__(self):
        """Initialize vector rule engine."""
        self.rules: List[VectorRule] = []
        self._initialize_safety_rules()
        self._initialize_behavioral_rules()
        self._initialize_contextual_rules()
        
        # Sort rules by priority (highest first)
        self.rules.sort(key=lambda r: -r.priority)
        
        log.debug(f"VectorRuleEngine initialized with {len(self.rules)} rules")
    
    def _initialize_safety_rules(self):
        """Initialize safety constraint rules."""
        
        # Prevent excessive edge when warmth is high (don't be mean when being nice)
        self.rules.append(VectorRule(
            name="high_warmth_low_edge",
            priority=100,
            condition=CombinationCondition([
                ("warmth", 0.7, ">="),
                ("edge", 0.6, ">")
            ], operator="and"),
            adjustments={"edge": (0.0, 0.5)},
            description="Limit edge when warmth is high"
        ))
        
        # Prevent excessive chaos when protectiveness is high
        self.rules.append(VectorRule(
            name="high_protection_low_chaos",
            priority=95,
            condition=CombinationCondition([
                ("protectiveness", 0.7, ">="),
                ("chaos", 0.6, ">")
            ], operator="and"),
            adjustments={"chaos": (0.0, 0.4)},
            description="Limit chaos when protectiveness is high"
        ))
        
        # Maintain minimum warmth when affection is high
        self.rules.append(VectorRule(
            name="high_affection_min_warmth",
            priority=90,
            condition=ThresholdCondition("affection", 0.7),
            adjustments={"warmth": (0.5, 1.0)},
            description="Ensure minimum warmth with high affection"
        ))
        
        # Limit expressiveness when focus is very high
        self.rules.append(VectorRule(
            name="high_focus_low_expressiveness",
            priority=85,
            condition=CombinationCondition([
                ("focus", 0.8, ">="),
                ("expressiveness", 0.7, ">")
            ], operator="and"),
            adjustments={"expressiveness": (0.0, 0.6)},
            description="Limit expressiveness during high focus"
        ))
    
    def _initialize_behavioral_rules(self):
        """Initialize behavioral modulation rules."""
        
        # Increase verbosity with high energy and low focus
        self.rules.append(VectorRule(
            name="energy_driven_verbosity",
            priority=50,
            condition=CombinationCondition([
                ("energy", 0.7, ">="),
                ("focus", 0.4, "<")
            ], operator="and"),
            adjustments={"verbosity": (0.6, 1.0)},
            description="Increase verbosity with high energy, low focus"
        ))
        
        # Increase mystery with high edge and low warmth
        self.rules.append(VectorRule(
            name="edge_mystery_correlation",
            priority=45,
            condition=CombinationCondition([
                ("edge", 0.6, ">="),
                ("warmth", 0.4, "<")
            ], operator="and"),
            adjustments={"mystery": (0.5, 1.0)},
            description="Increase mystery with high edge, low warmth"
        ))
        
        # Boost protectiveness when user interaction suggests need
        self.rules.append(VectorRule(
            name="contextual_protection",
            priority=40,
            condition=CombinationCondition([
                ("affection", 0.6, ">="),
                ("warmth", 0.5, ">=")
            ], operator="and"),
            adjustments={"protectiveness": (0.4, 0.8)},
            description="Boost protectiveness with high affection"
        ))
    
    def _initialize_contextual_rules(self):
        """Initialize context-aware rules."""
        
        # Reduce chaos when focus needs to be high (task mode)
        self.rules.append(VectorRule(
            name="task_mode_focus",
            priority=30,
            condition=ThresholdCondition("focus", 0.8),
            adjustments={"chaos": (0.0, 0.3)},
            description="Reduce chaos during high focus"
        ))
        
        # Increase warmth when expressiveness is high (emotional expression)
        self.rules.append(VectorRule(
            name="expressive_warmth",
            priority=25,
            condition=ThresholdCondition("expressiveness", 0.7),
            adjustments={"warmth": (0.45, 1.0)},
            description="Boost warmth with high expressiveness"
        ))
        
        # Balance energy with protectiveness (don't overexert)
        self.rules.append(VectorRule(
            name="energy_protection_balance",
            priority=20,
            condition=CombinationCondition([
                ("energy", 0.8, ">="),
                ("protectiveness", 0.7, ">=")
            ], operator="and"),
            adjustments={"energy": (0.5, 0.8)},
            description="Balance energy with protectiveness"
        ))
    
    def apply_rules(self, vector: PersonalityVector, 
                   max_passes: int = 3) -> PersonalityVector:
        """
        Apply all applicable rules to personality vector.
        
        Args:
            vector: Input personality vector
            max_passes: Maximum number of rule application passes
            
        Returns:
            Modified personality vector
        """
        result = vector.copy()
        modified = True
        passes = 0
        
        while modified and passes < max_passes:
            modified = False
            passes += 1
            
            for rule in self.rules:
                if rule.condition.evaluate(result):
                    # Apply rule adjustments
                    before = result.copy()
                    result = self._apply_adjustments(result, rule.adjustments)
                    
                    # Check if anything actually changed
                    if result.distance_to(before) > 0.001:
                        modified = True
                        log.debug(f"Applied rule: {rule.name}")
        
        if passes > 1:
            log.debug(f"Rule convergence took {passes} passes")
        
        return result
    
    def _apply_adjustments(self, vector: PersonalityVector, 
                         adjustments: Dict[str, Tuple[float, float]]) -> PersonalityVector:
        """
        Apply dimension adjustments to personality vector.
        
        Args:
            vector: Input personality vector
            adjustments: Dictionary of dimension -> (min, max) adjustments
            
        Returns:
            Adjusted personality vector
        """
        result_values = {}
        
        for dimension in vector.__dataclass_fields__.keys():
            current_val = getattr(vector, dimension)
            
            if dimension in adjustments:
                min_val, max_val = adjustments[dimension]
                # Clamp to specified range
                new_val = max(min_val, min(max_val, current_val))
                result_values[dimension] = new_val
            else:
                result_values[dimension] = current_val
        
        return PersonalityVector(**result_values)
    
    def add_rule(self, rule: VectorRule):
        """
        Add a new rule to the engine.
        
        Args:
            rule: VectorRule to add
        """
        self.rules.append(rule)
        # Re-sort by priority
        self.rules.sort(key=lambda r: -r.priority)
        log.debug(f"Added rule: {rule.name} (priority {rule.priority})")
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove a rule by name.
        
        Args:
            rule_name: Name of rule to remove
            
        Returns:
            True if rule was found and removed
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        
        if len(self.rules) < original_count:
            log.debug(f"Removed rule: {rule_name}")
            return True
        else:
            log.warning(f"Rule not found for removal: {rule_name}")
            return False
    
    def get_applicable_rules(self, vector: PersonalityVector) -> List[VectorRule]:
        """
        Get list of rules that would apply to given vector.
        
        Args:
            vector: Personality vector to check
            
        Returns:
            List of applicable VectorRule objects
        """
        return [rule for rule in self.rules if rule.condition.evaluate(vector)]
    
    def get_rule_info(self) -> Dict[str, Any]:
        """
        Get information about all rules in the engine.
        
        Returns:
            Dictionary with rule information
        """
        return {
            'total_rules': len(self.rules),
            'rules_by_priority': [
                {
                    'name': rule.name,
                    'priority': rule.priority,
                    'description': rule.description,
                    'adjustments': rule.adjustments
                }
                for rule in self.rules
            ]
        }
    
    def validate_vector(self, vector: PersonalityVector) -> List[str]:
        """
        Validate personality vector against safety constraints.
        
        Args:
            vector: Personality vector to validate
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for potentially unsafe combinations
        if vector.warmth > 0.8 and vector.edge > 0.7:
            warnings.append("High warmth with high edge may create inconsistent behavior")
        
        if vector.chaos > 0.8 and vector.focus > 0.8:
            warnings.append("High chaos with high focus may create erratic behavior")
        
        if vector.protectiveness > 0.9 and vector.energy < 0.2:
            warnings.append("High protectiveness with low energy may seem lethargic")
        
        # Check for extreme values
        for dimension in vector.__dataclass_fields__.keys():
            value = getattr(vector, dimension)
            if value < 0.1:
                warnings.append(f"Very low {dimension} ({value:.2f}) may limit expressiveness")
            elif value > 0.9:
                warnings.append(f"Very high {dimension} ({value:.2f}) may be overwhelming")
        
        return warnings


# Convenience functions for rule creation
def create_threshold_rule(name: str, priority: int, dimension: str, 
                       min_val: float, max_val: float,
                       adjustments: Dict[str, Tuple[float, float]],
                       description: str = "") -> VectorRule:
    """
    Create a rule based on dimension thresholds.
    
    Args:
        name: Rule name
        priority: Rule priority
        dimension: Dimension to check
        min_val: Minimum threshold value
        max_val: Maximum threshold value
        adjustments: Dimension adjustments
        description: Rule description
        
    Returns:
        VectorRule object
    """
    condition = ThresholdCondition(dimension, min_val, max_val)
    return VectorRule(name, priority, condition, adjustments, description)


def create_combination_rule(name: str, priority: int,
                          conditions: List[Tuple[str, float, str]],
                          operator: str,
                          adjustments: Dict[str, Tuple[float, float]],
                          description: str = "") -> VectorRule:
    """
    Create a rule based on dimension combinations.
    
    Args:
        name: Rule name
        priority: Rule priority
        conditions: List of (dimension, value, operator) tuples
        operator: "and" or "or" for combining conditions
        adjustments: Dimension adjustments
        description: Rule description
        
    Returns:
        VectorRule object
    """
    condition = CombinationCondition(conditions, operator)
    return VectorRule(name, priority, condition, adjustments, description)


# Global rule engine instance
_rule_engine: Optional[VectorRuleEngine] = None


def get_rule_engine() -> VectorRuleEngine:
    """Get the global rule engine instance."""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = VectorRuleEngine()
    return _rule_engine


def apply_safety_rules(vector: PersonalityVector) -> PersonalityVector:
    """
    Apply safety rules to personality vector.
    
    Args:
        vector: Input personality vector
        
    Returns:
        Safety-checked personality vector
    """
    engine = get_rule_engine()
    return engine.apply_rules(vector)
