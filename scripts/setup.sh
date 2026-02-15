#!/usr/bin/env bash
set -euo pipefail

# Unified setup script for Pi LLM with Ollama
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

PI_MODE=0
CONFIG_FILE="${PI_LLM_CONFIG_FILE:-configs/pi5-fast.env}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --pi) PI_MODE=1; shift ;;
    --config)
      if [ "$#" -lt 2 ]; then
        echo "Error: --config requires a file path."
        exit 1
      fi
      CONFIG_FILE="$2"
      shift 2
      ;;
    --help|-h) echo "Usage: bash scripts/setup.sh [--pi] [--config <path>]"; exit 0 ;;
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

# Load setup model/profile config if present
if [ -f "$CONFIG_FILE" ]; then
  set -o allexport
  source "$CONFIG_FILE"
  set +o allexport
  echo "Loaded setup config profile: $CONFIG_FILE"
fi

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
MODEL_NAME="${OLLAMA_MODEL:-qwen2.5:3b}"
echo ""
echo "Pulling ${MODEL_NAME} model via Ollama..."
echo "This may take a few minutes depending on your connection..."
ollama pull "${MODEL_NAME}"

echo ""
echo "Setup complete!"
echo "To start the server, run: bash scripts/start.sh"
echo "To generate an API key, run: python3 scripts/gen_key.py"
