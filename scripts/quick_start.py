# ============================================================================
# FILE: scripts/quick_start.py
# Simple quick-start helper that delegates to launcher.py
# ============================================================================

"""
scripts/quick_start.py — Quick Start Guide

Shows quick-start instructions and optionally runs launcher.

This is NOT a setup script - it just provides guidance and
delegates to the proper launcher.py flow.
"""

def show_guide():
    """Display quick-start guide"""
    guide = """
╔══════════════════════════════════════════════════════════════╗
║               🦊 KITSU QUICK START GUIDE 🦊                 ║
╚══════════════════════════════════════════════════════════════╝

📋 GETTING STARTED:

1️⃣  FIRST LAUNCH (Automatic Setup)
    
    python launcher.py
    
    → Detects first run automatically
    → Runs interactive setup wizard
    → Configures system based on your hardware
    → Creates all necessary directories

2️⃣  WHAT YOU'LL BE ASKED:

    • Your name and how Kitsu should address you
    • Admin privileges (for dev console access)
    • Permission levels (browser, system, files)
    • Personality defaults (mood and style)
    • Model selection (based on your GPU)
    • Feature selection (voice, avatar, etc.)

3️⃣  HARDWARE RECOMMENDATIONS:

    Low-end (GT 730, 2GB VRAM):
      → TinyLlama 1.1B
      → No avatar
      → Text mode only
      
    Mid-range (GTX 1060, 6GB VRAM):
      → Gemma 2B
      → Optional avatar
      → Voice mode supported
      
    High-end (RTX 3060+, 12GB VRAM):
      → Qwen 1.8B or custom model
      → Full avatar support
      → All features enabled

4️⃣  AFTER SETUP:

    • Configuration saved to data/config/
    • Start Kitsu: python launcher.py
    • Reconfigure: python scripts/first_run.py --reset
    • Check status: python scripts/first_run.py --status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 MANUAL CONFIGURATION:

Edit these files directly (then restart):
  
  • data/config.json           - Runtime settings
  • data/config/user_profile.json - User info
  • data/config/personality.json  - Personality defaults
  • data/config/permissions.json  - Security settings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 TROUBLESHOOTING:

❌ Setup wizard not appearing?
    → Check if data/runtime/.first_run_complete exists
    → Delete it to re-run setup: rm data/runtime/.first_run_complete

❌ Out of memory errors?
    → Use TinyLlama 1.1B model
    → Disable avatar in config
    → Close other GPU applications

❌ Import errors?
    → Install dependencies: pip install -r requirements.txt
    → Check Python version: python --version (3.7+ required)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 NEXT STEPS:

  1. Run launcher: python launcher.py
  2. Complete setup wizard
  3. Chat with Kitsu!
  4. Customize personality in /mood and /style commands
  5. Train custom LoRA (optional, see docs/lora_training.md)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Need help?
  • Check docs/ folder for detailed guides
  • View logs in data/logs/
  • Join Discord/GitHub for community support

Good luck! 🦊✨
"""
    print(guide)


def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Kitsu Quick Start Helper')
    parser.add_argument('--guide', action='store_true', help='Show guide only')
    parser.add_argument('--launch', action='store_true', help='Show guide and launch')
    
    args = parser.parse_args()
    
    if args.launch:
        show_guide()
        print("\n🚀 Launching Kitsu...\n")
        import subprocess
        sys.exit(subprocess.call([sys.executable, "launcher.py"]))
    else:
        show_guide()


if __name__ == "__main__":
    main()
