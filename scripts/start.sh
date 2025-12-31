#!/usr/bin/env bash
set -euo pipefail

# Start script for Pi LLM service
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

if [ ! -d .venv ]; then
  echo "Error: Virtual environment (.venv) not found."
  echo "Please run the setup script first:"
  echo "  bash scripts/setup.sh"
  exit 1
fi

# Activate virtualenv
source .venv/bin/activate

# Load environment variables if .env exists
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

# Default host and port (0.0.0.0 allows access from other devices on the network)
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "Starting Pi LLM server on ${HOST}:${PORT}..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
