# ============================================================================
# FILE: scripts/quick_start.sh (Unix/Linux/Mac)
# ============================================================================

"""
#!/bin/bash
# Quick start script for Kitsu (Unix/Linux/Mac)

echo "🦊 KITSU QUICK START"
echo "===================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.7+"
    exit 1
fi

echo "✓ Python 3 found"
echo ""

# Check if first run needed
if [ ! -f "data/runtime/.first_run_complete" ]; then
    echo "First launch detected. Setup wizard will run automatically."
    echo ""
fi

# Launch
echo "🚀 Launching Kitsu..."
python3 launcher.py
"""