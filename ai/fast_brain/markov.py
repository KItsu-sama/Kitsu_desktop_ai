"""
=====================================
markov.py (The Personality Mimic)
=====================================
This is where we build the Markov Chain engine that learns from user interactions.

This handles the "Blank Slate" learning of the user's style.

Legacy Refactor: Move any randomized response logic here.

Role: It stores the state machine for words. If the user says "A," what is the probability Kisu says "B"? It's perfect for the "Hai! -> Hai!" spam loop because it tracks the transition frequency.
"""

import json
import logging
import random
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, Counter
from pathlib import Path

log = logging.getLogger(__name__)


class MarkovChain:
    """
    Markov Chain for learning user interaction patterns.
    
    Tracks transition probabilities between user inputs and Kitsu responses
    to generate contextually appropriate replies.
    """
    
    def __init__(self, order: int = 2):
        """
        Initialize Markov Chain.
        
        Args:
            order: Order of the Markov chain (n-gram size)
        """
        self.order = order
        self.transitions: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)
        self.start_tokens: Counter = Counter()
        self.end_tokens: set = set()
        
        # Learning data
        self.conversation_history: List[Tuple[str, str]] = []  # (user_input, kisu_response)
        
        # Spam detection
        self.spam_patterns: Dict[str, int] = defaultdict(int)
        self.spam_threshold = 3  # Consecutive repeats considered spam
    
    def add_transition(self, user_input: str, kisu_response: str) -> None:
        """
        Add a user input -> response transition to the chain.
        
        Args:
            user_input: User's message
            kisu_response: Kitsu's response
        """
        # Tokenize inputs
        user_tokens = self._tokenize(user_input.lower())
        response_tokens = self._tokenize(kisu_response.lower())
        
        # Add to conversation history
        self.conversation_history.append((user_input, kisu_response))
        
        # Update spam patterns
        self._update_spam_patterns(user_input)
        
        # Build transitions from user input to response
        if len(user_tokens) >= self.order:
            for i in range(len(user_tokens) - self.order + 1):
                context = tuple(user_tokens[i:i + self.order])
                next_token = response_tokens[0] if response_tokens else "<END>"
                self.transitions[context][next_token] += 1
        
        # Track start tokens
        if user_tokens:
            self.start_tokens[user_tokens[0]] += 1
        
        # Track end tokens
        if response_tokens:
            self.end_tokens.add(response_tokens[-1])
    
    def generate_response(self, user_input: str, max_length: int = 20) -> Optional[str]:
        """
        Generate a response based on learned patterns.
        
        Args:
            user_input: User's current input
            max_length: Maximum response length
            
        Returns:
            Generated response or None if no pattern found
        """
        user_tokens = self._tokenize(user_input.lower())
        
        if len(user_tokens) < self.order:
            return None
        
        # Find best matching context
        context = tuple(user_tokens[-self.order:])
        if context not in self.transitions:
            # Try with shorter context
            for i in range(self.order - 1, 0, -1):
                if len(user_tokens) >= i:
                    context = tuple(user_tokens[-i:])
                    if context in self.transitions:
                        break
            else:
                return None
        
        # Generate response using Markov chain
        response_tokens = []
        current_context = context
        
        for _ in range(max_length):
            if current_context not in self.transitions:
                break
            
            next_token = self._weighted_choice(self.transitions[current_context])
            
            if next_token == "<END>":
                break
            
            response_tokens.append(next_token)
            
            # Update context for next iteration
            current_context = current_context[1:] + (next_token,)
        
        if not response_tokens:
            return None
        
        # Convert tokens back to text
        response = " ".join(response_tokens)
        return response.capitalize()
    
    def get_spam_probability(self, user_input: str) -> float:
        """
        Calculate probability that input is spam based on repetition patterns.
        
        Args:
            user_input: User input to check
            
        Returns:
            Spam probability (0.0 to 1.0)
        """
        normalized = user_input.lower().strip()
        count = self.spam_patterns.get(normalized, 0)
        
        # Recent conversation history spam check
        recent_inputs = [inp for inp, _ in self.conversation_history[-5:]]
        recent_count = sum(1 for inp in recent_inputs if inp.lower().strip() == normalized)
        
        # Combine factors
        pattern_spam = min(1.0, count / self.spam_threshold)
        recent_spam = min(1.0, recent_count / 3.0)
        
        return max(pattern_spam, recent_spam)
    
    def has_high_confidence(self, user_input: str) -> bool:
        """
        Check if we have high confidence in generating a response.
        
        Args:
            user_input: User input
            
        Returns:
            True if confidence is high enough
        """
        user_tokens = self._tokenize(user_input.lower())
        
        if len(user_tokens) < self.order:
            return False
        
        context = tuple(user_tokens[-self.order:])
        return context in self.transitions and len(self.transitions[context]) > 2
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Remove punctuation and split
        import re
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()
    
    def _weighted_choice(self, counter: Counter) -> str:
        """Choose randomly from counter weights."""
        items = list(counter.items())
        total = sum(weight for _, weight in items)
        
        if total == 0:
            return random.choice(list(counter.keys()))
        
        r = random.uniform(0, total)
        cumulative = 0
        
        for item, weight in items:
            cumulative += weight
            if r <= cumulative:
                return item
        
        return items[-1][0]  # Fallback
    
    def _update_spam_patterns(self, user_input: str) -> None:
        """Update spam pattern tracking."""
        normalized = user_input.lower().strip()
        self.spam_patterns[normalized] += 1
    
    def save_model(self, filepath: str) -> None:
        """
        Save the Markov model to disk.
        
        Args:
            filepath: Path to save file
        """
        data = {
            "order": self.order,
            "transitions": {str(k): dict(v) for k, v in self.transitions.items()},
            "start_tokens": dict(self.start_tokens),
            "end_tokens": list(self.end_tokens),
            "spam_patterns": dict(self.spam_patterns),
            "conversation_history": self.conversation_history[-1000:],  # Keep last 1000
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log.info(f"Saved Markov model to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """
        Load the Markov model from disk.
        
        Args:
            filepath: Path to load file
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.order = data.get("order", 2)
            self.transitions = defaultdict(Counter)
            for k, v in data.get("transitions", {}).items():
                # Convert string keys back to tuples
                key_tuple = tuple(k.strip("()").replace("'", "").split(", "))
                self.transitions[key_tuple] = Counter(v)
            
            self.start_tokens = Counter(data.get("start_tokens", {}))
            self.end_tokens = set(data.get("end_tokens", []))
            self.spam_patterns = defaultdict(int, data.get("spam_patterns", {}))
            self.conversation_history = data.get("conversation_history", [])
            
            log.info(f"Loaded Markov model from {filepath}")
            
        except FileNotFoundError:
            log.warning(f"Markov model file not found: {filepath}")
        except Exception as e:
            log.error(f"Error loading Markov model: {e}")


# Global instance
markov_chain = MarkovChain()


def add_conversation(user_input: str, kisu_response: str) -> None:
    """
    Add a conversation turn to the Markov chain.
    
    Args:
        user_input: User's message
        kisu_response: Kitsu's response
    """
    markov_chain.add_transition(user_input, kisu_response)


def generate_markov_response(user_input: str) -> Optional[str]:
    """
    Generate a response using the Markov chain.
    
    Args:
        user_input: User input
        
    Returns:
        Generated response or None
    """
    return markov_chain.generate_response(user_input)


def get_spam_probability(user_input: str) -> float:
    """
    Get spam probability for user input.
    
    Args:
        user_input: User input
        
    Returns:
        Spam probability (0.0 to 1.0)
    """
    return markov_chain.get_spam_probability(user_input)