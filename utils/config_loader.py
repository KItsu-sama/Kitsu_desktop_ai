"""
utils/config_loader.py

Configuration loading utilities extracted from legacy code.

Provides JSON loading, deep merging, and configuration management
with enhanced error handling and type safety.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

log = logging.getLogger(__name__)


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""
    pass


class ConfigLoader:
    """
    Utility class for loading and managing configuration files.
    
    Enhanced from legacy loader with:
    - Better error handling
    - Type validation
    - Deep merging capabilities
    - Environment variable support
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize config loader.
        
        Args:
            base_path: Base path for relative config file paths
        """
        self.base_path = base_path or Path.cwd()
        
    def load_json(self, path: Union[str, Path], required: bool = False) -> Dict[str, Any]:
        """
        Load JSON configuration file.
        
        Args:
            path: Path to JSON file
            required: If True, raise error if file doesn't exist
            
        Returns:
            Parsed JSON data as dictionary
            
        Raises:
            ConfigLoadError: If file is required but doesn't exist or is invalid
        """
        file_path = self.base_path / path if isinstance(path, str) else path
        
        if not file_path.exists():
            if required:
                raise ConfigLoadError(f"Required config file not found: {file_path}")
            log.debug(f"Config file not found, returning empty dict: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            log.debug(f"Loaded config from {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            raise ConfigLoadError(f"Invalid JSON in config file {file_path}: {e}")
        except Exception as e:
            raise ConfigLoadError(f"Error reading config file {file_path}: {e}")
    
    def save_json(self, path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            path: Path to save file
            data: Configuration data to save
            indent: JSON indentation level
        """
        file_path = self.base_path / path if isinstance(path, str) else path
        
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            log.debug(f"Saved config to {file_path}")
            
        except Exception as e:
            raise ConfigLoadError(f"Error saving config file {file_path}: {e}")
    
    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        The override dictionary values take precedence over base values.
        Nested dictionaries are merged recursively.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if (isinstance(value, dict) and 
                isinstance(result.get(key), dict)):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def load_configs(
        self, 
        paths: list[Union[str, Path]], 
        required: list[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Load and merge multiple configuration files.
        
        Files are loaded in order and deep merged, with later files
        taking precedence over earlier ones.
        
        Args:
            paths: List of config file paths to load
            required: List of paths that must exist
            
        Returns:
            Merged configuration dictionary
        """
        required = required or []
        merged_config = {}
        
        for path in paths:
            try:
                config = self.load_json(path, required=path in required)
                merged_config = self.deep_merge(merged_config, config)
            except ConfigLoadError as e:
                if path in required:
                    raise
                log.warning(f"Skipping optional config {path}: {e}")
        
        return merged_config
    
    def validate_config(
        self, 
        config: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> bool:
        """
        Validate configuration against a schema.
        
        Simple validation that checks required keys and basic types.
        
        Args:
            config: Configuration to validate
            schema: Schema definition with required keys and types
            
        Returns:
            True if valid, False otherwise
        """
        try:
            for key, spec in schema.items():
                if spec.get('required', False) and key not in config:
                    log.error(f"Required config key missing: {key}")
                    return False
                
                if key in config:
                    expected_type = spec.get('type')
                    if expected_type and not isinstance(config[key], expected_type):
                        log.error(f"Config key {key} has wrong type: "
                                 f"expected {expected_type.__name__}, "
                                 f"got {type(config[key]).__name__}")
                        return False
            
            return True
            
        except Exception as e:
            log.error(f"Config validation error: {e}")
            return False
    
    def get_config_value(
        self, 
        config: Dict[str, Any], 
        key_path: str, 
        default: Any = None
    ) -> Any:
        """
        Get a nested configuration value by key path.
        
        Args:
            config: Configuration dictionary
            key_path: Dot-separated path to value (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key_path.split('.')
            value = config
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set_config_value(
        self, 
        config: Dict[str, Any], 
        key_path: str, 
        value: Any
    ) -> Dict[str, Any]:
        """
        Set a nested configuration value by key path.
        
        Args:
            config: Configuration dictionary to modify
            key_path: Dot-separated path to value (e.g., 'database.host')
            value: Value to set
            
        Returns:
            Modified configuration dictionary
        """
        keys = key_path.split('.')
        current = config
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # Set the final value
        current[keys[-1]] = value
        return config


# Global instance for convenience
_default_loader = ConfigLoader()


def load_json(path: Union[str, Path], required: bool = False) -> Dict[str, Any]:
    """
    Load JSON configuration file using default loader.
    
    Args:
        path: Path to JSON file
        required: If True, raise error if file doesn't exist
        
    Returns:
        Parsed JSON data as dictionary
    """
    return _default_loader.load_json(path, required)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries using default loader.
    
    Args:
        base: Base dictionary
        override: Override dictionary
        
    Returns:
        Merged dictionary
    """
    return _default_loader.deep_merge(base, override)


def create_config_loader(base_path: Optional[Path] = None) -> ConfigLoader:
    """
    Create a new ConfigLoader instance.
    
    Args:
        base_path: Base path for relative config file paths
        
    Returns:
        ConfigLoader instance
    """
    return ConfigLoader(base_path)
