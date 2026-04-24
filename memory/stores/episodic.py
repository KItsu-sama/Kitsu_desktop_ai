"""
memory/stores/episodic.py

Episodic memory store for significant events and conversations.
Implements MemoryStoreContract.
"""

from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from core.contracts import MemoryStoreContract

log = logging.getLogger('kitsu.memory.stores.episodic')


@dataclass
class Episode:
    """Represents a single episodic memory episode."""
    id: str
    timestamp: float
    content: str
    context: Dict[str, Any]
    importance: float = 0.5
    emotional_weight: float = 0.0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class EpisodicMemoryStore(MemoryStoreContract):
    """Episodic memory with importance-based retention."""
    
    def __init__(self, max_episodes: int = 1000, persistence_path: Optional[Path] = None):
        self.max_episodes = max_episodes
        self.persistence_path = persistence_path
        self._episodes: Dict[str, Episode] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the store."""
        if self._initialized:
            return
        
        try:
            # Load from persistence if enabled
            if self.persistence_path and self.persistence_path.exists():
                with self.persistence_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for episode_id, episode_data in data.items():
                    self._episodes[episode_id] = Episode(**episode_data)
                
                log.info(f"Loaded {len(self._episodes)} episodes from {self.persistence_path}")
            
            self._initialized = True
            log.info("Episodic memory store initialized")
            
        except Exception as e:
            log.error(f"Failed to initialize episodic memory store: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the store."""
        if not self._initialized:
            return
        
        try:
            # Persist data if enabled
            if self.persistence_path:
                self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert episodes to dict for JSON serialization
                data_to_save = {}
                for episode_id, episode in self._episodes.items():
                    data_to_save[episode_id] = {
                        'id': episode.id,
                        'timestamp': episode.timestamp,
                        'content': episode.content,
                        'context': episode.context,
                        'importance': episode.importance,
                        'emotional_weight': episode.emotional_weight,
                        'tags': episode.tags
                    }
                
                with self.persistence_path.open('w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
                log.info(f"Saved {len(data_to_save)} episodes to {self.persistence_path}")
            
            self._initialized = False
            log.info("Episodic memory store shutdown")
            
        except Exception as e:
            log.error(f"Error during episodic memory store shutdown: {e}")
    
    async def write(self, key: str, value: Dict) -> None:
        """Write an episode."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        # Create episode from value
        episode = Episode(
            id=key,
            timestamp=value.get('timestamp', time.time()),
            content=value.get('content', str(value)),
            context=value.get('context', {}),
            importance=value.get('importance', 0.5),
            emotional_weight=value.get('emotional_weight', 0.0),
            tags=value.get('tags', [])
        )
        
        self._episodes[key] = episode
        
        # Enforce size limit (remove least important)
        if len(self._episodes) > self.max_episodes:
            self._evict_least_important()
    
    async def read(self, key: str) -> Optional[Dict]:
        """Read an episode by key."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        episode = self._episodes.get(key)
        if episode:
            return {
                'id': episode.id,
                'timestamp': episode.timestamp,
                'content': episode.content,
                'context': episode.context,
                'importance': episode.importance,
                'emotional_weight': episode.emotional_weight,
                'tags': episode.tags
            }
        return None
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for episodes matching query."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        if not query:
            # Return most recent episodes
            sorted_episodes = sorted(
                self._episodes.values(),
                key=lambda e: e.timestamp,
                reverse=True
            )
            return [self._episode_to_dict(ep) for ep in sorted_episodes[:top_k]]
        
        # Search and rank by relevance
        matching_episodes = []
        query_lower = query.lower()
        
        for episode in self._episodes.values():
            relevance_score = self._calculate_relevance(episode, query_lower)
            if relevance_score > 0:
                matching_episodes.append((episode, relevance_score))
        
        # Sort by relevance score, then by timestamp
        matching_episodes.sort(key=lambda x: (-x[1], -x[0].timestamp))
        
        # Return top_k results
        results = []
        for episode, _ in matching_episodes[:top_k]:
            results.append(self._episode_to_dict(episode))
        
        return results
    
    async def clear(self) -> None:
        """Clear all episodes."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        self._episodes.clear()
        log.info("Episodic memory cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        if not self._episodes:
            return {
                "total_episodes": 0,
                "max_episodes": self.max_episodes,
                "oldest_episode": None,
                "newest_episode": None,
                "average_importance": 0,
                "average_emotional_weight": 0
            }
        
        timestamps = [ep.timestamp for ep in self._episodes.values()]
        importances = [ep.importance for ep in self._episodes.values()]
        emotional_weights = [ep.emotional_weight for ep in self._episodes.values()]
        
        return {
            "total_episodes": len(self._episodes),
            "max_episodes": self.max_episodes,
            "oldest_episode": min(timestamps),
            "newest_episode": max(timestamps),
            "average_importance": sum(importances) / len(importances),
            "average_emotional_weight": sum(emotional_weights) / len(emotional_weights),
            "memory_usage_percent": (len(self._episodes) / self.max_episodes) * 100
        }
    
    def _evict_least_important(self) -> None:
        """Remove the least important episode."""
        if not self._episodes:
            return
        
        # Find episode with lowest combined score
        worst_episode = min(
            self._episodes.values(),
            key=lambda e: e.importance + e.emotional_weight
        )
        
        del self._episodes[worst_episode.id]
        log.debug(f"Evicted least important episode: {worst_episode.id}")
    
    def _calculate_relevance(self, episode: Episode, query: str) -> float:
        """Calculate relevance score for episode against query."""
        score = 0.0
        
        # Content matching
        if query in episode.content.lower():
            score += 2.0
        
        # Tag matching
        for tag in episode.tags:
            if query in tag.lower():
                score += 1.5
        
        # Context matching
        for context_value in episode.context.values():
            if isinstance(context_value, str) and query in context_value.lower():
                score += 1.0
        
        # Boost by importance and emotional weight
        score *= (1.0 + episode.importance + episode.emotional_weight)
        
        # Time decay (recent episodes get slight boost)
        age = time.time() - episode.timestamp
        if age < 3600:  # Less than 1 hour old
            score *= 1.2
        elif age < 86400:  # Less than 1 day old
            score *= 1.1
        
        return score
    
    def _episode_to_dict(self, episode: Episode) -> Dict:
        """Convert episode to dictionary representation."""
        return {
            'id': episode.id,
            'timestamp': episode.timestamp,
            'content': episode.content,
            'context': episode.context,
            'importance': episode.importance,
            'emotional_weight': episode.emotional_weight,
            'tags': episode.tags
        }