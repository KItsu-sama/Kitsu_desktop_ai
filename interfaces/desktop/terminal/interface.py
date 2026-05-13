"""
interfaces/desktop/terminal/interface.py

Terminal interface management.

Handles application mode selection and terminal interface setup.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from rich.console import Console

from .splash import SplashScreen
from .banner import Banner

log = logging.getLogger(__name__)


class TerminalInterface:
    """
    Terminal interface manager that handles mode selection and UI setup.
    
    Extracted from legacy/runtime/app.py mode management functionality.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.splash = SplashScreen(self.console)
        self.banner = Banner(self.console)
        self.mode = "text"
        self.model = "unknown"
    
    def set_mode(self, mode: str) -> None:
        """Set the application mode."""
        self.mode = mode
        log.info(f"Application mode set to: {mode}")
    
    def set_model(self, model: str) -> None:
        """Set the model name."""
        self.model = model
        log.info(f"Model set to: {model}")
    
    def display_startup_screen(self) -> None:
        """Display the complete startup screen."""
        self.splash.display_splash(self.mode, self.model)
    
    def display_help_text(self) -> None:
        """Display help information."""
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
        self.console.print(help_text)
    
    async def run_text_mode(self, orchestrator) -> None:
        """
        Run text chat interface.
        
        Args:
            orchestrator: The main orchestrator instance
        """
        log.info("Starting text mode interface")
        
        try:
            # Create concurrent tasks for chat and shutdown
            chat_task = asyncio.create_task(
                self._chat_loop(orchestrator),
                name="terminal_chat"
            )
            shutdown_task = asyncio.create_task(
                self._wait_for_shutdown(orchestrator),
                name="shutdown_watcher"
            )
            
            # Wait for either to complete
            done, pending = await asyncio.wait(
                [chat_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            log.exception(f"Text mode error: {e}")
    
    async def run_voice_mode(self, orchestrator) -> None:
        """
        Run voice interface (placeholder).
        
        Args:
            orchestrator: The main orchestrator instance
        """
        log.warning("Voice mode not yet implemented")
        log.info("Falling back to text mode...")
        await self.run_text_mode(orchestrator)
    
    async def _chat_loop(self, orchestrator) -> None:
        """Interactive chat loop for user input."""
        log.info("Chat loop started. Type 'help' for commands or 'quit' to exit.")
        
        try:
            while not orchestrator._shutdown_event.is_set():
                try:
                    # Get user input with better error handling
                    try:
                        user_input = await asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: input("\n> ")
                        )
                    except (EOFError, KeyboardInterrupt):
                        log.info("Input stream closed or interrupted")
                        orchestrator.request_stop()
                        break
                    except Exception as e:
                        log.error("Input error: %s", e)
                        orchestrator.request_stop()
                        break
                    
                    # Handle commands
                    if user_input.lower().strip() in ['/quit', '/exit', '/q']:
                        log.info("Quit command received")
                        orchestrator.request_stop()
                        break
                    elif user_input.startswith('/'):
                        # Route to command router for / commands
                        if orchestrator.command_router:
                            try:
                                result = await orchestrator.command_router.route(user_input)
                                if result.get('success', False):
                                    print(result.get('output', 'Command executed'))
                                else:
                                    print(f" {result.get('output', 'Command failed')}")
                            except Exception as e:
                                log.error(f"Command router error: {e}")
                                print(f" Command error: {e}")
                        else:
                            print(" Command router not available")
                    elif user_input.lower().strip() == 'help':
                        self.display_help_text()
                    elif user_input.lower().strip() == 'status':
                        await self._show_status(orchestrator)
                    elif user_input.strip():
                        # Process regular input through orchestrator
                        result = await orchestrator.process_input(user_input)
                        print(f"\n{result.get('source', 'kitsu').upper()}: {result.get('response', 'No response')}")
                        if result.get('confidence') and result['confidence'] < 1.0:
                            print(f"(confidence: {result['confidence']:.2f})")
                        print()
                        
                except EOFError:
                    log.info("EOF received - shutting down")
                    orchestrator.request_stop()
                    break
                except KeyboardInterrupt:
                    log.info("Keyboard interrupt in chat loop")
                    orchestrator.request_stop()
                    break
                    
        except asyncio.CancelledError:
            log.info("Chat loop cancelled")
        except Exception as e:
            log.error("Error in chat loop: %s", e)
    
    async def _wait_for_shutdown(self, orchestrator) -> None:
        """Wait for shutdown signal."""
        await orchestrator._shutdown_event.wait()
    
    async def _show_status(self, orchestrator) -> None:
        """Show current system status."""
        try:
            status = await orchestrator.health_check()
            print(f"\n=== System Status ===")
            print(f"Modules: {status.get('module_count', 0)} registered")
            print(f"Legacy OK: {status.get('legacy_subsystems', {}).get('fast_brain', False)}")
            print(f"Engine OK: {orchestrator.emotion_engine is not None}")
            print(f"Overall OK: {status.get('ok', False)}")
            print("========================\n")
        except Exception as e:
            print(f"Error getting status: {e}")
