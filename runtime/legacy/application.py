"""
src/application.py

Main application lifecycle manager.
Extracted from orchestrator.py to follow Single Responsibility Principle.

See docs/notes/application-lifecycle for detailed documentation.

Responsibilities:
- Application startup/shutdown
- Main event loop coordination
- Module lifecycle orchestration
- Graceful shutdown handling

Non-responsibilities:
- Input processing (→ input_manager.py)
- Health monitoring (→ system_monitor.py) 
- AI routing (→ orchestrator.py)
- UI interaction (→ interfaces)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from domain.contracts.contracts import ModuleContract
from runtime.communication.events import EventBus, EventType, EventPayload

logger = logging.getLogger(__name__)


class Application:
    """
    Main application lifecycle manager.
    
    Coordinates startup sequence, runs main event loop, 
    and handles graceful shutdown of all subsystems.
    """
    
    def __init__(self, orchestrator, event_bus: EventBus):
        self.orchestrator = orchestrator
        self.event_bus = event_bus
        self._running: bool = False
        self._shutdown_event: Optional[asyncio.Event] = None
        
    async def start(self) -> bool:
        """Start application and all registered modules."""
        logger.info("Starting application...")
        
        # Initialize shutdown event
        self._shutdown_event = asyncio.Event()
        
        # Start orchestrator first
        if not await self.orchestrator.start():
            logger.error("Failed to start orchestrator")
            return False
            
        # Start all registered modules
        if not await self.orchestrator.start_all():
            logger.error("Failed to start some modules")
            return False
        
        self._running = True
        logger.info("Application started successfully")
        return True
    
    async def stop(self) -> bool:
        """Stop application and all modules gracefully."""
        logger.info("Stopping application...")
        
        if not self._running:
            logger.debug("Application already stopped")
            return True
            
        self._running = False
        
        # Signal shutdown
        if self._shutdown_event:
            self._shutdown_event.set()
        
        # Stop orchestrator (which stops all modules)
        if not await self.orchestrator.stop():
            logger.error("Failed to stop orchestrator gracefully")
            return False
        
        logger.info("Application stopped")
        return True
    
    async def run(self) -> None:
        """Main application event loop."""
        if not self._running:
            await self.start()
        
        logger.info("Application main loop started")
        
        try:
            # Run orchestrator main loop
            await self.orchestrator.run()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except asyncio.CancelledError:
            logger.info("Application run cancelled")
        except Exception as e:
            logger.error(f"Application main loop error: {e}")
        finally:
            await self.stop()
            logger.info("Application shutdown complete")
    
    def request_shutdown(self, reason: str = "user_request") -> None:
        """Request application shutdown."""
        logger.info(f"Shutdown requested: {reason}")
        if self._shutdown_event:
            self._shutdown_event.set()
        
        # Emit shutdown event
        self.event_bus.emit(
            EventType.APP_SHUTDOWN,
            EventPayload(
                source='application',
                data={'reason': reason}
            )
        )
    
    @property # to check if application is running
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running
    
    @property
    def shutdown_event(self) -> Optional[asyncio.Event]:
        """Get shutdown event for external coordination."""
        return self._shutdown_event
