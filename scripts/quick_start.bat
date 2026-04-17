# ============================================================================
# FILE: scripts/quick_start.bat (Windows)
# ============================================================================

"""
@echo off
REM Quick start script for Kitsu (Windows)

echo 🦊 KITSU QUICK START
echo ====================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.7+
    exit /b 1
)

echo ✓ Python found
echo.

REM Check if first run needed
if not exist "data\\runtime\\.first_run_complete" (
    echo First launch detected. Setup wizard will run automatically.
    echo.
)

REM Launch
echo 🚀 Launching Kitsu...
python launcher.py
"""
