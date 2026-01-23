#!/bin/bash
# =============================================================================
# QRadar MCP Server - Setup Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=============================================="
echo "QRadar MCP Server - Setup"
echo "=============================================="

# Check Python
echo ""
echo "[1/3] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi
echo "Found: $(python3 --version)"

# Ask user about virtual environment
echo ""
echo "=============================================="
echo "Installation Options"
echo "=============================================="
echo ""
echo "1) Install with virtual environment (recommended)"
echo "2) Install globally (no virtual environment)"
echo ""
read -p "Choose option [1/2]: " choice

case $choice in
    1)
        USE_VENV=true
        echo ""
        echo "[2/3] Creating virtual environment..."
        VENV_DIR="$SCRIPT_DIR/.venv"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        echo "Created and activated: $VENV_DIR"
        ;;
    2)
        USE_VENV=false
        echo ""
        echo "[2/3] Using system Python..."
        echo "Installing to: $(python3 -m site --user-site)"
        ;;
    *)
        echo "Invalid option. Defaulting to virtual environment..."
        USE_VENV=true
        VENV_DIR="$SCRIPT_DIR/.venv"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        ;;
esac

# Install dependencies
echo ""
echo "[3/3] Installing dependencies..."
pip install --upgrade pip -q
pip install mcp httpx -q
pip install -e "$SCRIPT_DIR" -q
echo "Done! Installed: mcp, httpx"

# Instructions
echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "To run the MCP server:"
echo ""
if [ "$USE_VENV" = true ]; then
    echo "  source .venv/bin/activate"
fi
echo "  export QRADAR_HOST=\"https://your-qradar.com\""
echo "  export QRADAR_API_TOKEN=\"your-token\""
echo "  python3 -m src.server"
echo ""
