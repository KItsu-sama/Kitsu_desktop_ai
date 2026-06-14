"""
shared/flags/budgets.py

Budget management system for Kitsu's resource allocation.

Manages latency budgets, energy budgets, and resource budgets
to balance responsiveness with system efficiency.
"""

import time
import logging
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger(__name__)


class BudgetType(Enum):
    """Types of budgets."""
    LATENCY = "latency"      # Response time budgets
    ENERGY = "energy"        # Power consumption budgets
    CPU = "cpu"             # CPU usage budgets
    MEMORY = "memory"       # Memory usage budgets
    NETWORK = "network"     # Network usage budgets
    ANIMATION = "animation"  # Animation rendering budgets


class BudgetStatus(Enum):
    """Budget status."""
    WITHIN_LIMIT = "within_limit"
    APPROACHING_LIMIT = "approaching_limit"
    EXCEEDED = "exceeded"
    CRITICAL = "critical"


@dataclass
class BudgetLimit:
    """Budget limit configuration."""
    max_value: float
    warning_threshold: float = 0.8  # Warn at 80% of limit
    critical_threshold: float = 0.95  # Critical at 95% of limit
    time_window: float = 60.0  # Time window in seconds
    auto_adjust: bool = False  # Auto-adjust based on system state


@dataclass
class BudgetEntry:
    """Single budget measurement."""
    timestamp: float
    value: float
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetState:
    """Current state of a budget."""
    current_usage: float = 0.0
    average_usage: float = 0.0
    peak_usage: float = 0.0
    status: BudgetStatus = BudgetStatus.WITHIN_LIMIT
    last_warning: float = 0.0
    entries: List[BudgetEntry] = field(default_factory=list)
    total_measurements: int = 0


class EnergyBudget:
    """Specialized budget for energy management."""
    
    def __init__(self):
        self.battery_level = 100.0
        self.power_consumption = 0.0  # Watts
        self.thermal_state = "normal"
        self.power_saving_mode = False
        self.last_update = time.time()
        
        # Energy budget limits
        self.max_power_consumption = 50.0  # Watts
        self.low_battery_threshold = 20.0  # Percent
        self.critical_battery_threshold = 10.0  # Percent
        self.thermal_threshold = 80.0  # Celsius
    
    def update_battery_info(self) -> None:
        """Update battery information."""
        try:
            battery = psutil.sensors_battery()
            if battery:
                self.battery_level = battery.percent
                self.power_saving_mode = not battery.power_plugged and self.battery_level < self.low_battery_threshold
        except Exception:
            # Battery info not available
            pass
    
    def calculate_energy_budget(self) -> float:
        """
        Calculate energy budget factor (0.0 - 1.0).
        
        Returns:
            Energy budget factor where 1.0 = full power, 0.0 = minimal power
        """
        if self.power_saving_mode:
            return 0.3
        
        if self.battery_level < self.critical_battery_threshold:
            return 0.2
        elif self.battery_level < self.low_battery_threshold:
            return 0.5
        
        # Factor in thermal state
        if self.thermal_state == "critical":
            return 0.4
        elif self.thermal_state == "high":
            return 0.7
        
        return 1.0
    
    def should_reduce_activity(self) -> bool:
        """Check if activity should be reduced to save energy."""
        return (self.power_saving_mode or 
                self.battery_level < self.critical_battery_threshold or
                self.thermal_state == "critical")


class BudgetManager:
    """
    Manages all budget types for Kitsu's resource allocation.
    
    Features:
    - Real-time budget monitoring
    - Automatic budget adjustments
    - Energy-aware resource allocation
    - Performance optimization
    """
    
    def __init__(self):
        self.budgets: Dict[BudgetType, BudgetState] = {}
        self.limits: Dict[BudgetType, BudgetLimit] = {}
        self.energy_budget = EnergyBudget()
        
        # Budget change callbacks
        self.callbacks: Dict[BudgetType, List[Callable]] = {}
        
        # Initialize budgets
        self._setup_default_budgets()
        
        # Update intervals
        self.update_interval = 1.0  # seconds
        self.last_update = 0.0
        
        log.info("BudgetManager initialized")
    
    def _setup_default_budgets(self):
        """Setup default budget configurations."""
        # Latency budgets
        self.limits[BudgetType.LATENCY] = BudgetLimit(
            max_value=2.0,  # 2 seconds max response time
            warning_threshold=0.7,  # Warn at 1.4 seconds
            critical_threshold=0.9,  # Critical at 1.8 seconds
            time_window=10.0  # 10-second window
        )
        
        # Energy budgets (handled by EnergyBudget)
        self.limits[BudgetType.ENERGY] = BudgetLimit(
            max_value=100.0,  # Percentage
            warning_threshold=0.3,  # Warn at 30%
            critical_threshold=0.1,  # Critical at 10%
            time_window=60.0,
            auto_adjust=True
        )
        
        # CPU budgets
        self.limits[BudgetType.CPU] = BudgetLimit(
            max_value=80.0,  # 80% CPU max
            warning_threshold=0.7,  # Warn at 56%
            critical_threshold=0.9,  # Critical at 72%
            time_window=30.0,
            auto_adjust=True
        )
        
        # Memory budgets
        self.limits[BudgetType.MEMORY] = BudgetLimit(
            max_value=70.0,  # 70% memory max
            warning_threshold=0.8,  # Warn at 56%
            critical_threshold=0.95,  # Critical at 66.5%
            time_window=60.0
        )
        
        # Network budgets
        self.limits[BudgetType.NETWORK] = BudgetLimit(
            max_value=1.0,  # 1MB/s max
            warning_threshold=0.8,  # Warn at 0.8MB/s
            critical_threshold=0.95,  # Critical at 0.95MB/s
            time_window=10.0
        )
        
        # Animation budgets
        self.limits[BudgetType.ANIMATION] = BudgetLimit(
            max_value=60.0,  # 60 FPS max
            warning_threshold=0.8,  # Warn at 48 FPS
            critical_threshold=0.95,  # Critical at 57 FPS
            time_window=5.0,
            auto_adjust=True
        )
        
        # Initialize budget states
        for budget_type in self.limits:
            self.budgets[budget_type] = BudgetState()
    
    def record_measurement(
        self,
        budget_type: BudgetType,
        value: float,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a budget measurement.
        
        Args:
            budget_type: Type of budget
            value: Measured value
            source: Source of measurement
            metadata: Additional metadata
        """
        if budget_type not in self.budgets:
            log.warning(f"Unknown budget type: {budget_type.value}")
            return
        
        entry = BudgetEntry(
            timestamp=time.time(),
            value=value,
            source=source,
            metadata=metadata or {}
        )
        
        state = self.budgets[budget_type]
        state.entries.append(entry)
        state.total_measurements += 1
        
        # Update statistics
        state.current_usage = value
        state.peak_usage = max(state.peak_usage, value)
        
        # Calculate average over time window
        limit = self.limits[budget_type]
        cutoff_time = time.time() - limit.time_window
        recent_entries = [e for e in state.entries if e.timestamp >= cutoff_time]
        
        if recent_entries:
            state.average_usage = sum(e.value for e in recent_entries) / len(recent_entries)
        else:
            state.average_usage = value
        
        # Update status
        self._update_budget_status(budget_type)
        
        # Trigger callbacks if needed
        self._trigger_callbacks(budget_type, state)
        
        # Cleanup old entries
        if len(state.entries) > 1000:
            state.entries = state.entries[-500:]
    
    def _update_budget_status(self, budget_type: BudgetType) -> None:
        """Update budget status based on current usage."""
        state = self.budgets[budget_type]
        limit = self.limits[budget_type]
        
        usage_ratio = state.average_usage / limit.max_value
        
        if usage_ratio >= limit.critical_threshold:
            state.status = BudgetStatus.CRITICAL
        elif usage_ratio >= limit.warning_threshold:
            state.status = BudgetStatus.APPROACHING_LIMIT
        else:
            state.status = BudgetStatus.WITHIN_LIMIT
    
    def _trigger_callbacks(self, budget_type: BudgetType, state: BudgetState) -> None:
        """Trigger callbacks for budget changes."""
        if budget_type not in self.callbacks:
            return
        
        now = time.time()
        
        # Rate limit warnings
        if state.status in [BudgetStatus.APPROACHING_LIMIT, BudgetStatus.CRITICAL]:
            if now - state.last_warning < 30.0:  # Max one warning per 30 seconds
                return
            state.last_warning = now
        
        for callback in self.callbacks[budget_type]:
            try:
                callback(budget_type, state)
            except Exception as e:
                log.error(f"Budget callback error: {e}")
    
    def register_callback(self, budget_type: BudgetType, callback: Callable) -> None:
        """Register callback for budget changes."""
        if budget_type not in self.callbacks:
            self.callbacks[budget_type] = []
        self.callbacks[budget_type].append(callback)
    
    def get_budget_status(self, budget_type: BudgetType) -> BudgetState:
        """Get current status of a budget."""
        return self.budgets.get(budget_type, BudgetState())
    
    def get_energy_factor(self) -> float:
        """Get energy budget factor (0.0 - 1.0)."""
        self.energy_budget.update_battery_info()
        return self.energy_budget.calculate_energy_budget()
    
    def should_throttle(self, budget_type: BudgetType) -> bool:
        """Check if activity should be throttled for this budget type."""
        state = self.get_budget_status(budget_type)
        return state.status in [BudgetStatus.EXCEEDED, BudgetStatus.CRITICAL]
    
    def get_recommended_adjustments(self) -> Dict[str, Any]:
        """Get recommended adjustments based on budget status."""
        adjustments = {}
        energy_factor = self.get_energy_factor()
        
        # Check each budget type
        for budget_type, state in self.budgets.items():
            if state.status == BudgetStatus.CRITICAL:
                if budget_type == BudgetType.CPU:
                    adjustments["reduce_cpu_intensive_tasks"] = True
                    adjustments["lower_animation_fps"] = True
                elif budget_type == BudgetType.MEMORY:
                    adjustments["reduce_memory_usage"] = True
                    adjustments["clear_cache"] = True
                elif budget_type == BudgetType.ANIMATION:
                    adjustments["disable_animations"] = True
                    adjustments["use_minimal_rendering"] = True
                elif budget_type == BudgetType.LATENCY:
                    adjustments["increase_timeout_values"] = True
                    adjustments["reduce_concurrent_requests"] = True
                elif budget_type == BudgetType.NETWORK:
                    adjustments["reduce_network_requests"] = True
                    adjustments["use_local_cache"] = True
        
        # Energy-based adjustments
        if energy_factor < 0.5:
            adjustments.update({
                "enable_power_saving": True,
                "reduce_animation_quality": True,
                "lower_voice_frequency": True,
                "increase_idle_timeouts": True
            })
        
        if energy_factor < 0.3:
            adjustments.update({
                "disable_non_essential_features": True,
                "use_minimal_ui": True,
                "reduce_background_tasks": True
            })
        
        return adjustments
    
    def update_system_metrics(self) -> None:
        """Update system metrics automatically."""
        now = time.time()
        if now - self.last_update < self.update_interval:
            return
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.record_measurement(BudgetType.CPU, cpu_percent, "system_monitor")
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_measurement(BudgetType.MEMORY, memory.percent, "system_monitor")
            
            # Network usage (simplified)
            network = psutil.net_io_counters()
            if hasattr(self, '_last_network_bytes'):
                bytes_sent = network.bytes_sent - self._last_network_bytes[0]
                bytes_recv = network.bytes_recv - self._last_network_bytes[1]
                bytes_total = bytes_sent + bytes_recv
                mb_per_sec = (bytes_total / (1024 * 1024)) / self.update_interval
                self.record_measurement(BudgetType.NETWORK, mb_per_sec, "system_monitor")
            
            self._last_network_bytes = (network.bytes_sent, network.bytes_recv)
            
            # Energy/battery
            self.energy_budget.update_battery_info()
            self.record_measurement(BudgetType.ENERGY, self.energy_budget.battery_level, "battery_monitor")
            
        except Exception as e:
            log.error(f"Error updating system metrics: {e}")
        
        self.last_update = now
    
    def get_budget_summary(self) -> Dict[str, Any]:
        """Get summary of all budgets."""
        summary = {
            "budgets": {},
            "energy_factor": self.get_energy_factor(),
            "power_saving_mode": self.energy_budget.power_saving_mode,
            "battery_level": self.energy_budget.battery_level,
            "recommendations": self.get_recommended_adjustments()
        }
        
        for budget_type, state in self.budgets.items():
            limit = self.limits[budget_type]
            summary["budgets"][budget_type.value] = {
                "current_usage": state.current_usage,
                "average_usage": state.average_usage,
                "peak_usage": state.peak_usage,
                "status": state.status.value,
                "limit": limit.max_value,
                "warning_threshold": limit.max_value * limit.warning_threshold,
                "critical_threshold": limit.max_value * limit.critical_threshold,
                "total_measurements": state.total_measurements
            }
        
        return summary
    
    def tick(self) -> None:
        """Regular tick to update budgets."""
        self.update_system_metrics()


# Global instance
BUDGET_MANAGER = BudgetManager()