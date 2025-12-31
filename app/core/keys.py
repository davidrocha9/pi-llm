"""SQLite-backed API key store.

Design notes:
- Stores HMAC-SHA256 hashes (binary) along with a non-secret prefix for fast lookup.
- Uses a single SQLite file (configurable via `api_keys_db` setting).
"""

import hmac
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import List, Tuple

from app.config import get_settings


class KeyStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # allow access from multiple threads within the same process
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY,
                prefix TEXT NOT NULL,
                hash BLOB NOT NULL,
                created_at INTEGER NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                owner TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_keys_prefix ON api_keys(prefix)")
        self.conn.commit()

    @staticmethod
    def _compute_hash(raw: str, pepper: str | None) -> bytes:
        if pepper:
            return hmac.new(pepper.encode(), raw.encode(), hashlib.sha256).digest()
        return hashlib.sha256(raw.encode()).digest()

    def add_key(self, raw_key: str, prefix: str | None = None, owner: str | None = None) -> None:
        if prefix is None:
            if "_" in raw_key:
                prefix = raw_key.split("_", 1)[0]
            else:
                prefix = "_"  # fallback

        settings = get_settings()
        b = self._compute_hash(raw_key, settings.api_key_pepper)
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO api_keys (prefix, hash, created_at, owner) VALUES (?, ?, ?, ?)",
            (prefix, b, int(time.time()), owner),
        )
        self.conn.commit()

    def verify(self, raw_key: str) -> bool:
        # Extract prefix and lookup candidates
        if "_" in raw_key:
            prefix = raw_key.split("_", 1)[0]
        else:
            prefix = "_"

        cur = self.conn.cursor()
        cur.execute("SELECT hash, revoked FROM api_keys WHERE prefix = ?", (prefix,))
        rows: List[Tuple[bytes, int]] = cur.fetchall()
        if not rows:
            return False

        settings = get_settings()
        computed = self._compute_hash(raw_key, settings.api_key_pepper)
        for stored_hash, revoked in rows:
            if revoked:
                continue
            # constant-time comparison
            if hmac.compare_digest(computed, stored_hash):
                return True
        return False

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
