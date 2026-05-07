"""
shared/config.py - Single source of truth for configuration loading

Provides standardized config loading with priority order:
1. Defaults from shared/defaults.yaml
2. User settings from data/config/system_config.json  
3. Hardware profile from data/config/profile.json
4. CLI argument overrides (highest priority)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

from shared.file_security import safe_file_read, safe_file_write

logger = logging.getLogger('kitsu.config')


class ConfigMerger:
    """Merges configuration from multiple sources with priority."""
    
    def __init__(self, sources: List[str]):
        self.sources = sources
        
    def merge(self) -> Dict[str, Any]:
        """Merge all config sources in priority order."""
        result = {}
        
        for source in self.sources:
            try:
                if source == "CLI_ARGS":
                    # CLI args handled separately by caller
                    continue
                    
                config_data = self._load_source(source)
                if config_data:
                    result = self._deep_merge(result, config_data)
                    logger.debug(f"Loaded config from {source}")
                    
            except Exception as exc:
                logger.warning(f"Failed to load config source {source}: {exc}")
                
        return result
    
    def _load_source(self, source: str) -> Dict[str, Any]:
        """Load configuration from a single source."""
        source_path = Path(source)
        
        if not source_path.exists():
            logger.debug(f"Config source not found: {source}")
            return {}
            
        if source_path.suffix == '.yaml' or source_path.suffix == '.yml':
            return self._load_yaml(source_path)
        elif source_path.suffix == '.json':
            return self._load_json(source_path)
        else:
            logger.warning(f"Unsupported config format: {source}")
            return {}
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration."""
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration.""" 
        content = safe_file_read(str(path))
        if content:
            return json.loads(content)
        return {}
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, override takes precedence."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result


class Config:
    """Main configuration class with standardized loading."""
    
    @classmethod
    def load(cls, cli_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Load configuration from all sources.
        
        Args:
            cli_overrides: Dictionary of CLI argument overrides
            
        Returns:
            Merged configuration dictionary
        """
        cli_overrides = cli_overrides or {}
        
        # Define config sources in priority order
        sources = [
            "shared/defaults.yaml",           # 1. Defaults
            "data/config/system_config.json", # 2. User settings  
            "data/config/profile.json",       # 3. Hardware profile
        ]
        
        # Merge all sources
        merger = ConfigMerger(sources)
        config = merger.merge()
        
        # Apply CLI overrides (highest priority)
        if cli_overrides:
            config = merger._deep_merge(config, cli_overrides)
            logger.debug("Applied CLI overrides")
            
        # Validate required config sections
        cls._validate_config(config)
        
        return config
    
    @classmethod
    def _validate_config(cls, config: Dict[str, Any]) -> None:
        """Validate that required configuration sections exist."""
        required_sections = ['system', 'runtime']
        
        for section in required_sections:
            if section not in config:
                logger.warning(f"Missing required config section: {section}")
                config[section] = {}
    
    @classmethod
    def save_system_config(cls, config: Dict[str, Any]) -> bool:
        """Save system configuration to data/config/system_config.json."""
        try:
            config_path = Path("data/config/system_config.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = json.dumps(config, indent=2)
            return safe_file_write(str(config_path), content)
            
        except Exception as exc:
            logger.error(f"Failed to save system config: {exc}")
            return False
    
    @classmethod 
    def get_defaults(cls) -> Dict[str, Any]:
        """Get just the defaults configuration."""
        try:
            defaults_path = Path("shared/defaults.yaml")
            if defaults_path.exists():
                with open(defaults_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error(f"Failed to load defaults: {exc}")
            
        return {}


# Convenience function for quick loading
def load_config(cli_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """Quick access to Config.load()"""
    return Config.load(cli_overrides)


# Backward compatibility aliases
def get_system_config() -> Dict[str, Any]:
    """Get system config only (for backward compatibility)."""
    try:
        config_path = Path("data/config/system_config.json")
        if config_path.exists():
            content = safe_file_read(str(config_path))
            if content:
                return json.loads(content)
    except Exception as exc:
        logger.error(f"Failed to get system config: {exc}")
        
    return {}


def save_system_config(config: Dict[str, Any]) -> bool:
    """Save system config (backward compatibility wrapper)."""
    return Config.save_system_config(config)
