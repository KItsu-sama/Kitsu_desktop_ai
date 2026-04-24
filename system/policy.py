"""
system/policy.py

System-wide security and safety policies.
Enforces rules about what Kitsu can and cannot do.
"""

from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import List, Set, Optional, Dict, Any
from dataclasses import dataclass

log = logging.getLogger('kitsu.system.policy')


@dataclass(frozen=True)
class SecurityPolicy:
    """Security policy rule."""
    name: str
    description: str
    enabled: bool
    pattern: Optional[str] = None
    action: str = "block"  # block, warn, allow
    severity: str = "medium"  # low, medium, high, critical


class PolicyManager:
    """Manages system-wide security and safety policies."""
    
    # Default security policies
    DEFAULT_POLICIES = [
        SecurityPolicy(
            name="no_system_files",
            description="Block access to critical system files",
            enabled=True,
            pattern=r".*(Windows|System32|boot|etc|bin|sbin).*",
            action="block",
            severity="critical"
        ),
        SecurityPolicy(
            name="no_executable_files",
            description="Block execution of executable files",
            enabled=True,
            pattern=r".*\.(exe|bat|cmd|ps1|sh|py)$",
            action="block",
            severity="high"
        ),
        SecurityPolicy(
            name="no_sensitive_data",
            description="Block access to sensitive user data",
            enabled=True,
            pattern=r".*(password|secret|key|token|wallet|crypto).*",
            action="warn",
            severity="high"
        ),
        SecurityPolicy(
            name="no_network_automation",
            description="Block automated network requests without consent",
            enabled=True,
            action="block",
            severity="medium"
        ),
        SecurityPolicy(
            name="no_persistent_changes",
            description="Block changes to system configuration",
            enabled=True,
            pattern=r".*(registry|config|policy).*",
            action="block",
            severity="high"
        ),
        SecurityPolicy(
            name="limit_file_operations",
            description="Limit file operation frequency",
            enabled=True,
            action="warn",
            severity="medium"
        ),
        SecurityPolicy(
            name="require_confirmation_dangerous",
            description="Require confirmation for dangerous actions",
            enabled=True,
            action="block",
            severity="high"
        )
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path('data/config/policies.json')
        self.policies: Dict[str, SecurityPolicy] = {}
        self.violation_history: List[Dict[str, Any]] = []
        self.file_operation_count: Dict[str, int] = {}
        self.last_reset_time: float = 0
        
        self._load_policies()
    
    def _load_policies(self) -> None:
        """Load policies from configuration."""
        try:
            # Load default policies
            for policy in self.DEFAULT_POLICIES:
                self.policies[policy.name] = policy
            
            # Load custom policies from file
            if self.config_path.exists():
                import json
                with self.config_path.open('r', encoding='utf-8') as f:
                    config = json.load(f)
                
                for policy_data in config.get('custom_policies', []):
                    try:
                        policy = SecurityPolicy(
                            name=policy_data['name'],
                            description=policy_data['description'],
                            enabled=policy_data.get('enabled', True),
                            pattern=policy_data.get('pattern'),
                            action=policy_data.get('action', 'block'),
                            severity=policy_data.get('severity', 'medium')
                        )
                        self.policies[policy.name] = policy
                        log.info(f"Loaded custom policy: {policy.name}")
                    except (KeyError, ValueError) as e:
                        log.warning(f"Invalid policy {policy_data.get('name', 'unknown')}: {e}")
                
                # Override enabled status for default policies
                for policy_name, enabled in config.get('policy_overrides', {}).items():
                    if policy_name in self.policies:
                        self.policies[policy_name] = SecurityPolicy(
                            name=self.policies[policy_name].name,
                            description=self.policies[policy_name].description,
                            enabled=enabled,
                            pattern=self.policies[policy_name].pattern,
                            action=self.policies[policy_name].action,
                            severity=self.policies[policy_name].severity
                        )
            
            log.info(f"Loaded {len(self.policies)} security policies")
            
        except Exception as e:
            log.error(f"Failed to load policies: {e}")
            # Use defaults only
            for policy in self.DEFAULT_POLICIES:
                self.policies[policy.name] = policy
    
    def check_file_access(self, file_path: str, operation: str = "read") -> tuple[bool, str]:
        """
        Check if file access is allowed by policies.
        Returns (allowed, reason)
        """
        import time
        
        # Reset counters every hour
        current_time = time.time()
        if current_time - self.last_reset_time > 3600:
            self.file_operation_count.clear()
            self.last_reset_time = current_time
        
        # Check file operation limits
        if self.policies.get('limit_file_operations', SecurityPolicy('', '', False)).enabled:
            op_key = f"{operation}:{Path(file_path).parent}"
            self.file_operation_count[op_key] = self.file_operation_count.get(op_key, 0) + 1
            
            if self.file_operation_count[op_key] > 100:  # 100 operations per hour per directory
                return False, "Too many file operations in directory"
        
        # Check each enabled policy
        for policy in self.policies.values():
            if not policy.enabled:
                continue
            
            # Check pattern-based policies
            if policy.pattern and re.match(policy.pattern, file_path, re.IGNORECASE):
                result = self._evaluate_policy(policy, file_path, operation)
                if not result[0]:
                    return result
        
        return True, "Allowed"
    
    def check_action(self, action: str, context: Dict[str, Any] = None) -> tuple[bool, str]:
        """
        Check if an action is allowed by policies.
        Returns (allowed, reason)
        """
        context = context or {}
        
        # Check dangerous action policy
        dangerous_policy = self.policies.get('require_confirmation_dangerous')
        if dangerous_policy and dangerous_policy.enabled:
            dangerous_actions = ['delete', 'shutdown', 'restart', 'format', 'remove']
            if any(danger in action.lower() for danger in dangerous_actions):
                if not context.get('confirmed', False):
                    return False, f"Dangerous action requires confirmation: {action}"
        
        # Check network automation policy
        net_policy = self.policies.get('no_network_automation')
        if net_policy and net_policy.enabled:
            if 'network' in action.lower() and not context.get('user_initiated', False):
                return False, "Network automation requires user consent"
        
        return True, "Allowed"
    
    def _evaluate_policy(self, policy: SecurityPolicy, file_path: str, operation: str) -> tuple[bool, str]:
        """Evaluate a specific policy against file access."""
        # Record violation
        self._record_violation(policy, file_path, operation)
        
        if policy.action == "block":
            return False, f"Blocked by policy '{policy.name}': {policy.description}"
        elif policy.action == "warn":
            log.warning(f"Policy warning '{policy.name}' for {operation} on {file_path}")
            return True, f"Warning: {policy.description}"
        else:  # allow
            return True, "Allowed"
    
    def _record_violation(self, policy: SecurityPolicy, target: str, operation: str) -> None:
        """Record a policy violation."""
        import time
        
        violation = {
            'timestamp': time.time(),
            'policy': policy.name,
            'severity': policy.severity,
            'target': target,
            'operation': operation,
            'action': policy.action
        }
        
        self.violation_history.append(violation)
        
        # Keep only last 1000 violations
        if len(self.violation_history) > 1000:
            self.violation_history = self.violation_history[-1000:]
        
        log.warning(f"Policy violation: {policy.name} - {operation} on {target}")
    
    def add_policy(self, policy: SecurityPolicy) -> None:
        """Add a new security policy."""
        self.policies[policy.name] = policy
        self._save_policies()
        log.info(f"Added security policy: {policy.name}")
    
    def remove_policy(self, policy_name: str) -> None:
        """Remove a security policy."""
        if policy_name in self.policies:
            del self.policies[policy_name]
            self._save_policies()
            log.info(f"Removed security policy: {policy_name}")
    
    def enable_policy(self, policy_name: str) -> None:
        """Enable a security policy."""
        if policy_name in self.policies:
            policy = self.policies[policy_name]
            self.policies[policy_name] = SecurityPolicy(
                name=policy.name,
                description=policy.description,
                enabled=True,
                pattern=policy.pattern,
                action=policy.action,
                severity=policy.severity
            )
            self._save_policies()
            log.info(f"Enabled security policy: {policy_name}")
    
    def disable_policy(self, policy_name: str) -> None:
        """Disable a security policy."""
        if policy_name in self.policies:
            policy = self.policies[policy_name]
            self.policies[policy_name] = SecurityPolicy(
                name=policy.name,
                description=policy.description,
                enabled=False,
                pattern=policy.pattern,
                action=policy.action,
                severity=policy.severity
            )
            self._save_policies()
            log.info(f"Disabled security policy: {policy_name}")
    
    def _save_policies(self) -> None:
        """Save policies to configuration file."""
        try:
            import json
            
            custom_policies = []
            policy_overrides = {}
            
            for policy in self.policies.values():
                # Skip default policies unless overridden
                is_default = any(dp.name == policy.name for dp in self.DEFAULT_POLICIES)
                if is_default:
                    if not policy.enabled:  # Only save disabled default policies
                        policy_overrides[policy.name] = policy.enabled
                else:
                    custom_policies.append({
                        'name': policy.name,
                        'description': policy.description,
                        'enabled': policy.enabled,
                        'pattern': policy.pattern,
                        'action': policy.action,
                        'severity': policy.severity
                    })
            
            config = {
                'custom_policies': custom_policies,
                'policy_overrides': policy_overrides
            }
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config_path.open('w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            log.error(f"Failed to save policies: {e}")
    
    def get_violations(self, severity: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent policy violations."""
        violations = self.violation_history
        
        if severity:
            violations = [v for v in violations if v['severity'] == severity]
        
        return violations[-limit:]
    
    def get_policy_status(self) -> Dict[str, Any]:
        """Get current policy status."""
        enabled_count = sum(1 for p in self.policies.values() if p.enabled)
        total_violations = len(self.violation_history)
        
        # Calculate recent violations (last hour)
        import time
        current_time = time.time()
        recent_violations = len([v for v in self.violation_history 
                               if v['timestamp'] > (current_time - 3600)])
        
        return {
            'total_policies': len(self.policies),
            'enabled_policies': enabled_count,
            'total_violations': total_violations,
            'recent_violations': recent_violations,
            'file_operation_count': len(self.file_operation_count)
        }


# Global instance
_global_policy_manager: Optional[PolicyManager] = None


def get_policy_manager() -> PolicyManager:
    """Get global policy manager instance."""
    global _global_policy_manager
    if _global_policy_manager is None:
        _global_policy_manager = PolicyManager()
    return _global_policy_manager


def initialize_policy_manager(config_path: Optional[Path] = None) -> PolicyManager:
    """Initialize global policy manager."""
    global _global_policy_manager
    if _global_policy_manager is not None:
        raise RuntimeError("Policy manager already initialized.")
    
    _global_policy_manager = PolicyManager(config_path)
    return _global_policy_manager


def reset_policy_manager() -> None:
    """Reset global policy manager (for testing)."""
    global _global_policy_manager
    _global_policy_manager = None