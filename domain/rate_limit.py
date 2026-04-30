"""
system/rate_limit.py

Rate limiting for system actions and API calls.
Prevents abuse and resource exhaustion.
"""

from __future__ import annotations
import logging
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

log = logging.getLogger('kitsu.system.rate_limit')


@dataclass
class RateLimit:
    """Rate limit configuration."""
    max_requests: int
    time_window: int  # seconds
    penalty_multiplier: float = 1.0


class RateLimiter:
    """Rate limiter with sliding windows and penalties."""
    
    # Default rate limits for different action types
    DEFAULT_LIMITS = {
        'file_operations': RateLimit(100, 3600),      # 100 ops per hour
        'network_requests': RateLimit(50, 60),         # 50 requests per minute
        'system_actions': RateLimit(10, 60),            # 10 system actions per minute
        'automation_actions': RateLimit(5, 300),        # 5 automation actions per 5 minutes
        'api_calls': RateLimit(1000, 3600),           # 1000 API calls per hour
        'user_interactions': RateLimit(20, 60),         # 20 interactions per minute
    }
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.penalties: Dict[str, float] = defaultdict(float)
        self.blocked_until: Dict[str, float] = {}
        self.limits: Dict[str, RateLimit] = self.DEFAULT_LIMITS.copy()
    
    def set_limit(self, action_type: str, max_requests: int, time_window: int) -> None:
        """Set custom rate limit for an action type."""
        self.limits[action_type] = RateLimit(max_requests, time_window)
        log.info(f"Set rate limit for {action_type}: {max_requests}/{time_window}s")
    
    def check_limit(self, action_type: str, identifier: str = "default") -> Tuple[bool, str]:
        """
        Check if action is allowed by rate limits.
        Returns (allowed, reason)
        """
        current_time = time.time()
        
        # Check if blocked due to penalty
        if action_type in self.blocked_until:
            if current_time < self.blocked_until[action_type]:
                remaining = int(self.blocked_until[action_type] - current_time)
                return False, f"Rate limited. Try again in {remaining}s"
            else:
                del self.blocked_until[action_type]
        
        # Get rate limit for action type
        if action_type not in self.limits:
            return True, "No rate limit configured"
        
        limit = self.limits[action_type]
        key = f"{action_type}:{identifier}"
        
        # Clean old requests outside time window
        while (self.requests[key] and 
               current_time - self.requests[key][0] > limit.time_window):
            self.requests[key].popleft()
        
        # Apply penalty reduction
        effective_limit = int(limit.max_requests * (1.0 - self.penalties[action_type]))
        effective_limit = max(1, effective_limit)  # At least 1 request
        
        # Check if under limit
        if len(self.requests[key]) >= effective_limit:
            # Apply penalty for exceeding limit
            self._apply_penalty(action_type)
            return False, f"Rate limit exceeded: {len(self.requests[key])}/{effective_limit}"
        
        # Record request
        self.requests[key].append(current_time)
        return True, "Allowed"
    
    def record_request(self, action_type: str, identifier: str = "default") -> None:
        """Manually record a request (for async operations)."""
        current_time = time.time()
        key = f"{action_type}:{identifier}"
        self.requests[key].append(current_time)
    
    def apply_penalty(self, action_type: str, severity: float = 0.1) -> None:
        """Apply penalty to an action type (reduces rate limit)."""
        self.penalties[action_type] = min(0.9, self.penalties[action_type] + severity)
        log.warning(f"Applied penalty to {action_type}: {self.penalties[action_type]:.2f}")
    
    def reduce_penalty(self, action_type: str, amount: float = 0.05) -> None:
        """Reduce penalty for an action type."""
        self.penalties[action_type] = max(0.0, self.penalties[action_type] - amount)
        if self.penalties[action_type] > 0:
            log.info(f"Reduced penalty for {action_type}: {self.penalties[action_type]:.2f}")
    
    def _apply_penalty(self, action_type: str) -> None:
        """Apply automatic penalty for rate limit violation."""
        limit = self.limits.get(action_type)
        if limit:
            penalty_amount = 0.1 * limit.penalty_multiplier
            self.penalties[action_type] = min(0.9, self.penalties[action_type] + penalty_amount)
            
            # Block for a short time if penalty is high
            if self.penalties[action_type] > 0.5:
                block_time = time.time() + (self.penalties[action_type] * 60)  # Up to 54 seconds
                self.blocked_until[action_type] = block_time
                log.warning(f"Blocked {action_type} due to high penalty")
    
    def get_status(self, action_type: str, identifier: str = "default") -> Dict:
        """Get current rate limit status."""
        current_time = time.time()
        key = f"{action_type}:{identifier}"
        
        if action_type not in self.limits:
            return {"status": "no_limit"}
        
        limit = self.limits[action_type]
        
        # Clean old requests
        while (self.requests[key] and 
               current_time - self.requests[key][0] > limit.time_window):
            self.requests[key].popleft()
        
        effective_limit = int(limit.max_requests * (1.0 - self.penalties[action_type]))
        effective_limit = max(1, effective_limit)
        
        # Calculate time until limit resets
        reset_time = 0
        if self.requests[key]:
            reset_time = int(limit.time_window - (current_time - self.requests[key][0]))
        
        return {
            "current_requests": len(self.requests[key]),
            "max_requests": limit.max_requests,
            "effective_limit": effective_limit,
            "time_window": limit.time_window,
            "reset_in_seconds": max(0, reset_time),
            "penalty": self.penalties[action_type],
            "blocked_until": self.blocked_until.get(action_type, 0)
        }
    
    def reset_limits(self, action_type: Optional[str] = None) -> None:
        """Reset rate limits and penalties."""
        if action_type:
            # Reset specific action type
            keys_to_remove = [k for k in self.requests.keys() if k.startswith(f"{action_type}:")]
            for key in keys_to_remove:
                del self.requests[key]
            self.penalties[action_type] = 0.0
            if action_type in self.blocked_until:
                del self.blocked_until[action_type]
            log.info(f"Reset rate limits for {action_type}")
        else:
            # Reset all
            self.requests.clear()
            self.penalties.clear()
            self.blocked_until.clear()
            log.info("Reset all rate limits")
    
    def get_all_status(self) -> Dict:
        """Get status for all action types."""
        status = {}
        for action_type in self.limits.keys():
            status[action_type] = self.get_status(action_type)
        return status


# Global instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def initialize_rate_limiter() -> RateLimiter:
    """Initialize global rate limiter."""
    global _global_rate_limiter
    if _global_rate_limiter is not None:
        raise RuntimeError("Rate limiter already initialized.")
    
    _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def reset_rate_limiter() -> None:
    """Reset global rate limiter (for testing)."""
    global _global_rate_limiter
    _global_rate_limiter = None


# Decorator for rate limiting functions
def rate_limit(action_type: str, identifier: str = "default"):
    """Decorator to rate limit function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            allowed, reason = limiter.check_limit(action_type, identifier)
            
            if not allowed:
                raise Exception(f"Rate limit exceeded: {reason}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Async decorator for rate limiting async functions
def rate_limit_async(action_type: str, identifier: str = "default"):
    """Decorator to rate limit async function calls."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            allowed, reason = limiter.check_limit(action_type, identifier)
            
            if not allowed:
                raise Exception(f"Rate limit exceeded: {reason}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator