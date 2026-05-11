import asyncio
import logging
import sys
import os
from typing import Dict

# Ensure src is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("kitsu.main")

# Auto-import modules to register subscribers
import kitsu.modules.preprocess
import kitsu.modules.router
import kitsu.modules.reflex
import kitsu.modules.slm
import kitsu.modules.llm
import kitsu.modules.memory

class ChatApp:
    def __init__(self):
        self.pending_requests: Dict[str, asyncio.Future] = {}

    async def on_response_ready(self, ctx: RequestContext):
        """Long-lived subscriber for response events."""
        if ctx.id in self.pending_requests:
            future = self.pending_requests[ctx.id]
            if not future.done():
                future.set_result(ctx.response)

    async def run(self):
        print("\n--- Kitsu Local AI Fox (Desktop Edition) ---")
        print("Type 'exit' or 'quit' to stop.\n")

        # Register the long-lived subscriber once
        bus.subscribe("RESPONSE_READY", self.on_response_ready)

        loop = asyncio.get_running_loop()

        while True:
            try:
                # Non-blocking input() using executor
                text = await loop.run_in_executor(None, sys.stdin.readline)
                text = text.strip()

                if not text:
                    continue

                if text.lower() in ["exit", "quit"]:
                    break

                # Create request context
                ctx = RequestContext(text=text)

                # Register future for this request
                response_future = loop.create_future()
                self.pending_requests[ctx.id] = response_future

                # Start pipeline
                await bus.emit("INPUT_RECEIVED", ctx)

                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(response_future, timeout=10.0)
                    print(f"\nKitsu: {response}\n")
                except asyncio.TimeoutError:
                    print("\nKitsu: (Timed out waiting for response)\n")
                finally:
                    # Clean up pending request
                    self.pending_requests.pop(ctx.id, None)

            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in chat loop: {e}", exc_info=True)

        print("\nGoodbye!")

if __name__ == "__main__":
    app = ChatApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        pass
