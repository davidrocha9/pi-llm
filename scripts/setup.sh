#!/usr/bin/env bash
set -euo pipefail

# Unified setup script for Pi LLM with Ollama
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

PI_MODE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --pi) PI_MODE=1; shift ;;
    --help|-h) echo "Usage: bash scripts/setup.sh [--pi]"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== Pi LLM Setup (Ollama Edition) ==="

# Install Ollama if not present
if ! command -v ollama &> /dev/null; then
  echo "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "Ollama already installed ($(ollama --version))"
fi

# Create virtualenv if not present
if [ ! -d .venv ]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

# Activate virtualenv for the rest of the setup
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing project dependencies..."
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

if [ -f pyproject.toml ]; then
  pip install -e .
fi

# Pull the model using Ollama
echo ""
echo "Pulling Gemma 3 1B model via Ollama..."
echo "This may take a few minutes depending on your connection..."
ollama pull gemma:2b

echo ""
echo "Setup complete!"
echo "To start the server, run: bash scripts/start.sh"
echo "To generate an API key, run: python3 scripts/gen_key.py"
