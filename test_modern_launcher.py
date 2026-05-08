#!/usr/bin/env python3
"""
test_modern_launcher.py

Test script for the modern launcher with 4-layer architecture.
"""

import asyncio
import logging
import sys

# Setup path
sys.path.insert(0, '.')

async def test_modern_launcher():
    """Test the modern launcher with proper architecture."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== Testing Modern Launcher ===")
        
        # Import and use modern launcher
        from runtime.modern_launcher import launch_kitsu, shutdown_kitsu
        
        # Launch with safe mode for testing
        success = await launch_kitsu(
            profile_override="ultra_low",  # Use minimal profile for testing
            safe_mode=True,               # Force safe mode
            runtime_config=None
        )
        
        if success:
            logger.info("✅ Modern launcher startup successful!")
            
            # Keep running for a few seconds to test
            logger.info("Running for 5 seconds to test stability...")
            await asyncio.sleep(5)
            
            # Test shutdown
            shutdown_success = await shutdown_kitsu()
            if shutdown_success:
                logger.info("✅ Modern launcher shutdown successful!")
                return True
            else:
                logger.error("❌ Modern launcher shutdown failed!")
                return False
        else:
            logger.error("❌ Modern launcher startup failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    result = asyncio.run(test_modern_launcher())
    sys.exit(0 if result else 1)
