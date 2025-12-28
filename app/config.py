"""Configuration settings using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Security
    api_key: str = "change-me-in-production"

    # Model Configuration
    model_path: str = "models/gemma-3-1b-it.Q4_K_M.gguf"
    model_repo: str = "unsloth/gemma-3-1b-it-GGUF"
    model_filename: str = "gemma-3-1b-it.Q4_K_M.gguf"

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
    def model_path_resolved(self) -> Path:
        """Get the resolved model path."""
        return Path(self.model_path).resolve()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
