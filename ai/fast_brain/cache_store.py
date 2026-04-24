"""
=====================================
cache_store.py (The Instant Recall)
=====================================
The "Short-term Memory."

Legacy Refactor: Move any global variables you used to store "last_input" or "last_response."

Role: It stores the last 5–10 exchanges in a high-speed RAM buffer. If the user repeats a question exactly, kitsu pulls the answer from here in 0ms. This is crucial for the "Hai! -> Hai!" spam loop, where kitsu can instantly recognize and repeat the user's input without hitting the LLM.
"""

import time
import logging
from typing import List, Tuple, Optional, Dict, Any
from collections import deque

log = logging.getLogger(__name__)


class ConversationCache:
    """
    High-speed cache for recent conversation exchanges.
    
    Stores recent user inputs and responses for instant retrieval
    of repeated queries and spam detection.
    """
    
    def __init__(self, max_size: int = 10):
        """
        Initialize the conversation cache.
        
        Args:
            max_size: Maximum number of exchanges to store
        """
        self.max_size = max_size
        self.exchanges: deque = deque(maxlen=max_size)
        self.exact_matches: Dict[str, str] = {}  # input -> response mapping
        self.last_access: Dict[str, float] = {}  # Track access times
        
        # Performance stats
        self.cache_hits = 0
        self.cache_misses = 0
    
    def add_exchange(self, user_input: str, kitsu_response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a conversation exchange to the cache.
        
        Args:
            user_input: User's message
            kitsu_response: kitsu's response
            metadata: Additional metadata
        """
        exchange = {
            "user_input": user_input,
            "kitsu_response": kitsu_response,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        
        self.exchanges.append(exchange)
        
        # Update exact match cache
        normalized_input = user_input.lower().strip()
        self.exact_matches[normalized_input] = kitsu_response
        self.last_access[normalized_input] = time.time()
        
        log.debug(f"Added exchange to cache: {len(self.exchanges)}/{self.max_size}")
    
    def get_exact_match(self, user_input: str) -> Optional[str]:
        """
        Get cached response for exact input match.
        
        Args:
            user_input: User input to check
            
        Returns:
            Cached response or None
        """
        normalized_input = user_input.lower().strip()
        
        if normalized_input in self.exact_matches:
            self.cache_hits += 1
            self.last_access[normalized_input] = time.time()
            response = self.exact_matches[normalized_input]
            log.debug("Cache hit for exact match")
            return response
        
        self.cache_misses += 1
        return None
    
    def get_recent_exchanges(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent conversation exchanges.
        
        Args:
            count: Number of exchanges to return
            
        Returns:
            List of recent exchanges
        """
        return list(self.exchanges)[-count:]
    
    def is_spam_repeat(self, user_input: str, threshold: int = 3) -> bool:
        """
        Check if user input is spam based on recent repetition.
        
        Args:
            user_input: User input to check
            threshold: Number of recent repeats to consider spam
            
        Returns:
            True if input appears to be spam
        """
        normalized_input = user_input.lower().strip()
        
        # Count recent occurrences
        recent_count = 0
        for exchange in reversed(self.exchanges):
            if exchange["user_input"].lower().strip() == normalized_input:
                recent_count += 1
            else:
                break  # Only count consecutive repeats
        
        return recent_count >= threshold
    
    def get_spam_deflect_response(self, user_input: str) -> str:
        """
        Get an appropriate response for spam/repeated input.
        
        Args:
            user_input: The repeated input
            
        Returns:
            Deflect response
        """
        normalized = user_input.lower().strip()
        
        # Different responses based on input type
        if normalized in ["hai", "hai!", "heyo", "hey"]:
            responses = [
                "Hai! 😊",
                "Hai hai! ✨",
                "Hehe, hai! 🌟",
                "Hai! What's up? 💕",
            ]
        elif normalized in ["lol", "haha", "hehe"]:
            responses = [
                "Hehe! 😄",
                "Haha! 😂",
                "That's funny! 😆",
                "Hehe, you're funny! 🎭",
            ]
        else:
            responses = [
                "I heard you! 💕",
                "Got it! ✨",
                "You're enthusiastic! 🌟",
                "I see you're excited! 😊",
            ]
        
        # Rotate through responses to avoid monotony
        import random
        return random.choice(responses)
    
    def clear_old_entries(self, max_age_seconds: float = 3600) -> None:
        """
        Clear entries older than specified age.
        
        Args:
            max_age_seconds: Maximum age in seconds
        """
        current_time = time.time()
        to_remove = []
        
        for key, access_time in self.last_access.items():
            if current_time - access_time > max_age_seconds:
                to_remove.append(key)
        
        for key in to_remove:
            if key in self.exact_matches:
                del self.exact_matches[key]
            del self.last_access[key]
        
        if to_remove:
            log.debug(f"Cleared {len(to_remove)} old cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self.exchanges),
            "max_size": self.max_size,
            "exact_matches": len(self.exact_matches),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "oldest_entry_age": self._get_oldest_age(),
        }
    
    def _get_oldest_age(self) -> float:
        """Get age of oldest entry in seconds."""
        if not self.exchanges:
            return 0.0
        
        oldest_timestamp = min(exchange["timestamp"] for exchange in self.exchanges)
        return time.time() - oldest_timestamp


# Global instance
conversation_cache = ConversationCache()


def add_to_cache(user_input: str, kitsu_response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an exchange to the global cache.
    
    Args:
        user_input: User's message
        kitsu_response: kitsu's response
        metadata: Additional metadata
    """
    conversation_cache.add_exchange(user_input, kitsu_response, metadata)


def get_cached_response(user_input: str) -> Optional[str]:
    """
    Get cached response for user input.
    
    Args:
        user_input: User input
        
    Returns:
        Cached response or None
    """
    return conversation_cache.get_exact_match(user_input)


def check_spam(user_input: str) -> bool:
    """
    Check if user input is spam.
    
    Args:
        user_input: User input
        
    Returns:
        True if spam
    """
    return conversation_cache.is_spam_repeat(user_input)


def get_spam_response(user_input: str) -> str:
    """
    Get spam deflect response.
    
    Args:
        user_input: User input
        
    Returns:
        Deflect response
    """
    return conversation_cache.get_spam_deflect_response(user_input)