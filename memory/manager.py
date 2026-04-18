"""
memory/manager.py

High-level memory management interface.
Coordinates different memory stores and provides unified API.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from core.contracts import MemoryStoreContract
from memory.stores.episodic import EpisodicMemoryStore
from memory.stores.short_term import ShortTermMemoryStore
from memory.stores.vector_memory import VectorMemoryStore
from memory.stores.preferences import PreferenceStore

log = logging.getLogger('kitsu.memory.manager')


@dataclass
class MemoryConfig:
    """Configuration for memory system."""
    max_short_term: int = 100
    max_episodic: int = 1000
    max_vector_size: int = 10000
    persistence_enabled: bool = True
    data_dir: Path = Path('data/memory')


class MemoryManager:
    """Unified memory management system."""
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.stores: Dict[str, MemoryStoreContract] = {}
        self._initialized = False
        
        # Ensure data directory exists
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Initialize all memory stores."""
        if self._initialized:
            return
        
        try:
            # Initialize short-term memory
            self.stores['short_term'] = ShortTermMemoryStore(
                max_items=self.config.max_short_term,
                persistence_path=self.config.data_dir / 'short_term.json',
                cache_size=100  # Add cache size parameter
            )
            
            # Initialize episodic memory
            self.stores['episodic'] = EpisodicMemoryStore(
                max_episodes=self.config.max_episodic,
                persistence_path=self.config.data_dir / 'episodic.json'
            )
            
            # Initialize vector memory
            self.stores['vector'] = VectorMemoryStore(
                max_size=self.config.max_vector_size,
                persistence_path=self.config.data_dir / 'vector.json'
            )
            
            # Initialize preferences
            self.stores['preferences'] = PreferenceStore(
                persistence_path=self.config.data_dir / 'preferences.json'
            )
            
            # Initialize all stores
            for store_name, store in self.stores.items():
                await store.initialize()
                log.info(f"Initialized memory store: {store_name}")
            
            self._initialized = True
            log.info("Memory manager initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize memory manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all memory stores."""
        if not self._initialized:
            return
        
        try:
            for store_name, store in self.stores.items():
                await store.shutdown()
                log.info(f"Shutdown memory store: {store_name}")
            
            self._initialized = False
            log.info("Memory manager shutdown complete")
            
        except Exception as e:
            log.error(f"Error during memory manager shutdown: {e}")
    
    async def write(self, store_name: str, key: str, value: Dict) -> None:
        """Write to a specific memory store."""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        if store_name not in self.stores:
            raise ValueError(f"Unknown memory store: {store_name}")
        
        await self.stores[store_name].write(key, value)
        log.debug(f"Written to {store_name}: {key}")
    
    async def read(self, store_name: str, key: str) -> Optional[Dict]:
        """Read from a specific memory store."""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        if store_name not in self.stores:
            raise ValueError(f"Unknown memory store: {store_name}")
        
        result = await self.stores[store_name].read(key)
        log.debug(f"Read from {store_name}: {key} -> {result is not None}")
        return result
    
    async def search(self, store_name: str, query: str, top_k: int = 5) -> List[Dict]:
        """Search in a specific memory store."""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        if store_name not in self.stores:
            raise ValueError(f"Unknown memory store: {store_name}")
        
        results = await self.stores[store_name].search(query, top_k)
        log.debug(f"Searched {store_name} for '{query}': {len(results)} results")
        return results
    
    async def clear(self, store_name: Optional[str] = None) -> None:
        """Clear memory store(s)."""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        if store_name:
            if store_name not in self.stores:
                raise ValueError(f"Unknown memory store: {store_name}")
            
            await self.stores[store_name].clear()
            log.info(f"Cleared memory store: {store_name}")
        else:
            # Clear all stores
            for name, store in self.stores.items():
                await store.clear()
                log.info(f"Cleared memory store: {name}")
    
    async def consolidate(self) -> None:
        """Consolidate memories between stores."""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        try:
            # Move old items from short-term to episodic
            short_term_items = await self.stores['short_term'].search("", 1000)
            
            for item in short_term_items:
                # Check if item should be promoted to episodic memory
                if self._should_promote_to_episodic(item):
                    await self.stores['episodic'].write(
                        f"ep_{item.get('timestamp', 0)}_{item.get('key', 'unknown')}",
                        item
                    )
                    # Remove from short-term
                    await self.stores['short_term'].write(item.get('key', ''), None)
            
            log.info("Memory consolidation completed")
            
        except Exception as e:
            log.error(f"Memory consolidation failed: {e}")
    
    def _should_promote_to_episodic(self, item: Dict) -> bool:
        """Determine if an item should be promoted to episodic memory."""
        # Promote items older than 1 hour or marked as important
        import time
        current_time = time.time()
        item_time = item.get('timestamp', current_time)
        
        # Age-based promotion
        if current_time - item_time > 3600:  # 1 hour
            return True
        
        # Importance-based promotion
        if item.get('importance', 0) > 0.7:
            return True
        
        # Emotional significance
        if item.get('emotional_weight', 0) > 0.5:
            return True
        
        return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status of all memory stores."""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        status = {
            "initialized": True,
            "stores": {}
        }
        
        for store_name, store in self.stores.items():
            try:
                # Get basic stats from each store
                if hasattr(store, 'get_stats'):
                    stats = await store.get_stats()
                else:
                    # Fallback: do a search to estimate size
                    all_items = await store.search("", 10000)
                    stats = {"total_items": len(all_items)}
                
                status["stores"][store_name] = stats
                
            except Exception as e:
                status["stores"][store_name] = {"error": str(e)}
                log.warning(f"Failed to get stats for {store_name}: {e}")
        
        return status
    
    def get_store(self, store_name: str) -> MemoryStoreContract:
        """Get direct access to a memory store."""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        if store_name not in self.stores:
            raise ValueError(f"Unknown memory store: {store_name}")
        
        return self.stores[store_name]


# Global instance
_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance."""
    global _global_memory_manager
    if _global_memory_manager is None:
        raise RuntimeError("Memory manager not initialized. Call initialize_memory_manager() first.")
    return _global_memory_manager


async def initialize_memory_manager(config: Optional[MemoryConfig] = None) -> MemoryManager:
    """Initialize global memory manager."""
    global _global_memory_manager
    if _global_memory_manager is not None:
        raise RuntimeError("Memory manager already initialized.")
    
    _global_memory_manager = MemoryManager(config)
    await _global_memory_manager.initialize()
    return _global_memory_manager


def reset_memory_manager() -> None:
    """Reset global memory manager (for testing)."""
    global _global_memory_manager
    _global_memory_manager = None