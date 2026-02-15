#!/usr/bin/env bash
set -euo pipefail

# Uninstall script for Pi LLM
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

echo "=== Pi LLM Uninstall ==="
echo ""

# Confirm uninstall
read -p "This will remove all downloaded models, virtual environment, and configuration. Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo "Removing downloaded files and configurations..."

# Remove virtual environment
if [ -d .venv ]; then
    echo "  - Removing virtual environment (.venv)..."
    rm -rf .venv
fi

# Remove Ollama model
if command -v ollama &> /dev/null; then
    echo "  - Removing Ollama model (gemma:2b)..."
    ollama rm gemma:2b 2>/dev/null || echo "    (Model may not exist or Ollama not running)"
fi

# Remove downloaded models
if [ -d models ]; then
    echo "  - Removing downloaded models..."
    find models -type f -name "*.gguf" -delete 2>/dev/null || true
    find models -type d -name ".cache" -exec rm -rf {} + 2>/dev/null || true
fi

# Remove API keys database
if [ -f api_keys.db ]; then
    echo "  - Removing API keys database..."
    rm -f api_keys.db
fi

# Remove API keys text file
if [ -f api_keys.txt ]; then
    echo "  - Removing API keys file..."
    rm -f api_keys.txt
fi

# Remove .env file
if [ -f .env ]; then
    echo "  - Removing .env configuration..."
    rm -f .env
fi

# Remove Python cache
if [ -d app ]; then
    echo "  - Removing Python cache files..."
    find app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find app -type f -name "*.pyc" -delete 2>/dev/null || true
fi

# Optionally uninstall Ollama
if command -v ollama &> /dev/null; then
    echo ""
    read -p "Do you want to uninstall Ollama as well? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  - Uninstalling Ollama..."
        # Stop Ollama if running
        if pgrep -x "ollama" > /dev/null; then
            echo "    Stopping Ollama service..."
            pkill -x ollama 2>/dev/null || true
            sleep 2
        fi
        # Remove Ollama binary and data
        if [ -f /usr/local/bin/ollama ]; then
            sudo rm -f /usr/local/bin/ollama
        fi
        if [ -d /usr/local/lib/ollama ]; then
            sudo rm -rf /usr/local/lib/ollama
        fi
        if [ -d ~/.ollama ]; then
            rm -rf ~/.ollama
        fi
        echo "    Ollama uninstalled."
    else
        echo "  - Keeping Ollama installed (you can remove it manually if needed)"
    fi
fi

echo ""
echo "=== Uninstall Complete ==="
echo ""
echo "The following have been removed:"
echo "  - Virtual environment (.venv)"
echo "  - Downloaded models"
echo "  - API keys and configuration"
echo "  - Python cache files"
echo ""
echo "The following files are preserved:"
echo "  - Source code (app/, scripts/)"
echo "  - Git repository"
echo ""
echo "To reinstall, run: bash scripts/setup.sh"
