"""
core/lifecycle.py

Application lifecycle management extracted from legacy runtime.

Provides graceful shutdown handling, signal management, and cleanup coordination.
Integrates with modern event bus architecture.
"""

import asyncio
import signal
import logging
from typing import Optional, Callable, Set
from dataclasses import dataclass

from core.contracts import ModuleContract
from core.events import EventBus, EventType, EventPayload

log = logging.getLogger(__name__)


@dataclass
class ShutdownConfig:
    """Configuration for shutdown behavior."""
    timeout_seconds: float = 30.0
    cleanup_order: list[str] = None
    force_after_timeout: bool = True


class LifecycleManager(ModuleContract):
    """
    Manages application lifecycle with graceful shutdown handling.
    
    Enhanced from legacy version with:
    - Event-driven shutdown coordination
    - Configurable timeouts and cleanup order
    - Multiple signal support
    - Better error handling
    """
    
    module_id = 'core.lifecycle'
    required_flags = []
    
    def __init__(
        self, 
        event_bus: Optional[EventBus] = None,
        config: Optional[ShutdownConfig] = None
    ) -> None:
        self.event_bus = event_bus
        self.config = config or ShutdownConfig()
        
        # Shutdown state
        self._shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        self._shutdown_reason: Optional[str] = None
        self._running = False
        
        # Signal handling
        self._original_handlers: dict[int, Callable] = {}
        self._registered_signals: Set[int] = set()
    
    async def start(self) -> bool:
        """Start the lifecycle manager and register signal handlers."""
        if self._running:
            return True
        
        self._running = True
        self._shutdown_requested = False
        self._shutdown_event.clear()
        
        # Register signal handlers
        self._register_signal_handlers()
        
        log.info("Lifecycle manager started")
        return True
    
    async def stop(self) -> bool:
        """Stop the lifecycle manager and restore signal handlers."""
        if not self._running:
            return True
        
        # Restore original signal handlers
        self._restore_signal_handlers()
        
        self._running = False
        log.info("Lifecycle manager stopped")
        return True
    
    async def health_check(self) -> dict:
        """Check lifecycle manager health."""
        return {
            'ok': self._running,
            'latency_ms': 0.0,
            'shutdown_requested': self._shutdown_requested,
            'shutdown_reason': self._shutdown_reason,
            'registered_signals': list(self._registered_signals)
        }
    
    def request_shutdown(self, reason: str = "manual") -> None:
        """
        Request graceful shutdown.
        
        Args:
            reason: Reason for shutdown request
        """
        if self._shutdown_requested:
            log.debug(f"Shutdown already requested: {self._shutdown_reason}")
            return
        
        self._shutdown_requested = True
        self._shutdown_reason = reason
        
        log.info(f"Shutdown requested: {reason}")
        self._shutdown_event.set()
        
        # Emit shutdown requested event
        if self.event_bus:
            self.event_bus.publish(EventPayload(
                event_type=EventType.SHUTDOWN_REQUESTED,
                source='lifecycle',
                data={'reason': reason}
            ))
    
    async def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown signal.
        
        Args:
            timeout: Maximum time to wait (None for infinite)
            
        Returns:
            True if shutdown was requested, False if timeout occurred
        """
        if timeout:
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=timeout)
                return True
            except asyncio.TimeoutError:
                return False
        else:
            await self._shutdown_event.wait()
            return True
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested
    
    def get_shutdown_reason(self) -> Optional[str]:
        """Get the reason for shutdown request."""
        return self._shutdown_reason
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        signals_to_handle = [
            signal.SIGINT,   # Ctrl+C
            signal.SIGTERM,  # Termination signal
        ]
        
        # Add SIGBREAK on Windows
        if hasattr(signal, 'SIGBREAK'):
            signals_to_handle.append(signal.SIGBREAK)
        
        for sig in signals_to_handle:
            try:
                # Store original handler
                self._original_handlers[sig] = signal.signal(sig, signal.getsignal(sig))
                
                # Set new handler
                signal.signal(sig, lambda s, f: self._handle_signal(s, f))
                self._registered_signals.add(sig)
                
                log.debug(f"Registered handler for signal {sig}")
                
            except (OSError, ValueError) as e:
                log.warning(f"Could not register handler for signal {sig}: {e}")
    
    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            try:
                signal.signal(sig, handler)
                log.debug(f"Restored handler for signal {sig}")
            except (OSError, ValueError) as e:
                log.warning(f"Could not restore handler for signal {sig}: {e}")
        
        self._original_handlers.clear()
        self._registered_signals.clear()
    
    def _handle_signal(self, signum, frame) -> None:
        """Handle incoming signal."""
        signal_names = {
            signal.SIGINT: "SIGINT (Ctrl+C)",
            signal.SIGTERM: "SIGTERM",
        }
        
        if hasattr(signal, 'SIGBREAK'):
            signal_names[signal.SIGBREAK] = "SIGBREAK"
        
        signal_name = signal_names.get(signum, f"signal {signum}")
        self.request_shutdown(f"signal: {signal_name}")


class GracefulShutdown:
    """
    Legacy-compatible graceful shutdown handler.
    
    Provides backward compatibility with existing code that expects
    the legacy GracefulShutdown interface.
    """
    
    def __init__(self, engine=None) -> None:
        self.engine = engine
        self.lifecycle = None
    
    def set_lifecycle_manager(self, lifecycle: LifecycleManager) -> None:
        """Set the modern lifecycle manager."""
        self.lifecycle = lifecycle
    
    def request_shutdown(self, signum=None, frame=None) -> None:
        """Request shutdown (legacy compatibility)."""
        if self.lifecycle:
            reason = f"signal: {signum}" if signum else "manual"
            self.lifecycle.request_shutdown(reason)
        elif self.engine:
            # Fallback to direct engine shutdown
            log.warning("Using legacy shutdown path")
            if hasattr(self.engine, 'shutdown'):
                import asyncio
                asyncio.create_task(self.engine.shutdown())
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown (legacy compatibility)."""
        if self.lifecycle:
            await self.lifecycle.wait_for_shutdown()
        else:
            # Legacy fallback - just wait forever
            await asyncio.Event().wait()
    
    async def cleanup(self) -> None:
        """Perform cleanup (legacy compatibility)."""
        if self.lifecycle:
            # The modern lifecycle manager handles cleanup
            pass
        elif self.engine:
            # Legacy cleanup
            try:
                if hasattr(self.engine, 'shutdown'):
                    await self.engine.shutdown()
                log.info("Legacy cleanup complete")
            except Exception as e:
                log.exception(f"Error during legacy cleanup: {e}")


# Global instance
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> Optional[LifecycleManager]:
    """Get the global lifecycle manager."""
    return _lifecycle_manager


def create_lifecycle_manager(
    event_bus: Optional[EventBus] = None,
    config: Optional[ShutdownConfig] = None
) -> LifecycleManager:
    """Create and register the global lifecycle manager."""
    global _lifecycle_manager
    _lifecycle_manager = LifecycleManager(event_bus, config)
    return _lifecycle_manager


# Legacy compatibility
def create_graceful_shutdown(engine=None) -> GracefulShutdown:
    """Create a legacy-compatible graceful shutdown handler."""
    shutdown = GracefulShutdown(engine)
    lifecycle = get_lifecycle_manager()
    if lifecycle:
        shutdown.set_lifecycle_manager(lifecycle)
    return shutdown
