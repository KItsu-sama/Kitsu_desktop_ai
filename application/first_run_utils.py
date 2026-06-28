"""application/first_run_utils.py

First-run utilities:
- deterministic first-run state + validity checks
- atomic IO helpers
- lightweight schema validation for wizard output

Design goals:
- avoid heavy imports
- keep IO operations robust against crashes/interruption
- ensure config schemas are consistent with the canonical wizard structure
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict


# Canonical config schema (runtime generated)


class SystemSection(TypedDict):
    platform: str
    platform_version: str
    python_version: str
    capabilities: Dict[str, bool]
    headless: bool


class KitsuSection(TypedDict):
    permissions: Dict[str, bool]
    personality: Dict[str, Any]
    runtime: Dict[str, Any]
    features: Dict[str, bool]


class UserSection(TypedDict):
    name: str
    nickname: str
    refer_title: str
    gender: str
    status: str
    permissions: Dict[str, bool]
    relationship: Dict[str, Any]


class CanonicalWizardConfig(TypedDict):
    system: SystemSection
    kitsu: KitsuSection
    user: UserSection
    customized: bool


@dataclass(frozen=True)
class FirstRunState:
    completed: bool
    completed_marker_path: Path
    session_marker_path: Path
    last_completed_at: Optional[str]


@dataclass(frozen=True)
class ConfigPaths:
    system_config: Path
    user_profile: Path
    permissions: Path
    personality: Path
    runtime: Path
    feature_manifest: Path
    modules_config: Path


DEFAULT_PATHS = ConfigPaths(
    system_config=Path("data/config/system_config.json"),
    user_profile=Path("data/config/user_profile.json"),
    permissions=Path("data/config/permissions.json"),
    personality=Path("data/config/personality.json"),
    runtime=Path("data/config.json"),
    feature_manifest=Path("data/runtime/feature_manifest.json"),
    modules_config=Path("data/config/modules_config.json"),
)


def _atomic_replace(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # os.replace is atomic on the same filesystem.
    os.replace(str(src), str(dst))


def atomic_write_text(path: Path, data: str, *, encoding: str = "utf-8") -> None:
    """Atomic write for text files.

    Writes to a sibling temp file then replaces the destination.
    """
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(data, encoding=encoding)
        _atomic_replace(tmp, path)
    finally:
        # Best-effort cleanup
        if tmp.exists() and tmp != path:
            try:
                tmp.unlink()
            except Exception:
                pass


def atomic_write_json(path: Path, data: Any, *, encoding: str = "utf-8", indent: int = 2) -> None:
    """Atomic write for JSON files."""
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=indent), encoding=encoding)


def _read_marker(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        txt = path.read_text(encoding="utf-8").strip()
        return txt if txt else None
    except Exception:
        return None


def load_first_run_state(
    *,
    completed_marker_path: Path = Path("data/runtime/.first_run_complete"),
    session_marker_path: Path = Path("data/runtime/.first_run"),
) -> FirstRunState:
    """Load marker-based first-run state.

    Note: this is intentionally lightweight and avoids importing application runtime modules.
    """
    completed = completed_marker_path.exists()

    # If marker contains a timestamp, keep it. Otherwise fallback to file mtime.
    marker_value = _read_marker(completed_marker_path)
    last_completed_at: Optional[str]
    if marker_value:
        last_completed_at = marker_value
    else:
        try:
            if completed:
                ts = completed_marker_path.stat().st_mtime
                last_completed_at = datetime.fromtimestamp(ts).isoformat()
            else:
                last_completed_at = None
        except Exception:
            last_completed_at = None

    return FirstRunState(
        completed=completed,
        completed_marker_path=completed_marker_path,
        session_marker_path=session_marker_path,
        last_completed_at=last_completed_at,
    )


def _has_minimal_required_files(paths: ConfigPaths) -> bool:
    # Minimal set required to treat first-run as valid.
    required = [
        paths.system_config,
        paths.user_profile,
        paths.permissions,
        paths.personality,
        paths.runtime,
        paths.modules_config,
    ]
    return all(p.exists() for p in required)


def is_first_run_valid(state: FirstRunState, *, paths: ConfigPaths = DEFAULT_PATHS) -> bool:
    """Validate first-run by combining marker, file presence, and content checks."""
    if not state.completed:
        return False
    if not _has_minimal_required_files(paths):
        return False
    return validate_config_files(paths)


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def validate_config_files(paths: ConfigPaths) -> bool:
    """Validate that required config files exist, parse, and contain expected keys."""
    system = _load_json(paths.system_config)
    user = _load_json(paths.user_profile)
    permissions = _load_json(paths.permissions)
    personality = _load_json(paths.personality)
    runtime = _load_json(paths.runtime)
    modules = _load_json(paths.modules_config)

    if not all([system, user, permissions, personality, runtime, modules]):
        return False

    if not system.get("completed_setup"):
        return False
    if "capabilities" not in system or not isinstance(system.get("capabilities"), dict):
        return False

    if not user.get("completed_setup"):
        return False
    for key in ("name", "nickname", "permissions"):
        if key not in user:
            return False

    if "safe_mode" not in permissions:
        return False

    if "default_mood" not in personality or "default_style" not in personality:
        return False

    if "model" not in runtime:
        return False

    modules_section = modules.get("modules")
    if not isinstance(modules_section, dict) or not modules_section:
        return False

    return True


def _require_type(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def validate_wizard_config(cfg: Dict[str, Any]) -> CanonicalWizardConfig:
    """Validate wizard output and normalize to CanonicalWizardConfig.

    Raises ValueError on validation failures.
    """
    _require_type(isinstance(cfg, dict), "wizard config must be a dict")

    # Support historical partial payloads by mapping known legacy keys.
    # Canonical expected keys: system/kitsu/user/customized.
    if "customized" not in cfg:
        cfg = {**cfg, "customized": True}

    # Some older first_run implementations used `user_profile`.
    if "user" not in cfg and "user_profile" in cfg:
        cfg = {**cfg, "user": cfg["user_profile"]}

    for key in ("system", "kitsu", "user", "customized"):
        _require_type(key in cfg, f"missing wizard key: {key}")

    system = cfg["system"]
    kitsu = cfg["kitsu"]
    user = cfg["user"]



    _require_type(isinstance(system, dict), "system must be a dict")
    _require_type(isinstance(kitsu, dict), "kitsu must be a dict")
    _require_type(isinstance(user, dict), "user must be a dict")

    for k in ("platform", "platform_version", "python_version", "capabilities", "headless"):
        _require_type(k in system, f"system missing: {k}")

    caps = system["capabilities"]
    _require_type(isinstance(caps, dict), "system.capabilities must be a dict")
    for cap_key in ("gpu", "cuda", "audio_input", "audio_output", "display", "network"):
        _require_type(cap_key in caps, f"system.capabilities missing: {cap_key}")
        _require_type(isinstance(caps[cap_key], bool), f"system.capabilities.{cap_key} must be bool")

    permissions = kitsu.get("permissions")
    _require_type(isinstance(permissions, dict), "kitsu.permissions must be a dict")
    _require_type("safe_mode" in permissions, "kitsu.permissions.safe_mode missing")

    personality = kitsu.get("personality")
    _require_type(isinstance(personality, dict), "kitsu.personality must be a dict")

    runtime = kitsu.get("runtime")
    _require_type(isinstance(runtime, dict), "kitsu.runtime must be a dict")
    _require_type("model" in runtime, "kitsu.runtime.model missing")

    features = kitsu.get("features")
    _require_type(isinstance(features, dict), "kitsu.features must be a dict")
    for fid, enabled in features.items():
        _require_type(isinstance(enabled, bool), f"kitsu.features.{fid} must be bool")

    for k in ("name", "nickname", "refer_title", "gender", "status", "permissions", "relationship"):
        _require_type(k in user, f"user missing: {k}")

    user_perms = user["permissions"]
    _require_type(isinstance(user_perms, dict), "user.permissions must be a dict")
    _require_type("is_admin" in user_perms, "user.permissions.is_admin missing")
    _require_type(isinstance(user_perms["is_admin"], bool), "user.permissions.is_admin must be bool")

    # Return typed view
    return cfg  # type: ignore[return-value]


