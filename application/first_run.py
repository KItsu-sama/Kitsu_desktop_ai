"""application/first_run.py

First Run System - Unified initialization for Kitsu architecture.

This module provides first-run setup that integrates with the event-driven system
and creates proper configuration for the Kitsu runtime environment.

NOTE:
- This file orchestrates first-run steps and writes config files.
- IO robustness and schema validation are delegated to application/first_run_utils.py
  where appropriate.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
import platform
from typing import Dict, Any
from datetime import datetime

# Add project root to path
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger("kitsu.first_run")

# First run marker paths
FIRST_RUN_FLAG = Path("data/runtime/.first_run_complete")
SESSION_FIRST_RUN = Path("data/runtime/.first_run")


def detect_system_info() -> Dict[str, Any]:
    """Detect system platform and capabilities."""
    info: Dict[str, Any] = {
        "platform": platform.system().lower(),
        "platform_version": platform.version(),
        "python_version": sys.version,
        "capabilities": {
            "gpu": False,
            "cuda": False,
            "audio_input": False,
            "audio_output": False,
            "display": True,
            "network": True,
        },
        "headless": False,
    }

    if info["platform"] == "darwin":
        info["platform"] = "macos"

    # GPU (lazy; optional)
    try:
        import torch  # type: ignore

        info["capabilities"]["gpu"] = bool(torch.cuda.is_available())
        info["capabilities"]["cuda"] = bool(torch.cuda.is_available())
        if info["capabilities"]["cuda"]:
            info["gpu_name"] = torch.cuda.get_device_name(0)
    except Exception:
        logger.debug("PyTorch not available")

    # Audio (optional)
    try:
        import pyaudio  # type: ignore

        info["capabilities"]["audio_input"] = True
        info["capabilities"]["audio_output"] = True
    except Exception:
        logger.debug("PyAudio not available")

    # Headless
    try:
        if not sys.stdin or not sys.stdin.isatty():
            info["capabilities"]["display"] = False
            info["headless"] = True
    except Exception:
        pass

    return info


def write_config_file(path: Path, data: Any, name: str) -> bool:
    """Write configuration file (atomic via temp + replace)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(path)

        logger.info(f"✓ {name} → {path}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to write {name}: {e}")
        return False


def _data_root(root: Path | None = None) -> Path:
    return root if root is not None else Path("data")


def write_system_config(system_info: Dict[str, Any], *, root: Path | None = None) -> bool:
    config = {
        "platform": system_info["platform"],
        "platform_version": system_info.get("platform_version", "unknown"),
        "python_version": system_info.get("python_version", "unknown"),
        "capabilities": system_info["capabilities"],
        "install_date": datetime.now().isoformat(),
        "version": "1.0.0",
        "completed_setup": True,
        "runtime": {
            "architecture": "event_driven",
            "input_system": "input_mux",
            "pipeline": "multi_tier",
            "event_bus": "kitsu.core.event_bus",
        },
    }

    return write_config_file(_data_root(root) / "config/system_config.json", config, "System Config")


def write_user_profile(wizard_results: Dict[str, Any], *, root: Path | None = None) -> bool:
    user_path = _data_root(root) / "config/user_profile.json"

    existing: Dict[str, Any] = {}
    if user_path.exists():
        try:
            existing = json.loads(user_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    new_profile = wizard_results.get("user", {}) or wizard_results.get("user_profile", {})

    merged = existing.copy()
    merged.update(new_profile)

    existing_perms = existing.get("permissions", {})
    new_perms = new_profile.get("permissions", {})
    merged["permissions"] = {**existing_perms, **new_perms}

    merged["completed_setup"] = True

    return write_config_file(user_path, merged, "User Profile")


def write_permissions(wizard_results: Dict[str, Any], *, root: Path | None = None) -> bool:
    kitsu = wizard_results.get("kitsu", {})
    permissions = (kitsu.get("permissions") if isinstance(kitsu, dict) else None) or wizard_results.get(
        "permissions",
        {
            "browser_hooks": False,
            "system_control": False,
            "file_access": False,
            "safe_mode": True,
            "can_train": False,
            "can_modify_memory": True,
        },
    )

    return write_config_file(_data_root(root) / "config/permissions.json", permissions, "Permissions")


def write_personality_config(wizard_results: Dict[str, Any], *, root: Path | None = None) -> bool:
    kitsu = wizard_results.get("kitsu", {})
    personality = (kitsu.get("personality") if isinstance(kitsu, dict) else None) or wizard_results.get(
        "personality",
        {
            "default_mood": "behave",
            "default_style": "chaotic",
            "enable_sass": True,
            "enable_pranks": False,
            "sass_level": 0.3,
            "prank_frequency": 0.0,
            "emotion_decay_rate": 0.1,
            "emotion_threshold": 0.3,
            "max_stack_size": 5,
        },
    )

    return write_config_file(_data_root(root) / "config/personality.json", personality, "Personality")


def write_runtime_config(wizard_results: Dict[str, Any], *, root: Path | None = None) -> bool:
    kitsu = wizard_results.get("kitsu", {})
    runtime = (kitsu.get("runtime") if isinstance(kitsu, dict) else None) or wizard_results.get(
        "runtime",
        {
            "mode": "text",
            "model": "",
            "is_character_model": False,
            "temperature": 0.8,
            "streaming": True,
            "greet_on_startup": True,
            "continuous_decay": False,
            "enable_tts": False,
            "enable_stt": False,
            "enable_avatar": False,
            "memory_max_history": 200,
            "slm": {"enabled": True},
            "llm": {"enabled": True, "base_url": "", "model": ""},
        },
    )

    return write_config_file(_data_root(root) / "config.json", runtime, "Runtime Config")


def write_feature_manifest(wizard_results: Dict[str, Any], *, root: Path | None = None) -> bool:
    kitsu = wizard_results.get("kitsu", {})
    features = (kitsu.get("features") if isinstance(kitsu, dict) else None) or wizard_results.get("features", {})

    manifest = {
        "enabled_features": [k for k, v in features.items() if v],
        "disabled_features": [k for k, v in features.items() if not v],
        "last_updated": datetime.now().isoformat(),
    }

    return write_config_file(_data_root(root) / "runtime/feature_manifest.json", manifest, "Feature Manifest")


def write_modules_config(*, root: Path | None = None) -> bool:
    modules_config = {
        "modules": {
            "input_mux": {"enabled": True},
            "input_manager": {"enabled": True},
            "slm": {"enabled": True},
            "llm": {"enabled": True, "fallback": True},
            "memory": {"enabled": True},
            "judge": {"enabled": True},
        },
        "event_system": {
            "bus_type": "kitsu.core.event_bus",
            "max_subscribers": 100,
            "timeout_ms": 5000,
        },
        "pipeline": {
            "tiers": ["fast_brain", "slm", "llm"],
            "judge_validation": True,
            "behavior_gating": True,
        },
    }

    return write_config_file(_data_root(root) / "config/modules_config.json", modules_config, "Modules Config")


def _validate_staged_configs(staging: Path) -> bool:
    """Validate staged config JSON content before promotion.

    Uses `ConfigPaths` constructed relative to the staging root so paths
    match what was actually written.
    """
    from application.first_run_utils import validate_config_files, ConfigPaths

    paths = ConfigPaths(
        system_config=staging / "config/system_config.json",
        user_profile=staging / "config/user_profile.json",
        permissions=staging / "config/permissions.json",
        personality=staging / "config/personality.json",
        runtime=staging / "config.json",
        feature_manifest=staging / "runtime/feature_manifest.json",
        modules_config=staging / "config/modules_config.json",
    )
    return validate_config_files(paths)



def create_directory_structure() -> bool:
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
        Path("assets/sounds"),
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


def install_features(enabled_features: Dict[str, bool]) -> bool:
    logger.info("Installing selected features...")

    try:
        spec_path = Path("docs/featurespec.json")
        if not spec_path.exists():
            logger.warning("Feature spec not found, skipping feature installation")
            return True

        specs = json.loads(spec_path.read_text(encoding="utf-8"))
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


def _maybe_short_circuit_valid_setup() -> bool:
    """Fast path: if marker + minimal config files exist, skip wizard work."""
    try:
        from application.first_run_utils import load_first_run_state, is_first_run_valid

        state = load_first_run_state(
            completed_marker_path=FIRST_RUN_FLAG,
            session_marker_path=SESSION_FIRST_RUN,
        )
        return is_first_run_valid(state)
    except Exception:
        return False


class FirstRun:
    def __init__(self) -> None:
        self.system_info: Dict[str, Any] = {}
        self.wizard_results: Dict[str, Any] = {}

    async def run_setup(self, interactive: bool = True) -> bool:
        if _maybe_short_circuit_valid_setup():
            logger.info("First-run already valid; skipping setup")
            return True

        try:
            logger.info("🦊 KITSU FIRST RUN INITIALIZATION")

            self.system_info = detect_system_info()

            if interactive:
                self.wizard_results = await self._run_interactive_wizard()
            else:
                self.wizard_results = self._apply_default_wizard()

            success = self._write_configs()
            success &= create_directory_structure()

            features = self.wizard_results.get("features", {})
            if isinstance(features, dict) and features:
                success &= install_features(features)

            if success:
                if self._mark_first_run_complete():
                    logger.info("First-run setup complete")
                else:
                    logger.warning("Setup completed but marker file could not be written")
            else:
                logger.error("First-run setup completed with errors")

            return bool(success)
        except Exception as e:
            logger.error(f"First-run setup failed: {e}", exc_info=True)
            return False

    async def _run_interactive_wizard(self) -> Dict[str, Any]:
        try:
            from scripts.setup_wizard import SetupWizard

            wizard = SetupWizard(self.system_info)
            return wizard.run()
        except Exception as e:
            logger.error(f"Wizard failed: {e}")
            return self._apply_default_wizard()

    def _apply_default_wizard(self) -> Dict[str, Any]:
        return {
            "system": self.system_info or {
                "platform": "unknown",
                "platform_version": "unknown",
                "python_version": sys.version,
                "capabilities": {
                    "gpu": False,
                    "cuda": False,
                    "audio_input": False,
                    "audio_output": False,
                    "display": False,
                    "network": True,
                },
                "headless": True,
            },
            "kitsu": {
                "permissions": {
                    "browser_hooks": False,
                    "system_control": False,
                    "file_access": False,
                    "safe_mode": True,
                    "can_train": False,
                    "can_modify_memory": True,
                },
                "personality": {
                    "default_mood": "behave",
                    "default_style": "chaotic",
                    "enable_sass": True,
                    "enable_pranks": False,
                    "sass_level": 0.3,
                    "prank_frequency": 0.0,
                    "emotion_decay_rate": 0.1,
                    "emotion_threshold": 0.3,
                    "max_stack_size": 5,
                },
                "runtime": {
                    "mode": "text",
                    "model": "",
                    "is_character_model": False,
                    "temperature": 0.8,
                    "streaming": True,
                    "greet_on_startup": True,
                    "continuous_decay": False,
                    "enable_tts": False,
                    "enable_stt": False,
                    "enable_avatar": False,
                    "memory_max_history": 200,
                    "slm": {"enabled": True},
                    "llm": {"enabled": True, "base_url": "", "model": ""},
                },
                "features": {
                    "input_mux": True,
                    "pipeline": True,
                    "event_bus": True,
                    "memory_system": True,
                },
            },
            "user": {
                "name": "User",
                "nickname": "User",
                "refer_title": "User",
                "gender": "unspecified",
                "status": "user",
                "permissions": {"is_admin": False, "dev_console": False},
                "relationship": {
                    "trust_level": 0.5,
                    "affinity": 0.5,
                    "lore_tag": "stranger",
                },
            },
            "customized": False,
        }

    def _write_configs(self) -> bool:
        return self._write_configs_transactional(Path("data/runtime"))

    def _write_configs_transactional(self, staging_dir: Path) -> bool:
        """Write all configs to staging, validate, then promote atomically.

        Staging mirrors the canonical `data/` layout. We then promote by copying
        staged `*.json` files into the real `data/` directory.
        """
        import shutil

        staging = staging_dir / "first_run_staging"
        staging.mkdir(parents=True, exist_ok=True)

        try:
            ok = True
            ok &= write_system_config(self.system_info or {}, root=staging)
            ok &= write_user_profile(self.wizard_results, root=staging)
            ok &= write_permissions(self.wizard_results, root=staging)
            ok &= write_personality_config(self.wizard_results, root=staging)
            ok &= write_runtime_config(self.wizard_results, root=staging)
            ok &= write_feature_manifest(self.wizard_results, root=staging)
            ok &= write_modules_config(root=staging)

            if not ok:
                return False

            if not _validate_staged_configs(staging):
                logger.error("Staged first-run configs failed validation")
                return False

            promoted = 0
            for src in sorted(staging.rglob("*.json")):
                rel = src.relative_to(staging)
                dst = Path("data") / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                promoted += 1

            logger.info(f"Promoted {promoted} JSON files from staging to data/")
            return True
        finally:
            shutil.rmtree(staging, ignore_errors=True)


    def _mark_first_run_complete(self) -> bool:
        try:
            FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
            FIRST_RUN_FLAG.write_text("true", encoding="utf-8")

            SESSION_FIRST_RUN.parent.mkdir(parents=True, exist_ok=True)
            SESSION_FIRST_RUN.write_text("true", encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to write first-run completion marker: {e}")
            return False


_first_run = FirstRun()


async def run_first_run(interactive: bool = True) -> bool:
    # Gateway-only / ephemeral startup: force non-interactive.
    if bool(os.environ.get("KITSU_GATEWAY_ONLY")):
        interactive = False
    return await _first_run.run_setup(interactive)




def check_setup_complete() -> bool:
    return FIRST_RUN_FLAG.exists()


def reset_setup() -> bool:
    try:
        import shutil

        for path in [Path("data/config"), Path("data/runtime")]:
            if path.exists():
                shutil.rmtree(path)

        for marker in [FIRST_RUN_FLAG, SESSION_FIRST_RUN]:
            if marker.exists():
                marker.unlink()

        logger.info("First-run configuration reset")
        return True
    except Exception as e:
        logger.error(f"Failed to reset configuration: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Kitsu First Run Setup")
    parser.add_argument("--status", action="store_true", help="Show setup status")
    parser.add_argument("--run", action="store_true", help="Run first-run setup")
    parser.add_argument("--reset", action="store_true", help="Reset first-run configuration")
    parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.status:
        if check_setup_complete():
            print("First-run setup complete")
        else:
            print("First-run setup not completed")

    
    elif args.run:
        success = asyncio.run(run_first_run(interactive=not args.non_interactive))
        sys.exit(0 if success else 1)

    elif args.reset:
        success = reset_setup()
        sys.exit(0 if success else 1)

    else:
        parser.print_help()

