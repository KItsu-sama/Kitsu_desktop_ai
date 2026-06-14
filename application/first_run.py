"""
# application/first_run.py
First Run System - Unified initialization for Kitsu architecture.

This module provides first-run setup that integrates with the event-driven system
and creates proper configuration for the Kitsu runtime environment.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to path
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger("kitsu.first_run")

# First run marker paths
FIRST_RUN_FLAG = Path("data/runtime/.first_run_complete")
SESSION_FIRST_RUN = Path("data/runtime/.first_run")


# =============================================================================
# System Detection
# =============================================================================

def detect_system_info() -> Dict[str, Any]:
    """
    Detect system platform and capabilities.
    
    Returns:
        Dict with platform info and capabilities
    """
    info = {
        "platform": platform.system().lower(),
        "platform_version": platform.version(),
        "python_version": sys.version,
        "capabilities": {
            "gpu": False,
            "cuda": False,
            "audio_input": False,
            "audio_output": False,
            "display": True,
            "network": True
        },
        "headless": False
    }
    
    # Normalize platform
    if info["platform"] == "darwin":
        info["platform"] = "macos"
    
    # Check GPU
    try:
        import torch
        info["capabilities"]["gpu"] = torch.cuda.is_available()
        info["capabilities"]["cuda"] = torch.cuda.is_available()
        if info["capabilities"]["cuda"]:
            info["gpu_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        logger.debug("PyTorch not available")
    
    # Check audio
    try:
        import pyaudio
        info["capabilities"]["audio_input"] = True
        info["capabilities"]["audio_output"] = True
    except ImportError:
        logger.debug("PyAudio not available")
    
    # Check headless
    if not sys.stdin or not sys.stdin.isatty():
        info["capabilities"]["display"] = False
        info["headless"] = True
    
    return info


# =============================================================================
# Configuration Writers
# =============================================================================

def write_config_file(path: Path, data: Dict[str, Any], name: str) -> bool:
    """
    Write configuration file atomically.
    
    Args:
        path: Path to config file
        data: Configuration data
        name: Config name (for logging)
        
    Returns:
        True if successful
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        
        temp = path.with_suffix('.tmp')
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp.replace(path)
        
        logger.info(f"✓ {name} → {path}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to write {name}: {e}")
        return False


def write_system_config(system_info: Dict[str, Any]) -> bool:
    """Write system configuration"""
    config = {
        "platform": system_info["platform"],
        "platform_version": system_info.get("platform_version", "unknown"),
        "python_version": system_info.get("python_version", "unknown"),
        "capabilities": system_info["capabilities"],
        "install_date": datetime.now().isoformat(),
        "version": "1.0.0",
        "completed_setup": True,
        "model": "kitsu:character",
        "runtime": {
            "architecture": "event_driven",
            "input_system": "input_mux",
            "pipeline": "multi_tier",
            "event_bus": "kitsu.core.event_bus"
        }
    }
    
    return write_config_file(
        Path("data/config/system_config.json"),
        config,
        "System Config"
    )


def write_user_profile(wizard_results: Dict[str, Any]) -> bool:
    """Write user profile, merging with existing if present"""
    user_path = Path("data/config/user_profile.json")
    
    existing = {}
    if user_path.exists():
        try:
            existing = json.loads(user_path.read_text(encoding='utf-8'))
        except Exception:
            existing = {}
    
    new_profile = wizard_results.get("user_profile", {})
    
    merged = existing.copy()
    merged.update(new_profile)
    
    existing_perms = existing.get("permissions", {})
    new_perms = new_profile.get("permissions", {})
    merged["permissions"] = {**existing_perms, **new_perms}
    
    merged["completed_setup"] = True
    
    return write_config_file(user_path, merged, "User Profile")


def write_permissions(wizard_results: Dict[str, Any]) -> bool:
    """Write permissions configuration"""
    permissions = wizard_results.get("permissions", {
        "browser_hooks": False,
        "system_control": False,
        "file_access": False,
        "safe_mode": True,
        "can_train": False,
        "can_modify_memory": True
    })
    
    return write_config_file(
        Path("data/config/permissions.json"),
        permissions,
        "Permissions"
    )


def write_personality_config(wizard_results: Dict[str, Any]) -> bool:
    """Write personality configuration"""
    personality = wizard_results.get("personality", {
        "default_mood": "behave",
        "default_style": "chaotic",
        "enable_sass": True,
        "enable_pranks": False,
        "sass_level": 0.3,
        "prank_frequency": 0.0,
        "emotion_decay_rate": 0.1,
        "emotion_threshold": 0.3,
        "max_stack_size": 5
    })
    
    return write_config_file(
        Path("data/config/personality.json"),
        personality,
        "Personality"
    )


def write_runtime_config(wizard_results: Dict[str, Any]) -> bool:
    """Write runtime configuration"""
    runtime = wizard_results.get("runtime", {
        "mode": "text",
        "model": "kitsu:character",
        "is_character_model": True,
        "temperature": 0.8,
        "streaming": True,
        "greet_on_startup": True,
        "continuous_decay": False,
        "enable_tts": False,
        "enable_stt": False,
        "enable_avatar": False,
        "memory_max_history": 200
    })
    
    return write_config_file(
        Path("data/config.json"),
        runtime,
        "Runtime Config"
    )


def write_feature_manifest(wizard_results: Dict[str, Any]) -> bool:
    """Write enabled features manifest"""
    features = wizard_results.get("features", {})
    
    manifest = {
        "enabled_features": [k for k, v in features.items() if v],
        "disabled_features": [k for k, v in features.items() if not v],
        "last_updated": datetime.now().isoformat()
    }
    
    return write_config_file(
        Path("data/runtime/feature_manifest.json"),
        manifest,
        "Feature Manifest"
    )


def write_modules_config() -> bool:
    """Write modules configuration"""
    modules_config = {
        "modules": {
            "input_mux": {"enabled": True},
            "input_manager": {"enabled": True},
            "slm": {"enabled": True, "model": "Qwen2.5-1.5B"},
            "llm": {"enabled": True, "fallback": True},
            "memory": {"enabled": True},
            "judge": {"enabled": True}
        },
        "event_system": {
            "bus_type": "kitsu.core.event_bus",
            "max_subscribers": 100,
            "timeout_ms": 5000
        },
        "pipeline": {
            "tiers": ["fast_brain", "slm", "llm"],
            "judge_validation": True,
            "behavior_gating": True
        }
    }
    
    return write_config_file(
        Path("data/config/modules_config.json"),
        modules_config,
        "Modules Config"
    )


# =============================================================================
# Directory Structure
# =============================================================================

def create_directory_structure() -> bool:
    """Create all required directories"""
    logger.info("Creating directory structure...")
    
    directories = [
        Path("data/config"),
        Path("data/runtime"),
        Path("data/memory"),
        Path("data/memory/backups"),
        Path("data/logs"),
        Path("data/logs/sessions"),
        Path("data/learning"),
        Path("data/lora"),
        Path("assets/models"),
        Path("assets/sounds")
    ]
    
    success = True
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"  ✓ {directory}")
        except Exception as e:
            logger.error(f"  ✗ Failed to create {directory}: {e}")
            success = False
    
    return success


# =============================================================================
# Feature Installation
# =============================================================================

def install_features(enabled_features: Dict[str, bool]) -> bool:
    """
    Install/enable selected features.
    
    Args:
        enabled_features: Dict of feature_id -> enabled
        
    Returns:
        True if all installations successful
    """
    logger.info("Installing selected features...")
    
    try:
        spec_path = Path("docs/featurespec.json")
        if not spec_path.exists():
            logger.warning("Feature spec not found, skipping feature installation")
            return True
        
        specs = json.loads(spec_path.read_text(encoding='utf-8'))
    except Exception as e:
        logger.error(f"Failed to load feature specs: {e}")
        return False
    
    success = True
    for feature in specs.get("features", []):
        feature_id = feature.get("id")
        
        if not enabled_features.get(feature_id, False):
            continue
        
        feature_name = feature.get("name")
        logger.info(f"  Installing {feature_name}...")
        
        folder = feature.get("folder")
        if folder:
            try:
                Path(folder).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"    ✗ Failed to create {folder}: {e}")
                success = False
        
        logger.info(f"    ✓ {feature_name} enabled (files will be downloaded when needed)")
    
    return success


# =============================================================================
# First Run Core
# =============================================================================

class FirstRun:
    """First-run system that integrates with event-driven architecture."""
    
    def __init__(self):
        self.system_info = None
        self.wizard_results = {}
        
    async def run_setup(self, interactive: bool = True) -> bool:
        """
        Run first-run setup.
        
        Args:
            interactive: Whether to run interactive setup wizard
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info("🦊 KITSU FIRST RUN INITIALIZATION")
            logger.info("=" * 60)
            
            # 1. Detect system capabilities
            logger.info("\n📊 Detecting system capabilities...")
            self.system_info = detect_system_info()
            
            logger.info(f"  Platform: {self.system_info['platform']}")
            logger.info(f"  GPU: {self.system_info['capabilities']['gpu']}")
            logger.info(f"  Audio: {self.system_info['capabilities']['audio_input']}")
            logger.info(f"  Headless: {self.system_info.get('headless', False)}")
            
            # 2. Run setup wizard or apply defaults
            logger.info("\n⚙️  Running setup wizard...")
            
            if interactive:
                self.wizard_results = await self._run_interactive_wizard()
            else:
                self.wizard_results = self._apply_default_wizard()
            
            # 3. Write configuration files
            logger.info("\n📝 Writing configuration files...")
            success = self._write_configs()
            
            # 4. Create directory structure
            logger.info("\n📁 Creating directories...")
            success &= create_directory_structure()
            
            # 5. Install features
            features = self.wizard_results.get("features", {})
            if features:
                logger.info("\n🔌 Installing features...")
                success &= install_features(features)
            
            # 6. Mark completion
            if success:
                if self._mark_first_run_complete():
                    logger.info("\n✅ First-run setup complete!")
                else:
                    logger.warning("\n⚠️  Setup completed, but marker file could not be written")
            else:
                logger.error("\n❌ Setup completed with errors")
            
            logger.info("=" * 60 + "\n")
            return success
            
        except Exception as e:
            logger.error(f"First-run setup failed: {e}", exc_info=True)
            return False
    
    async def _run_interactive_wizard(self) -> Dict[str, Any]:
        """Run interactive setup wizard."""
        try:
            from scripts.setup_wizard import SetupWizard
            wizard = SetupWizard(self.system_info)
            return wizard.run()
        except ImportError as e:
            logger.error(f"Wizard import failed: {e}")
            return self._apply_default_wizard()
        except Exception as e:
            logger.error(f"Wizard failed: {e}")
            return self._apply_default_wizard()
    
    def _apply_default_wizard(self) -> Dict[str, Any]:
        """Apply default configuration for non-interactive setup."""
        return {
            "user_profile": {
                "name": "User",
                "preferences": {
                    "theme": "default",
                    "voice_enabled": False
                }
            },
            "permissions": {
                "browser_hooks": False,
                "system_control": False,
                "file_access": False,
                "safe_mode": True,
                "can_train": False,
                "can_modify_memory": True
            },
            "personality": {
                "default_mood": "behave",
                "default_style": "chaotic",
                "enable_sass": True,
                "emotion_decay_rate": 0.1,
                "emotion_threshold": 0.3,
                "max_stack_size": 5
            },
            "runtime": {
                "mode": "text",
                "model": "kitsu:character",
                "temperature": 0.8,
                "streaming": True,
                "greet_on_startup": True,
                "enable_tts": False,
                "enable_stt": False,
                "enable_avatar": False,
                "memory_max_history": 200
            },
            "features": {
                "input_mux": True,
                "pipeline": True,
                "event_bus": True,
                "memory_system": True
            }
        }
    
    def _write_configs(self) -> bool:
        """Write all configuration files."""
        success = True
        
        # System config
        success &= write_system_config(self.system_info)
        
        # User profile
        success &= write_user_profile(self.wizard_results)
        
        # Permissions
        success &= write_permissions(self.wizard_results)
        
        # Personality config
        success &= write_personality_config(self.wizard_results)
        
        # Runtime config
        success &= write_runtime_config(self.wizard_results)
        
        # Feature manifest
        success &= write_feature_manifest(self.wizard_results)
        
        # Modules config
        success &= write_modules_config()
        
        return success
    
    def _mark_first_run_complete(self) -> bool:
        """Mark first-run as complete."""
        try:
            FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
            FIRST_RUN_FLAG.write_text('true', encoding='utf-8')
            
            # Also create session marker
            SESSION_FIRST_RUN.parent.mkdir(parents=True, exist_ok=True)
            SESSION_FIRST_RUN.write_text('true', encoding='utf-8')
            
            return True
        except Exception as e:
            logger.error(f"Failed to write first-run completion marker: {e}")
            return False


# =============================================================================
# Public API
# =============================================================================

# Singleton instance
_first_run = FirstRun()

async def run_first_run(interactive: bool = True) -> bool:
    """
    Main entry point for first-run setup.
    
    Args:
        interactive: Whether to run interactive setup
        
    Returns:
        True if successful
    """
    return await _first_run.run_setup(interactive)

def check_setup_complete() -> bool:
    """Check if first-run has been completed."""
    return FIRST_RUN_FLAG.exists()

def reset_setup() -> bool:
    """Reset first-run configuration."""
    try:
        import shutil
        
        # Remove config directories
        for path in [Path("data/config"), Path("data/runtime")]:
            if path.exists():
                shutil.rmtree(path)
        
        # Remove markers
        for marker in [FIRST_RUN_FLAG, SESSION_FIRST_RUN]:
            if marker.exists():
                marker.unlink()
        
        logger.info("✅ First-run configuration reset")
        return True
    except Exception as e:
        logger.error(f"Failed to reset configuration: {e}")
        return False


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Kitsu First Run Setup')
    parser.add_argument('--status', action='store_true', help='Show setup status')
    parser.add_argument('--run', action='store_true', help='Run first-run setup')
    parser.add_argument('--reset', action='store_true', help='Reset first-run configuration')
    parser.add_argument('--non-interactive', action='store_true', help='Run in non-interactive mode')
    
    args = parser.parse_args()
    
    # Setup logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    if args.status:
        if check_setup_complete():
            print("✅ First-run setup complete")
            config_path = Path("data/config.json")
            if config_path.exists():
                try:
                    cfg = json.loads(config_path.read_text(encoding='utf-8'))
                    print(f"   Model: {cfg.get('model')}")
                    print(f"   Mode: {cfg.get('mode')}")
                except Exception:
                    pass
        else:
            print("⚠️  First-run setup not completed")
    
    elif args.run:
        interactive = not args.non_interactive
        success = asyncio.run(run_first_run(interactive=interactive))
        sys.exit(0 if success else 1)
    
    elif args.reset:
        try:
            from rich.prompt import Confirm
            if Confirm.ask("Reset first-run configuration?", default=False):
                if reset_setup():
                    print("✅ Configuration reset")
                else:
                    print("❌ Reset failed")
                    sys.exit(1)
        except ImportError:
            response = input("Reset first-run configuration? (y/N): ")
            if response.lower() == 'y':
                if reset_setup():
                    print("✅ Configuration reset")
                else:
                    print("❌ Reset failed")
                    sys.exit(1)
    
    else:
        parser.print_help()