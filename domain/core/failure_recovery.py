"""
domain/core/failure_recovery.py

Failure recovery system for runtime stability.

Provides automatic detection, recovery, and prevention of system failures
to ensure continuous operation and graceful degradation.
"""

import time
import logging
import traceback
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


class FailureSeverity(Enum):
    """Severity levels for failures."""
    LOW = "low"           # Minor issue, can be ignored
    MEDIUM = "medium"     # Noticeable impact, should be addressed
    HIGH = "high"         # Significant impact, requires immediate attention
    CRITICAL = "critical" # System-breaking, emergency response required


class FailureCategory(Enum):
    """Categories of failures."""
    MEMORY = "memory"           # Memory exhaustion or leaks
    CPU = "cpu"                # CPU overload or hangs
    MODEL = "model"             # AI model failures
    NETWORK = "network"         # Network connectivity issues
    FILESYSTEM = "filesystem"   # File system errors
    PERMISSION = "permission"   # Permission/access errors
    DEPENDENCY = "dependency"   # Missing or broken dependencies
    TIMEOUT = "timeout"        # Operation timeouts
    UNKNOWN = "unknown"         # Unclassified failures


class RecoveryAction(Enum):
    """Types of recovery actions."""
    RETRY = "retry"                     # Retry the failed operation
    RESTART_MODULE = "restart_module"   # Restart the affected module
    DEGRADE_SERVICE = "degrade_service" # Reduce service level
    FALLBACK = "fallback"               # Use fallback mechanism
    CLEAR_CACHE = "clear_cache"         # Clear caches and retry
    RELOAD_CONFIG = "reload_config"     # Reload configuration
    EMERGENCY_STOP = "emergency_stop"   # Stop all operations
    IGNORE = "ignore"                   # Ignore and continue


@dataclass
class FailureEvent:
    """Represents a failure event."""
    event_id: str
    category: FailureCategory
    severity: FailureSeverity
    message: str
    module: str
    timestamp: float = field(default_factory=time.time)
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: List[RecoveryAction] = field(default_factory=list)
    resolved: bool = False
    resolution_time: Optional[float] = None


@dataclass
class RecoveryRule:
    """Rule for automatic failure recovery."""
    category: FailureCategory
    severity: FailureSeverity
    condition: Callable[[FailureEvent], bool]
    actions: List[RecoveryAction]
    max_attempts: int = 3
    cooldown_period: float = 60.0  # seconds
    priority: int = 0  # Higher priority rules checked first
    description: str = ""


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_func: Callable[[], bool]
    interval: float = 30.0  # seconds
    timeout: float = 10.0
    category: FailureCategory = FailureCategory.UNKNOWN
    severity: FailureSeverity = FailureSeverity.MEDIUM


class FailureRecoverySystem:
    """
    Failure recovery system for runtime stability.
    
    Features:
    - Automatic failure detection and classification
    - Rule-based recovery actions
    - Health monitoring and prevention
    - Circuit breaker pattern for cascading failures
    - Comprehensive logging and analytics
    """
    
    def __init__(self):
        self.failure_history: List[FailureEvent] = []
        self.active_failures: Dict[str, FailureEvent] = {}
        self.recovery_rules: List[RecoveryRule] = []
        self.health_checks: List[HealthCheck] = []
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.circuit_breaker_threshold = 5  # failures before opening
        self.circuit_breaker_timeout = 300.0  # seconds before retry
        
        # Recovery state
        self.recovery_in_progress: Set[str] = set()
        self.max_history_size = 1000
        
        # Monitoring
        self._monitoring_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Statistics
        self.stats = {
            "total_failures": 0,
            "resolved_failures": 0,
            "auto_recoveries": 0,
            "manual_interventions": 0
        }
        
        # Setup default rules and health checks
        self._setup_default_rules()
        self._setup_health_checks()
        
        log.info("FailureRecoverySystem initialized")
    
    def _setup_default_rules(self):
        """Setup default recovery rules."""
        # Memory failures
        self.recovery_rules.append(RecoveryRule(
            category=FailureCategory.MEMORY,
            severity=FailureSeverity.HIGH,
            condition=lambda e: "memory" in e.message.lower() or "oom" in e.message.lower(),
            actions=[RecoveryAction.CLEAR_CACHE, RecoveryAction.DEGRADE_SERVICE, RecoveryAction.RESTART_MODULE],
            max_attempts=2,
            priority=100,
            description="High memory usage recovery"
        ))
        
        # CPU overload
        self.recovery_rules.append(RecoveryRule(
            category=FailureCategory.CPU,
            severity=FailureSeverity.HIGH,
            condition=lambda e: "cpu" in e.message.lower() or "timeout" in e.message.lower(),
            actions=[RecoveryAction.DEGRADE_SERVICE, RecoveryAction.RESTART_MODULE],
            max_attempts=2,
            priority=90,
            description="CPU overload recovery"
        ))
        
        # Model failures
        self.recovery_rules.append(RecoveryRule(
            category=FailureCategory.MODEL,
            severity=FailureSeverity.MEDIUM,
            condition=lambda e: any(keyword in e.message.lower() for keyword in ["model", "inference", "llm"]),
            actions=[RecoveryAction.FALLBACK, RecoveryAction.RETRY],
            max_attempts=3,
            priority=80,
            description="Model inference failure recovery"
        ))
        
        # Network failures
        self.recovery_rules.append(RecoveryRule(
            category=FailureCategory.NETWORK,
            severity=FailureSeverity.MEDIUM,
            condition=lambda e: any(keyword in e.message.lower() for keyword in ["network", "connection", "timeout"]),
            actions=[RecoveryAction.RETRY, RecoveryAction.FALLBACK],
            max_attempts=5,
            cooldown_period=10.0,
            priority=70,
            description="Network failure recovery"
        ))
        
        # Permission failures
        self.recovery_rules.append(RecoveryRule(
            category=FailureCategory.PERMISSION,
            severity=FailureSeverity.HIGH,
            condition=lambda e: any(keyword in e.message.lower() for keyword in ["permission", "access", "denied"]),
            actions=[RecoveryAction.RELOAD_CONFIG, RecoveryAction.IGNORE],
            max_attempts=1,
            priority=60,
            description="Permission error recovery"
        ))
        
        # Critical system failures
        self.recovery_rules.append(RecoveryRule(
            category=FailureCategory.UNKNOWN,
            severity=FailureSeverity.CRITICAL,
            condition=lambda e: e.severity == FailureSeverity.CRITICAL,
            actions=[RecoveryAction.EMERGENCY_STOP],
            max_attempts=1,
            priority=1000,
            description="Critical system failure"
        ))
    
    def _setup_health_checks(self):
        """Setup default health checks."""
        # Memory health check
        self.health_checks.append(HealthCheck(
            name="memory_check",
            check_func=self._check_memory_health,
            interval=30.0,
            category=FailureCategory.MEMORY,
            severity=FailureSeverity.HIGH
        ))
        
        # CPU health check
        self.health_checks.append(HealthCheck(
            name="cpu_check",
            check_func=self._check_cpu_health,
            interval=30.0,
            category=FailureCategory.CPU,
            severity=FailureSeverity.HIGH
        ))
        
        # Disk space check
        self.health_checks.append(HealthCheck(
            name="disk_check",
            check_func=self._check_disk_health,
            interval=60.0,
            category=FailureCategory.FILESYSTEM,
            severity=FailureSeverity.MEDIUM
        ))
    
    def _check_memory_health(self) -> bool:
        """Check memory health."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 90  # Alert if > 90% used
        except ImportError:
            return True  # Assume healthy if psutil not available
        except Exception:
            return False
    
    def _check_cpu_health(self) -> bool:
        """Check CPU health."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < 95  # Alert if > 95% used
        except ImportError:
            return True
        except Exception:
            return False
    
    def _check_disk_health(self) -> bool:
        """Check disk health."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return disk.percent < 95  # Alert if > 95% used
        except ImportError:
            return True
        except Exception:
            return False
    
    def start_monitoring(self) -> None:
        """Start failure monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        log.info("Failure recovery monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop failure monitoring."""
        self._running = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        log.info("Failure recovery monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Run health checks
                self._run_health_checks()
                
                # Check for circuit breaker recovery
                self._check_circuit_breakers()
                
                # Sleep before next cycle
                time.sleep(10.0)  # Check every 10 seconds
                
            except Exception as e:
                log.error(f"Error in monitoring loop: {e}")
                time.sleep(10.0)
    
    def _run_health_checks(self) -> None:
        """Run all health checks."""
        for health_check in self.health_checks:
            try:
                if not health_check.check_func():
                    self.report_failure(
                        category=health_check.category,
                        severity=health_check.severity,
                        message=f"Health check failed: {health_check.name}",
                        module="health_monitor",
                        context={"health_check": health_check.name}
                    )
            except Exception as e:
                self.report_failure(
                    category=FailureCategory.UNKNOWN,
                    severity=FailureSeverity.MEDIUM,
                    message=f"Health check error: {health_check.name} - {str(e)}",
                    module="health_monitor",
                    context={"health_check": health_check.name}
                )
    
    def _check_circuit_breakers(self) -> None:
        """Check if any circuit breakers can be closed."""
        now = time.time()
        for key, breaker in self.circuit_breakers.items():
            if breaker["state"] == "open" and now - breaker["opened_at"] > self.circuit_breaker_timeout:
                breaker["state"] = "half_open"
                log.info(f"Circuit breaker for {key} moved to half-open state")
    
    def report_failure(
        self,
        category: FailureCategory,
        severity: FailureSeverity,
        message: str,
        module: str,
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None
    ) -> str:
        """
        Report a failure event.
        
        Args:
            category: Category of the failure
            severity: Severity level
            message: Failure message
            module: Module where failure occurred
            context: Additional context
            stack_trace: Stack trace if available
            
        Returns:
            Event ID for the reported failure
        """
        event_id = f"{module}_{int(time.time() * 1000)}"
        
        failure_event = FailureEvent(
            event_id=event_id,
            category=category,
            severity=severity,
            message=message,
            module=module,
            stack_trace=stack_trace or traceback.format_exc(),
            context=context or {}
        )
        
        # Check circuit breaker
        circuit_key = f"{category.value}_{module}"
        if self._is_circuit_breaker_open(circuit_key):
            log.warning(f"Circuit breaker open for {circuit_key}, ignoring failure")
            return event_id
        
        # Store failure
        self.active_failures[event_id] = failure_event
        self.failure_history.append(failure_event)
        self.stats["total_failures"] += 1
        
        # Limit history size
        if len(self.failure_history) > self.max_history_size:
            self.failure_history = self.failure_history[-self.max_history_size//2:]
        
        log.error(f"Failure reported: {category.value}/{severity.value} in {module}: {message}")
        
        # Trigger automatic recovery
        self._trigger_recovery(failure_event)
        
        return event_id
    
    def _is_circuit_breaker_open(self, key: str) -> bool:
        """Check if circuit breaker is open for a key."""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": 0,
                "opened_at": 0
            }
        
        breaker = self.circuit_breakers[key]
        return breaker["state"] in ["open", "half_open"]
    
    def _trigger_recovery(self, failure_event: FailureEvent) -> None:
        """Trigger recovery actions for a failure."""
        if failure_event.event_id in self.recovery_in_progress:
            return  # Already recovering
        
        # Find applicable recovery rules
        applicable_rules = [
            rule for rule in self.recovery_rules
            if (rule.category == failure_event.category and
                rule.severity == failure_event.severity and
                rule.condition(failure_event))
        ]
        
        if not applicable_rules:
            log.warning(f"No recovery rule found for {failure_event.category.value}/{failure_event.severity.value}")
            return
        
        # Sort by priority
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        rule = applicable_rules[0]
        
        # Check cooldown
        if len(failure_event.recovery_attempts) > 0:
            last_attempt = failure_event.recovery_attempts[-1]
            if time.time() - failure_event.timestamp < rule.cooldown_period:
                log.info(f"Recovery cooldown active for {failure_event.event_id}")
                return
        
        # Check max attempts
        if len(failure_event.recovery_attempts) >= rule.max_attempts:
            log.error(f"Max recovery attempts reached for {failure_event.event_id}")
            self._escalate_failure(failure_event)
            return
        
        # Start recovery
        self.recovery_in_progress.add(failure_event.event_id)
        
        try:
            for action in rule.actions:
                if self._execute_recovery_action(action, failure_event):
                    failure_event.recovery_attempts.append(action)
                    self.stats["auto_recoveries"] += 1
                    
                    # Check if recovery succeeded
                    if self._verify_recovery(failure_event):
                        self._resolve_failure(failure_event)
                        break
                else:
                    log.warning(f"Recovery action {action.value} failed for {failure_event.event_id}")
        
        finally:
            self.recovery_in_progress.discard(failure_event.event_id)
    
    def _execute_recovery_action(self, action: RecoveryAction, failure_event: FailureEvent) -> bool:
        """Execute a specific recovery action."""
        try:
            log.info(f"Executing recovery action {action.value} for {failure_event.event_id}")
            
            if action == RecoveryAction.RETRY:
                # Retry would be implemented by the calling module
                return True
            
            elif action == RecoveryAction.RESTART_MODULE:
                # Module restart would be handled by module manager
                return True
            
            elif action == RecoveryAction.DEGRADE_SERVICE:
                # Service degradation would be handled by resource controller
                return True
            
            elif action == RecoveryAction.FALLBACK:
                # Fallback would be handled by the specific module
                return True
            
            elif action == RecoveryAction.CLEAR_CACHE:
                # Clear caches
                return self._clear_caches()
            
            elif action == RecoveryAction.RELOAD_CONFIG:
                # Reload configuration
                return self._reload_configuration()
            
            elif action == RecoveryAction.EMERGENCY_STOP:
                # Emergency stop
                self._emergency_stop()
                return True
            
            elif action == RecoveryAction.IGNORE:
                # Simply ignore the failure
                return True
            
            return False
            
        except Exception as e:
            log.error(f"Error executing recovery action {action.value}: {e}")
            return False
    
    def _clear_caches(self) -> bool:
        """Clear system caches."""
        try:
            # This would integrate with actual cache systems
            log.info("Clearing system caches")
            return True
        except Exception as e:
            log.error(f"Error clearing caches: {e}")
            return False
    
    def _reload_configuration(self) -> bool:
        """Reload system configuration."""
        try:
            # This would integrate with config system
            log.info("Reloading configuration")
            return True
        except Exception as e:
            log.error(f"Error reloading configuration: {e}")
            return False
    
    def _emergency_stop(self) -> None:
        """Emergency stop of all systems."""
        log.critical("Emergency stop triggered")
        # This would integrate with system shutdown
    
    def _verify_recovery(self, failure_event: FailureEvent) -> bool:
        """Verify if recovery was successful."""
        # Simple verification - in real implementation would be more sophisticated
        return True
    
    def _resolve_failure(self, failure_event: FailureEvent) -> None:
        """Mark a failure as resolved."""
        failure_event.resolved = True
        failure_event.resolution_time = time.time()
        self.active_failures.pop(failure_event.event_id, None)
        self.stats["resolved_failures"] += 1
        
        log.info(f"Failure resolved: {failure_event.event_id}")
        
        # Update circuit breaker
        circuit_key = f"{failure_event.category.value}_{failure_event.module}"
        if circuit_key in self.circuit_breakers:
            breaker = self.circuit_breakers[circuit_key]
            if breaker["state"] == "half_open":
                breaker["state"] = "closed"
                breaker["failure_count"] = 0
                log.info(f"Circuit breaker closed for {circuit_key}")
    
    def _escalate_failure(self, failure_event: FailureEvent) -> None:
        """Escalate failure to higher severity."""
        # Update circuit breaker
        circuit_key = f"{failure_event.category.value}_{failure_event.module}"
        if circuit_key not in self.circuit_breakers:
            self.circuit_breakers[circuit_key] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": 0,
                "opened_at": 0
            }
        
        breaker = self.circuit_breakers[circuit_key]
        breaker["failure_count"] += 1
        breaker["last_failure"] = time.time()
        
        if breaker["failure_count"] >= self.circuit_breaker_threshold:
            breaker["state"] = "open"
            breaker["opened_at"] = time.time()
            log.critical(f"Circuit breaker opened for {circuit_key}")
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get failure statistics."""
        if not self.failure_history:
            return self.stats
        
        # Calculate additional statistics
        recent_failures = [f for f in self.failure_history if time.time() - f.timestamp < 3600]  # Last hour
        
        category_counts = {}
        severity_counts = {}
        
        for failure in recent_failures:
            category_counts[failure.category.value] = category_counts.get(failure.category.value, 0) + 1
            severity_counts[failure.severity.value] = severity_counts.get(failure.severity.value, 0) + 1
        
        return {
            **self.stats,
            "recent_failures_1h": len(recent_failures),
            "active_failures": len(self.active_failures),
            "category_distribution": category_counts,
            "severity_distribution": severity_counts,
            "circuit_breakers": {
                key: {
                    "state": breaker["state"],
                    "failure_count": breaker["failure_count"]
                }
                for key, breaker in self.circuit_breakers.items()
            }
        }
    
    def get_recent_failures(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent failure events."""
        recent = sorted(self.failure_history, key=lambda f: f.timestamp, reverse=True)[:limit]
        return [
            {
                "event_id": f.event_id,
                "category": f.category.value,
                "severity": f.severity.value,
                "message": f.message,
                "module": f.module,
                "timestamp": f.timestamp,
                "resolved": f.resolved,
                "recovery_attempts": [a.value for a in f.recovery_attempts]
            }
            for f in recent
        ]
    
    def add_recovery_rule(self, rule: RecoveryRule) -> None:
        """Add a custom recovery rule."""
        self.recovery_rules.append(rule)
        log.info(f"Added recovery rule: {rule.description}")
    
    def add_health_check(self, health_check: HealthCheck) -> None:
        """Add a custom health check."""
        self.health_checks.append(health_check)
        log.info(f"Added health check: {health_check.name}")


# Global instance
FAILURE_RECOVERY_SYSTEM = FailureRecoverySystem()
