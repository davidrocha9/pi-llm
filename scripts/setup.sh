#!/usr/bin/env bash
set -euo pipefail

# Unified setup script for dev and Raspberry Pi
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

echo "=== Pi LLM Setup ==="

# Create virtualenv if not present
if [ ! -d .venv ]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

# Activate virtualenv for the rest of the setup
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

# Install llama-cpp-python with optimizations if on Pi or aarch64
if [ "$PI_MODE" -eq 1 ] || [ "$(uname -m)" = "aarch64" ]; then
  echo "Installing llama-cpp-python with OpenBLAS optimizations..."
  # Try to install system dependencies if possible (non-blocking)
  if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" -eq 0 ]; then
    apt-get update && apt-get install -y build-essential cmake libopenblas-dev pkg-config
  fi
  CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" \
    pip install --no-cache-dir llama-cpp-python
else
  echo "Installing llama-cpp-python (standard build)..."
  pip install --no-cache-dir llama-cpp-python
fi

echo "Installing project dependencies..."
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

if [ -f pyproject.toml ]; then
  pip install -e .
fi

# Ensure models directory exists
mkdir -p models

# Download the model automatically
echo "Downloading model (this may take a few minutes)..."
python3 scripts/download_model.py --auto

echo ""
echo "Setup complete!"
echo "To start the server, run: bash scripts/start.sh"
echo "To generate an API key, run: python3 scripts/gen_key.py"
