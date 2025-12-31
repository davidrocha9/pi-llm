"""LLM manager for loading and running inference."""

import logging
from pathlib import Path
from typing import Iterator

from app.config import Settings

logger = logging.getLogger(__name__)


class LLMManager:
    """Manages the LLM model lifecycle and inference."""

    def __init__(self, settings: Settings):
        """Initialize the LLM manager.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._model = None
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._is_loaded

    def load_model(self) -> None:
        """Load the LLM model from disk.

        Raises:
            FileNotFoundError: If the model file doesn't exist.
            RuntimeError: If model loading fails.
        """
        model_path = Path(self.settings.model_path)

        # If configured path doesn't exist, attempt to find a matching
        # .gguf file in the repository `models/` directory. This handles
        # small filename variations (e.g. dot vs hyphen mistakes).
        if not model_path.exists():
            repo_root = Path(__file__).resolve().parents[2]
            models_dir = (repo_root / "models").resolve()

            target_name = Path(self.settings.model_path).name
            if not target_name and getattr(self.settings, "model_filename", None):
                target_name = self.settings.model_filename

            def _normalize(name: str) -> str:
                return "".join(ch.lower() for ch in name if ch.isalnum())

            found = None
            if models_dir.exists():
                for p in models_dir.iterdir():
                    if p.suffix.lower() != ".gguf":
                        continue
                    if _normalize(p.name) == _normalize(target_name):
                        found = p
                        break

            if found:
                model_path = found
            else:
                raise FileNotFoundError(
                    f"Model not found at {model_path}. "
                    f"Run 'python scripts/download_model.py' to download it."
                )

        try:
            # Import here to avoid loading llama_cpp if not needed
            from llama_cpp import Llama

            logger.info(f"Loading model from {model_path}...")
            logger.info(f"  Context size: {self.settings.n_ctx}")
            logger.info(f"  Threads: {self.settings.n_threads}")

            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self.settings.n_ctx,
                n_threads=self.settings.n_threads,
                verbose=False,
            )

            self._is_loaded = True
            logger.info("Model loaded successfully!")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Failed to load model: {e}") from e

    def unload_model(self) -> None:
        """Unload the model from memory."""
        if self._model:
            del self._model
            self._model = None
            self._is_loaded = False
            logger.info("Model unloaded")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop: list[str] | None = None,
    ) -> dict:
        """Generate text from prompt (non-streaming).

        Args:
            prompt: The input prompt.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            top_p: Top-p sampling parameter.
            top_k: Top-k sampling parameter.
            stop: Stop sequences.

        Returns:
            Dictionary with generated text and token counts.

        Raises:
            RuntimeError: If the model is not loaded.
        """
        if not self._is_loaded or not self._model:
            raise RuntimeError("Model not loaded")

        response = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=stop or [],
            echo=False,
        )

        return {
            "text": response["choices"][0]["text"],
            "prompt_tokens": response["usage"]["prompt_tokens"],
            "completion_tokens": response["usage"]["completion_tokens"],
            "total_tokens": response["usage"]["total_tokens"],
        }

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop: list[str] | None = None,
    ) -> Iterator[str]:
        """Generate text from prompt with streaming, yielding smaller token-like pieces.

        This method splits incoming streamed chunks on whitespace boundaries (preserving
        trailing spaces) so downstream consumers receive incremental pieces rather than
        large text blobs.
        """
        import re

        if not self._is_loaded or not self._model:
            raise RuntimeError("Model not loaded")

        stream = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=stop or [],
            echo=False,
            stream=True,
        )

        buffer = ""
        token_re = re.compile(r"\S+\s*")

        for chunk in stream:
            piece = chunk["choices"][0].get("text", "")
            if not piece:
                continue
            buffer += piece

            # Emit any full "tokens" (non-space sequences plus following spaces)
            pos = 0
            for m in token_re.finditer(buffer):
                start, end = m.span()
                if end <= len(buffer):
                    yield buffer[start:end]
                    pos = end

            # Keep the remainder in buffer
            buffer = buffer[pos:]

        # Emit any leftover buffer at the end
        if buffer:
            yield buffer

    def get_token_count(self, text: str) -> int:
        """Count the number of tokens in the given text.

        Args:
            text: The text to tokenize.

        Returns:
            Number of tokens.

        Raises:
            RuntimeError: If the model is not loaded.
        """
        if not self._is_loaded or not self._model:
            raise RuntimeError("Model not loaded")

        tokens = self._model.tokenize(text.encode("utf-8"))
        return len(tokens)
