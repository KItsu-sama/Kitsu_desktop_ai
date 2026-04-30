"""
scripts/first_run.py — First Run Initialization (Architecture Compliant)

RESPONSIBILITIES:
- Detect system capabilities
- Run SetupWizard (if interactive)
- Write all configuration files to data/config/
- Create directory structure
- Install/enable selected features

MUST NOT:
- Start main runtime
- Import core runtime modules
- Run async code
- Assume interactivity

Called ONLY by launcher.py before main.py starts.
"""

import sys
import json
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Ensure scripts directory is importable
_script_dir = Path(__file__).parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

log = logging.getLogger("kitsu.first_run")
FIRST_RUN_FLAG = Path("data/runtime/.first_run_complete")


def _mark_first_run_complete() -> bool:
    try:
        FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
        FIRST_RUN_FLAG.write_text('true', encoding='utf-8')
        return True
    except Exception as e:
        log.error(f"Failed to write first-run completion marker: {e}")
        return False


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
        log.debug("PyTorch not available")
    
    # Check audio
    try:
        import pyaudio
        info["capabilities"]["audio_input"] = True
        info["capabilities"]["audio_output"] = True
    except ImportError:
        log.debug("PyAudio not available")
    
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
        # Ensure parent exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write
        temp = path.with_suffix('.tmp')
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp.replace(path)
        
        log.info(f"✓ {name} → {path}")
        return True
    except Exception as e:
        log.error(f"✗ Failed to write {name}: {e}")
        return False


def write_system_config(system_info: Dict[str, Any]) -> bool:
    """Write system configuration"""
    config = {
        "platform": system_info["platform"],
        "platform_version": system_info.get("platform_version", "unknown"),
        "python_version": system_info.get("python_version", "unknown"),
        "capabilities": system_info["capabilities"],
        "install_date": datetime.now().isoformat(),
        "version": "0.1.0",
        "completed_setup": True,
        "model": "kitsu:character",
        "runtime": {}
    }
    
    return write_config_file(
        Path("data/config/system_config.json"),
        config,
        "System Config"
    )


def write_user_profile(wizard_results: Dict[str, Any]) -> bool:
    """Write user profile, merging with existing if present"""
    user_path = Path("data/config/user_profile.json")
    
    # Load existing if present
    existing = {}
    if user_path.exists():
        try:
            existing = json.loads(user_path.read_text(encoding='utf-8'))
        except Exception:
            existing = {}
    
    # Get new profile from wizard
    new_profile = wizard_results.get("user_profile", {})
    
    # Merge (preserve existing unless wizard explicitly changed)
    merged = existing.copy()
    merged.update(new_profile)
    
    # Merge permissions carefully
    existing_perms = existing.get("permissions", {})
    new_perms = new_profile.get("permissions", {})
    merged["permissions"] = {**existing_perms, **new_perms}
    
    # Mark as complete
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


# =============================================================================
# Directory Structure
# =============================================================================

def create_directory_structure() -> bool:
    """Create all required directories"""
    log.info("Creating directory structure...")
    
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
            log.debug(f"  ✓ {directory}")
        except Exception as e:
            log.error(f"  ✗ Failed to create {directory}: {e}")
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
    log.info("Installing selected features...")
    
    # Load feature specs
    try:
        spec_path = Path("docs/featurespec.json")
        if not spec_path.exists():
            log.warning("Feature spec not found, skipping feature installation")
            return True
        
        specs = json.loads(spec_path.read_text(encoding='utf-8'))
    except Exception as e:
        log.error(f"Failed to load feature specs: {e}")
        return False
    
    success = True
    for feature in specs.get("features", []):
        feature_id = feature.get("id")
        
        if not enabled_features.get(feature_id, False):
            continue
        
        feature_name = feature.get("name")
        log.info(f"  Installing {feature_name}...")
        
        # Create feature directories
        folder = feature.get("folder")
        if folder:
            try:
                Path(folder).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                log.error(f"    ✗ Failed to create {folder}: {e}")
                success = False
        
        # Feature files are now downloaded on-demand during feature activation
        log.info(f"    ✓ {feature_name} enabled (files will be downloaded when needed)")
    
    return success


# =============================================================================
# Main Entry Point
# =============================================================================

def run_first_run() -> bool:
    """
    Execute first-run initialization.
    
    Returns:
        True if successful, False otherwise
    """
    log.info("=" * 60)
    log.info("  KITSU FIRST RUN INITIALIZATION")
    log.info("=" * 60)
    
    # 1. Detect system
    log.info("\n📊 Detecting system capabilities...")
    system_info = detect_system_info()
    
    log.info(f"  Platform: {system_info['platform']}")
    log.info(f"  GPU: {system_info['capabilities']['gpu']}")
    log.info(f"  Audio: {system_info['capabilities']['audio_input']}")
    log.info(f"  Headless: {system_info.get('headless', False)}")
    
    # 2. Run setup wizard
    log.info("\n⚙️  Running setup wizard...")
    
    try:
        # Try importing as a sibling module in the scripts directory first
        try:
            from setup_wizard import SetupWizard
        except ModuleNotFoundError:
            # If that fails, try adding scripts to path and import
            if str(_script_dir) not in sys.path:
                sys.path.insert(0, str(_script_dir))
            from setup_wizard import SetupWizard
        
        wizard = SetupWizard(system_info)
        
        # Interactive or headless
        if sys.stdin and sys.stdin.isatty():
            wizard_results = wizard.run()
        else:
            log.info("  Non-interactive environment, using defaults")
            wizard_results = wizard.apply_defaults()
    
    except ImportError as e:
        log.error(f"  ✗ SetupWizard import failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False
    except Exception as e:
        log.error(f"  ✗ Wizard failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False
    
    # 3. Write configuration files
    log.info("\n📝 Writing configuration files...")
    
    success = True
    success &= write_system_config(system_info)
    success &= write_user_profile(wizard_results)
    success &= write_permissions(wizard_results)
    success &= write_personality_config(wizard_results)
    success &= write_runtime_config(wizard_results)
    success &= write_feature_manifest(wizard_results)
    
    # 4. Create directories
    log.info("\n📁 Creating directories...")
    success &= create_directory_structure()
    
    # 5. Install features
    features = wizard_results.get("features", {})
    if features:
        log.info("\n🔌 Installing features...")
        success &= install_features(features)
    
    # 6. Summary
    log.info("\n" + "=" * 60)
    if success:
        if _mark_first_run_complete():
            log.info("  ✅ First run initialization complete!")
        else:
            log.warning("  ⚠️  First run completed, but marker file could not be written")
    else:
        log.error("  ⚠️  Completed with errors")
    log.info("=" * 60 + "\n")
    
    return success


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI interface for first_run management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage first-run setup')
    parser.add_argument('--status', action='store_true', help='Show setup status')
    parser.add_argument('--run', action='store_true', help='Run first-run setup')
    parser.add_argument('--reset', action='store_true', help='Reset configuration')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    if args.status:
        # Show status
        flag = Path("data/runtime/.first_run_complete")
        config = Path("data/config.json")
        
        if flag.exists():
            print("✅ First-run setup complete")
            if config.exists():
                try:
                    cfg = json.loads(config.read_text(encoding='utf-8'))
                    print(f"Model: {cfg.get('model')}")
                    print(f"Mode: {cfg.get('mode')}")
                except Exception:
                    pass
        else:
            print("⚠️  First-run not complete")
    
    elif args.run:
        # Run setup
        success = run_first_run()
        sys.exit(0 if success else 1)
    
    elif args.reset:
        # Reset (with confirmation)
        try:
            from rich.prompt import Confirm
            if not Confirm.ask("Remove all configuration?", default=False):
                print("Aborted")
                return
        except ImportError:
            response = input("Remove all configuration? (y/N): ")
            if response.lower() != 'y':
                print("Aborted")
                return
        
        # Remove configs
        import shutil
        try:
            if Path("data/config").exists():
                shutil.rmtree("data/config")
            if Path("data/runtime/.first_run_complete").exists():
                Path("data/runtime/.first_run_complete").unlink()
            print("✅ Configuration reset")
        except Exception as e:
            print(f"❌ Reset failed: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()