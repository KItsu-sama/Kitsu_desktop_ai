"""
Modern InputManager Module - Coordinates AI pipeline for the modern system.

This module acts as a coordinator that routes events between the existing
AI modules (SLM, LLM, etc.) and provides a unified interface.
"""

import asyncio
import logging
from kitsu.core.event_bus import bus
from kitsu.core.context import RequestContext, can_respond

logger = logging.getLogger(__name__)

class InputManager:
    """
    Modern Input Manager - coordinates AI pipeline processing.
    
    Instead of reimplementing the AI pipeline, this module
    coordinates the existing modules and ensures proper event flow.
    """
    
    def __init__(self):
        self.module_id = 'input_manager'
        self._initialized = False
        
    async def process_normalized_input(self, ctx: RequestContext) -> None:
        """
        Process normalized input by routing to appropriate AI module.
        
        This coordinator delegates to the existing SLM/LLM modules
        rather than reimplementing the pipeline logic.
        """
        try:
            if not can_respond(ctx):
                logger.debug(f"Skipping already responded request: {ctx.id}")
                return
            
            logger.info(f"Processing input: {ctx.text[:50]}... (id={ctx.id})")
            
            # Route to SLM path - let existing modules handle the pipeline
            await bus.emit("SLM_PATH", ctx)
                
        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            ctx.response = "Sorry, I encountered an error processing your request."
            await bus.emit("RESPONSE_READY", ctx)

# Auto-register the module
input_manager = InputManager()

# Subscribe to normalized input events
async def on_input_normalized(ctx: RequestContext):
    """Handle normalized input events."""
    await input_manager.process_normalized_input(ctx)

# Register subscriber when module is imported
bus.subscribe("INPUT_NORMALIZED", on_input_normalized)
logger.info("InputManager module registered")
