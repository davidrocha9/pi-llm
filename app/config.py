"""Configuration settings using Pydantic Settings."""

import hashlib
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Security
    api_keys_path: str = "api_keys.txt"
    # Optional comma-separated list of SHA-256 hashes (env fallback)
    api_key_hashes: str | None = None
    # Optional server-side pepper for HMAC (defense-in-depth)
    # Set `API_KEY_PEPPER` in environment/secret manager to enable HMAC-based hashing.
    api_key_pepper: str | None = None
    # Optional SQLite DB path for API keys (preferred for Raspberry Pi).
    # If a relative path is provided it will be resolved against the repo root.
    api_keys_db: str | None = "api_keys.db"

    # Model Configuration
    model_path: str = "models/gemma-3-1b-it-Q4_K_M.gguf"
    model_repo: str = "unsloth/gemma-3-1b-it-GGUF"
    model_filename: str = "gemma-3-1b-it-Q4_K_M.gguf"

    # LLM Settings (optimized for Raspberry Pi 5)
    n_ctx: int = 2048  # Context window size
    n_threads: int = 4  # CPU threads for inference
    max_tokens: int = 512  # Default max tokens per response

    # Concurrency Settings
    # Note: LLM inference is serialized (llama-cpp not thread-safe), but multiple
    # requests can be tracked/queued. Higher values allow more pending requests.
    max_concurrent_requests: int = 4  # Max tracked concurrent requests
    max_queue_size: int = 100  # Max pending requests in overflow queue

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def valid_api_key_hashes(self) -> list[str]:
        """Get all valid API key hashes (from keys file)."""
        hashes = []
        # First, check env var `API_KEY_HASHES` (comma-separated)
        if self.api_key_hashes:
            hashes.extend([h.strip() for h in self.api_key_hashes.split(",") if h.strip()])

        # Then, fallback to file-based hashes. Treat relative paths as
        # repository-root-relative so the app finds the same file regardless
        # of current working directory.
        repo_root = Path(__file__).resolve().parents[1]
        path = Path(self.api_keys_path)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if path.exists():
            try:
                file_hashes = path.read_text().splitlines()
                hashes.extend([h.strip() for h in file_hashes if h.strip()])
            except Exception:
                pass

        # Also allow an env var `API_KEYS_FILE` to override path
        env_path = os.getenv("API_KEYS_FILE")
        if env_path:
            p = Path(env_path)
            if not p.is_absolute():
                p = (repo_root / p).resolve()
            if p.exists():
                try:
                    file_hashes = p.read_text().splitlines()
                    hashes.extend([h.strip() for h in file_hashes if h.strip()])
                except Exception:
                    pass
        # Note: if a SQLite DB is configured, it will be used instead of file-based
        # lookup (see app/core/keys.py). This property preserves backward-compatibility
        # for code that wants a simple list of hashes.
        return list(set(hashes))

    @property
    def model_path_resolved(self) -> Path:
        """Get the resolved model path."""
        return Path(self.model_path).resolve()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
