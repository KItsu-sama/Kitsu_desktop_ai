"""
system/permission_manager.py

Manages user permissions for system actions.
Category-based permissions with risk levels and confirmation requirements.
"""

from __future__ import annotations
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Set, Optional
from dataclasses import dataclass

log = logging.getLogger('kitsu.system.permission_manager')


class PermissionCategory(Enum):
    """Permission categories with different risk levels."""
    FILESYSTEM = "filesystem"
    DISPLAY = "display"
    SYSTEM = "system"
    BROWSER = "browser"
    NETWORK = "network"
    AUDIO = "audio"
    AUTOMATION = "automation"


class RiskLevel(Enum):
    """Risk levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ActionPermission:
    """Permission definition for a specific action."""
    category: PermissionCategory
    risk_level: RiskLevel
    requires_confirmation: bool
    cooldown_seconds: int = 0
    description: str = ""


class PermissionManager:
    """Manages system permissions and user consent."""
    
    # Default permission definitions
    DEFAULT_PERMISSIONS = {
        # Filesystem actions
        "file.read": ActionPermission(
            category=PermissionCategory.FILESYSTEM,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            description="Read files"
        ),
        "file.write": ActionPermission(
            category=PermissionCategory.FILESYSTEM,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            cooldown_seconds=5,
            description="Write/modify files"
        ),
        "file.delete": ActionPermission(
            category=PermissionCategory.FILESYSTEM,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            cooldown_seconds=10,
            description="Delete files"
        ),
        
        # Display actions
        "display.wallpaper": ActionPermission(
            category=PermissionCategory.DISPLAY,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            description="Change wallpaper"
        ),
        "display.overlay": ActionPermission(
            category=PermissionCategory.DISPLAY,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            description="Show desktop overlay"
        ),
        
        # System actions
        "system.sleep": ActionPermission(
            category=PermissionCategory.SYSTEM,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            cooldown_seconds=30,
            description="Put system to sleep"
        ),
        "system.shutdown": ActionPermission(
            category=PermissionCategory.SYSTEM,
            risk_level=RiskLevel.CRITICAL,
            requires_confirmation=True,
            cooldown_seconds=60,
            description="Shutdown system"
        ),
        "system.monitor_off": ActionPermission(
            category=PermissionCategory.SYSTEM,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            description="Turn off monitor"
        ),
        
        # Browser actions
        "browser.tab_hide": ActionPermission(
            category=PermissionCategory.BROWSER,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            description="Hide browser tabs"
        ),
        "browser.tab_crop": ActionPermission(
            category=PermissionCategory.BROWSER,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            cooldown_seconds=5,
            description="Crop browser tabs"
        ),
        
        # Network actions
        "network.search": ActionPermission(
            category=PermissionCategory.NETWORK,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            description="Web search"
        ),
        "network.request": ActionPermission(
            category=PermissionCategory.NETWORK,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False,
            description="HTTP requests"
        ),
        
        # Audio actions
        "audio.microphone": ActionPermission(
            category=PermissionCategory.AUDIO,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            cooldown_seconds=10,
            description="Access microphone"
        ),
        "audio.play": ActionPermission(
            category=PermissionCategory.AUDIO,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            description="Play audio"
        ),
        
        # Automation actions
        "automation.keyboard": ActionPermission(
            category=PermissionCategory.AUTOMATION,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            cooldown_seconds=30,
            description="Keyboard automation"
        ),
        "automation.mouse": ActionPermission(
            category=PermissionCategory.AUTOMATION,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            cooldown_seconds=30,
            description="Mouse automation"
        ),
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path('data/config/permissions.json')
        self.enabled_categories: Set[PermissionCategory] = set()
        self.custom_permissions: Dict[str, ActionPermission] = {}
        self.action_history: Dict[str, float] = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load permission configuration from file."""
        try:
            if self.config_path.exists():
                with self.config_path.open('r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Load enabled categories
                for cat_str in config.get('enabled_categories', []):
                    try:
                        cat = PermissionCategory(cat_str)
                        self.enabled_categories.add(cat)
                    except ValueError:
                        log.warning(f"Unknown permission category: {cat_str}")
                
                # Load custom permissions
                for action, perm_data in config.get('custom_permissions', {}).items():
                    try:
                        self.custom_permissions[action] = ActionPermission(
                            category=PermissionCategory(perm_data['category']),
                            risk_level=RiskLevel(perm_data['risk_level']),
                            requires_confirmation=perm_data['requires_confirmation'],
                            cooldown_seconds=perm_data.get('cooldown_seconds', 0),
                            description=perm_data.get('description', '')
                        )
                    except (KeyError, ValueError) as e:
                        log.warning(f"Invalid custom permission {action}: {e}")
                
                log.info(f"Loaded permissions from {self.config_path}")
            else:
                # Set default enabled categories
                self.enabled_categories = {
                    PermissionCategory.DISPLAY,
                    PermissionCategory.NETWORK
                }
                self._save_config()
                
        except Exception as e:
            log.error(f"Failed to load permissions config: {e}")
            # Use defaults
            self.enabled_categories = {
                PermissionCategory.DISPLAY,
                PermissionCategory.NETWORK
            }
    
    def _save_config(self) -> None:
        """Save permission configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                'enabled_categories': [cat.value for cat in self.enabled_categories],
                'custom_permissions': {
                    action: {
                        'category': perm.category.value,
                        'risk_level': perm.risk_level.value,
                        'requires_confirmation': perm.requires_confirmation,
                        'cooldown_seconds': perm.cooldown_seconds,
                        'description': perm.description
                    }
                    for action, perm in self.custom_permissions.items()
                }
            }
            
            with self.config_path.open('w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            log.error(f"Failed to save permissions config: {e}")
    
    def enable_category(self, category: PermissionCategory) -> None:
        """Enable a permission category."""
        self.enabled_categories.add(category)
        self._save_config()
        log.info(f"Enabled permission category: {category.value}")
    
    def disable_category(self, category: PermissionCategory) -> None:
        """Disable a permission category."""
        self.enabled_categories.discard(category)
        self._save_config()
        log.info(f"Disabled permission category: {category.value}")
    
    def is_category_enabled(self, category: PermissionCategory) -> bool:
        """Check if a permission category is enabled."""
        return category in self.enabled_categories
    
    def get_permission(self, action: str) -> ActionPermission:
        """Get permission definition for an action."""
        # Check custom permissions first
        if action in self.custom_permissions:
            return self.custom_permissions[action]
        
        # Check default permissions
        if action in self.DEFAULT_PERMISSIONS:
            return self.DEFAULT_PERMISSIONS[action]
        
        # Unknown action - assume high risk
        return ActionPermission(
            category=PermissionCategory.SYSTEM,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            description=f"Unknown action: {action}"
        )
    
    def is_permitted(self, action: str) -> bool:
        """Check if an action is permitted."""
        permission = self.get_permission(action)
        
        # Check if category is enabled
        if not self.is_category_enabled(permission.category):
            return False
        
        # Check cooldown
        if self._is_in_cooldown(action, permission.cooldown_seconds):
            return False
        
        return True
    
    def requires_confirmation(self, action: str) -> bool:
        """Check if an action requires user confirmation."""
        permission = self.get_permission(action)
        return permission.requires_confirmation
    
    def can_execute(self, action: str) -> tuple[bool, str]:
        """
        Check if an action can be executed.
        Returns (can_execute, reason)
        """
        permission = self.get_permission(action)
        
        # Check category
        if not self.is_category_enabled(permission.category):
            return False, f"Permission category {permission.category.value} is disabled"
        
        # Check cooldown
        if self._is_in_cooldown(action, permission.cooldown_seconds):
            remaining = int(permission.cooldown_seconds - (self.action_history.get(action, 0)))
            return False, f"Action in cooldown ({remaining}s remaining)"
        
        return True, "Permitted"
    
    def record_action(self, action: str) -> None:
        """Record that an action was executed."""
        import time
        self.action_history[action] = time.time()
    
    def _is_in_cooldown(self, action: str, cooldown_seconds: int) -> bool:
        """Check if action is in cooldown period."""
        if cooldown_seconds <= 0:
            return False
        
        import time
        last_time = self.action_history.get(action, 0)
        return (time.time() - last_time) < cooldown_seconds
    
    def get_status(self) -> Dict:
        """Get current permission status."""
        return {
            'enabled_categories': [cat.value for cat in self.enabled_categories],
            'total_categories': len(PermissionCategory),
            'custom_permissions_count': len(self.custom_permissions),
            'recent_actions': len(self.action_history)
        }
    
    def add_custom_permission(self, action: str, permission: ActionPermission) -> None:
        """Add a custom permission."""
        self.custom_permissions[action] = permission
        self._save_config()
        log.info(f"Added custom permission for {action}")
    
    def remove_custom_permission(self, action: str) -> None:
        """Remove a custom permission."""
        if action in self.custom_permissions:
            del self.custom_permissions[action]
            self._save_config()
            log.info(f"Removed custom permission for {action}")


# Global instance
_global_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get global permission manager instance."""
    global _global_permission_manager
    if _global_permission_manager is None:
        _global_permission_manager = PermissionManager()
    return _global_permission_manager


def initialize_permission_manager(config_path: Optional[Path] = None) -> PermissionManager:
    """Initialize global permission manager."""
    global _global_permission_manager
    if _global_permission_manager is not None:
        raise RuntimeError("Permission manager already initialized.")
    
    _global_permission_manager = PermissionManager(config_path)
    return _global_permission_manager


def reset_permission_manager() -> None:
    """Reset global permission manager (for testing)."""
    global _global_permission_manager
    _global_permission_manager = None