#!/usr/bin/env bash
set -euo pipefail

# Generate a secure API key and insert into .env (backup if present)
ENV_FILE=".env"

PYTHON_BIN=$(command -v python3 || command -v python || true)
if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3 not found in PATH. Activate your virtualenv or install Python 3.11+." >&2
  echo "If you have a venv here, run: source .venv/bin/activate" >&2
  exit 1
fi

NEW_KEY=$($PYTHON_BIN - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)

echo "Generated API key: $NEW_KEY"

if [ -f "$ENV_FILE" ]; then
  if grep -q '^API_KEY=' "$ENV_FILE"; then
    # Rewrite the file in-place without creating backups for portability
    # Use python to safely update the API_KEY line
    $PYTHON_BIN - "$ENV_FILE" "$NEW_KEY" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
new_key = sys.argv[2]
text = env_path.read_text() if env_path.exists() else ''
lines = text.splitlines()
for i, l in enumerate(lines):
    if l.startswith('API_KEY='):
        lines[i] = f'API_KEY={new_key}'
        break
else:
    lines.append(f'API_KEY={new_key}')
env_path.write_text('\n'.join(lines) + ('\n' if lines else ''))
PY
    echo "Replaced API_KEY in $ENV_FILE"
  else
    echo "API_KEY=${NEW_KEY}" >> "$ENV_FILE"
    echo "Added API_KEY to $ENV_FILE"
  fi
else
  echo "API_KEY=${NEW_KEY}" > "$ENV_FILE"
  echo "Created $ENV_FILE with API_KEY"
fi

echo
echo "Use this key with header X-API-Key when calling the API:" 
echo
echo "  $NEW_KEY"
echo
echo "Example curl (non-streaming):"
echo "curl -X POST http://localhost:8000/generate \\" 
echo "  -H 'Content-Type: application/json' \\" 
echo "  -H \"X-API-Key: $NEW_KEY\" \\" 
echo "  -d '{\"prompt\": \"Hello!\", \"stream\": false}'"

# Optionally copy to clipboard if xclip or pbcopy present
if command -v xclip >/dev/null 2>&1; then
  echo -n "$NEW_KEY" | xclip -selection clipboard && echo "(Copied key to clipboard via xclip)"
elif command -v pbcopy >/dev/null 2>&1; then
  echo -n "$NEW_KEY" | pbcopy && echo "(Copied key to clipboard via pbcopy)"
fi

exit 0
