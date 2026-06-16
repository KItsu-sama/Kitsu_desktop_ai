"""
application/launcher.py

Modern Launcher - Clean entry point for the modern Kitsu system.

This launcher provides a clean, modern interface to start Kitsu with
the new event-driven architecture. Includes runtime state tracking,
crash recovery, and safe-mode support.

Startup phases:
1. BOOTING - Initial state
2. Configuration loading and validation
3. First-run setup (if needed)
4. Event bus initialization
5. Application initialization
6. RUNNING - Full operation
7. SHUTTING_DOWN - Graceful shutdown
8. STOPPED/FAILED - Final state
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

logger = logging.getLogger("launcher")


# Make both the project root and the application package root importable
APP_ROOT = Path(__file__).parent
PROJECT_ROOT = APP_ROOT.parent
for path in (str(APP_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from .main import ChatApp
from .first_run import check_setup_complete
from .splash import Splash
from .core.event_bus import bus
from runtime.core.runtime_state import RuntimeState, RuntimeStateStore
from runtime.core.crash_manager import (
    record_crash,
    check_should_force_safe_mode,
    mark_boot_successful,
    init_crash_logging,
)

LOGO = r"""
╭────────────────────────────────────────────────────────── 🦊 KITSU AI ──────────────────────────────────────────────────────────╮
│                                                                                                                                            │
│ Event-Driven Architecture                                                                                                                   │
│ • InputMux (Sanity Layer) → EventBus → AI Pipeline                                                                                           │
│ • Multi-tier processing: FastBrain → SLM → LLM                                                                                               │
│ • Judge validation and behavior gating                                                                                                       │
│                                                                                                                                            │
│ Type /help for commands or start chatting below!                                                                                            │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""

class Launcher:
    """Launcher for Kitsu AI system with state tracking and crash recovery."""
    
    def __init__(self, safe_mode: bool = False):
        self.app = None
        self._running = False
        self._safe_mode = safe_mode
        self.state_store = RuntimeStateStore.get_singleton()
    
    async def start(self):
        """Start the modern Kitsu system with state tracking."""
        init_crash_logging()
        success = False
        
        try:
            # Phase 1: BOOTING state
            self.state_store.set_state(
                RuntimeState.BOOTING,
                reason="Application startup initiated"
            )
            
            # Apply CLI safe mode early so downstream startup can honor it.
            if self._safe_mode:
                os.environ.setdefault("KITSU_SAFE_MODE", "1")
                os.environ.setdefault("kitsu_SAFE_MODE", "1")
                logger.info("Safe mode enabled from launcher CLI")

            # Check if safe mode should be forced due to crash history or env.
            if check_should_force_safe_mode():
                self._safe_mode = True
                logger.warning("Safe mode forced due to crash history")
                self.state_store.set_safe_mode_forced(True)
            
            # Phase 2: Display splash screen
            try:
                splash = Splash()
                model = "kitsu:character"  # Default model
                try:
                    import json
                    config_path = Path("data/config.json")
                    if config_path.exists():
                        config = json.loads(config_path.read_text())
                        model = config.get("model", model)
                except Exception:
                    pass  # Use default if config fails
                
                splash.display_splash(mode="text", model=model)
            except Exception as e:
                logger.warning(f"Splash screen failed: {e}")
                print(LOGO)
            
            # Phase 3: First-run setup check
            if not check_setup_complete():
                logger.info("First-run setup needed, running initialization...")
                try:
                    from .first_run import run_first_run
                    init_success = await run_first_run(interactive=True)
                    if not init_success:
                        msg = "First-run setup failed"
                        print(f"\n❌ {msg}")
                        self.state_store.set_state(
                            RuntimeState.FAILED,
                            reason=msg
                        )
                        return False
                except Exception as e:
                    self.state_store.set_state(
                        RuntimeState.FAILED,
                        reason="First-run setup crashed",
                        exception=e
                    )
                    record_crash("first_run", e)
                    raise
            
            # Phase 4: Event bus initialization
            try:
                await bus.start()
                logger.info("Event bus initialized")
            except Exception as e:
                self.state_store.set_state(
                    RuntimeState.FAILED,
                    reason="Event bus initialization failed",
                    exception=e
                )
                record_crash("event_bus_init", e)
                raise
            
            # Phase 5: Application initialization
            try:
                self.app = ChatApp()
                self._running = True
                logger.info("Chat application initialized")
            except Exception as e:
                self.state_store.set_state(
                    RuntimeState.FAILED,
                    reason="Chat application initialization failed",
                    exception=e
                )
                record_crash("app_init", e)
                raise
            
            # Phase 6a: Optional EmotionEngine startup (degraded if fails)
            try:
                from domain.personality.emotion_engine import EmotionEngine
                emotion_engine = EmotionEngine.get_singleton()
                asyncio.create_task(emotion_engine.run())
                logger.info("EmotionEngine background task started")
            except (ImportError, AttributeError, RuntimeError) as e:
                # Degrade instead of failing completely
                self.state_store.set_state(
                    RuntimeState.DEGRADED,
                    reason="EmotionEngine failed to start (degraded mode)"
                )
                logger.warning(f"EmotionEngine not available - running in degraded mode: {e}")
            
            # Phase 6b: RUNNING state
            logger.info("Kitsu system starting...")
            self.state_store.set_state(
                RuntimeState.RUNNING,
                reason="System fully initialized and operational"
            )
            
            # Mark boot as successful (crash counter reset)
            mark_boot_successful()
            
            # Phase 7: Main chat loop
            await self.app.run()
            success = True
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            logger.info("Shutdown requested by user")
            self.state_store.set_state(RuntimeState.SHUTTING_DOWN, reason="User interrupt")
        except Exception as e:
            logger.error(f"Launcher error: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            
            # Record crash if not already recorded
            if self.state_store.get_state() != RuntimeState.FAILED:
                self.state_store.set_state(
                    RuntimeState.FAILED,
                    reason="Unhandled launcher exception",
                    exception=e
                )
                record_crash("launcher_main", e)
        finally:
            # Phase 8: Graceful shutdown
            self._running = False
            self.state_store.set_state(RuntimeState.SHUTTING_DOWN, reason="Cleanup phase")
            
            try:
                await bus.stop()
                logger.info("Event bus stopped")
            except Exception as e:
                logger.error(f"Error stopping event bus: {e}")
            
            self.state_store.set_state(RuntimeState.STOPPED, reason="Application stopped")
            logger.info("Kitsu system stopped")

        return success
    
    async def stop(self):
        """Stop the modern Kitsu system."""
        if self._running:
            self._running = False
            self.state_store.set_state(RuntimeState.SHUTTING_DOWN, reason="Explicit stop requested")
            logger.info("Modern Kitsu system stopping...")

# Main entry point
async def main():
    """Main entry point for Kitsu system."""
    launcher = Launcher()
    await launcher.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


# NOTE : add No ServiceContainer (DI) ,ModuleRegistry ,LifecycleManager ,RuntimeOrchestrator ,phased startup (Phase 0-5)