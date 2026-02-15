#!/usr/bin/env bash
set -euo pipefail

# Start script for Pi LLM service (Ollama Edition)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

if [ ! -d .venv ]; then
  echo "Error: Virtual environment (.venv) not found."
  echo "Please run the setup script first:"
  echo "  bash scripts/setup.sh"
  exit 1
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
  echo "Error: Ollama not found."
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
OLLAMA_PORT=${OLLAMA_PORT:-11434}

echo "Starting Ollama server..."

# Start Ollama in the background if not already running
if ! curl -s "http://localhost:${OLLAMA_PORT}" > /dev/null 2>&1; then
  ollama serve &
  OLLAMA_PID=$!
  
  # Wait for Ollama to be ready
  echo "Waiting for Ollama to start..."
  for i in {1..30}; do
    if curl -s "http://localhost:${OLLAMA_PORT}" > /dev/null 2>&1; then
      echo "Ollama is ready!"
      break
    fi
    sleep 1
  done
  
  if ! curl -s "http://localhost:${OLLAMA_PORT}" > /dev/null 2>&1; then
    echo "Error: Ollama failed to start"
    exit 1
  fi
else
  echo "Ollama is already running"
fi

echo ""
echo "Starting Pi LLM server on ${HOST}:${PORT}..."
echo "Ollama API available at http://localhost:${OLLAMA_PORT}"
echo ""

# Trap to kill Ollama when the script exits
cleanup() {
  echo ""
  echo "Shutting down..."
  if [ -n "${OLLAMA_PID:-}" ]; then
    kill $OLLAMA_PID 2>/dev/null || true
  fi
}
trap cleanup EXIT

exec uvicorn app.main:app --host "$HOST" --port "$PORT"
