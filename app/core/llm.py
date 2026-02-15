"""LLM manager for Ollama-based inference."""

import logging
from typing import Iterator

import ollama
from app.config import Settings

logger = logging.getLogger(__name__)


class LLMManager:
    """Manages the Ollama LLM lifecycle and inference."""

    MODEL_NAME = "gemma:2b"

    def __init__(self, settings: Settings):
        """Initialize the LLM manager.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._client = None
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._is_loaded

    def load_model(self) -> None:
        """Verify Ollama is running and the model is available."""
        try:
            self._client = ollama.Client()

            # Check if Ollama is reachable
            logger.info("Connecting to Ollama...")
            self._client.list()

            # Check if model exists, pull if not
            models = self._client.list()
            model_names = [m.model for m in models.models] if hasattr(models, 'models') else []

            if self.MODEL_NAME not in model_names:
                logger.info(f"Model {self.MODEL_NAME} not found. Pulling...")
                self._client.pull(self.MODEL_NAME)

            self._is_loaded = True
            logger.info(f"Ollama ready with model: {self.MODEL_NAME}")

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise RuntimeError(f"Failed to connect to Ollama: {e}") from e

    def unload_model(self) -> None:
        """Unload the model (no-op for Ollama)."""
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
            RuntimeError: If Ollama is not connected.
        """
        if not self._is_loaded or not self._client:
            raise RuntimeError("Ollama not connected")

        response = self._client.generate(
            model=self.MODEL_NAME,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "stop": stop or [],
            },
        )

        # Estimate token counts (Ollama doesn't always provide these)
        text = response.get("response", "")
        prompt_tokens = len(prompt.split())  # Rough estimate
        completion_tokens = len(text.split())  # Rough estimate

        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
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
        """Generate text from prompt with streaming."""
        if not self._is_loaded or not self._client:
            raise RuntimeError("Ollama not connected")

        stream = self._client.generate(
            model=self.MODEL_NAME,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "stop": stop or [],
            },
            stream=True,
        )

        for chunk in stream:
            text = chunk.get("response", "")
            if text:
                yield text

    def get_token_count(self, text: str) -> int:
        """Count the number of tokens in the given text (estimated).

        Args:
            text: The text to tokenize.

        Returns:
            Estimated number of tokens.
        """
        # Rough estimate: ~0.75 tokens per word on average
        return int(len(text.split()) * 1.3)
