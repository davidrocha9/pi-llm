#!/usr/bin/env python3
"""Generate a secure API key and store it in the configured keys file."""

import os
import secrets
import sys
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parents[1]

    venv_python = repo_root / ".venv" / "bin" / "python3"
    if venv_python.exists() and sys.executable != str(venv_python):
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)

    sys.path.insert(0, str(repo_root))

    try:
        from app.config import get_settings
        from app.core.keys import KeyStore
    except ImportError as e:
        print(f"Error importing application modules: {e}")
        print("Please ensure you have run 'bash scripts/setup.sh' first.")
        sys.exit(1)

    new_key = secrets.token_urlsafe(32)
    settings = get_settings()

    db_path = os.getenv("API_KEYS_DB") or settings.api_keys_db or "api_keys.db"
    p = Path(db_path)
    if not p.is_absolute():
        p = (repo_root / p).resolve()

    try:
        ks = KeyStore(p)
        ks.add_key(new_key)
        ks.close()
        try:
            p.chmod(0o600)
        except Exception:
            pass
        print(f"Generated API key: {new_key}")
    except Exception as e:
        print(f"Error writing key to DB: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
