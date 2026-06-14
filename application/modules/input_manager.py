"""
application/modules/input_manager.py

DEPRECATED: This module is no longer used in the modern pipeline.

The modern pipeline is:
  RAW_INPUT → input_mux (InputMux) → INPUT_RECEIVED → preprocess → router → (reflex|slm|llm)

This file is kept for reference but is not subscribed to any events.
Do not use INPUT_NORMALIZED — that event is never emitted.
"""

import asyncio
import logging
from ..core.event_bus import bus
from ..core.context import RequestContext, can_respond

logger = logging.getLogger(__name__)

# DEPRECATED: This module is obsolete. Kept for backward compatibility only.
# The actual pipeline is implemented through direct subscriptions in each module:
# - input_mux.py subscribes to RAW_INPUT
# - preprocess.py subscribes to INPUT_RECEIVED
# - router.py subscribes to PREPROCESS_DONE
# - reflex.py, slm.py, llm.py handle their respective paths

logger.warning("input_manager.py is deprecated and not active in the modern pipeline")
