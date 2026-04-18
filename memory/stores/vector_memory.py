"""
memory/stores/vector_memory.py

Vector memory store for semantic search and embeddings.
Implements MemoryStoreContract.
"""

from __future__ import annotations
import json
import logging
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from core.contracts import MemoryStoreContract

log = logging.getLogger('kitsu.memory.stores.vector_memory')


class VectorMemoryStore(MemoryStoreContract):
    """Simple vector memory with cosine similarity search."""
    
    def __init__(self, max_size: int = 10000, persistence_path: Optional[Path] = None):
        self.max_size = max_size
        self.persistence_path = persistence_path
        self._vectors: Dict[str, Tuple[List[float], Dict]] = {}  # key -> (vector, metadata)
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
                
                for key, (vector, metadata) in data.items():
                    self._vectors[key] = (vector, metadata)
                
                log.info(f"Loaded {len(self._vectors)} vectors from {self.persistence_path}")
            
            self._initialized = True
            log.info("Vector memory store initialized")
            
        except Exception as e:
            log.error(f"Failed to initialize vector memory store: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the store."""
        if not self._initialized:
            return
        
        try:
            # Persist data if enabled
            if self.persistence_path:
                self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
                
                with self.persistence_path.open('w', encoding='utf-8') as f:
                    json.dump(self._vectors, f, indent=2, ensure_ascii=False)
                
                log.info(f"Saved {len(self._vectors)} vectors to {self.persistence_path}")
            
            self._initialized = False
            log.info("Vector memory store shutdown")
            
        except Exception as e:
            log.error(f"Error during vector memory store shutdown: {e}")
    
    async def write(self, key: str, value: Dict) -> None:
        """Write a vector with metadata."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        # Extract or generate vector
        vector = value.get('vector', self._text_to_vector(value.get('content', str(value))))
        
        metadata = {
            'timestamp': value.get('timestamp', time.time()),
            'content': value.get('content', str(value)),
            'source': value.get('source', 'unknown'),
            'importance': value.get('importance', 0.5)
        }
        
        self._vectors[key] = (vector, metadata)
        
        # Enforce size limit (remove oldest)
        if len(self._vectors) > self.max_size:
            self._evict_oldest()
    
    async def read(self, key: str) -> Optional[Dict]:
        """Read vector metadata by key."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        if key in self._vectors:
            vector, metadata = self._vectors[key]
            return {
                'vector': vector,
                'metadata': metadata
            }
        return None
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar vectors."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        if not self._vectors:
            return []
        
        # Convert query to vector
        query_vector = self._text_to_vector(query)
        
        # Calculate similarities
        similarities = []
        for key, (vector, metadata) in self._vectors.items():
            similarity = self._cosine_similarity(query_vector, vector)
            similarities.append((key, similarity, metadata))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k results
        results = []
        for key, similarity, metadata in similarities[:top_k]:
            results.append({
                'key': key,
                'similarity': similarity,
                'metadata': metadata
            })
        
        return results
    
    async def clear(self) -> None:
        """Clear all vectors."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        self._vectors.clear()
        log.info("Vector memory cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        if not self._vectors:
            return {
                "total_vectors": 0,
                "max_size": self.max_size,
                "oldest_vector": None,
                "newest_vector": None,
                "average_importance": 0,
                "memory_usage_percent": 0
            }
        
        timestamps = []
        importances = []
        
        for vector, metadata in self._vectors.values():
            timestamps.append(metadata.get('timestamp', 0))
            importances.append(metadata.get('importance', 0))
        
        return {
            "total_vectors": len(self._vectors),
            "max_size": self.max_size,
            "oldest_vector": min(timestamps),
            "newest_vector": max(timestamps),
            "average_importance": sum(importances) / len(importances),
            "memory_usage_percent": (len(self._vectors) / self.max_size) * 100
        }
    
    def _text_to_vector(self, text: str) -> List[float]:
        """
        Simple text-to-vector conversion using TF-IDF-like approach.
        In production, this would use a proper embedding model.
        """
        # Simple character-based vectorization
        text = text.lower()
        vector_size = 128  # Fixed vector size
        
        # Create simple frequency-based vector
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Normalize and create vector
        vector = [0.0] * vector_size
        for i, char in enumerate(sorted(char_counts.keys())[:vector_size]):
            if i < vector_size:
                vector[i] = char_counts[char] / len(text)
        
        return vector
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        # Pad vectors to same length
        max_len = max(len(vec1), len(vec2))
        if len(vec1) < max_len:
            vec1 = vec1 + [0.0] * (max_len - len(vec1))
        if len(vec2) < max_len:
            vec2 = vec2 + [0.0] * (max_len - len(vec2))
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))
        
        # Avoid division by zero
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def _evict_oldest(self) -> None:
        """Remove the oldest vector."""
        if not self._vectors:
            return
        
        oldest_key = None
        oldest_time = float('inf')
        
        for key, (_, metadata) in self._vectors.items():
            timestamp = metadata.get('timestamp', 0)
            if timestamp < oldest_time:
                oldest_time = timestamp
                oldest_key = key
        
        if oldest_key:
            del self._vectors[oldest_key]
            log.debug(f"Evicted oldest vector: {oldest_key}")