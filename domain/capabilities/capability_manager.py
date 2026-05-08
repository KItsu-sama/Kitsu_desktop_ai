"""
domain/capabilities/capability_manager.py

Capability sandbox system for Kitsu's safety.

This system prevents dangerous operations by requiring explicit permission
for sensitive capabilities like file access, desktop control, and system changes.
"""

import time
import logging
import json
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


class Capability(Enum):
    """System capabilities that require permission."""
    
    # File system
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    EXECUTE_PROGRAMS = "execute_programs"
    
    # Network
    WEB_SEARCH = "web_search"
    NETWORK_REQUESTS = "network_requests"
    
    # Desktop/System
    CONTROL_WINDOWS = "control_windows"
    SHUTDOWN_PC = "shutdown_pc"
    CONTROL_BROWSER = "control_browser"
    MONITOR_POWER = "monitor_power"
    SYSTEM_SETTINGS = "system_settings"
    
    # Privacy
    ACCESS_CAMERA = "access_camera"
    ACCESS_MICROPHONE = "access_microphone"
    READ_CLIPBOARD = "read_clipboard"
    WRITE_CLIPBOARD = "write_clipboard"
    
    # Automation
    DESKTOP_AUTOMATION = "desktop_automation"
    SCHEDULING = "scheduling"


class PermissionLevel(Enum):
    """Permission levels for capabilities."""
    DENIED = "denied"
    PROMPT = "prompt"  # Ask user each time
    TEMPORARY = "temporary"  # Granted for limited time
    GRANTED = "granted"  # Permanent permission


@dataclass
class PermissionContext:
    """Context for a permission request."""
    capability: Capability
    requested_by: str  # Module/plugin name
    reason: str
    scope: Optional[str] = None  # e.g., specific file path
    duration: Optional[float] = None  # For temporary grants
    urgency: str = "normal"  # low, normal, high, critical


@dataclass
class AuditEntry:
    """Audit log entry for capability usage."""
    timestamp: float
    capability: Capability
    requested_by: str
    granted: bool
    reason: str
    scope: Optional[str]
    decision_by: str  # user, auto, denied


@dataclass
class CapabilityRule:
    """Rule for capability access."""
    capability: Capability
    level: PermissionLevel
    scope_patterns: List[str] = field(default_factory=list)
    max_duration: Optional[float] = None
    requires_reason: bool = True
    auto_grant_conditions: List[str] = field(default_factory=list)


class CapabilityManager:
    """
    Manages capability permissions and access control.
    
    Features:
    - Permission prompts and temporary grants
    - Scope-based access control
    - Comprehensive audit logging
    - Risk assessment and auto-grant rules
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.permissions: Dict[Capability, PermissionLevel] = {}
        self.temporary_grants: Dict[Capability, float] = {}  # capability -> expiry
        self.scope_permissions: Dict[str, Set[Capability]] = {}  # scope -> capabilities
        self.audit_log: List[AuditEntry] = []
        self.rules: Dict[Capability, CapabilityRule] = {}
        
        # Permission prompt callbacks
        self.prompt_callback: Optional[Callable[[PermissionContext], bool]] = None
        
        # Default permissions - conservative
        self._setup_default_permissions()
        
        if config_path:
            self.load_config(config_path)
    
    def _setup_default_permissions(self):
        """Setup conservative default permissions."""
        # High-risk capabilities - always prompt
        high_risk = [
            Capability.DELETE_FILES,
            Capability.SHUTDOWN_PC,
            Capability.SYSTEM_SETTINGS,
            Capability.EXECUTE_PROGRAMS,
        ]
        
        # Medium-risk capabilities - prompt for new scopes
        medium_risk = [
            Capability.WRITE_FILES,
            Capability.CONTROL_WINDOWS,
            Capability.CONTROL_BROWSER,
            Capability.DESKTOP_AUTOMATION,
        ]
        
        # Low-risk capabilities - can be auto-granted
        low_risk = [
            Capability.READ_FILES,
            Capability.WEB_SEARCH,
            Capability.NETWORK_REQUESTS,
            Capability.MONITOR_POWER,
        ]
        
        # Privacy-sensitive - always prompt
        privacy_sensitive = [
            Capability.ACCESS_CAMERA,
            Capability.ACCESS_MICROPHONE,
            Capability.READ_CLIPBOARD,
            Capability.WRITE_CLIPBOARD,
        ]
        
        for cap in high_risk:
            self.permissions[cap] = PermissionLevel.PROMPT
            self.rules[cap] = CapabilityRule(
                capability=cap,
                level=PermissionLevel.PROMPT,
                requires_reason=True
            )
        
        for cap in medium_risk:
            self.permissions[cap] = PermissionLevel.PROMPT
            self.rules[cap] = CapabilityRule(
                capability=cap,
                level=PermissionLevel.PROMPT,
                max_duration=300.0,  # 5 minutes max
                requires_reason=True
            )
        
        for cap in low_risk:
            self.permissions[cap] = PermissionLevel.TEMPORARY
            self.rules[cap] = CapabilityRule(
                capability=cap,
                level=PermissionLevel.TEMPORARY,
                max_duration=60.0,  # 1 minute
                requires_reason=False
            )
        
        for cap in privacy_sensitive:
            self.permissions[cap] = PermissionLevel.PROMPT
            self.rules[cap] = CapabilityRule(
                capability=cap,
                level=PermissionLevel.PROMPT,
                requires_reason=True
            )
    
    def set_prompt_callback(self, callback: Callable[[PermissionContext], bool]):
        """Set callback for permission prompts."""
        self.prompt_callback = callback
    
    def check_permission(
        self,
        capability: Capability,
        requested_by: str,
        reason: str = "",
        scope: Optional[str] = None
    ) -> bool:
        """
        Check if a capability is permitted.
        
        Args:
            capability: The capability being requested
            requested_by: Module/plugin name requesting access
            reason: Reason for the request
            scope: Optional scope (e.g., file path)
            
        Returns:
            True if permission granted, False otherwise
        """
        # Clean up expired temporary grants
        self._cleanup_expired_grants()
        
        # Check scope-specific permissions first
        if scope and self._check_scope_permission(capability, scope):
            self._log_audit(capability, requested_by, True, reason, scope, "scope")
            return True
        
        # Check temporary grants
        if capability in self.temporary_grants:
            self._log_audit(capability, requested_by, True, reason, scope, "temporary")
            return True
        
        # Check base permission level
        level = self.permissions.get(capability, PermissionLevel.PROMPT)
        
        if level == PermissionLevel.GRANTED:
            self._log_audit(capability, requested_by, True, reason, scope, "granted")
            return True
        
        elif level == PermissionLevel.TEMPORARY:
            # Auto-grant temporary with default duration
            rule = self.rules.get(capability)
            duration = rule.max_duration if rule else 60.0
            self.grant_temporary(capability, duration)
            self._log_audit(capability, requested_by, True, reason, scope, "auto_temporary")
            return True
        
        elif level == PermissionLevel.PROMPT:
            return self._prompt_for_permission(
                PermissionContext(
                    capability=capability,
                    requested_by=requested_by,
                    reason=reason or f"Access requested by {requested_by}",
                    scope=scope
                )
            )
        
        else:  # DENIED
            self._log_audit(capability, requested_by, False, reason, scope, "denied")
            return False
    
    def _prompt_for_permission(self, context: PermissionContext) -> bool:
        """Prompt user for permission."""
        if self.prompt_callback:
            granted = self.prompt_callback(context)
            self._log_audit(
                context.capability,
                context.requested_by,
                granted,
                context.reason,
                context.scope,
                "user"
            )
            return granted
        
        # No prompt callback - default to deny for safety
        log.warning(f"No prompt callback set for {context.capability.value} - denying")
        self._log_audit(
            context.capability,
            context.requested_by,
            False,
            context.reason,
            context.scope,
            "no_callback"
        )
        return False
    
    def grant_temporary(self, capability: Capability, duration: float) -> None:
        """Grant temporary permission for specified duration."""
        expiry = time.time() + duration
        self.temporary_grants[capability] = expiry
        log.info(f"Temporary grant: {capability.value} for {duration}s")
    
    def grant_permanent(self, capability: Capability) -> None:
        """Grant permanent permission."""
        self.permissions[capability] = PermissionLevel.GRANTED
        log.info(f"Permanent grant: {capability.value}")
    
    def deny_capability(self, capability: Capability) -> None:
        """Deny a capability permanently."""
        self.permissions[capability] = PermissionLevel.DENIED
        log.info(f"Capability denied: {capability.value}")
    
    def set_scope_permission(self, scope: str, capabilities: List[Capability]) -> None:
        """Set permissions for a specific scope (e.g., directory)."""
        self.scope_permissions[scope] = set(capabilities)
        log.info(f"Scope permissions set for {scope}: {[c.value for c in capabilities]}")
    
    def _check_scope_permission(self, capability: Capability, scope: str) -> bool:
        """Check if capability is allowed for specific scope."""
        for scope_pattern, allowed_caps in self.scope_permissions.items():
            if scope.startswith(scope_pattern) and capability in allowed_caps:
                return True
        return False
    
    def _cleanup_expired_grants(self) -> None:
        """Remove expired temporary grants."""
        now = time.time()
        expired = [cap for cap, expiry in self.temporary_grants.items() if expiry <= now]
        for cap in expired:
            del self.temporary_grants[cap]
            log.debug(f"Temporary grant expired: {cap.value}")
    
    def _log_audit(
        self,
        capability: Capability,
        requested_by: str,
        granted: bool,
        reason: str,
        scope: Optional[str],
        decision_by: str
    ) -> None:
        """Log audit entry."""
        entry = AuditEntry(
            timestamp=time.time(),
            capability=capability,
            requested_by=requested_by,
            granted=granted,
            reason=reason,
            scope=scope,
            decision_by=decision_by
        )
        self.audit_log.append(entry)
        
        # Keep audit log manageable
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]
        
        log.debug(f"Audit: {capability.value} by {requested_by} -> {granted} ({decision_by})")
    
    def get_risk_score(self, capability: Capability) -> float:
        """Get risk score for capability (0.0 - 1.0)."""
        high_risk = {
            Capability.DELETE_FILES,
            Capability.SHUTDOWN_PC,
            Capability.SYSTEM_SETTINGS,
            Capability.EXECUTE_PROGRAMS,
            Capability.ACCESS_CAMERA,
            Capability.ACCESS_MICROPHONE,
        }
        
        medium_risk = {
            Capability.WRITE_FILES,
            Capability.CONTROL_WINDOWS,
            Capability.CONTROL_BROWSER,
            Capability.DESKTOP_AUTOMATION,
            Capability.READ_CLIPBOARD,
            Capability.WRITE_CLIPBOARD,
        }
        
        if capability in high_risk:
            return 0.8
        elif capability in medium_risk:
            return 0.5
        else:
            return 0.2
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        recent = self.audit_log[-limit:]
        return [
            {
                "timestamp": entry.timestamp,
                "capability": entry.capability.value,
                "requested_by": entry.requested_by,
                "granted": entry.granted,
                "reason": entry.reason,
                "scope": entry.scope,
                "decision_by": entry.decision_by
            }
            for entry in recent
        ]
    
    def get_permission_status(self) -> Dict[str, Any]:
        """Get current permission status."""
        return {
            "permissions": {cap.value: level.value for cap, level in self.permissions.items()},
            "temporary_grants": {
                cap.value: expiry - time.time()
                for cap, expiry in self.temporary_grants.items()
            },
            "scope_permissions": {
                scope: [cap.value for cap in caps]
                for scope, caps in self.scope_permissions.items()
            }
        }
    
    def save_config(self, path: str) -> None:
        """Save configuration to file."""
        config = {
            "permissions": {cap.value: level.value for cap, level in self.permissions.items()},
            "scope_permissions": {
                scope: [cap.value for cap in caps]
                for scope, caps in self.scope_permissions.items()
            }
        }
        
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_config(self, path: str) -> None:
        """Load configuration from file."""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
            
            # Load permissions
            for cap_str, level_str in config.get("permissions", {}).items():
                try:
                    cap = Capability(cap_str)
                    level = PermissionLevel(level_str)
                    self.permissions[cap] = level
                except ValueError:
                    log.warning(f"Invalid config entry: {cap_str} = {level_str}")
            
            # Load scope permissions
            for scope, cap_list in config.get("scope_permissions", {}).items():
                try:
                    caps = [Capability(cap_str) for cap_str in cap_list]
                    self.scope_permissions[scope] = set(caps)
                except ValueError as e:
                    log.warning(f"Invalid scope permission for {scope}: {e}")
            
            log.info(f"Loaded capability config from {path}")
            
        except FileNotFoundError:
            log.info(f"Config file not found: {path} - using defaults")
        except Exception as e:
            log.error(f"Error loading config: {e}")


# Global instance
CAPABILITY_MANAGER = CapabilityManager()
