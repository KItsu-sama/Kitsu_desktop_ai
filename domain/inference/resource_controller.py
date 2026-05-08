"""
domain/inference/resource_controller.py

Resource-aware inference and rendering tier controller.

Dynamically adapts to system resources for student Potato compatibility.
Features automatic tier switching, battery/thermal awareness, and performance monitoring.
"""

import time
import logging
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from domain.contracts.lifecycle import BaseModule, ModuleState, Monitorable, ResourceAware

log = logging.getLogger(__name__)


class InferenceTier(Enum):
    """Inference capability tiers."""
    LLM = "llm"           # Full large language model
    SLM = "slm"           # Small language model
    REFLEX = "reflex"     # Fast reflex responses


class RenderTier(Enum):
    """Rendering capability tiers."""
    FULL_3D = "full_3d"   # Complete 3D model
    PARTIAL_3D = "partial_3d"  # Simplified 3D
    CHIBI_2D = "chibi_2d"  # 2D chibi style
    MINIMAL = "minimal"   # Minimal rendering


class PowerState(Enum):
    """System power states."""
    BATTERY_CRITICAL = "battery_critical"  # < 10%
    BATTERY_LOW = "battery_low"          # < 30%
    BATTERY_NORMAL = "battery_normal"    # > 30%
    POWERED = "powered"                  # Plugged in


class ThermalState(Enum):
    """System thermal states."""
    THERMAL_CRITICAL = "thermal_critical"  # > 85°C
    THERMAL_HIGH = "thermal_high"          # > 75°C
    THERMAL_WARM = "thermal_warm"          # > 65°C
    THERMAL_NORMAL = "thermal_normal"     # < 65°C


@dataclass
class SystemMetrics:
    """Current system resource metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_available: bool = False
    gpu_memory_percent: float = 0.0
    battery_percent: float = 100.0
    battery_plugged: bool = True
    temperature: float = 50.0  # Celsius
    disk_usage_percent: float = 0.0
    network_active: bool = False
    
    def get_power_state(self) -> PowerState:
        """Get current power state."""
        if self.battery_plugged:
            return PowerState.POWERED
        elif self.battery_percent < 10:
            return PowerState.BATTERY_CRITICAL
        elif self.battery_percent < 30:
            return PowerState.BATTERY_LOW
        else:
            return PowerState.BATTERY_NORMAL
    
    def get_thermal_state(self) -> ThermalState:
        """Get current thermal state."""
        if self.temperature > 85:
            return ThermalState.THERMAL_CRITICAL
        elif self.temperature > 75:
            return ThermalState.THERMAL_HIGH
        elif self.temperature > 65:
            return ThermalState.THERMAL_WARM
        else:
            return ThermalState.THERMAL_NORMAL


@dataclass
class InferenceConfig:
    """Configuration for inference tier."""
    max_tokens: int
    context_window: int
    temperature: float
    timeout_seconds: float
    max_concurrent_requests: int
    memory_limit_mb: int
    cpu_limit_percent: float


@dataclass
class RenderConfig:
    """Configuration for render tier."""
    max_fps: float
    model_quality: float  # 0.0 - 1.0
    texture_quality: float
    shadow_quality: float
    particle_effects: bool
    vsync_enabled: bool
    resolution_scale: float


class ResourceController(BaseModule, Monitorable, ResourceAware):
    """
    Resource-aware inference and rendering tier controller.
    
    Features:
    - Dynamic tier switching based on system resources
    - Battery and thermal awareness
    - Performance monitoring and adaptive degradation
    - Potato laptop optimization
    """
    
    def __init__(self):
        super().__init__(module_id="domain.inference.resource_controller", required_flags=[])
        self._monitoring = False
        self.metrics = SystemMetrics()
        self.current_inference_tier = InferenceTier.SLM
        self.current_render_tier = RenderTier.CHIBI_2D
        self.last_metrics_update = 0.0
        self.metrics_update_interval = 2.0  # seconds
        
        # Tier configurations
        self.inference_configs: Dict[InferenceTier, InferenceConfig] = {}
        self.render_configs: Dict[RenderTier, RenderConfig] = {}
        self._setup_tier_configs()
        
        # Performance history
        self.performance_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # Tier change callbacks
        self.inference_callbacks: List[Callable[[InferenceTier, InferenceTier], None]] = []
        self.render_callbacks: List[Callable[[RenderTier, RenderTier], None]] = []
        
        # Adaptive thresholds
        self.performance_threshold = 0.8  # Switch down if performance < 80%
        self.stability_threshold = 0.9     # Switch up if stable > 90%
        
        log.info("ResourceController initialized")
    
    def _setup_tier_configs(self):
        """Setup configurations for each tier."""
        # Inference configurations
        self.inference_configs[InferenceTier.LLM] = InferenceConfig(
            max_tokens=2048,
            context_window=8192,
            temperature=0.7,
            timeout_seconds=30.0,
            max_concurrent_requests=2,
            memory_limit_mb=2048,
            cpu_limit_percent=80.0
        )
        
        self.inference_configs[InferenceTier.SLM] = InferenceConfig(
            max_tokens=1024,
            context_window=4096,
            temperature=0.6,
            timeout_seconds=15.0,
            max_concurrent_requests=3,
            memory_limit_mb=1024,
            cpu_limit_percent=60.0
        )
        
        self.inference_configs[InferenceTier.REFLEX] = InferenceConfig(
            max_tokens=256,
            context_window=512,
            temperature=0.3,
            timeout_seconds=2.0,
            max_concurrent_requests=5,
            memory_limit_mb=256,
            cpu_limit_percent=30.0
        )
        
        # Render configurations
        self.render_configs[RenderTier.FULL_3D] = RenderConfig(
            max_fps=60.0,
            model_quality=1.0,
            texture_quality=1.0,
            shadow_quality=1.0,
            particle_effects=True,
            vsync_enabled=True,
            resolution_scale=1.0
        )
        
        self.render_configs[RenderTier.PARTIAL_3D] = RenderConfig(
            max_fps=45.0,
            model_quality=0.7,
            texture_quality=0.6,
            shadow_quality=0.5,
            particle_effects=False,
            vsync_enabled=True,
            resolution_scale=0.8
        )
        
        self.render_configs[RenderTier.CHIBI_2D] = RenderConfig(
            max_fps=30.0,
            model_quality=0.4,
            texture_quality=0.4,
            shadow_quality=0.0,
            particle_effects=False,
            vsync_enabled=False,
            resolution_scale=0.6
        )
        
        self.render_configs[RenderTier.MINIMAL] = RenderConfig(
            max_fps=15.0,
            model_quality=0.2,
            texture_quality=0.2,
            shadow_quality=0.0,
            particle_effects=False,
            vsync_enabled=False,
            resolution_scale=0.4
        )
    
    def update_metrics(self) -> None:
        """Update system resource metrics."""
        now = time.time()
        if now - self.last_metrics_update < self.metrics_update_interval:
            return
        
        try:
            # CPU and memory
            self.metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            self.metrics.memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.metrics.disk_usage_percent = disk.percent
            
            # Battery (if available)
            try:
                battery = psutil.sensors_battery()
                if battery:
                    self.metrics.battery_percent = battery.percent
                    self.metrics.battery_plugged = battery.power_plugged
            except Exception:
                # Battery not available
                self.metrics.battery_plugged = True
            
            # Network activity
            network = psutil.net_io_counters()
            self.metrics.network_active = (network.bytes_sent + network.bytes_recv) > 0
            
            # Temperature (platform-specific)
            self.metrics.temperature = self._get_system_temperature()
            
            # GPU (basic detection)
            self.metrics.gpu_available = self._detect_gpu()
            
            self.last_metrics_update = now
            
        except Exception as e:
            log.error(f"Error updating system metrics: {e}")
    
    def _get_system_temperature(self) -> float:
        """Get system temperature (platform-specific)."""
        try:
            if platform.system() == "Windows":
                # Windows temperature monitoring
                import wmi
                w = wmi.WMI()
                temps = w.Win32_TemperatureProbe()
                if temps:
                    return float(temps[0].CurrentReading) / 10.0 - 273.15
            elif platform.system() == "Linux":
                # Linux temperature monitoring
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            return entries[0].current
        except Exception:
            pass
        
        return 50.0  # Default temperature
    
    def _detect_gpu(self) -> bool:
        """Detect if GPU is available."""
        try:
            # Basic GPU detection
            import platform
            if platform.system() == "Windows":
                try:
                    import wmi
                    w = wmi.WMI()
                    for gpu in w.Win32_VideoController():
                        if "NVIDIA" in gpu.Name or "AMD" in gpu.Name or "Radeon" in gpu.Name:
                            return True
                except Exception:
                    pass
            return False
        except Exception:
            return False
    
    def evaluate_inference_tier(self) -> InferenceTier:
        """Evaluate appropriate inference tier based on resources."""
        power_state = self.metrics.get_power_state()
        thermal_state = self.metrics.get_thermal_state()
        
        # Critical conditions force lowest tier
        if (power_state == PowerState.BATTERY_CRITICAL or 
            thermal_state == ThermalState.THERMAL_CRITICAL):
            return InferenceTier.REFLEX
        
        # High resource usage
        if (self.metrics.cpu_percent > 80 or 
            self.metrics.memory_percent > 85 or
            thermal_state == ThermalState.THERMAL_HIGH):
            return InferenceTier.REFLEX
        
        # Medium resource usage or low battery
        if (self.metrics.cpu_percent > 60 or 
            self.metrics.memory_percent > 70 or
            power_state == PowerState.BATTERY_LOW or
            thermal_state == ThermalState.THERMAL_WARM):
            return InferenceTier.SLM
        
        # Good conditions allow LLM
        if (self.metrics.cpu_percent < 40 and 
            self.metrics.memory_percent < 50 and
            power_state in [PowerState.BATTERY_NORMAL, PowerState.POWERED] and
            thermal_state == ThermalState.THERMAL_NORMAL):
            return InferenceTier.LLM
        
        # Default to SLM
        return InferenceTier.SLM
    
    def evaluate_render_tier(self) -> RenderTier:
        """Evaluate appropriate render tier based on resources."""
        power_state = self.metrics.get_power_state()
        thermal_state = self.metrics.get_thermal_state()
        
        # Critical conditions force minimal rendering
        if (power_state == PowerState.BATTERY_CRITICAL or 
            thermal_state == ThermalState.THERMAL_CRITICAL):
            return RenderTier.MINIMAL
        
        # High resource usage
        if (self.metrics.cpu_percent > 80 or 
            self.metrics.memory_percent > 85 or
            thermal_state == ThermalState.THERMAL_HIGH):
            return RenderTier.MINIMAL
        
        # Medium resource usage or low battery
        if (self.metrics.cpu_percent > 60 or 
            self.metrics.memory_percent > 70 or
            power_state == PowerState.BATTERY_LOW or
            thermal_state == ThermalState.THERMAL_WARM):
            return RenderTier.CHIBI_2D
        
        # Good conditions with GPU
        if (self.metrics.gpu_available and
            self.metrics.cpu_percent < 40 and 
            self.metrics.memory_percent < 50 and
            power_state in [PowerState.BATTERY_NORMAL, PowerState.POWERED] and
            thermal_state == ThermalState.THERMAL_NORMAL):
            return RenderTier.FULL_3D
        
        # Good conditions without GPU
        if (self.metrics.cpu_percent < 40 and 
            self.metrics.memory_percent < 50 and
            power_state in [PowerState.BATTERY_NORMAL, PowerState.POWERED] and
            thermal_state == ThermalState.THERMAL_NORMAL):
            return RenderTier.PARTIAL_3D
        
        # Default to chibi
        return RenderTier.CHIBI_2D
    
    def update_tiers(self) -> None:
        """Update inference and render tiers based on current metrics."""
        self.update_metrics()
        
        new_inference_tier = self.evaluate_inference_tier()
        new_render_tier = self.evaluate_render_tier()
        
        # Check for inference tier changes
        if new_inference_tier != self.current_inference_tier:
            old_tier = self.current_inference_tier
            self.current_inference_tier = new_inference_tier
            
            log.info(f"Inference tier changed: {old_tier.value} -> {new_inference_tier.value}")
            
            # Trigger callbacks
            for callback in self.inference_callbacks:
                try:
                    callback(old_tier, new_inference_tier)
                except Exception as e:
                    log.error(f"Inference tier callback error: {e}")
        
        # Check for render tier changes
        if new_render_tier != self.current_render_tier:
            old_tier = self.current_render_tier
            self.current_render_tier = new_render_tier
            
            log.info(f"Render tier changed: {old_tier.value} -> {new_render_tier.value}")
            
            # Trigger callbacks
            for callback in self.render_callbacks:
                try:
                    callback(old_tier, new_render_tier)
                except Exception as e:
                    log.error(f"Render tier callback error: {e}")
    
    def get_inference_config(self) -> InferenceConfig:
        """Get current inference configuration."""
        return self.inference_configs[self.current_inference_tier]
    
    def get_render_config(self) -> RenderConfig:
        """Get current render configuration."""
        return self.render_configs[self.current_render_tier]
    
    def register_inference_callback(self, callback: Callable[[InferenceTier, InferenceTier], None]) -> None:
        """Register callback for inference tier changes."""
        self.inference_callbacks.append(callback)
    
    def register_render_callback(self, callback: Callable[[RenderTier, RenderTier], None]) -> None:
        """Register callback for render tier changes."""
        self.render_callbacks.append(callback)
    
    def record_performance(
        self,
        inference_time: float,
        render_fps: float,
        success: bool = True
    ) -> None:
        """Record performance metrics for adaptive tuning."""
        self.performance_history.append({
            "timestamp": time.time(),
            "inference_tier": self.current_inference_tier.value,
            "render_tier": self.current_render_tier.value,
            "inference_time": inference_time,
            "render_fps": render_fps,
            "success": success,
            "cpu_percent": self.metrics.cpu_percent,
            "memory_percent": self.metrics.memory_percent
        })
        
        # Limit history size
        if len(self.performance_history) > self.max_history_size:
            self.performance_history = self.performance_history[-self.max_history_size//2:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of recent performance."""
        if not self.performance_history:
            return {}
        
        recent = self.performance_history[-20:]  # Last 20 entries
        
        return {
            "avg_inference_time": sum(p["inference_time"] for p in recent) / len(recent),
            "avg_render_fps": sum(p["render_fps"] for p in recent) / len(recent),
            "success_rate": sum(1 for p in recent if p["success"]) / len(recent),
            "current_inference_tier": self.current_inference_tier.value,
            "current_render_tier": self.current_render_tier.value,
            "performance_history_size": len(self.performance_history)
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        return {
            "metrics": {
                "cpu_percent": self.metrics.cpu_percent,
                "memory_percent": self.metrics.memory_percent,
                "gpu_available": self.metrics.gpu_available,
                "battery_percent": self.metrics.battery_percent,
                "battery_plugged": self.metrics.battery_plugged,
                "temperature": self.metrics.temperature,
                "power_state": self.metrics.get_power_state().value,
                "thermal_state": self.metrics.get_thermal_state().value
            },
            "tiers": {
                "inference": self.current_inference_tier.value,
                "render": self.current_render_tier.value
            },
            "configs": {
                "inference": {
                    "max_tokens": self.get_inference_config().max_tokens,
                    "timeout": self.get_inference_config().timeout_seconds,
                    "memory_limit": self.get_inference_config().memory_limit_mb
                },
                "render": {
                    "max_fps": self.get_render_config().max_fps,
                    "model_quality": self.get_render_config().model_quality,
                    "resolution_scale": self.get_render_config().resolution_scale
                }
            },
            "performance": self.get_performance_summary()
        }
    
    def force_inference_tier(self, tier: InferenceTier) -> None:
        """Force specific inference tier."""
        old_tier = self.current_inference_tier
        self.current_inference_tier = tier
        log.info(f"Inference tier forced: {old_tier.value} -> {tier.value}")
    
    def force_render_tier(self, tier: RenderTier) -> None:
        """Force specific render tier."""
        old_tier = self.current_render_tier
        self.current_render_tier = tier
        log.info(f"Render tier forced: {old_tier.value} -> {tier.value}")
    
    def tick(self) -> None:
        """Regular tick to update resource monitoring."""
        self.update_tiers()
    
    async def _on_start(self) -> bool:
        """Start resource monitoring."""
        try:
            await self.start_monitoring()
            return True
        except Exception as e:
            log.error(f"Failed to start ResourceController: {e}")
            return False
    
    async def _on_stop(self) -> bool:
        """Stop resource monitoring."""
        try:
            await self.stop_monitoring()
            return True
        except Exception as e:
            log.error(f"Failed to stop ResourceController: {e}")
            return False
    
    async def _on_health_check(self) -> dict:
        """Health check for ResourceController."""
        return {
            "ok": self._monitoring,
            "latency_ms": 0.0,
            "current_inference_tier": self.current_inference_tier.value,
            "current_render_tier": self.current_render_tier.value,
            "monitoring_active": self._monitoring
        }
    
    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        self._monitoring = True
        log.info("ResourceController monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self._monitoring = False
        log.info("ResourceController monitoring stopped")
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring
    
    async def handle_resource_pressure(self, resource_type: str, level: float) -> None:
        """Handle resource pressure events."""
        if resource_type == "cpu" and level > 0.8:
            await self._handle_high_cpu()
        elif resource_type == "memory" and level > 0.9:
            await self._handle_high_memory()
        elif resource_type == "battery" and level < 0.2:
            await self._handle_low_battery()
    
    async def handle_tier_change(self, tier: str) -> None:
        """Handle tier change events."""
        if tier == "degrade":
            await self._degrade_tier()
        elif tier == "upgrade":
            await self._upgrade_tier()


# Global instance
RESOURCE_CONTROLLER = ResourceController()
