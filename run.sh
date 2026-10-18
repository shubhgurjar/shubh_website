#!/bin/bash
set -e

# Change to the project directory
cd "$(dirname "$0")"

echo "=========================================================="
echo "  Shubh's Software Engineering Career Knowledge Hub"
echo "=========================================================="

# Check for Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 is not installed or not in your PATH."
    exit 1
fi

echo "✓ Using Python: $($PYTHON_CMD --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "⚙️ Creating virtual environment (venv)..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
VENV_PYTHON="$PWD/venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "❌ Error: Virtual environment Python was not found at $VENV_PYTHON."
    exit 1
fi

# Check if fastapi is installed, otherwise install requirements
if ! "$VENV_PYTHON" -c "import fastapi, uvicorn" &>/dev/null; then
    echo "📦 Installing required dependencies from requirements.txt..."
    "$VENV_PYTHON" -m pip install -r requirements.txt
fi

echo "=========================================================="
echo "🚀 Launching Career Knowledge Hub at http://localhost:8000"
echo "   Default master password: admin123"
echo "   Press Ctrl+C to stop the server"
echo "=========================================================="

"$VENV_PYTHON" app.py
