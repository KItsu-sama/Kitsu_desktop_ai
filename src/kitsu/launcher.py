"""
src/kitsu/launcher.py

Modern Launcher - Clean entry point for the modern Kitsu system.

This launcher provides a clean, modern interface to start Kitsu with
the new event-driven architecture.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("kitsu.launcher")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from kitsu.main import ChatApp
from kitsu.first_run import check_modern_setup_complete
from kitsu.splash import ModernSplash
from kitsu.core.event_bus import bus

LOGO = r"""
╭────────────────────────────────────────────────────────── 🦊 KITSU AI - Modern Edition ──────────────────────────────────────────────────────────╮
│                                                                                                                                                            │
│ Modern Event-Driven Architecture                                                                                                                               │
│ • InputMux (Sanity Layer) → EventBus → AI Pipeline                                                                                                            │
│ • Multi-tier processing: FastBrain → SLM → LLM                                                                                                                │
│ • Judge validation and behavior gating                                                                                                                           │
│                                                                                                                                                            │
│ Type /help for commands or start chatting below!                                                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""

class ModernLauncher:
    """Modern launcher for Kitsu AI system."""
    
    def __init__(self):
        self.app = None
        self._running = False
    
    async def start(self):
        """Start the modern Kitsu system."""
        # Display splash screen
        try:
            splash = ModernSplash()
            model = "kitsu:character"  # Default model
            try:
                import json
                from pathlib import Path
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
        
        try:
            # Check if first-run setup is needed
            if not check_modern_setup_complete():
                logger.info("First-run setup needed, running modern initialization...")
                from kitsu.first_run import run_modern_first_run
                success = await run_modern_first_run(interactive=True)
                if not success:
                    print("\n❌ First-run setup failed. Please check logs.")
                    return
            
            # Initialize the chat application
            await bus.start()
            self.app = ChatApp()
            self._running = True
            
            logger.info("Modern Kitsu system starting...")
            
            # Start the main chat loop
            await self.app.run()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error(f"Launcher error: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
        finally:
            self._running = False
            await bus.stop()
            logger.info("Modern Kitsu system stopped")
    
    async def stop(self):
        """Stop the modern Kitsu system."""
        if self._running:
            self._running = False
            logger.info("Modern Kitsu system stopping...")

# Main entry point
async def main():
    """Main entry point for modern Kitsu system."""
    launcher = ModernLauncher()
    await launcher.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
