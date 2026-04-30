"""
config/unified_config.py

Unified configuration system consolidating all configuration sources.
This fixes configuration sprawl by providing a single source of truth.
"""

from __future__ import annotations

import logging
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field, fields
from typing import Dict, Any, Optional, List, Union
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigFormat(Enum):
    """Supported configuration formats."""
    JSON = "json"
    YAML = "yaml"
    PYTHON = "python"


@dataclass
class HardwareProfileConfig:
    """Hardware profile configuration."""
    name: str
    ram_gb: float
    cpu_cores: int
    has_gpu: bool
    gpu_memory_gb: Optional[float] = None
    flags: Dict[str, bool] = field(default_factory=dict)
    description: str = ""


@dataclass
class CapabilityConfig:
    """Capability flags configuration."""
    use_fast_brain: bool = True
    use_emotion: bool = True
    use_2d: bool = False
    use_3d: bool = False
    use_slm: bool = False
    use_llm: bool = False
    use_voice: bool = False
    use_shimeji: bool = False
    use_system_control: bool = False


@dataclass
class AIConfig:
    """AI stack configuration."""
    fast_brain: Dict[str, Any] = field(default_factory=dict)
    slm: Dict[str, Any] = field(default_factory=dict)
    llm: Dict[str, Any] = field(default_factory=dict)
    hybrid: Dict[str, Any] = field(default_factory=dict)
    local_confidence_threshold: float = 0.1
    complexity_threshold: float = 0.6
    resource_threshold: float = 0.5
    max_local_tokens: int = 64
    max_external_tokens: int = 512
    temperature_local: float = 0.8
    temperature_external: float = 0.7
    preferred_mode: str = "local"
    fallback_to_external: bool = True
    use_local_for_simple: bool = True


@dataclass
class EmotionConfig:
    """Emotion system configuration."""
    continuous_decay: bool = True
    mood_decay_rate: float = 0.95
    style_decay_rate: float = 0.90
    state_decay_rate: float = 0.85
    max_stack_size: int = 10
    resistance_threshold: float = 0.8
    trigger_sensitivity: float = 0.5
    personality_influence: float = 0.7


@dataclass
class MemoryConfig:
    """Memory system configuration."""
    max_short_term_memories: int = 100
    max_episodic_memories: int = 50
    max_vector_memories: int = 1000
    memory_retention_days: int = 30
    compression_threshold: int = 1000
    auto_cleanup: bool = True
    backup_enabled: bool = True
    backup_interval_hours: int = 24


@dataclass
class UIConfig:
    """User interface configuration."""
    theme: str = "default"
    avatar_style: str = "anime"
    window_opacity: float = 0.9
    always_on_top: bool = False
    show_debug_info: bool = False
    font_size: int = 12
    chat_history_limit: int = 100
    command_prefix: str = "/"
    auto_save_interval: int = 300


@dataclass
class SystemConfig:
    """System integration configuration."""
    wallpaper_control: bool = False
    cursor_theme: str = "default"
    tab_management: bool = False
    power_management: bool = False
    file_access: bool = False
    automation: bool = False
    network_access: bool = True
    audio_visualizer: bool = False
    permissions_prompt: bool = True


@dataclass
class PerformanceConfig:
    """Performance tuning configuration."""
    monitoring_interval: float = 5.0
    health_check_interval: float = 10.0
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[float] = None
    auto_optimize: bool = True
    aggressive_cleanup: bool = False
    model_unload_timeout: int = 300


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    console_enabled: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5
    log_to_memory: bool = False


@dataclass
class UnifiedConfig:
    """Unified configuration consolidating all system settings."""
    # Core sections
    hardware: HardwareProfileConfig = field(default_factory=HardwareProfileConfig)
    capabilities: CapabilityConfig = field(default_factory=CapabilityConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    emotion: EmotionConfig = field(default_factory=EmotionConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Runtime
    mode: str = "text"
    model: str = "unknown"
    debug: bool = False
    profile_override: Optional[str] = None
    
    # Metadata
    version: str = "1.0.0"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at


class UnifiedConfigManager:
    """Manages unified configuration loading, saving, and validation."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("data/config")
        self.config_file = self.config_dir / "unified_config.json"
        self.profiles_dir = self.config_dir / "profiles"
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self, profile_override: Optional[str] = None) -> UnifiedConfig:
        """Load configuration from file with optional profile override."""
        # Load base config
        config = self._load_base_config()
        
        # Apply profile override if specified
        if profile_override:
            profile = self._load_profile(profile_override)
            config = self._apply_profile(config, profile)
        
        # Validate configuration
        self._validate_config(config)
        
        return config
    
    def save_config(self, config: UnifiedConfig) -> None:
        """Save configuration to file."""
        from datetime import datetime
        config.updated_at = datetime.now().isoformat()
        
        # Convert to dict
        config_dict = self._config_to_dict(config)
        
        # Save to file
        with open(self.config_file, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        logger.info(f"Configuration saved to {self.config_file}")
    
    def _load_base_config(self) -> UnifiedConfig:
        """Load base configuration from file."""
        if not self.config_file.exists():
            logger.info("Config file not found, creating default config")
            return UnifiedConfig()
        
        try:
            with open(self.config_file, 'r') as f:
                config_dict = json.load(f)
            return self._dict_to_config(config_dict)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return UnifiedConfig()
    
    def _load_profile(self, profile_name: str) -> Dict[str, Any]:
        """Load a specific profile configuration."""
        profile_file = self.profiles_dir / f"{profile_name}.json"
        
        if not profile_file.exists():
            # Try YAML format
            yaml_file = self.profiles_dir / f"{profile_name}.yaml"
            if yaml_file.exists():
                with open(yaml_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"Profile {profile_name} not found")
                return {}
        
        with open(profile_file, 'r') as f:
            return json.load(f)
    
    def _apply_profile(self, config: UnifiedConfig, profile: Dict[str, Any]) -> UnifiedConfig:
        """Apply profile overrides to configuration."""
        # Apply capability flags
        if 'capabilities' in profile:
            for key, value in profile['capabilities'].items():
                if hasattr(config.capabilities, key):
                    setattr(config.capabilities, key, value)
        
        # Apply other sections
        for section_name, section_data in profile.items():
            if section_name == 'capabilities':
                continue  # Already handled
            
            if hasattr(config, section_name):
                section = getattr(config, section_name)
                for key, value in section_data.items():
                    if hasattr(section, key):
                        setattr(section, key, value)
        
        return config
    
    def _validate_config(self, config: UnifiedConfig) -> None:
        """Validate configuration consistency."""
        errors = []
        
        # Validate capability dependencies
        if config.capabilities.use_3d and not config.capabilities.use_2d:
            errors.append("use_3d requires use_2d to also be enabled")
        
        if config.capabilities.use_llm and not config.capabilities.use_slm:
            errors.append("use_llm requires use_slm to also be enabled")
        
        if config.capabilities.use_voice and not (config.capabilities.use_slm or config.capabilities.use_fast_brain):
            errors.append("use_voice requires at least use_slm or use_fast_brain")
        
        # Validate AI config
        if config.ai.max_local_tokens < 1:
            errors.append("max_local_tokens must be at least 1")
        
        if config.ai.max_external_tokens < 1:
            errors.append("max_external_tokens must be at least 1")
        
        # Validate memory config
        if config.memory.max_short_term_memories < 1:
            errors.append("max_short_term_memories must be at least 1")
        
        if config.memory.max_episodic_memories < 1:
            errors.append("max_episodic_memories must be at least 1")
        
        # Log errors or success
        if errors:
            for error in errors:
                logger.error(f"Configuration validation error: {error}")
            raise ValueError(f"Configuration validation failed: {errors}")
        else:
            logger.info("Configuration validation passed")
    
    def _config_to_dict(self, config: UnifiedConfig) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization."""
        return {
            'hardware': self._dataclass_to_dict(config.hardware),
            'capabilities': self._dataclass_to_dict(config.capabilities),
            'ai': self._dataclass_to_dict(config.ai),
            'emotion': self._dataclass_to_dict(config.emotion),
            'memory': self._dataclass_to_dict(config.memory),
            'ui': self._dataclass_to_dict(config.ui),
            'system': self._dataclass_to_dict(config.system),
            'performance': self._dataclass_to_dict(config.performance),
            'logging': self._dataclass_to_dict(config.logging),
            'mode': config.mode,
            'model': config.model,
            'debug': config.debug,
            'profile_override': config.profile_override,
            'version': config.version,
            'created_at': config.created_at,
            'updated_at': config.updated_at,
        }
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> UnifiedConfig:
        """Convert dictionary to config object."""
        # Create nested objects
        config_dict['hardware'] = HardwareProfileConfig(**config_dict.get('hardware', {}))
        config_dict['capabilities'] = CapabilityConfig(**config_dict.get('capabilities', {}))
        config_dict['ai'] = AIConfig(**config_dict.get('ai', {}))
        config_dict['emotion'] = EmotionConfig(**config_dict.get('emotion', {}))
        config_dict['memory'] = MemoryConfig(**config_dict.get('memory', {}))
        config_dict['ui'] = UIConfig(**config_dict.get('ui', {}))
        config_dict['system'] = SystemConfig(**config_dict.get('system', {}))
        config_dict['performance'] = PerformanceConfig(**config_dict.get('performance', {}))
        config_dict['logging'] = LoggingConfig(**config_dict.get('logging', {}))
        
        return UnifiedConfig(**config_dict)
    
    def _dataclass_to_dict(self, obj) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        return {field.name: getattr(obj, field.name) for field in fields(obj)}


# Global config manager
_config_manager: Optional[UnifiedConfigManager] = None


def get_config_manager() -> UnifiedConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = UnifiedConfigManager()
    return _config_manager


def load_config(profile_override: Optional[str] = None) -> UnifiedConfig:
    """Load unified configuration."""
    manager = get_config_manager()
    return manager.load_config(profile_override)


def save_config(config: UnifiedConfig) -> None:
    """Save unified configuration."""
    manager = get_config_manager()
    manager.save_config(config)
