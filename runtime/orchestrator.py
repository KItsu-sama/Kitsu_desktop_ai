"""
core/orchestrator.py

Main orchestrator for Kitsu. Manages subsystem lifecycle + event routing.

Rules:
- Only imports from core/contracts.py and core/bus.py.
- Receives subsystem instances injected by app/bootstrap.py.
- Wires event routing between subsystems via the bus.
- Runs the main event loop + module lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Type, Any

from runtime.bus import bus
from domain.contracts.contracts import (
    # Legacy contracts
    AIProvider, EmotionProvider, AvatarController, MemoryStore, SystemGateway,
    # Modern contracts  
    ModuleContract, AIProviderContract, MemoryStoreContract,
)
from runtime.events import (
    # Legacy events
    InputReceived, ResponseReady, EmotionChanged, EmotionSignal,
    AvatarExpressionRequest, IdleStateChanged, SubsystemFailed, ShutdownRequested,
    # Modern events
    EventType, EventPayload,
)
from domain.personality.emotion_engine import EmotionEngine
from domain.personality.kitsu_self import KitsuSelf
from domain.personality.emotion_manager import EmotionManager
from runtime.behavior_engine import BehaviorEngine, AttentionConfig
# New focused managers
from runtime.application import Application
from domain.interaction.input_manager import InputManager
from runtime.system_monitor import SystemMonitor
# New interfaces (fix dependency inversion)
from domain.contracts.interfaces import (
    IAvatarController, IPersonalityEngine, ICommandRouter, ITerminalInterface,
    get_interface, InterfaceType
)
# Unified module registry (fix dual architecture)
from runtime.module_registry import get_module_registry, ModuleType
try:
    from runtime.brain.state import KitsuState
    from runtime.brain.router import IntentRouter
    from runtime.brain.binary_reasoner import BinaryReasoner
except ImportError:
    KitsuState = None
    IntentRouter = None
    BinaryReasoner = None
from domain.personality.memory_manager import MemoryManager, MemoryType, MemoryConfig
from domain.personality.reaction_mapper import ReactionMapper
from domain.personality.emotion_controller import EmotionController
from infra.llm.llm_fallback_generator import LLMFallback
try:
    from runtime.compression.hybrid_generator import HybridGenerator, GenerationConfig, GenerationMode
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False

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

    def __init__(self, runtime_config: Optional[Any] = None):
        self.runtime_config = runtime_config
        if runtime_config and hasattr(runtime_config, 'merged'):
            config_dict = runtime_config.merged
        else:
            config_dict = runtime_config or {}
        
        # Safe config extraction
        self.core_config = self._safe_get_config(config_dict, "core")
        self.emotion_config = self._safe_get_config(config_dict, "emotion")
        self.memory_config = self._safe_get_config(config_dict, "memory")
        if HYBRID_AVAILABLE:
            self.hybrid_config = self._safe_get_config(config_dict, "hybrid")
        else:
            self.hybrid_config = {}

        # Legacy subsystems (injected by bootstrap.py)
        self.fast_brain: Optional[AIProvider] = None
        self.slm: Optional[AIProvider] = None
        self.llm: Optional[AIProvider] = None
        self.emotion: Optional[EmotionProvider] = None
        self.avatar: Optional[AvatarController] = None
        self.memory: Optional[MemoryStore] = None
        self.gateway: Optional[SystemGateway] = None
        self.personality: Optional[Any] = None

        # Modern modules (ModuleContract) - use unified registry
        self._registry = get_module_registry()
        self._modules: Dict[str, ModuleContract] = {}
        self._statuses: Dict[str, ModuleStatus] = {}
        
        # Runtime state
        self._running: bool = False
        self._shutdown_event: Optional[asyncio.Event] = None
        self._wired: bool = False
        
        # Application mode management
        self.app_mode = config_dict.get("mode", "text")
        self.app_model = config_dict.get("model", "unknown")

        # Focused managers (initialized later)
        self.application: Optional[Application] = None
        self.input_manager: Optional[InputManager] = None
        self.system_monitor: Optional[SystemMonitor] = None

        # Merged from kitsu_engine
        self.kitsu_self: Optional[KitsuSelf] = None
        self.emotion_engine: Optional[EmotionEngine] = None
        self.emotion_manager: Optional[EmotionManager] = None
        self.emotion_controller: Optional[EmotionController] = None
        self.reaction_mapper: Optional[ReactionMapper] = None
        self.core_memory: Optional[MemoryManager] = None
        self.router = IntentRouter() if IntentRouter else None
        self.reasoner = BinaryReasoner() if BinaryReasoner else None
        self.state = KitsuState() if KitsuState else type('MockState', (), {
            'reset': lambda self: None, 
            'user_input': '', 
            'mood': 'neutral', 
            'style': 'normal', 
            'dominant_emotion': 'neutral', 
            'final_response': '', 
            'processing_stage': 'idle',
            'update_emotional_state': lambda self, *args, **kwargs: None,
            'update_from_emotion_engine': lambda self, *args, **kwargs: None,
            'to_dict': lambda self: {},
            'llm_prompt': '',
        })()
        self.compression = None
        self.hybrid_generator: Optional[HybridGenerator] = None
        self._compression_ready = False
        self.llm_fallback = LLMFallback(memory=None)
        
        # Behavior Engine for attention gate
        behavior_config = AttentionConfig(**self.core_config.get("attention", {}))
        self.behavior_engine = BehaviorEngine(behavior_config)
        
        # Command Router for handling interface commands (use interface)
        self.command_router: Optional[ICommandRouter] = None

        # Initialize focused managers
        from runtime.events import EventBus
        event_bus = EventBus()  # Use legacy bus for compatibility
        self.application = Application(self, event_bus)
        self.input_manager = InputManager(self)
        self.system_monitor = SystemMonitor(self, event_bus)

    # --- ModuleContract Implementation ---

    def _safe_get_config(self, config_dict: Dict[str, Any], key: str) -> Dict[str, Any]:
        """Safely extract a config dictionary, returning empty dict if missing or invalid."""
        try:
            if not isinstance(config_dict, dict):
                return {}
            value = config_dict.get(key, {})
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    async def start(self) -> bool:
        """Start orchestrator + wire all event handlers."""
        # Initialize shutdown event when event loop is available
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        self.wire()
        await self._initialize_engine()
        
        # Initialize command router with self as controller (use interface)
        command_router_impl = get_interface(InterfaceType.COMMAND_ROUTER)
        if command_router_impl and hasattr(command_router_impl, 'route'):
            self.command_router = command_router_impl
        else:
            # Fallback to direct import for compatibility
            from interfaces.desktop.commands.command_router import CommandRouter
            self.command_router = CommandRouter(self)
        
        # Start system monitoring
        if self.system_monitor:
            await self.system_monitor.start_monitoring()
        
        self._running = True
        logger.info("Orchestrator started and wired")
        return True

    async def stop(self) -> bool:
        """Stop orchestrator + shutdown all modules."""
        # Stop system monitoring
        if self.system_monitor:
            await self.system_monitor.stop_monitoring()
        
        await self._shutdown_engine()
        await self.shutdown()
        self._running = False
        logger.info("Orchestrator stopped")
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check across all subsystems."""
        # Use unified registry for detailed health
        registry_health = await self._registry.health_check()
        
        # Use system monitor for detailed health if available
        if self.system_monitor:
            system_health = await self.system_monitor.collect_system_health()
            return {
                'ok': system_health.ok,
                'latency_ms': system_health.avg_latency_ms,
                'module_count': system_health.module_count,
                'healthy_modules': system_health.healthy_modules,
                'failed_modules': system_health.failed_modules,
                'timestamp': system_health.timestamp,
                'registry_health': registry_health,
            }
        
        # Fallback to basic health check
        legacy_status = {
            'fast_brain': getattr(self.fast_brain, 'is_available', lambda: False)() if self.fast_brain else False,
            'slm': await getattr(self.slm, 'is_available', lambda: False)() if self.slm else False,
            'llm': await getattr(self.llm, 'is_available', lambda: False)() if self.llm else False,
            'emotion': True if self.emotion else False,
            'avatar': (self.avatar.is_visible() if hasattr(self.avatar, 'is_visible') else False) if self.avatar else False,
        }
        
        return {
            'ok': all(s.healthy for s in self._statuses.values()) if self._statuses else True,
            'latency_ms': 0.0,
            'legacy_subsystems': legacy_status,
            'module_count': len(self._modules),
            'registry_health': registry_health,
        }

    # --- Legacy Wiring (bootstrap.py calls this) ---

    def wire(self) -> None:
        """Subscribe all legacy event handlers. Called once after injection."""
        if self._wired:
            logger.debug("Orchestrator already wired, skipping duplicate subscriptions")
            return
        
        bus.subscribe(InputReceived, self._on_input)
        bus.subscribe(ResponseReady, self._on_response_ready)
        bus.subscribe(EmotionChanged, self._on_emotion_changed)
        bus.subscribe(SubsystemFailed, self._on_subsystem_failed)
        bus.subscribe(ShutdownRequested, self._on_shutdown_requested)
        self._wired = True
        logger.info("Orchestrator legacy wiring complete.")

    # --- Modern Module Management ---

    async def register(self, module: ModuleContract) -> None:
        """Register a ModuleContract-compliant module."""
        # Register with unified registry
        self._registry.register_module(
            module_id=module.module_id,
            module_class=type(module),
            module_type=ModuleType.MODERN,
            dependencies=getattr(module, 'required_flags', [])
        )
        
        # Keep local mapping for compatibility
        if module.module_id in self._modules:
            raise RuntimeError(f'Module already registered: {module.module_id}')
        self._modules[module.module_id] = module
        self._statuses[module.module_id] = ModuleStatus(module_id=module.module_id)
        logger.debug('Registered module %s', module.module_id)

    async def unregister(self, module_id: str) -> bool:
        """Unregister a module and clean up its resources."""
        if module_id not in self._modules:
            logger.warning('Module not registered: %s', module_id)
            return False
        
        # Stop module if it's running
        if self._statuses[module_id].started:
            await self.stop_module(module_id)
        
        # Clean up
        del self._modules[module_id]
        del self._statuses[module_id]
        logger.debug('Unregistered module %s', module_id)
        return True

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
        """Stop a specific module with timeout and proper exception handling."""
        module = self.get_module(module_id)
        if not module:
            return False
        try:
            # Add timeout to prevent hanging modules from blocking shutdown
            result = await asyncio.wait_for(module.stop(), timeout=10.0)
            # Handle modules that return None instead of boolean
            if result is None:
                result = True
            self._statuses[module_id].started = not result
            return result
        except asyncio.TimeoutError:
            logger.error('Module %s stop timed out after 10 seconds', module_id)
            self._statuses[module_id].last_error = 'Stop timed out'
            self._statuses[module_id].started = False
            return False  # Continue shutdown despite timeout
        except Exception as e:
            logger.exception('Failed to stop %s: %s', module_id, e)
            self._statuses[module_id].last_error = str(e)
            self._statuses[module_id].started = False
            return False  # Continue shutdown despite error

    async def start_all(self) -> bool:
        """Start all registered modules."""
        # Use unified registry for dependency-ordered startup
        success = await self._registry.start_all()
        
        # Update local status for compatibility
        for module_id, module_info in self._registry.get_all_modules().items():
            if module_id in self._statuses:
                self._statuses[module_id].started = (module_info.status.value == 'running')
                self._statuses[module_id].healthy = (module_info.status.value != 'failed')
        
        return success

    async def shutdown(self) -> None:
        """Graceful shutdown of all modules (reverse start order)."""
        # Use unified registry for dependency-ordered shutdown
        await self._registry.stop_all()
        
        # Update local status for compatibility
        for module_id, module_info in self._registry.get_all_modules().items():
            if module_id in self._statuses:
                self._statuses[module_id].started = False
        
        if self._shutdown_event:
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

    # --- Legacy Event Handlers (simplified) ---

    async def _on_input(self, event: InputReceived) -> None:
        """Delegate input processing to InputManager."""
        if self.input_manager:
            await self.input_manager._handle_input(event)
        else:
            logger.warning("InputManager not available, dropping input: %s", event.text)

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
        # Ensure shutdown event is initialized
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
            
        logger.info("Orchestrator main loop started.")
        
        # Start chat loop task
        chat_task = asyncio.create_task(self._chat_loop()) if getattr(self, '_chat_enabled', True) else None
        
        try:
            # Run active monitoring loop with emotion manager heartbeat
            while self._shutdown_event and not self._shutdown_event.is_set():
                try:
                    # EmotionManager heartbeat (1-second tick)
                    if self.emotion_manager:
                        await self.emotion_manager.tick()
                    
                    # Check module health periodically
                    await self._check_module_health()
                    
                    # Wait a short time before next check
                    # Use wait_for with timeout to allow shutdown interruption
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=1.0)
                        break  # If wait_for completes without timeout, shutdown was requested
                    except asyncio.TimeoutError:
                        # Timeout is expected - continue loop (1-second heartbeat)
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
            while not (self._shutdown_event and self._shutdown_event.is_set()):
                try:
                    # Get user input with better error handling
                    try:
                        user_input = await asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: input("\n> ")
                        )
                    except (EOFError, KeyboardInterrupt):
                        # Handle closed stdin or interrupt gracefully
                        logger.info("Input stream closed or interrupted")
                        self.request_stop()
                        break
                    except Exception as e:
                        logger.error("Input error: %s", e)
                        self.request_stop()
                        break
                    
                    # Handle commands
                    if user_input.lower().strip() in ['quit', 'exit', 'q']:
                        logger.info("Quit command received")
                        self.request_stop()
                        break
                    elif user_input.startswith('/'):
                        # Route to command router for / commands (use interface)
                        if self.command_router:
                            try:
                                result = await self.command_router.route(user_input)
                                if result.get('success', False):
                                    print(result.get('output', 'Command executed'))
                                else:
                                    print(f" {result.get('output', 'Command failed')}")
                            except Exception as e:
                                logger.error(f"Command router error: {e}")
                                print(f" Command error: {e}")
                        else:
                            print(" Command router not available")
                    elif user_input.lower().strip() == 'help':
                        self._show_help()
                    elif user_input.lower().strip() == 'status':
                        await self._show_status()
                    elif user_input.strip():
                        # Process regular input through Kitsu engine
                        result = await self.process_input(user_input)
                        bus.publish(ResponseReady(
                            input_text=user_input,
                            response_text=result['response'],
                            source=result.get('source', 'kitsu_engine'),
                            confidence=result.get('confidence', 0.8),
                        ))
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

Use /help for full command list with all interface commands.

Any other text will be processed as chat input.
        """
        print(help_text)
    
    async def _show_status(self) -> None:
        """Show current system status."""
        try:
            status = await self.health_check()
            print(f"\n=== System Status ===")
            print(f"Modules: {status.get('module_count', 0)} registered")
            print(f"Legacy OK: {status.get('legacy_subsystems', {}).get('fast_brain', False)}")
            print(f"Engine OK: {self.emotion_engine is not None}")
            print(f"Overall OK: {status.get('ok', False)}")
            print("========================\n")
        except Exception as e:
            print(f"Error getting status: {e}")
    
    def request_stop(self) -> None:
        """Request orchestrator shutdown."""
        if self._shutdown_event:
            self._shutdown_event.set()
    
    def get_app_mode(self) -> str:
        """Get the current application mode."""
        return self.app_mode
    
    def get_app_model(self) -> str:
        """Get the current application model."""
        return self.app_model
    
    def set_app_mode(self, mode: str) -> None:
        """Set the application mode."""
        self.app_mode = mode
        logger.info(f"Application mode changed to: {mode}")
    
    def set_app_model(self, model: str) -> None:
        """Set the application model."""
        self.app_model = model
        logger.info(f"Application model changed to: {model}")
    
    async def run_interface(self, terminal_interface=None) -> None:
        """
        Run the appropriate interface based on application mode.
        
        Args:
            terminal_interface: Terminal interface instance to use
        """
        logger.info(f"Running in {self.app_mode} mode")
        
        if not terminal_interface:
            # Try to get terminal interface from registry
            terminal_impl = get_interface(InterfaceType.UI)
            if terminal_impl and hasattr(terminal_impl, 'run_text_mode'):
                terminal_interface = terminal_impl
            else:
                # Fallback to direct import for compatibility
                from interfaces.desktop.terminal.interface import TerminalInterface
                terminal_interface = TerminalInterface()
            terminal_interface.set_mode(self.app_mode)
            terminal_interface.set_model(self.app_model)
        
        try:
            if self.app_mode == "voice":
                await terminal_interface.run_voice_mode(self)
            else:
                await terminal_interface.run_text_mode(self)
        except Exception as e:
            logger.exception(f"Interface run error: {e}")
        finally:
            # Cleanup
            if hasattr(self, 'shutdown_handler') and self.shutdown_handler:
                await self.shutdown_handler.cleanup()
            if hasattr(self, '_initialize_engine') and callable(self._initialize_engine):
                await self._initialize_engine()

    async def _initialize_engine(self):
        try:
            await self._initialize_personality()
            await self._initialize_emotion_engine()
            await self._initialize_emotion_manager()
            await self._initialize_memory()
            await self._initialize_emotion_controller()
            await self._initialize_compression()
        except Exception as e:
            logger.error(f"Failed to initialize engine: {e}")
            # Continue without engine

    async def _initialize_personality(self):
        self.kitsu_self = KitsuSelf(
            initial_state=self.core_config.get("personality", {})
        )
        logger.info("Core personality initialized")

    async def _initialize_emotion_engine(self):
        self.emotion_engine = EmotionEngine(
            kitsu_self=self.kitsu_self,
            continuous_decay=self.emotion_config.get("continuous_decay", True),
        )
        logger.info("Emotion engine initialized")

    async def _initialize_emotion_manager(self):
        # Load saved state from memory if available
        saved_state = None
        if self.core_memory:
            try:
                # Try to get saved emotion state from memory
                saved_state = await self.core_memory.retrieve_recent_emotion_state()
            except Exception as e:
                logger.debug(f"Could not load saved emotion state: {e}")
        
        self.emotion_manager = EmotionManager(
            kitsu_identity=self.kitsu_self,
            initial_state=saved_state,
            continuous_decay=False  # Orchestrator controls timing
        )
        logger.info("EmotionManager initialized as SSoT")

    async def _initialize_memory(self):
        config = MemoryConfig(
            max_short_term=self.memory_config.get("max_short_term_memories", 100),
            max_episodic=self.memory_config.get("max_episodic_memories", 50),
        )
        self.core_memory = MemoryManager(kitsu_self=self.kitsu_self, config=config)
        await self.core_memory.start_episodic_session("Core Session")
        logger.info("Core memory initialized")

    async def _initialize_emotion_controller(self):
        self.emotion_controller = EmotionController(
            emotion_engine=self.emotion_engine,
            kitsu_self=self.kitsu_self,
            reaction_mapper=self.reaction_mapper,
            memory_manager=self.core_memory,
        )
        await self.emotion_controller.start()
        logger.info("Emotion controller initialized")

    async def _initialize_compression(self):
        try:
            # Try to import compression pipeline
            try:
                from runtime.compression.pipeline import CompressionPipeline
                self.compression = CompressionPipeline()
                if hasattr(self.compression, 'load_encoder'):
                    self.compression.load_encoder()
                self._compression_ready = (self.compression is not None and 
                                          hasattr(self.compression, 'encoder') and 
                                          self.compression.encoder._is_built)
                logger.info("Compression pipeline initialized")
            except ImportError:
                logger.debug("Compression pipeline not available")
                self.compression = None
                self._compression_ready = False
        except Exception as e:
            logger.error(f"Failed to initialize compression: {e}")
            self.compression = None
            self._compression_ready = False

        # Only initialize hybrid generator if compression is definitely ready
        if HYBRID_AVAILABLE and self._compression_ready and self.compression:
            try:
                self.hybrid_generator = HybridGenerator(
                    compression=self.compression,
                    config=GenerationConfig(**self.hybrid_config)
                )
                logger.info("Hybrid generator initialized")
            except Exception as e:
                logger.error(f"Failed to initialize hybrid generator: {e}")
                self.hybrid_generator = None
        else:
            self.hybrid_generator = None

    async def _shutdown_engine(self):
        if self.emotion_controller:
            await self.emotion_controller.stop()
        if self.core_memory:
            await self.core_memory.stop()
        logger.info("Engine shutdown complete")

    async def process_input(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        force_generation_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        #NOTE: legacy/core/kitsu_engine still need to be refactored to use the new module system 
        """
        Main processing loop.

        Path A — compression ready:
            1. IntentRouter  (pure Python)
            2. EmotionEngine (pure Python)
            3. BinaryReasoner (pure Python)
            4. CompressionPipeline.process(input + state) → binary vector
            5. BinaryTranslator.build_prompt(vector + state) → prompt string
            6. LLMController.executor.execute(prompt) → response text  [1 call]

        Path B — compression not ready (fallback):
        """
        
        # --- Validate input early ---
        if not user_input or not isinstance(user_input, str):
            return {
                "response": "",
                "text": "",
                "emotional_state": {},
                "mood": "neutral",
                "style": "normal",
                "emotion": "neutral",
                "confidence": 0.0,
                "binary_vector": None,
                "debug_log": None,
                "binary_features": {},
                "routing": {"intent": "unknown"},
                "generation_metadata": {},
                "generation_time": 0.0,
                "error": "Invalid input",
                "source": "llm_fallback_generator"
            }

        # --- Start timing for LLM generation ---
        import time
        start_time = time.time()

        # --- Step 1: Reset state, populate input ---
        try:
            self.state.reset()
            self.state.user_input = user_input
        except Exception as e:
            logger.error("Failed to reset state: %s", e)
            # Return error result if state can't be reset
            return {
                "response": "System error: state reset failed",
                "text": "",
                "emotional_state": {},
                "mood": "neutral",
                "style": "normal",
                "emotion": "neutral",
                "confidence": 0.0,
                "binary_vector": None,
                "debug_log": None,
                "binary_features": {},
                "routing": {"intent": "unknown"},
                "generation_metadata": {},
                "generation_time": 0.0,
                "error": "State reset failed",
                "source": "llm_fallback_generator"
            }

        # --- Step 2: Emotional state (pure Python) ---
        # process_user_input fires keyword triggers and updates the emotion stack,
        # then update_from_emotion_engine() pulls resistance, stack_size, is_hidden
        # and all other EmotionEngine fields into KitsuState in one canonical call.
        try:
            if self.emotion_engine:
                self.emotion_engine.process_user_input(user_input, self.state)
                self.state.update_from_emotion_engine(self.emotion_engine)
        except Exception as e:
            logger.warning("Emotion processing failed, continuing with defaults: %s", e)
            # Continue with default state values

        # Convenience locals (read from state so everything is in sync)
        emotional_state = self.emotion_engine.get_emotional_state() if self.emotion_engine else {}
        mood = self.state.mood
        style = self.state.style
        emotion = self.state.dominant_emotion

        # --- Step 3: Intent routing (pure Python) ---
        try:
            routing = await self.router.route(user_input, {"state": self.state}) if self.router else {"intent": "unknown"}
        except Exception as e:
            logger.warning("Intent routing failed: %s", e)
            routing = {"intent": "unknown"}

        # --- Step 4: Binary reasoning (pure Python) ---
        try:
            reasoning = self.reasoner.reason(self.state) if self.reasoner else {"binary_features": {}}
        except Exception as e:
            logger.warning("Binary reasoning failed: %s", e)
            reasoning = {"binary_features": {}}
        binary_features: Dict[str, int] = reasoning.get("binary_features", {})

        # --- Step 5: Memory retrieval if flagged ---
        memory_context = None
        if binary_features.get("memory_relevant") or binary_features.get("use_memory"):
            memory_context = await self._retrieve_memory_context(user_input)

        # --- Step 6: Generate response ---
        response_text = ""
        binary_vector = None
        debug_log = None
        generation_metadata = {}
        source = None

        if self._compression_ready and self.compression and self.hybrid_generator:
            response_text = self.generate_fast_response(routing.get("intent"), {"mood": mood, "style": style, "state": "normal"}, binary_features)
        elif self._compression_ready and self.compression:
            result = await self._generate_compressed(user_input, emotional_state, binary_features, memory_context)
            response_text, binary_vector, debug_log = result
            source = "kitsu_engine"
        else:
            response_text, source = await self._generate_fallback(user_input, mood, style)
        
        # Validate response was generated
        if not response_text or not isinstance(response_text, str):
            logger.warning("Response generation failed or returned invalid type, using fallback")
            response_text = self.llm_fallback.generate(
                mood=mood or "behave",
                style=style or "sweet",
                cause="generation_failed",
                raw_input=user_input
            )
            source = "llm_fallback_generator"

        # Only store non-empty responses in memory
        if response_text and self.core_memory:
            try:
                await self.core_memory.store_memory(
                    content=f"{user_input} -> {response_text}",
                    memory_type=MemoryType.SHORT_TERM,
                    emotional_tags=[emotion],
                    context_tags=["chat"],
                )
            except Exception as e:
                logger.warning("Failed to store memory: %s", e)

        self.state.final_response = response_text
        self.state.processing_stage = "complete"

        end_time = time.time()
        generation_time = end_time - start_time

        result = {
            "response": response_text,
            "text": response_text,
            "emotional_state": emotional_state,
            "mood": mood,
            "style": style,
            "emotion": emotion,
            "avatar_hint": self._safe_get_avatar_hint(),
            "voice_params": self._get_voice_params(emotional_state),
            "memory_references": [],
            "confidence": generation_metadata.get("confidence", 0.8),
            "binary_vector": binary_vector.tolist() if (binary_vector is not None and hasattr(binary_vector, 'tolist')) else None,
            "debug_log": debug_log,
            "binary_features": binary_features,
            "routing": routing,
            "generation_metadata": generation_metadata,
            "generation_time": generation_time,
            "source": source or "llm_fallback_generator",
        }

        # Publish events
        bus.publish(EmotionChanged(mood=mood, style=style, state=emotion, dominant_emotion=emotion, intensity=emotional_state.get("confidence", 0.5)))
        if result.get('avatar_hint'):
            bus.publish(AvatarExpressionRequest(mood=mood, style=style, state=emotion))

        return result

    def generate_fast_response(self, intent, personality, features):
        # Validate personality dict
        if not personality or not isinstance(personality, dict):
            personality = {"mood": "behave", "style": "sweet", "state": "normal"}
            
        mood = personality.get("mood", "behave")
        style = personality.get("style", "sweet")
        state = personality.get("state", "normal")
        
        if intent == "greeting":
            responses = {
                "fox": "Kon! *wags tail*",
                "glitch": "H3LLO HUM4N",
                "behave": "Hello! How are you today?",
            }
            return responses.get(state, "Hello!")
        elif intent == "question":
            return "That's an interesting question. Let me think about it."
        elif intent == "short":
            return "Okay!"
        
        if state == "fox":
            return "*tilts head* What do you mean?"
        elif state == "glitch":
            return "ERR0R: INPUT_UNRECOGNIZED"
        elif mood == "flirty":
            return "Oh, you're so sweet! 😘"
        elif style == "sweet":
            return "I understand. Let's talk more!"
        else:
            return "I see."

    async def _generate_fallback(self, user_input: str, mood: str, style: str) -> Tuple[str, str]:
        """
        Generate response using SLM → LLM → Fallback tier.
        
        Pipeline:
        1. Try SLM (fast, personality-aware)
        2. If SLM confidence is low or unavailable, try LLM
        3. Fall back to personality generator if all else fails
        
        Returns:
            (response_text, source) tuple where source is 'slm', 'llm', or 'llm_fallback_generator'
        """
        personality_hint = f"{mood or 'behave'}, {style or 'sweet'}"
        context = {
            "personality_hint": personality_hint,
            "mood": mood or "behave",
            "style": style or "sweet"
        }
        
        # --- Tier 1: SLM (Small Language Model) ---
        if self.slm:
            try:
                logger.debug("SLM: Attempting fast response generation")
                
                # Check if SLM has the advanced confidence-based interface
                if hasattr(self.slm, 'infer_with_confidence'):
                    response, confidence = await self.slm.infer_with_confidence(user_input, context)
                    
                    if response and hasattr(self.slm, 'needs_llm_escalation'):
                        if not self.slm.needs_llm_escalation(confidence):
                            logger.info("SLM: Response generated with confidence=%.2f", confidence)
                            return response, "slm"
                        else:
                            logger.debug("SLM: Low confidence, escalating to LLM")
                    elif response:
                        logger.info("SLM: Response generated")
                        return response, "slm"
                elif hasattr(self.slm, 'query'):
                    # Fall back to basic sync query interface
                    response = self.slm.query(user_input, context)
                    if response:
                        logger.info("SLM: Response generated via query")
                        return response, "slm"
            except Exception:
                logger.warning("SLM failed")
                return self.llm_fallback.generate(
                    mood=mood or "behave",
                    style=style or "sweet",
                    cause="crash",
                    raw_input=user_input
                ), "llm_fallback_generator"
        
        # --- Tier 2: LLM (Large Language Model) ---
        if self.llm:
            try:
                logger.debug("LLM: Attempting response generation")
                response = self.llm.query(user_input)
                if response:
                    logger.info("LLM: Response generated")
                    return response, "llm"
            except Exception as e:
                logger.warning("LLM failed: %s", e)
        
        # --- Tier 3: Personality Fallback ---
        logger.debug("LLM not available, using personality fallback")
        return self.llm_fallback.generate(
            mood=mood or "behave",
            style=style or "sweet",
            cause="unavailable",
            raw_input=user_input
        ), "llm_fallback_generator"

    def _get_voice_params(self, emotional_state: Dict[str, Any]) -> Dict[str, float]:
        return {"pitch": 1.0, "speed": 1.0}

    def _safe_get_avatar_hint(self) -> Optional[str]:
        """Safely get avatar hint from emotion engine."""
        if not self.emotion_engine:
            return None
        try:
            return self.emotion_engine.get_avatar_hint()
        except Exception as e:
            logger.debug("Failed to get avatar hint: %s", e)
            return None

    async def _generate_compressed(self, user_input: str, emotional_state: Dict[str, Any], binary_features: Dict[str, int], memory_context: Optional[str]):
        """
        Generate response using SLM → LLM tier (compression path).
        
        Pipeline:
        1. Try SLM (fast, personality-aware)
        2. If SLM confidence is low or unavailable, try LLM
        """
        mood = emotional_state.get("dominant_emotion", "behave")
        style = emotional_state.get("style", "sweet")
        personality_hint = f"{mood}, {style}"
        
        context = {
            "personality_hint": personality_hint,
            "emotion_state": str(emotional_state),
            "memory_context": memory_context or ""
        }
        
        # --- Try SLM first ---
        if self.slm:
            try:
                logger.debug("Compressed path: SLM attempting response")
                
                if hasattr(self.slm, 'infer_with_confidence'):
                    response, confidence = await self.slm.infer_with_confidence(user_input, context)
                    
                    if response and hasattr(self.slm, 'needs_llm_escalation'):
                        if not self.slm.needs_llm_escalation(confidence):
                            logger.info("Compressed path: SLM accepted (conf=%.2f)", confidence)
                            return response, None, None
                    elif response:
                        logger.info("Compressed path: SLM response accepted")
                        return response, None, None
                elif hasattr(self.slm, 'query'):
                    response = self.slm.query(user_input, context)
                    if response:
                        logger.info("Compressed path: SLM response via query")
                        return response, None, None
            except Exception as e:
                logger.warning("Compressed path: SLM failed: %s", e)
        
        # --- Fallback to LLM ---
        logger.debug("Compressed path: Escalating to LLM")
        prompt = f"User: {user_input}\nMemory: {memory_context or ''}\nRespond as Kitsu."
        if self.llm:
            response_text = self.llm.query(prompt)
        else:
            response_text = "No response generator available."
        return response_text, None, None




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