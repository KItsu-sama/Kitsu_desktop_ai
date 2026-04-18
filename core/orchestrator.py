"""
core/orchestrator.py

Main orchestrator for Kitsu. Manages subsystem lifecycle + event routing.

Rules:
- Only imports from core/contracts.py and core/bus.py.
- Never imports from ai/, personality/, ui/, system/, etc.
- Receives subsystem instances injected by app/bootstrap.py.
- Wires event routing between subsystems via the bus.
- Runs the main event loop + module lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from core.bus import bus
from core.contracts import (
    # Legacy contracts
    AIProvider, EmotionProvider, AvatarController, MemoryStore, SystemGateway,
    # Modern contracts  
    ModuleContract, AIProviderContract, MemoryStoreContract,
)
from core.events import (
    # Legacy events
    InputReceived, ResponseReady, EmotionChanged, EmotionSignal,
    AvatarExpressionRequest, IdleStateChanged, SubsystemFailed, ShutdownRequested,
    # Modern events
    EventType, EventPayload,
)

logger = logging.getLogger(__name__)


@dataclass
class ModuleStatus:
    """Status tracking for registered modules."""
    module_id: str
    healthy: bool = False
    started: bool = False
    last_error: Optional[str] = None


class Orchestrator(ModuleContract):
    """Unified orchestrator for both legacy and modern subsystems."""
    
    module_id = 'core.orchestrator'
    required_flags: List[str] = []

    def __init__(self) -> None:
        # Legacy subsystems (injected by bootstrap.py)
        self.fast_brain: Optional[AIProvider] = None
        self.slm: Optional[AIProvider] = None
        self.llm: Optional[AIProvider] = None
        self.emotion: Optional[EmotionProvider] = None
        self.avatar: Optional[AvatarController] = None
        self.memory: Optional[MemoryStore] = None
        self.gateway: Optional[SystemGateway] = None
        self.personality: Optional[Any] = None

        # Modern modules (ModuleContract)
        self._modules: Dict[str, ModuleContract] = {}
        self._statuses: Dict[str, ModuleStatus] = {}
        
        # Runtime state
        self._running: bool = False
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._chat_enabled: bool = True

    # --- ModuleContract Implementation ---

    async def start(self) -> bool:
        """Start orchestrator + wire all event handlers."""
        self.wire()
        self._running = True
        logger.info("Orchestrator started and wired")
        return True

    async def stop(self) -> bool:
        """Stop orchestrator + shutdown all modules."""
        await self.shutdown()
        self._running = False
        logger.info("Orchestrator stopped")
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check across all subsystems."""
        results = {}
        
        # Legacy subsystems
        legacy_status = {
            'fast_brain': getattr(self.fast_brain, 'is_available', lambda: False)() if self.fast_brain else False,
            'slm': getattr(self.slm, 'is_available', lambda: False)() if self.slm else False,
            'llm': getattr(self.llm, 'is_available', lambda: False)() if self.llm else False,
            'emotion': True if self.emotion else False,
            'avatar': self.avatar.is_visible() if self.avatar else False,
        }
        results['legacy'] = legacy_status
        
        # Modern modules
        results['modules'] = self.get_status()
        
        return {
            'ok': all(s.healthy for s in self._statuses.values()) if self._statuses else True,
            'latency_ms': 0.0,
            'legacy_subsystems': legacy_status,
            'module_count': len(self._modules),
        }

    # --- Legacy Wiring (bootstrap.py calls this) ---

    def wire(self) -> None:
        """Subscribe all legacy event handlers. Called once after injection."""
        bus.subscribe(InputReceived, self._on_input)
        bus.subscribe(ResponseReady, self._on_response_ready)
        bus.subscribe(EmotionChanged, self._on_emotion_changed)
        bus.subscribe(SubsystemFailed, self._on_subsystem_failed)
        bus.subscribe(ShutdownRequested, self._on_shutdown_requested)
        logger.info("Orchestrator legacy wiring complete.")

    # --- Modern Module Management ---

    async def register(self, module: ModuleContract) -> None:
        """Register a ModuleContract-compliant module."""
        if module.module_id in self._modules:
            raise RuntimeError(f'Module already registered: {module.module_id}')
        self._modules[module.module_id] = module
        self._statuses[module.module_id] = ModuleStatus(module_id=module.module_id)
        logger.debug('Registered module %s', module.module_id)

    def get_module(self, module_id: str) -> Optional[ModuleContract]:
        """Get registered module by ID."""
        return self._modules.get(module_id)

    async def start_module(self, module_id: str) -> bool:
        """Start a specific module."""
        module = self.get_module(module_id)
        if not module:
            logger.error('Unknown module %s', module_id)
            return False
        
        try:
            result = await module.start()
            self._statuses[module_id].started = result
            self._statuses[module_id].healthy = result
            if result:
                bus.publish(EventPayload(
                    event_type=EventType.MODULE_STARTED,
                    source='orchestrator',
                    data={'module_id': module_id}
                ))
            return result
        except Exception as exc:
            self._statuses[module_id].last_error = str(exc)
            bus.publish(EventPayload(
                event_type=EventType.MODULE_FAILED,
                source='orchestrator',
                data={'module_id': module_id, 'error': str(exc)}
            ))
            logger.exception('Failed to start %s', module_id)
            return False

    async def stop_module(self, module_id: str) -> bool:
        """Stop a specific module."""
        module = self.get_module(module_id)
        if not module:
            return False
        try:
            result = await module.stop()
            # Handle modules that return None instead of boolean
            if result is None:
                result = True
            self._statuses[module_id].started = not result
            return result
        except Exception:
            logger.exception('Failed to stop %s', module_id)
            return False

    async def start_all(self) -> bool:
        """Start all registered modules."""
        for module_id in self._modules:
            if not await self.start_module(module_id):
                logger.warning('Failed to start module %s', module_id)
                return False
        return True

    async def shutdown(self) -> None:
        """Graceful shutdown of all modules (reverse start order)."""
        # Don't try to stop ourselves - that would cause infinite recursion
        for module_id in reversed(list(self._modules.keys())):
            if module_id != self.module_id:  # Skip self
                await self.stop_module(module_id)
        self._shutdown_event.set()
        bus.publish(EventPayload(
            event_type=EventType.APP_SHUTDOWN,
            source='orchestrator',
            data=None
        ))

    def get_status(self) -> Dict[str, ModuleStatus]:
        """Get status of all registered modules."""
        return dict(self._statuses)
    
    async def _check_module_health(self) -> None:
        """Periodic health check for all modules."""
        try:
            for module_id, status in self._statuses.items():
                if status.started:
                    module = self._modules.get(module_id)
                    if module and hasattr(module, 'health_check'):
                        try:
                            health_result = await module.health_check()
                            # Update health status based on health_check result
                            if isinstance(health_result, dict):
                                status.healthy = health_result.get('ok', True)
                            else:
                                status.healthy = bool(health_result)
                        except Exception as e:
                            logger.debug("Health check failed for %s: %s", module_id, e)
                            status.healthy = False
                            status.last_error = str(e)
        except Exception as e:
            logger.debug("Error during module health check: %s", e)

    # --- Legacy Event Handlers (unchanged) ---

    def _on_input(self, event: InputReceived) -> None:
        """Route input through the legacy AI pipeline."""
        # FastBrain first
        if self.fast_brain and self.fast_brain.is_available():
            response = self.fast_brain.query(event.text)
            if response is not None:
                if self.personality and isinstance(response, str):
                    try:
                        response = self.personality.decorate_response(response, source='fast_brain')
                    except Exception as exc:
                        logger.warning('Personality injection failed: %s', exc)

                bus.publish(ResponseReady(
                    input_text=event.text,
                    response_text=response,
                    source="fast_brain",
                    confidence=1.0,
                ))
                return

        # SLM fallback
        if self.slm and self.slm.is_available():
            response = self.slm.query(event.text)
            if response is not None:
                if self.personality and isinstance(response, str):
                    try:
                        response = self.personality.decorate_response(response, source='slm')
                    except Exception as exc:
                        logger.warning('Personality injection failed: %s', exc)

                bus.publish(ResponseReady(
                    input_text=event.text,
                    response_text=response,
                    source="slm",
                    confidence=0.75,
                ))
                return

        # LLM fallback
        if self.llm and self.llm.is_available():
            response = self.llm.query(event.text)
            if response is not None:
                if self.personality and isinstance(response, str):
                    try:
                        response = self.personality.decorate_response(response, source='llm')
                    except Exception as exc:
                        logger.warning('Personality injection failed: %s', exc)

                bus.publish(ResponseReady(
                    input_text=event.text,
                    response_text=response,
                    source="llm",
                    confidence=0.9,
                ))
                return

        logger.warning("No AI provider could handle input: %r", event.text)

    def _on_response_ready(self, event: ResponseReady) -> None:
        """Feed the final response back into FastBrain learning loop and display to user."""
        if self.fast_brain:
            self.fast_brain.train(event.input_text, event.response_text)
        
        # Display response to user in chat
        print(f"\n{event.source.upper()}: {event.response_text}")
        if event.confidence < 1.0:
            print(f"(confidence: {event.confidence:.2f})")
        print()  # Add spacing after response

    def _on_emotion_changed(self, event: EmotionChanged) -> None:
        """Forward emotion state to avatar."""
        if self.avatar:
            self.avatar.set_expression(event.mood, event.style, event.state)

    def _on_subsystem_failed(self, event: SubsystemFailed) -> None:
        logger.error("Subsystem failure: %s — %s", event.subsystem, event.error)

    def _on_shutdown_requested(self, event: ShutdownRequested) -> None:
        logger.info("Shutdown requested: %s", event.reason)
        asyncio.create_task(self.shutdown())

    # --- Main Loop ---

    async def run(self) -> None:
        """Run the main orchestrator event loop."""
        logger.info("Orchestrator main loop started.")
        
        # Start chat loop task
        chat_task = asyncio.create_task(self._chat_loop()) if self._chat_enabled else None
        
        try:
            # Run active monitoring loop instead of just waiting
            while not self._shutdown_event.is_set():
                try:
                    # Check module health periodically
                    await self._check_module_health()
                    
                    # Wait a short time before next check
                    # Use wait_for with timeout to allow shutdown interruption
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=1.0)
                        break  # If wait_for completes without timeout, shutdown was requested
                    except asyncio.TimeoutError:
                        # Timeout is expected - continue loop
                        continue
                except asyncio.CancelledError:
                    # Handle cancellation gracefully
                    logger.info("Orchestrator run cancelled")
                    break
                except Exception as e:
                    logger.error("Error in orchestrator main loop: %s", e)
                    await asyncio.sleep(1.0)  # Prevent rapid error loops
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except asyncio.CancelledError:
            logger.info("Orchestrator run cancelled")
        finally:
            # Cancel chat task if running
            if chat_task and not chat_task.done():
                chat_task.cancel()
                try:
                    await chat_task
                except asyncio.CancelledError:
                    pass
            logger.info("Orchestrator main loop stopped.")

    async def _chat_loop(self) -> None:
        """Interactive chat loop for user input."""
        logger.info("Chat loop started. Type 'help' for commands or 'quit' to exit.")
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Get user input
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: input("\n> ")
                    )
                    
                    # Handle commands
                    if user_input.lower().strip() in ['quit', 'exit', 'q']:
                        logger.info("Quit command received")
                        self.request_stop()
                        break
                    elif user_input.lower().strip() == 'help':
                        self._show_help()
                    elif user_input.lower().strip() == 'status':
                        self._show_status()
                    elif user_input.strip():
                        # Process regular input through AI pipeline
                        bus.publish(InputReceived(text=user_input))
                    
                except EOFError:
                    logger.info("EOF received - shutting down")
                    self.request_stop()
                    break
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt in chat loop")
                    self.request_stop()
                    break
                    
        except asyncio.CancelledError:
            logger.info("Chat loop cancelled")
        except Exception as e:
            logger.error("Error in chat loop: %s", e)
    
    def _show_help(self) -> None:
        """Show available commands."""
        help_text = """
Available commands:
  help    - Show this help message
  status  - Show system status
  quit    - Exit the application
  exit    - Exit the application
  q       - Exit the application

Any other text will be processed as chat input.
        """
        print(help_text)
    
    def _show_status(self) -> None:
        """Show current system status."""
        try:
            status = asyncio.get_event_loop().run_until_complete(self.health_check())
            print(f"\n=== System Status ===")
            print(f"Modules: {status.get('module_count', 0)} registered")
            print(f"Legacy OK: {status.get('legacy_subsystems', {}).get('fast_brain', False)}")
            print(f"Overall OK: {status.get('ok', False)}")
            print("========================\n")
        except Exception as e:
            print(f"Error getting status: {e}")
    
    def request_stop(self) -> None:
        """Request orchestrator shutdown."""
        self._shutdown_event.set()


# Global singleton
orchestrator: Orchestrator = Orchestrator()

# ---------------------------------------------------------------------------
# Usage:
"""
orch = Orchestrator()
orch.fast_brain = FastBrain()
orch.wire()
await orch.run()

# NEW
await orchestrator.register(AIModule())
await orchestrator.start_all()
await orchestrator.run()
"""