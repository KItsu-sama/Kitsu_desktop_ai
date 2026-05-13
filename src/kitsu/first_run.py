"""
Modern First Run System - Unified initialization for modern Kitsu architecture.

This module provides first-run setup that integrates with the modern
event-driven system and creates proper configuration for both modern and legacy workflows.
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

from scripts.first_run import (
    detect_system_info, write_config_file, create_directory_structure,
    write_system_config, write_user_profile, write_permissions,
    write_personality_config, write_runtime_config, write_feature_manifest,
    install_features, FIRST_RUN_FLAG
)

logger = logging.getLogger("kitsu.first_run")

class ModernFirstRun:
    """Modern first-run system that integrates with event-driven architecture."""
    
    def __init__(self):
        self.system_info = None
        self.wizard_results = {}
        
    async def run_setup(self, interactive: bool = True) -> bool:
        """
        Run modern first-run setup.
        
        Args:
            interactive: Whether to run interactive setup wizard
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info("🦊 KITSU MODERN FIRST RUN INITIALIZATION")
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
                self.wizard_results = await self._apply_default_wizard()
            
            # 3. Write modern configuration files
            logger.info("\n📝 Writing modern configuration files...")
            success = await self._write_modern_configs()
            
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
                    logger.info("\n✅ Modern first-run setup complete!")
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
            # Try importing modern wizard first
            try:
                from setup_wizard import SetupWizard
                wizard = SetupWizard(self.system_info)
                return wizard.run()
            except ImportError:
                # Fallback to legacy wizard
                logger.warning("Modern wizard not available, using legacy fallback")
                from scripts.setup_wizard import SetupWizard
                wizard = SetupWizard(self.system_info)
                return wizard.run()
        except Exception as e:
            logger.error(f"Wizard failed: {e}")
            return {}
    
    async def _apply_default_wizard(self) -> Dict[str, Any]:
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
                "modern_pipeline": True,
                "event_bus": True,
                "memory_system": True
            }
        }
    
    async def _write_modern_configs(self) -> bool:
        """Write modern configuration files."""
        success = True
        
        # System config with modern runtime info
        system_config = {
            "platform": self.system_info["platform"],
            "platform_version": self.system_info.get("platform_version", "unknown"),
            "python_version": self.system_info.get("python_version", "unknown"),
            "capabilities": self.system_info["capabilities"],
            "install_date": datetime.now().isoformat(),
            "version": "1.0.0-modern",
            "completed_setup": True,
            "model": "kitsu:character",
            "runtime": {
                "architecture": "modern_event_driven",
                "input_system": "input_mux",
                "pipeline": "multi_tier",
                "event_bus": "kitsu.core.event_bus"
            }
        }
        success &= write_config_file(
            Path("data/config/system_config.json"),
            system_config,
            "Modern System Config"
        )
        
        # User profile
        success &= write_user_profile(self.wizard_results)
        
        # Permissions
        success &= write_permissions(self.wizard_results)
        
        # Personality config
        success &= write_personality_config(self.wizard_results)
        
        # Runtime config (compatible with both modern and legacy)
        success &= write_runtime_config(self.wizard_results)
        
        # Feature manifest
        success &= write_feature_manifest(self.wizard_results)
        
        # Modern-specific config
        modern_config = {
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
        success &= write_config_file(
            Path("data/config/modern_config.json"),
            modern_config,
            "Modern Modules Config"
        )
        
        return success
    
    def _mark_first_run_complete(self) -> bool:
        """Mark modern first-run as complete."""
        try:
            FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
            FIRST_RUN_FLAG.write_text('modern_complete', encoding='utf-8')
            
            # Also create modern marker
            modern_marker = Path("data/runtime/.modern_first_run")
            modern_marker.parent.mkdir(parents=True, exist_ok=True)
            modern_marker.write_text('true', encoding='utf-8')
            
            return True
        except Exception as e:
            logger.error(f"Failed to write first-run completion marker: {e}")
            return False

# Singleton instance
modern_first_run = ModernFirstRun()

async def run_modern_first_run(interactive: bool = True) -> bool:
    """
    Main entry point for modern first-run setup.
    
    Args:
        interactive: Whether to run interactive setup
        
    Returns:
        True if successful
    """
    return await modern_first_run.run_setup(interactive)

def check_modern_setup_complete() -> bool:
    """Check if modern first-run has been completed."""
    modern_marker = Path("data/runtime/.modern_first_run")
    return modern_marker.exists()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Modern Kitsu First Run Setup')
    parser.add_argument('--status', action='store_true', help='Show setup status')
    parser.add_argument('--run', action='store_true', help='Run modern first-run setup')
    parser.add_argument('--reset', action='store_true', help='Reset modern configuration')
    
    args = parser.parse_args()
    
    if args.status:
        if check_modern_setup_complete():
            print("✅ Modern first-run setup complete")
        else:
            print("⚠️  Modern first-run setup not completed")
    
    elif args.run:
        success = asyncio.run(run_modern_first_run())
        sys.exit(0 if success else 1)
    
    elif args.reset:
        try:
            from rich.prompt import Confirm
            if Confirm.ask("Reset modern configuration?", default=False):
                # Remove modern marker
                modern_marker = Path("data/runtime/.modern_first_run")
                if modern_marker.exists():
                    modern_marker.unlink()
                print("✅ Modern configuration reset")
        except ImportError:
            response = input("Reset modern configuration? (y/N): ")
            if response.lower() == 'y':
                modern_marker = Path("data/runtime/.modern_first_run")
                if modern_marker.exists():
                    modern_marker.unlink()
                print("✅ Modern configuration reset")
    
    else:
        parser.print_help()
