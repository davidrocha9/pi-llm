#!/usr/bin/env bash
set -euo pipefail

# Unified setup script for dev and Raspberry Pi
# Usage:
#   Run for standard setup (creates venv, installs deps, tries to download model):
#     bash scripts/setup.sh
#   Run with Pi-specific system packages (requires sudo):
#     sudo bash scripts/setup.sh --pi
#   To have the script activate the virtualenv in your current shell, source it:
#     source scripts/setup.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

PI_MODE=0
ACTIVATE_FLAG=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --pi) PI_MODE=1; shift ;;
    --activate) ACTIVATE_FLAG=1; shift ;;
    --help|-h) echo "Usage: source scripts/setup.sh [--pi] [--activate]  OR  bash scripts/setup.sh [--pi]"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== Pi LLM Unified Setup ==="

if [ "$PI_MODE" -eq 1 ]; then
  echo "Running Pi-specific system setup (requires sudo)..."
  apt-get update && apt-get upgrade -y
  apt-get install -y python3-pip python3-venv python3-dev build-essential cmake libopenblas-dev pkg-config
fi

# Create virtualenv if not present
if [ ! -d .venv ]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

echo "Activating virtualenv..."
source .venv/bin/activate

echo "Upgrading pip and installing project dependencies..."
pip install --upgrade pip

# Install llama-cpp-python with OpenBLAS on Pi (if PI_MODE) or standard on x86
if [ "$PI_MODE" -eq 1 ] || [ "$(uname -m)" = "aarch64" ]; then
  echo "Installing llama-cpp-python with OpenBLAS optimizations (this may take several minutes)..."
  CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" \
    pip install --no-cache-dir llama-cpp-python
else
  echo "Installing llama-cpp-python (standard build)..."
  pip install --no-cache-dir llama-cpp-python
fi

echo "Installing remaining Python dependencies..."
pip install -e ".[dev]" || pip install -e .

echo "Ensuring huggingface_hub is available..."
pip install --no-cache-dir huggingface_hub

# Ensure models directory exists
mkdir -p models

echo "Attempting to auto-download a preferred .gguf model (this may be ~800MB)"
python scripts/download_model.py --auto || echo "Auto-download failed or skipped; run: python scripts/download_model.py --auto"

# Ensure .env exists and contains an API_KEY
if [ ! -f .env ]; then
  echo "Creating .env from .env.example"
  cp .env.example .env
fi

if ! grep -q '^API_KEY=' .env; then
  echo "Generating API_KEY in .env"
  NEW_KEY=$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)
  echo "API_KEY=${NEW_KEY}" >> .env
  echo "Created API_KEY and saved to .env"
fi

echo
echo "Setup complete."

# If the script is sourced, and .venv exists, activate it automatically when requested
if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  # Script is sourced in the current shell
  if [ -d .venv ]; then
    # If user passed --activate or script was sourced, activate venv
    if [ "$ACTIVATE_FLAG" -eq 1 ] || true; then
      # shellcheck disable=SC1091
      source .venv/bin/activate
      echo "Virtualenv activated in current shell." 
    fi
  fi
else
  # Script executed as a child process — cannot activate parent shell venv
  if [ "$ACTIVATE_FLAG" -eq 1 ]; then
    echo "To activate the virtualenv in your shell, source this script instead:" >&2
    echo "  source scripts/setup.sh --activate" >&2
  else
    echo "To activate the virtualenv in your shell run: source .venv/bin/activate" >&2
  fi
fi

echo "Start the server with: bash scripts/start.sh" 

# Make helper scripts executable so start.sh can be run directly
chmod +x scripts/start.sh || true
chmod +x scripts/activate.sh || true
chmod +x scripts/gen_key.sh || true

exit 0
