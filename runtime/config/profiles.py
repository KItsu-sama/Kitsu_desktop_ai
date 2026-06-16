"""
app/profiles.py

Hardware detection for automatic profile selection.
Returns a profile name string — does NOT set flags.
Called by launcher.py before flags are set.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.schemas import load_profile_config, load_and_validate

logger = logging.getLogger('kitsu.app.profiles')

PROFILE_DIR = Path('shared/profiles')
SAFE_PROFILE_PATH = PROFILE_DIR / 'ultra_low.yaml'
CACHE_DIR = Path.home() / '.kitsu' / 'kitsu_cache'
CPU_BENCHMARK_FILE = CACHE_DIR / 'cpu_benchmark.json'


@dataclass
class HardwareProfile:
    name: str
    tier: str
    available_ram_gb: float
    cpu_score: float
    profile_path: Path
    profile_definition: Any


def _get_ram_gb() -> float:
    """Return available system RAM in GB. Returns 0.0 if detection fails."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass
    # Fallback: try reading /proc/meminfo on Linux
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb / (1024 ** 2)
    except (OSError, ValueError):
        pass
    logger.warning("Could not detect RAM. Defaulting to conservative estimate.")
    return 0.0


def _get_cpu_threads() -> int:
    """Return logical CPU thread count."""
    try:
        import os
        count = os.cpu_count()
        return count if count else 1
    except Exception:
        return 1


def _benchmark_cpu() -> float:
    """Benchmark CPU performance and cache result."""
    try:
        if CPU_BENCHMARK_FILE.exists():
            data = json.loads(CPU_BENCHMARK_FILE.read_text(encoding='utf-8'))
            score = float(data.get('cpu_score', 0.0))
            if score > 0:
                return score
    except Exception:
        logger.debug('Failed to read cached CPU benchmark')

    start = time.perf_counter()
    total = 0
    for i in range(100_000):
        total += i * i
    duration = max(1e-6, time.perf_counter() - start)
    score = round(min(100.0, max(1.0, 50.0 / duration)), 2)

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CPU_BENCHMARK_FILE.write_text(json.dumps({'cpu_score': score}), encoding='utf-8')
    except Exception:
        logger.debug('Unable to cache CPU benchmark')

    return score


def _load_hardware_thresholds() -> dict[str, Any]:
    """Load hardware thresholds from config/defaults.yaml."""
    try:
        defaults = load_and_validate(Path('config/defaults.yaml'), dict)
        return defaults.get('hardware', {})
    except Exception:
        logger.debug('Failed to load hardware thresholds, using defaults')
        return {}


def _resolve_profile_override(name: str) -> Path:
    """Resolve profile override path."""
    candidate = Path(name)
    if candidate.exists():
        return candidate
    candidate = PROFILE_DIR / f'{name}.yaml'
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f'Profile override not found: {name}')


def detect_hardware_profile() -> str:
    """
    Detect hardware tier and return the appropriate profile name.

    Simple tier mapping (fallback when config unavailable):
        RAM < 4 GB   → ultra_low
        RAM 4–8 GB   → balanced
        RAM > 8 GB   → full
    """
    ram_gb = _get_ram_gb()
    cpu_threads = _get_cpu_threads()
    os_name = platform.system()

    logger.info(
        "Hardware detection: RAM=%.1fGB, CPU threads=%d, OS=%s",
        ram_gb, cpu_threads, os_name
    )

    if ram_gb == 0.0:
        logger.warning("RAM detection failed. Using ultra_low profile.")
        return "ultra_low"

    if ram_gb < 4.0:
        profile = "ultra_low"
    elif ram_gb < 8.0:
        profile = "balanced"
    else:
        profile = "full"

    # Additional downgrade: single-core CPU forces ultra_low regardless of RAM
    if cpu_threads <= 1 and profile != "ultra_low":
        logger.warning("Single-core CPU detected. Downgrading to ultra_low.")
        profile = "ultra_low"

    logger.info("Selected hardware profile: %s", profile)
    return profile


def get_profile_path(profile_name: str) -> str:
    """Return the relative path to a profile YAML from the project root."""
    return f"config/profiles/{profile_name}.yaml"


def _is_safe_mode_env_enabled() -> bool:
    return any(
        os.environ.get(key, "").lower() in ("1", "true", "yes")
        for key in ("kitsu_SAFE_MODE", "KITSU_SAFE_MODE")
    )


def select_profile(profile_override: str | None = None, safe_mode: bool = False) -> HardwareProfile:
    """
    Select profile with full override support and advanced hardware detection.
    
    Priority order:
    1. safe_mode → ultra_low.yaml
    2. profile_override arg
    3. kitsu_PROFILE env var
    4. kitsu_SAFE_MODE env var
    5. Advanced hardware detection
    6. Simple hardware detection fallback
    """
    if safe_mode or _is_safe_mode_env_enabled():
        profile_path = SAFE_PROFILE_PATH
        logger.info('Safe mode enabled: using %s', SAFE_PROFILE_PATH.name)
    elif profile_override:
        profile_path = _resolve_profile_override(profile_override)
        logger.info('Using profile override: %s', profile_path.name)
    elif os.environ.get('kitsu_PROFILE'):
        profile_path = _resolve_profile_override(os.environ['kitsu_PROFILE'])
        logger.info('Using kitsu_PROFILE env: %s', profile_path.name)
    else:
        # Try advanced detection first
        try:
            ram_gb = _get_ram_gb()
            cpu_score = _benchmark_cpu()
            thresholds = _load_hardware_thresholds()
            
            logger.info('Advanced detection: ram=%.2fGB cpu=%.2f', ram_gb, cpu_score)
            
            if ram_gb < thresholds.get('micro_ram_gb', 2.0) or cpu_score < thresholds.get('micro_cpu_score', 20):
                profile_path = PROFILE_DIR / 'ultra_low.yaml'
            elif ram_gb < thresholds.get('low_ram_gb', 4.0) or cpu_score < thresholds.get('low_cpu_score', 50):
                profile_path = PROFILE_DIR / 'balanced.yaml'
            elif ram_gb < thresholds.get('mid_ram_gb', 8.0) or cpu_score < thresholds.get('mid_cpu_score', 80):
                profile_path = PROFILE_DIR / 'balanced.yaml'
            else:
                profile_path = PROFILE_DIR / 'full.yaml'
                
            logger.info('Advanced profile selection: %s', profile_path.name)
        except Exception:
            # Fallback to simple detection
            logger.info('Advanced detection failed, using simple detection')
            profile_name = detect_hardware_profile()
            profile_path = PROFILE_DIR / f'{profile_name}.yaml'

    profile_definition = load_profile_config(profile_path)
    return HardwareProfile(
        name=profile_definition.name,
        tier=profile_definition.tier,
        available_ram_gb=_get_ram_gb(),
        cpu_score=_benchmark_cpu(),
        profile_path=profile_path,
        profile_definition=profile_definition,
    )