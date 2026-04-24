"""
memory/stores/preferences.py

Preference store for user settings and learned preferences.
Implements MemoryStoreContract.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.contracts import MemoryStoreContract

log = logging.getLogger('kitsu.memory.stores.preferences')


class PreferenceStore(MemoryStoreContract):
    """Persistent preference store with default values."""
    
    def __init__(self, persistence_path: Optional[Path] = None):
        self.persistence_path = persistence_path
        self._preferences: Dict[str, Any] = {}
        self._defaults = {
            'personality.mood': 'behave',
            'personality.style': 'sweet',
            'voice.enabled': False,
            'ui.theme': 'default',
            'response.length': 'medium',
            'automation.level': 'conservative'
        }
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the store."""
        if self._initialized:
            return
        
        try:
            # Load from persistence if enabled
            if self.persistence_path and self.persistence_path.exists():
                with self.persistence_path.open('r', encoding='utf-8') as f:
                    loaded_preferences = json.load(f)
                
                # Merge with defaults
                self._preferences = {**self._defaults, **loaded_preferences}
                
                log.info(f"Loaded {len(self._preferences)} preferences from {self.persistence_path}")
            else:
                # Use defaults
                self._preferences = self._defaults.copy()
                log.info("Using default preferences")
            
            self._initialized = True
            log.info("Preference store initialized")
            
        except Exception as e:
            log.error(f"Failed to initialize preference store: {e}")
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
                    json.dump(self._preferences, f, indent=2, ensure_ascii=False)
                
                log.info(f"Saved {len(self._preferences)} preferences to {self.persistence_path}")
            
            self._initialized = False
            log.info("Preference store shutdown")
            
        except Exception as e:
            log.error(f"Error during preference store shutdown: {e}")
    
    async def write(self, key: str, value: Dict) -> None:
        """Write a preference value."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        # Handle special case for clearing preference
        if value is None:
            if key in self._preferences:
                del self._preferences[key]
                log.debug(f"Cleared preference: {key}")
            return
        
        # Extract actual value if it's wrapped
        if isinstance(value, dict) and 'value' in value:
            actual_value = value['value']
        else:
            actual_value = value
        
        self._preferences[key] = actual_value
        log.debug(f"Set preference: {key} = {actual_value}")
    
    async def read(self, key: str) -> Optional[Dict]:
        """Read a preference value."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        value = self._preferences.get(key)
        if value is not None:
            return {'value': value, 'key': key}
        return None
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for preferences matching query."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        if not query:
            # Return all preferences
            return [
                {'key': key, 'value': value}
                for key, value in self._preferences.items()
            ][:top_k]
        
        # Search in keys and values
        results = []
        query_lower = query.lower()
        
        for key, value in self._preferences.items():
            if (query_lower in key.lower() or 
                (isinstance(value, str) and query_lower in value.lower())):
                results.append({'key': key, 'value': value})
                
                if len(results) >= top_k:
                    break
        
        return results
    
    async def clear(self) -> None:
        """Clear all preferences (reset to defaults)."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        self._preferences = self._defaults.copy()
        log.info("Preferences reset to defaults")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        return {
            "total_preferences": len(self._preferences),
            "default_preferences": len(self._defaults),
            "custom_preferences": len(self._preferences) - len(self._defaults),
            "preference_keys": list(self._preferences.keys())
        }
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value synchronously."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        return self._preferences.get(key, default or self._defaults.get(key))
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set a preference value synchronously."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        self._preferences[key] = value
        log.debug(f"Set preference: {key} = {value}")
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all preferences as a copy."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        return self._preferences.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset all preferences to defaults."""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        self._preferences = self._defaults.copy()
        log.info("Reset all preferences to defaults")