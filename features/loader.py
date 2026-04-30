"""
modules/loader.py

Plugin system for loading optional modules and extensions.
"""

from __future__ import annotations

import logging
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ModuleLoader:
    """Handles loading and management of optional modules."""
    
    def __init__(self, modules_dir: Path = None):
        self.modules_dir = modules_dir or Path(__file__).parent
        self.loaded_modules: Dict[str, Any] = {}
        
    def load_module(self, module_name: str) -> Optional[Any]:
        """Load a specific module by name."""
        try:
            module_path = self.modules_dir / module_name
            if not module_path.exists():
                logger.warning(f"Module directory not found: {module_path}")
                return None
                
            spec = importlib.util.spec_from_file_location(
                module_name, 
                module_path / "__init__.py"
            )
            if spec is None or spec.loader is None:
                logger.error(f"Could not create spec for module: {module_name}")
                return None
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            self.loaded_modules[module_name] = module
            logger.info(f"Loaded module: {module_name}")
            return module
            
        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            return None
    
    def unload_module(self, module_name: str) -> bool:
        """Unload a module."""
        if module_name in self.loaded_modules:
            del self.loaded_modules[module_name]
            logger.info(f"Unloaded module: {module_name}")
            return True
        return False
    
    def list_available_modules(self) -> List[str]:
        """List all available module directories."""
        modules = []
        for item in self.modules_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                modules.append(item.name)
        return modules
    
    def get_loaded_modules(self) -> List[str]:
        """Get list of currently loaded modules."""
        return list(self.loaded_modules.keys())


# Global module loader instance
_module_loader = ModuleLoader()


def get_module_loader() -> ModuleLoader:
    """Get the global module loader instance."""
    return _module_loader


def load_plugin_module(module_name: str) -> Optional[Any]:
    """Convenience function to load a plugin module."""
    return _module_loader.load_module(module_name)