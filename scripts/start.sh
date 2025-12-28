#!/usr/bin/env bash
set -euo pipefail

# Start script for Pi LLM service
# Usage: bash scripts/start.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f .env ]; then
  # Export variables from .env into the environment for child processes
  # shellcheck disable=SC1091
  set -o allexport
  source .env
  set +o allexport
fi

if [ -d .venv ]; then
  source .venv/bin/activate
else
  echo "Virtualenv not found. Run: bash scripts/setup.sh" >&2
  exit 1
fi

: ${HOST:=127.0.0.1}
: ${PORT:=8000}

echo "Starting Pi LLM server on ${HOST}:${PORT}..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
