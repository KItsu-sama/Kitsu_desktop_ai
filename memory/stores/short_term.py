"""
memory/stores/short_term.py

Short-term memory store for recent interactions.
Implements MemoryStoreContract.
"""

from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import OrderedDict

from core.contracts import MemoryStoreContract

log = logging.getLogger('kitsu.memory.stores.short_term')


class ShortTermMemoryStore(MemoryStoreContract):
    """In-memory short-term store with LRU eviction."""
    
    def __init__(self, max_items: int = 100, persistence_path: Optional[Path] = None):
        self.max_items = max_items
        self.persistence_path = persistence_path
        self._data: OrderedDict[str, Dict] = OrderedDict()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the store."""
        if self._initialized:
            return
        
        try:
            # Load from persistence if enabled
            if self.persistence_path and self.persistence_path.exists():
                with self.persistence_path.open('r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # Restore data in order
                for key, value in loaded_data.items():
                    self._data[key] = value
                
                log.info(f"Loaded {len(self._data)} items from {self.persistence_path}")
            
            self._initialized = True
            log.info("Short-term memory store initialized")
            
        except Exception as e:
            log.error(f"Failed to initialize short-term memory store: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the store."""
        if not self._initialized:
            return
        
        try:
            # Persist data if enabled
            if self.persistence_path:
                self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert to regular dict for JSON serialization
                data_to_save = dict(self._data)
                
                with self.persistence_path.open('w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
                log.info(f"Saved {len(data_to_save)} items to {self.persistence_path}")
            
            self._initialized = False
            log.info("Short-term memory store shutdown")
            
        except Exception as e:
            log.error(f"Error during short-term memory store shutdown: {e}")
    
    async def write(self, key: str, value: Dict) -> None:
        """Write a key-value pair."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        # Add timestamp if not present
        if 'timestamp' not in value:
            value = value.copy()
            value['timestamp'] = time.time()
        
        # Update or insert
        if key in self._data:
            # Move to end (most recent)
            del self._data[key]
        
        self._data[key] = value
        
        # Enforce size limit (LRU eviction)
        while len(self._data) > self.max_items:
            oldest_key = next(iter(self._data))
            del self._data[oldest_key]
            log.debug(f"Evicted oldest item: {oldest_key}")
    
    async def read(self, key: str) -> Optional[Dict]:
        """Read a value by key."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        value = self._data.get(key)
        
        if value:
            # Move to end (mark as recently used)
            del self._data[key]
            self._data[key] = value
        
        return value
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for items matching query."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        if not query:
            # Return all items if no query
            return list(self._data.values())[-top_k:]
        
        # Simple text search
        results = []
        query_lower = query.lower()
        
        for key, value in reversed(self._data.items()):  # Most recent first
            if self._matches_query(value, query_lower):
                results.append(value)
                if len(results) >= top_k:
                    break
        
        return results
    
    async def clear(self) -> None:
        """Clear all data."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        self._data.clear()
        log.info("Short-term memory cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        current_time = time.time()
        ages = []
        
        for value in self._data.values():
            timestamp = value.get('timestamp', current_time)
            ages.append(current_time - timestamp)
        
        return {
            "total_items": len(self._data),
            "max_items": self.max_items,
            "oldest_item_age": max(ages) if ages else 0,
            "newest_item_age": min(ages) if ages else 0,
            "average_age": sum(ages) / len(ages) if ages else 0,
            "memory_usage_percent": (len(self._data) / self.max_items) * 100
        }
    
    def _matches_query(self, item: Dict, query: str) -> bool:
        """Check if an item matches the search query."""
        # Search in common fields
        searchable_fields = ['content', 'text', 'message', 'response', 'key']
        
        for field in searchable_fields:
            if field in item and isinstance(item[field], str):
                if query in item[field].lower():
                    return True
        
        # Also search in the key if it's a string
        if 'key' in item and isinstance(item['key'], str):
            if query in item['key'].lower():
                return True
        
        return False