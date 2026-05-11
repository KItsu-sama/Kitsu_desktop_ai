"""
Strip Controller: Enforce hardware tier constraints on intelligence routing.

Matrix:
  
| Component  | ultra_low        | balanced       | full             |
|------------|------------------|----------------|------------------|
| FastBrain  | ✓ (required)     | ✓ (required)   | ✓ (required)    |
| SLM        | ✗ (forbidden)    | ✓ (optional)   | ✓ (optional)    |
| LLM        | ✗ (forbidden)    | ✗ (forbidden)  | ✓ (optional)    |
| TTS        | ✗ (forbidden)    | ✓ (optional)   | ✓ (optional)    |
| Vector DB  | ✗ (forbidden)    | ✗ (forbidden)  | ✓ (optional)    |

Design:
  - Query capability flags to determine tier
  - Gracefully downgrade to next lower tier if target unavailable
  - No latency impact (< 1ms flags lookup)
"""

from __future__ import annotations

import logging
from typing import Optional

from shared.capability_flags import CapabilityFlags
from runtime.policy_router import RoutingTarget

logger = logging.getLogger('kitsu.router.strip_controller')


class StripController:
    """
    Enforce hardware tier constraints on routing decisions.
    
    Prevents ultra_low devices from attempting SLM/LLM,
    and gracefully downgrades to available resources.
    """

    def __init__(self, flags: CapabilityFlags) -> None:
        """
        Initialize with capability flags from active profile.
        
        Args:
            flags: CapabilityFlags instance from bootstrap
        """
        self.flags = flags

    def _get_available_targets(self) -> set[RoutingTarget]:
        """
        Determine which routing targets are available on this tier.
        
        Returns:
            Set of available RoutingTarget enums
        """
        available = set()

        # FastBrain is always required
        if self.flags.use_fast_brain:
            available.add(RoutingTarget.FASTBRAIN)

        # SLM is optional on mid+ tiers
        if self.flags.use_slm:
            available.add(RoutingTarget.SLM)

        # LLM is optional on high tiers only
        if self.flags.use_llm:
            available.add(RoutingTarget.LLM)

        # Template/fallback always available
        available.add(RoutingTarget.TEMPLATE)

        logger.debug('Available routing targets: %s', {t.value for t in available})
        return available

    async def enforce(self, requested_target: RoutingTarget) -> RoutingTarget:
        """
        Enforce tier constraints on requested target.
        
        If requested target unavailable, gracefully degrade to next lower tier.
        
        Degradation chain:
          LLM → SLM → FastBrain → Template
        
        Args:
            requested_target: Desired RoutingTarget from policy router
        
        Returns:
            Available RoutingTarget (same as requested, or downgraded)
        """
        available = self._get_available_targets()

        # If requested target available, use it
        if requested_target in available:
            return requested_target

        # Degradation chain
        degradation_chain = [
            (RoutingTarget.LLM, RoutingTarget.SLM),
            (RoutingTarget.SLM, RoutingTarget.FASTBRAIN),
            (RoutingTarget.FASTBRAIN, RoutingTarget.TEMPLATE),
            (RoutingTarget.TEMPLATE, RoutingTarget.TEMPLATE),  # terminal fallback
        ]

        current = requested_target
        for source, fallback in degradation_chain:
            if current == source:
                if fallback in available:
                    logger.debug(
                        'Tier constraint: downgrading %s → %s',
                        source.value,
                        fallback.value
                    )
                    return fallback
                current = fallback

        # Should never reach here (TEMPLATE is always available)
        logger.warning(
            'Tier constraint: no available targets found; defaulting to FASTBRAIN'
        )
        return RoutingTarget.FASTBRAIN

    async def check_memory_available(self, target: RoutingTarget) -> bool:
        """
        Check if enough memory is available for target.
        
        Supplementary check beyond capability flags.
        Can be used to refuse SLM load if system is under memory pressure.
        
        Args:
            target: RoutingTarget to check memory for
        
        Returns:
            True if enough memory estimated to be available
        """
        try:
            import psutil
            available_mb = psutil.virtual_memory().available / (1024 ** 2)
            
            # Rough estimates (can be tuned)
            memory_requirements = {
                RoutingTarget.FASTBRAIN: 50,      # always in RAM
                RoutingTarget.TEMPLATE: 10,        # minimal
                RoutingTarget.SLM: 300,            # micro-SLM + context
                RoutingTarget.LLM: 2000,           # large model + context
            }
            
            required = memory_requirements.get(target, 50)
            is_available = available_mb >= required
            
            if not is_available:
                logger.debug(
                    'Memory check: %s needs %.0fMB, but only %.0fMB available',
                    target.value,
                    required,
                    available_mb
                )
            
            return is_available
        except ImportError:
            logger.debug('psutil not available; skipping memory check')
            return True
        except Exception:
            logger.exception('Memory check failed; assuming available')
            return True

    def describe_tier(self) -> dict[str, bool]:
        """
        Describe the current tier's capabilities.
        
        Returns:
            Dict of capability flags for introspection
        """
        return {
            'use_fast_brain': self.flags.use_fast_brain,
            'use_slm': self.flags.use_slm,
            'use_llm': self.flags.use_llm,
            'use_2d': self.flags.use_2d,
            'use_3d': self.flags.use_3d,
            'use_voice': self.flags.use_voice,
            'use_emotion': self.flags.use_emotion,
            'use_system_control': self.flags.use_system_control,
        }
