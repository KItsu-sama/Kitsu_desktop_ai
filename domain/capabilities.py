"""
system/capabilities.py

Capability flags and hardware tier detection.
Read-only after startup validation.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass

log = logging.getLogger('kitsu.system.capabilities')


@dataclass(frozen=True)
class HardwareProfile:
    """Hardware capability profile with tier and flags."""
    name: str
    tier: str  # micro, low, mid, high
    ram_gb: int
    cpu_cores: int
    has_gpu: bool
    flags: Set[str]


class CapabilityManager:
    """Manages capability flags and hardware detection."""
    
    # Core capability flags
    FLAGS = {
        'USE_FAST_BRAIN': True,      # Always active
        'USE_EMOTION': True,         # Emotion system
        'USE_2D': False,            # 2D avatar renderer
        'USE_3D': False,            # 3D VRM renderer  
        'USE_SLM': False,            # Small language model
        'USE_LLM': False,            # Full LLM
        'USE_VOICE': False,          # Microphone + TTS
        'USE_SHIMEJI': False,        # Desktop overlay
        'USE_SYSTEM_CONTROL': False,  # OS actions
    }
    
    # Hardware profiles
    PROFILES = {
        'ultra_low': HardwareProfile(
            name='ultra_low',
            tier='micro',
            ram_gb=2,
            cpu_cores=2,
            has_gpu=False,
            flags={'USE_FAST_BRAIN', 'USE_EMOTION'}
        ),
        'balanced': HardwareProfile(
            name='balanced',
            tier='mid',
            ram_gb=8,
            cpu_cores=4,
            has_gpu=False,
            flags={'USE_FAST_BRAIN', 'USE_EMOTION', 'USE_2D', 'USE_SLM'}
        ),
        'full': HardwareProfile(
            name='full',
            tier='high',
            ram_gb=16,
            cpu_cores=8,
            has_gpu=True,
            flags={
                'USE_FAST_BRAIN', 'USE_EMOTION', 'USE_2D', 'USE_3D',
                'USE_SLM', 'USE_LLM', 'USE_VOICE', 'USE_SHIMEJI', 'USE_SYSTEM_CONTROL'
            }
        )
    }
    
    def __init__(self, profile_override: str | None = None):
        self._profile: HardwareProfile
        self._active_flags: Set[str]
        self._locked = False
        
        if profile_override:
            self._load_profile(profile_override)
        else:
            self._detect_hardware()
        
        self._validate_flags()
        self._locked = True
    
    def _detect_hardware(self) -> None:
        """Auto-detect hardware and select appropriate profile."""
        try:
            import psutil
            
            # Get system info
            ram_gb = psutil.virtual_memory().total // (1024**3)
            cpu_cores = psutil.cpu_count(logical=True)
            
            # Simple GPU detection
            has_gpu = self._detect_gpu()
            
            log.info(f"Hardware detected: {ram_gb}GB RAM, {cpu_cores} cores, GPU: {has_gpu}")
            
            # Select profile based on hardware
            if ram_gb < 4:
                profile = 'ultra_low'
            elif ram_gb < 8 or cpu_cores < 4:
                profile = 'ultra_low'
            elif ram_gb < 16 or not has_gpu:
                profile = 'balanced'
            else:
                profile = 'full'
                
            self._load_profile(profile)
            
        except Exception as e:
            log.warning(f"Hardware detection failed: {e}, falling back to ultra_low")
            self._load_profile('ultra_low')
    
    def _detect_gpu(self) -> bool:
        """Simple GPU detection."""
        try:
            import platform
            if platform.system() == 'Windows':
                import wmi
                c = wmi.WMI()
                for gpu in c.Win32_VideoController():
                    if 'NVIDIA' in gpu.Name or 'AMD' in gpu.Name or 'Radeon' in gpu.Name:
                        return True
            else:
                # Try nvidia-smi
                import subprocess
                result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
                return result.returncode == 0
        except Exception:
            pass
        return False
    
    def _load_profile(self, profile_name: str) -> None:
        """Load a specific hardware profile."""
        if profile_name not in self.PROFILES:
            raise ValueError(f"Unknown profile: {profile_name}")
        
        self._profile = self.PROFILES[profile_name]
        self._active_flags = self._profile.flags.copy()
        log.info(f"Loaded profile: {profile_name} with flags: {self._active_flags}")
    
    def _validate_flags(self) -> None:
        """Validate flag combinations."""
        # 3D requires GPU
        if 'USE_3D' in self._active_flags and not self._profile.has_gpu:
            log.warning("3D requested but no GPU detected, disabling USE_3D")
            self._active_flags.discard('USE_3D')
        
        # LLM requires sufficient RAM
        if 'USE_LLM' in self._active_flags and self._profile.ram_gb < 8:
            log.warning("LLM requested but insufficient RAM, disabling USE_LLM")
            self._active_flags.discard('USE_LLM')
        
        # Ensure core flags are always present
        self._active_flags.update({'USE_FAST_BRAIN', 'USE_EMOTION'})
    
    @property
    def profile(self) -> HardwareProfile:
        """Current hardware profile."""
        return self._profile
    
    @property
    def active_flags(self) -> Set[str]:
        """Set of currently active capability flags."""
        return self._active_flags.copy()
    
    def is_enabled(self, flag: str) -> bool:
        """Check if a capability flag is enabled."""
        return flag in self._active_flags
    
    def get_enabled_modules(self) -> List[str]:
        """Get list of enabled module names based on flags."""
        modules = []
        flag_to_module = {
            'USE_2D': 'avatar_2d',
            'USE_3D': 'avatar_3d',
            'USE_SLM': 'slm',
            'USE_LLM': 'llm',
            'USE_VOICE': 'voice',
            'USE_SHIMEJI': 'shimeji',
            'USE_SYSTEM_CONTROL': 'system_control'
        }
        
        for flag, module in flag_to_module.items():
            if self.is_enabled(flag):
                modules.append(module)
        
        return modules
    
    def to_dict(self) -> Dict:
        """Serialize capabilities to dict."""
        return {
            'profile': self._profile.name,
            'tier': self._profile.tier,
            'flags': list(self._active_flags),
            'hardware': {
                'ram_gb': self._profile.ram_gb,
                'cpu_cores': self._profile.cpu_cores,
                'has_gpu': self._profile.has_gpu
            }
        }


# Global instance
_global_capabilities: CapabilityManager | None = None


def get_capabilities() -> CapabilityManager:
    """Get global capability manager instance."""
    global _global_capabilities
    if _global_capabilities is None:
        raise RuntimeError("Capabilities not initialized. Call initialize_capabilities() first.")
    return _global_capabilities


def initialize_capabilities(profile_override: str | None = None) -> CapabilityManager:
    """Initialize global capability manager."""
    global _global_capabilities
    if _global_capabilities is not None:
        raise RuntimeError("Capabilities already initialized.")
    
    _global_capabilities = CapabilityManager(profile_override)
    return _global_capabilities


def reset_capabilities() -> None:
    """Reset global capabilities (for testing)."""
    global _global_capabilities
    _global_capabilities = None