"""LLM manager for Ollama-based inference."""

import logging
import time
from typing import Iterator

import ollama
from app.config import Settings

logger = logging.getLogger(__name__)


class LLMManager:
    """Manages the Ollama LLM lifecycle and inference."""

    def __init__(self, settings: Settings):
        """Initialize the LLM manager.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self.model_name = settings.ollama_model
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
            models = self._client.list()
            model_names = (
                [m.model for m in models.models] if hasattr(models, "models") else []
            )

            if self.model_name not in model_names:
                logger.info(f"Model {self.model_name} not found. Pulling...")
                self._client.pull(self.model_name)

            if self.settings.ollama_warmup:
                self._warmup()

            self._is_loaded = True
            logger.info(f"Ollama ready with model: {self.model_name}")

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
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop: list[str] | None = None,
        n_ctx: int | None = None,
        n_threads: int | None = None,
    ) -> dict:
        """Generate text from prompt (non-streaming).

        Args:
            prompt: The input prompt.
            system: Optional system prompt to guide the model's behavior.
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

        return self.generate_with_metrics(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=stop,
            n_ctx=n_ctx,
            n_threads=n_threads,
        )

    def generate_with_metrics(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop: list[str] | None = None,
        n_ctx: int | None = None,
        n_threads: int | None = None,
    ) -> dict:
        """Generate text and include Ollama timing metrics when available."""
        if not self._is_loaded or not self._client:
            raise RuntimeError("Ollama not connected")

        request_params = {
            "model": self.model_name,
            "messages": self._build_messages(prompt, system),
            "options": self._build_options(
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                n_ctx=n_ctx,
                n_threads=n_threads,
            ),
            "keep_alive": self.settings.ollama_keep_alive,
        }

        started = time.perf_counter()
        response = self._client.chat(**request_params)
        latency_s = max(time.perf_counter() - started, 1e-9)

        text = response.get("message", {}).get("content", "")
        prompt_tokens = int(response.get("prompt_eval_count") or len(prompt.split()))
        completion_tokens = int(response.get("eval_count") or len(text.split()))
        total_tokens = prompt_tokens + completion_tokens

        load_duration = response.get("load_duration")
        prompt_eval_duration = response.get("prompt_eval_duration")
        eval_duration = response.get("eval_duration")
        total_duration = response.get("total_duration")

        ttft_ms = None
        if isinstance(prompt_eval_duration, int):
            ttft_ns = prompt_eval_duration + (
                load_duration if isinstance(load_duration, int) else 0
            )
            ttft_ms = round(ttft_ns / 1_000_000, 2)

        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": round(latency_s * 1000, 2),
            "time_to_first_token_ms": ttft_ms,
            "load_ms": self._duration_to_ms(load_duration),
            "prompt_eval_ms": self._duration_to_ms(prompt_eval_duration),
            "eval_ms": self._duration_to_ms(eval_duration),
            "total_duration_ms": self._duration_to_ms(total_duration),
            "prompt_tokens_per_second": self._tokens_per_second(
                token_count=prompt_tokens,
                duration_ns=prompt_eval_duration,
                fallback_tokens=prompt_tokens,
                fallback_duration_s=latency_s,
            ),
            "completion_tokens_per_second": self._tokens_per_second(
                token_count=completion_tokens,
                duration_ns=eval_duration,
                fallback_tokens=completion_tokens,
                fallback_duration_s=latency_s,
            ),
        }

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop: list[str] | None = None,
        n_ctx: int | None = None,
        n_threads: int | None = None,
    ) -> Iterator[str]:
        """Generate text from prompt with streaming."""
        if not self._is_loaded or not self._client:
            raise RuntimeError("Ollama not connected")

        request_params = {
            "model": self.model_name,
            "messages": self._build_messages(prompt, system),
            "options": self._build_options(
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                n_ctx=n_ctx,
                n_threads=n_threads,
            ),
            "keep_alive": self.settings.ollama_keep_alive,
            "stream": True,
        }

        stream = self._client.chat(**request_params)

        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content

    def get_token_count(self, text: str) -> int:
        """Count the number of tokens in the given text (estimated).

        Args:
            text: The text to tokenize.

        Returns:
            Estimated number of tokens.
        """
        # Rough estimate: ~0.75 tokens per word on average
        return int(len(text.split()) * 1.3)

    def _build_messages(self, prompt: str, system: str | None) -> list[dict[str, str]]:
        """Create chat-formatted messages."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_options(
        self,
        max_tokens: int | None,
        temperature: float,
        top_p: float,
        top_k: int,
        stop: list[str] | None,
        n_ctx: int | None = None,
        n_threads: int | None = None,
    ) -> dict:
        """Build Ollama generation options with Pi-friendly defaults."""
        return {
            "num_predict": max_tokens if max_tokens is not None else self.settings.max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "num_thread": n_threads if n_threads is not None else self.settings.n_threads,
            "num_ctx": n_ctx if n_ctx is not None else self.settings.n_ctx,
            "stop": stop or [],
        }

    def _warmup(self) -> None:
        """Warm the model so first user request has lower latency."""
        if not self._client:
            return

        try:
            logger.info("Warming up Ollama model...")
            self._client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": "hi"}],
                options={
                    "num_predict": 1,
                    "temperature": 0.0,
                    "num_thread": self.settings.n_threads,
                    "num_ctx": self.settings.n_ctx,
                },
                keep_alive=self.settings.ollama_keep_alive,
            )
            logger.info("Model warmup complete")
        except Exception as e:
            logger.warning(f"Warmup skipped due to error: {e}")

    @staticmethod
    def _duration_to_ms(duration_ns: int | None) -> float | None:
        """Convert a nanoseconds duration value to milliseconds."""
        if not isinstance(duration_ns, int):
            return None
        return round(duration_ns / 1_000_000, 2)

    @staticmethod
    def _tokens_per_second(
        token_count: int,
        duration_ns: int | None,
        fallback_tokens: int,
        fallback_duration_s: float,
    ) -> float:
        """Calculate tokens/s using Ollama durations, with wall-clock fallback."""
        if isinstance(duration_ns, int) and duration_ns > 0:
            return round(token_count / (duration_ns / 1_000_000_000), 2)
        if fallback_duration_s > 0:
            return round(fallback_tokens / fallback_duration_s, 2)
        return 0.0
