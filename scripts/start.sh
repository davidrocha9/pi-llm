#!/usr/bin/env bash
set -euo pipefail

# Start script for Pi LLM service (Ollama Edition)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

# Config profile path (can be overridden with --config or PI_LLM_CONFIG_FILE)
CONFIG_FILE="${PI_LLM_CONFIG_FILE:-configs/pi5-fast.env}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --config)
      if [ "$#" -lt 2 ]; then
        echo "Error: --config requires a file path."
        exit 1
      fi
      CONFIG_FILE="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash scripts/start.sh [--config <path>]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Usage: bash scripts/start.sh [--config <path>]"
      exit 1
      ;;
  esac
done

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

# Load environment variables if .env exists (optional baseline)
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

# Load selected runtime profile (takes precedence over .env)
if [ -f "$CONFIG_FILE" ]; then
  set -o allexport
  source "$CONFIG_FILE"
  set +o allexport
  echo "Loaded config profile: $CONFIG_FILE"
else
  echo "Config profile not found: $CONFIG_FILE"
  echo "Continuing with environment/default settings."
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
echo "Model profile: ${OLLAMA_MODEL:-qwen2.5:3b}"
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
