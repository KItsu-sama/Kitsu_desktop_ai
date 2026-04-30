"""
personality/kitsu_self_interface.py

Abstract interface for KitsuSelf to reduce coupling.

Provides a clean interface for EmotionEngine to interact with KitsuSelf
without direct dependencies on internal implementation.
"""

from typing import Protocol, Dict, Any, Optional


class KitsuSelfInterface(Protocol):
    """
    Protocol interface for KitsuSelf to reduce coupling.
    
    This defines the minimal interface that EmotionEngine needs
    from KitsuSelf, allowing for easier testing and modularity.
    """
    
    def get_reflection(self) -> Dict[str, float]:
        """
        Get the current reflection state.
        
        Returns:
            Dictionary of reflection values (0.0 - 1.0)
        """
        ...
    
    def get_mode(self) -> str:
        """
        Get the current mode.
        
        Returns:
            Current mode string
        """
        ...
    
    def get_role(self) -> str:
        """
        Get the current role.
        
        Returns:
            Current role string
        """
        ...
    
    def export_state(self) -> Dict[str, Any]:
        """
        Export current state for external consumption.
        
        Returns:
            Dictionary containing current state
        """
        ...
    
    def update_reflection(self, updates: Dict[str, float]) -> None:
        """
        Update reflection values.
        
        Args:
            updates: Dictionary of reflection updates
        """
        ...


class KitsuSelfAdapter:
    """
    Adapter to wrap existing KitsuSelf instances to the interface.
    
    This provides backward compatibility while enforcing the interface.
    """
    
    def __init__(self, kitsu_self_instance):
        self.kitsu_self = kitsu_self_instance
    
    def get_reflection(self) -> Dict[str, float]:
        """Get reflection from wrapped instance."""
        if hasattr(self.kitsu_self, 'reflection'):
            return getattr(self.kitsu_self, 'reflection', {})
        return {}
    
    def get_mode(self) -> str:
        """Get mode from wrapped instance."""
        return getattr(self.kitsu_self, 'mode', 'default')
    
    def get_role(self) -> str:
        """Get role from wrapped instance."""
        return getattr(self.kitsu_self, 'role', 'default')
    
    def export_state(self) -> Dict[str, Any]:
        """Export state from wrapped instance."""
        if hasattr(self.kitsu_self, 'export_state'):
            return self.kitsu_self.export_state()
        return {}
    
    def update_reflection(self, updates: Dict[str, float]) -> None:
        """Update reflection on wrapped instance."""
        if hasattr(self.kitsu_self, 'reflection'):
            for key, value in updates.items():
                if key in self.kitsu_self.reflection:
                    old = self.kitsu_self.reflection[key]
                    new = max(0.0, min(1.0, old + value))
                    self.kitsu_self.reflection[key] = new
