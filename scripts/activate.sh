#!/usr/bin/env bash
# Convenience script to activate the project's virtualenv
if [ -d "$(dirname "$0")/../.venv" ]; then
  # shellcheck disable=SC1091
  source "$(dirname "$0")/../.venv/bin/activate"
  echo "Activated .venv"
else
  echo "Virtualenv .venv not found. Run: bash scripts/setup.sh" >&2
  return 1
fi
