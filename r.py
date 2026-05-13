#!/usr/bin/env python3
"""
r.py — Kitsu Desktop AI Entry Point

Single unified CLI wrapper that:
  - Parses command-line arguments
  - Configures the runtime environment
  - Delegates to ModernLauncher for all runtime operations

This is the ONLY public entry point. No application logic here.
"""

import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path

# Setup unbuffered output and UTF-8 encoding
sys.stdin.reconfigure(encoding='utf-8', errors='ignore')
os.environ['PYTHONUNBUFFERED'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'



LOGO = r""" 
=============================||=============================

                ░\                        /░
             /░/  ░\                    /░  \░\
           /░/      \░\              /░/      \░\
           ░/         \░\          /░/         \░
         /░░           \░\        /░/           ░░\
        /░░             \░\      /░/             ░░\
        ░░     /░░░░\    ░░\____/░░    /░░░░\     ░░
        ░░    |░░░░░░░ /░░/░░||░░\░░\ ░░░░░░░|    ░░
        ░░   /░░░░░░░░░░░░░_=┘└=_░░░░░░░░░░░░░\   ░░
        \░░  |░░░/░░░░░░░//      \\░░░░░░░░\░░|  ░░/
         \░░/░░░░░░__░░░||        ||░░░__░░░░░░\░░/
          \░░░░░░/1010\_░\\      //░_/0010\░░░░░░/
          /░░\░░░░\0101_\░░¯=┐┌=¯░░/_0010/░░░░/░░\
          ░░_\¯\\_░░░░░░¯\░░░||░░░/¯░░░░░░_//¯/_░░
        /░░/10\   ¯\░░░░░░░░░||░░░░░░░░░/¯   /01\░░\
        ░░░\010\     ¯\░░░░░░||░░░░░░/¯     /010/░░░
       ░░\░░¯001¯\_     \░░░░||░░░░/     _/¯011¯░░/░░
       ░|11\░░░░¯\0=¯ = _ \░░||░░/ _ = ¯=1/¯░░░░/01|░
       \░░0101\░░░░░░░░░░░'░░||░░'░░░░░░░░░░░/0100░░/
        \░░\0010░░░_101\░░░░░||░░░░░/110_░░░1010/░░/
          \_░░░░░_/101/░░░/░░||░░\░░░\010\_░░░░░_/
             ¯\\_░░░░░░░░/|░░||░░|\░░░░░░░__//¯
                 ¯\\_░░░░\ ¯¯  ¯¯ /░░░░░//¯
                      \░░░░░░¯¯░░░░░░░/
                       \░░░░░||░░░░░/ 
                         ¯¯==--==¯¯

=============================||=============================
"""


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def parse_args() -> dict:
    """Parse and return CLI arguments as configuration dict."""
    parser = argparse.ArgumentParser(
        prog="kitsu",
        description="Kitsu Desktop AI - Local AI Assistant Runtime"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--logo",
        action="store_true",
        help="Display Kitsu logo and exit"
    )

    parser.add_argument(
        "--safe",
        action="store_true",
        help="Force safe-mode profile (minimal resources)"
    )

    parser.add_argument(
        "--profile",
        type=str,
        help="Override hardware profile (e.g., 'ultra_low', 'mid', 'high')"
    )

    args = parser.parse_args()
    
    return {
        "debug": args.debug,
        "logo": args.logo,
        "safe": args.safe,
        "profile": args.profile,
    }


async def main() -> int:
    """Main entry point - delegates to ModernLauncher."""
    args = parse_args()
    
    # Setup logging
    setup_logging(debug=args["debug"])
    logger = logging.getLogger(__name__)
    
    # Show logo and exit if requested
    if args["logo"]:
        print(LOGO)
        return 0
    
    # Import and run modern launcher
    try:
        from runtime.launchers.modern_launcher import ModernLauncher
    except ImportError as e:
        print(f"❌ Failed to import ModernLauncher: {e}")
        return 1
    
    try:
        launcher = ModernLauncher()
        
        success = await launcher.launch(
            profile_override=args["profile"],
            safe_mode=args["safe"]
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("⏸️  Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Launcher failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
