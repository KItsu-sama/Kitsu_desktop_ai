"""
memory/unified_manager.py

Unified memory management consolidating all memory systems.
This fixes memory management fragmentation by providing a single
coordinated memory system with pluggable backends.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union, Callable
from enum import Enum
from pathlib import Path
import json
import pickle

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory storage."""
    SHORT_TERM = "short_term"
    EPISODIC = "episodic"
    VECTOR = "vector"
    PREFERENCES = "preferences"
    EMOTION = "emotion"
    WORKING = "working"


class MemoryPriority(Enum):
    """Memory retention priority."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TEMPORARY = "temporary"


@dataclass
class MemoryItem:
    """Unified memory item."""
    id: str
    content: Any
    memory_type: MemoryType
    priority: MemoryPriority
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    
    def __post_init__(self):
        self.last_accessed = self.created_at
        self._calculate_size()
    
    def _calculate_size(self) -> None:
        """Calculate approximate size of the memory item."""
        try:
            if isinstance(self.content, str):
                self.size_bytes = len(self.content.encode('utf-8'))
            elif isinstance(self.content, (dict, list)):
                self.size_bytes = len(pickle.dumps(self.content))
            else:
                self.size_bytes = 64  # Default estimate
        except Exception:
            self.size_bytes = 64
    
    def access(self) -> Any:
        """Access the memory item and update tracking."""
        self.last_accessed = time.time()
        self.access_count += 1
        return self.content
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the memory item."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if memory item has a tag."""
        return tag in self.tags


@dataclass
class MemoryStats:
    """Memory system statistics."""
    total_items: int = 0
    total_size_bytes: int = 0
    by_type: Dict[MemoryType, int] = field(default_factory=lambda: {t: 0 for t in MemoryType})
    by_priority: Dict[MemoryPriority, int] = field(default_factory=lambda: {p: 0 for p in MemoryPriority})
    oldest_item: Optional[float] = None
    newest_item: Optional[float] = None
    avg_access_count: float = 0.0


class MemoryBackend:
    """Abstract memory backend interface."""
    
    def store(self, item: MemoryItem) -> bool:
        """Store a memory item."""
        raise NotImplementedError
    
    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by ID."""
        raise NotImplementedError
    
    def delete(self, item_id: str) -> bool:
        """Delete a memory item by ID."""
        raise NotImplementedError
    
    def list_by_type(self, memory_type: MemoryType) -> List[MemoryItem]:
        """List all items of a specific type."""
        raise NotImplementedError
    
    def list_by_tags(self, tags: List[str]) -> List[MemoryItem]:
        """List all items with specific tags."""
        raise NotImplementedError
    
    def cleanup(self, max_items: int, max_age: float) -> int:
        """Clean up old items, return number of items removed."""
        raise NotImplementedError
    
    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        raise NotImplementedError


class InMemoryBackend(MemoryBackend):
    """In-memory backend for fast access."""
    
    def __init__(self):
        self._items: Dict[str, MemoryItem] = {}
        self._type_index: Dict[MemoryType, Dict[str, MemoryItem]] = {t: {} for t in MemoryType}
        self._tag_index: Dict[str, Dict[str, MemoryItem]] = {}
    
    def store(self, item: MemoryItem) -> bool:
        """Store a memory item."""
        self._items[item.id] = item
        
        # Update type index
        self._type_index[item.memory_type][item.id] = item
        
        # Update tag index
        for tag in item.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = {}
            self._tag_index[tag][item.id] = item
        
        return True
    
    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by ID."""
        return self._items.get(item_id)
    
    def delete(self, item_id: str) -> bool:
        """Delete a memory item by ID."""
        item = self._items.pop(item_id, None)
        if item:
            # Remove from type index
            self._type_index[item.memory_type].pop(item_id, None)
            
            # Remove from tag indexes
            for tag in item.tags:
                self._tag_index.get(tag, {}).pop(item_id, None)
            
            return True
        return False
    
    def list_by_type(self, memory_type: MemoryType) -> List[MemoryItem]:
        """List all items of a specific type."""
        return list(self._type_index[memory_type].values())
    
    def list_by_tags(self, tags: List[str]) -> List[MemoryItem]:
        """List all items with specific tags."""
        if not tags:
            return []
        
        # Find items that have all specified tags
        candidate_items = set(self._tag_index.get(tags[0], {}).values())
        for tag in tags[1:]:
            tag_items = set(self._tag_index.get(tag, {}).values())
            candidate_items.intersection_update(tag_items)
        
        return list(candidate_items)
    
    def cleanup(self, max_items: int, max_age: float) -> int:
        """Clean up old items, return number of items removed."""
        current_time = time.time()
        items_to_remove = []
        
        # Find items to remove
        for item in self._items.values():
            if (len(self._items) > max_items and 
                item.priority == MemoryPriority.TEMPORARY) or \
               (current_time - item.created_at) > max_age:
                items_to_remove.append(item.id)
        
        # Remove items
        for item_id in items_to_remove:
            self.delete(item_id)
        
        return len(items_to_remove)
    
    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        if not self._items:
            return MemoryStats()
        
        stats = MemoryStats()
        stats.total_items = len(self._items)
        stats.total_size_bytes = sum(item.size_bytes for item in self._items.values())
        
        for item in self._items.values():
            stats.by_type[item.memory_type] += 1
            stats.by_priority[item.priority] += 1
            if stats.oldest_item is None or item.created_at < stats.oldest_item:
                stats.oldest_item = item.created_at
            if stats.newest_item is None or item.created_at > stats.newest_item:
                stats.newest_item = item.created_at
            stats.avg_access_count = sum(item.access_count for item in self._items.values()) / len(self._items)
        
        return stats


class FileBackend(MemoryBackend):
    """File-based backend for persistent storage."""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.storage_dir / "index.json"
        self._items: Dict[str, MemoryItem] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load memory index from file."""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    index_data = json.load(f)
                
                for item_id, item_data in index_data.items():
                    item = MemoryItem(
                        id=item_data['id'],
                        content=pickle.loads(item_data['content']),
                        memory_type=MemoryType(item_data['memory_type']),
                        priority=MemoryPriority(item_data['priority']),
                        tags=item_data['tags'],
                        metadata=item_data['metadata'],
                        created_at=item_data['created_at'],
                        last_accessed=item_data['last_accessed'],
                        access_count=item_data['access_count'],
                        size_bytes=item_data['size_bytes']
                    )
                    self._items[item_id] = item
                    
                logger.info(f"Loaded {len(self._items)} memory items from file")
            except Exception as e:
                logger.error(f"Failed to load memory index: {e}")
    
    def _save_index(self) -> None:
        """Save memory index to file."""
        try:
            index_data = {}
            for item_id, item in self._items.items():
                index_data[item_id] = {
                    'id': item.id,
                    'content': pickle.dumps(item.content),
                    'memory_type': item.memory_type.value,
                    'priority': item.priority.value,
                    'tags': item.tags,
                    'metadata': item.metadata,
                    'created_at': item.created_at,
                    'last_accessed': item.last_accessed,
                    'access_count': item.access_count,
                    'size_bytes': item.size_bytes
                }
            
            with open(self._index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save memory index: {e}")
    
    def store(self, item: MemoryItem) -> bool:
        """Store a memory item."""
        self._items[item.id] = item
        self._save_index()
        return True
    
    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by ID."""
        item = self._items.get(item_id)
        if item:
            item.access()
            self._save_index()
        return item
    
    def delete(self, item_id: str) -> bool:
        """Delete a memory item by ID."""
        if item_id in self._items:
            del self._items[item_id]
            self._save_index()
            return True
        return False
    
    def list_by_type(self, memory_type: MemoryType) -> List[MemoryItem]:
        """List all items of a specific type."""
        return [item for item in self._items.values() if item.memory_type == memory_type]
    
    def list_by_tags(self, tags: List[str]) -> List[MemoryItem]:
        """List all items with specific tags."""
        return [item for item in self._items.values() 
                if all(tag in item.tags for tag in tags)]
    
    def cleanup(self, max_items: int, max_age: float) -> int:
        """Clean up old items, return number of items removed."""
        current_time = time.time()
        items_to_remove = []
        
        for item in self._items.values():
            if (len(self._items) > max_items and 
                item.priority == MemoryPriority.TEMPORARY) or \
               (current_time - item.created_at) > max_age:
                items_to_remove.append(item.id)
        
        for item_id in items_to_remove:
            self.delete(item_id)
        
        return len(items_to_remove)
    
    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        if not self._items:
            return MemoryStats()
        
        stats = MemoryStats()
        stats.total_items = len(self._items)
        stats.total_size_bytes = sum(item.size_bytes for item in self._items.values())
        
        for item in self._items.values():
            stats.by_type[item.memory_type] += 1
            stats.by_priority[item.priority] += 1
            if stats.oldest_item is None or item.created_at < stats.oldest_item:
                stats.oldest_item = item.created_at
            if stats.newest_item is None or item.created_at > stats.newest_item:
                stats.newest_item = item.created_at
            stats.avg_access_count = sum(item.access_count for item in self._items.values()) / len(self._items)
        
        return stats


class UnifiedMemoryManager:
    """Unified memory manager consolidating all memory systems."""
    
    def __init__(self, backend: MemoryBackend = None):
        self.backend = backend or InMemoryBackend()
        self._cleanup_interval = 300  # 5 minutes
        self._max_items = 10000
        self._max_age = 86400  # 24 hours
        self._auto_cleanup = True
        self._last_cleanup = time.time()
    
    def store(
        self, 
        content: Any,
        memory_type: MemoryType,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store content in memory and return item ID."""
        item_id = f"{memory_type.value}_{int(time.time() * 1000)}_{hash(str(content)) % 10000}"
        
        item = MemoryItem(
            id=item_id,
            content=content,
            memory_type=memory_type,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        if self.backend.store(item):
            self._maybe_cleanup()
            return item_id
        else:
            raise RuntimeError("Failed to store memory item")
    
    def retrieve(self, item_id: str) -> Optional[Any]:
        """Retrieve content by item ID."""
        item = self.backend.retrieve(item_id)
        return item.access() if item else None
    
    def retrieve_by_type(self, memory_type: MemoryType, limit: int = 50) -> List[Any]:
        """Retrieve items by type."""
        items = self.backend.list_by_type(memory_type)
        # Sort by last accessed (most recent first)
        items.sort(key=lambda x: x.last_accessed, reverse=True)
        return [item.access() for item in items[:limit]]
    
    def retrieve_by_tags(self, tags: List[str], limit: int = 50) -> List[Any]:
        """Retrieve items by tags."""
        items = self.backend.list_by_tags(tags)
        # Sort by last accessed (most recent first)
        items.sort(key=lambda x: x.last_accessed, reverse=True)
        return [item.access() for item in items[:limit]]
    
    def delete(self, item_id: str) -> bool:
        """Delete item by ID."""
        return self.backend.delete(item_id)
    
    def search(self, query: str, memory_type: Optional[MemoryType] = None, limit: int = 20) -> List[Any]:
        """Simple text search in memory content."""
        items = []
        
        if memory_type:
            items = self.backend.list_by_type(memory_type)
        else:
            items = [item for item in self.backend._items.values()] if hasattr(self.backend, '_items')]
        
        # Simple text search
        matching_items = []
        for item in items:
            content_str = str(item.content).lower()
            if query.lower() in content_str:
                matching_items.append(item)
        
        # Sort by relevance (access count and recency)
        matching_items.sort(key=lambda x: (x.access_count, x.last_accessed), reverse=True)
        
        return [item.access() for item in matching_items[:limit]]
    
    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        return self.backend.get_stats()
    
    def cleanup(self) -> int:
        """Manually trigger cleanup, return number of items removed."""
        return self.backend.cleanup(self._max_items, self._max_age)
    
    def _maybe_cleanup(self) -> None:
        """Trigger cleanup if needed."""
        if not self._auto_cleanup:
            return
        
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            removed = self.cleanup()
            if removed > 0:
                logger.info(f"Auto-cleanup removed {removed} memory items")
            self._last_cleanup = current_time
    
    def set_cleanup_policy(self, max_items: int, max_age: int, auto_cleanup: bool = True) -> None:
        """Set cleanup policy."""
        self._max_items = max_items
        self._max_age = max_age
        self._auto_cleanup = auto_cleanup


# Global memory manager instance
_memory_manager: Optional[UnifiedMemoryManager] = None


def get_memory_manager(backend: MemoryBackend = None) -> UnifiedMemoryManager:
    """Get the global memory manager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = UnifiedMemoryManager(backend)
    return _memory_manager


def set_memory_manager(manager: UnifiedMemoryManager) -> None:
    """Set the global memory manager (for testing)."""
    global _memory_manager
    _memory_manager = manager
