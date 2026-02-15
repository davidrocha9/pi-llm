"""Async request queue for managing inference requests."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class InferenceRequest:
    """Represents a single inference request in the queue."""

    prompt: str
    system: str | None = None
    max_tokens: int = 96
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    stop: list[str] = field(default_factory=list)
    stream: bool = True

    # Internal state
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at_monotonic: float = field(default_factory=time.monotonic)
    _token_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    _done: asyncio.Event = field(default_factory=asyncio.Event)
    _stats: dict = field(default_factory=dict)
    _error: Exception | None = field(default=None)

    async def put_token(self, token: str) -> None:
        """Add a generated token to the stream.

        Args:
            token: The generated token.
        """
        await self._token_queue.put(token)

    async def complete(self, stats: dict) -> None:
        """Mark the request as complete.

        Args:
            stats: Token statistics (prompt_tokens, completion_tokens, total_tokens).
        """
        self._stats = stats
        await self._token_queue.put(None)  # Sentinel value
        self._done.set()

    async def fail(self, error: Exception) -> None:
        """Mark the request as failed.

        Args:
            error: The exception that caused the failure.
        """
        self._error = error
        await self._token_queue.put(None)  # Sentinel value
        self._done.set()

    async def token_stream(self) -> AsyncIterator[str]:
        """Iterate over generated tokens as they become available.

        Yields:
            Generated tokens one at a time.

        Raises:
            Exception: If the request failed with an error.
        """
        while True:
            token = await self._token_queue.get()
            if token is None:  # Sentinel value
                if self._error:
                    raise self._error
                break
            yield token

    async def get_stats(self) -> dict:
        """Get token statistics after completion.

        Returns:
            Dictionary with prompt_tokens, completion_tokens, total_tokens.
        """
        await self._done.wait()
        return self._stats


class RequestQueue:
    """Async queue for managing inference requests."""

    def __init__(self, maxsize: int = 100):
        """Initialize the request queue.

        Args:
            maxsize: Maximum number of pending requests.
        """
        self._queue: asyncio.Queue[InferenceRequest] = asyncio.Queue(maxsize=maxsize)

    @property
    def size(self) -> int:
        """Get the current queue size."""
        return self._queue.qsize()

    @property
    def maxsize(self) -> int:
        """Get configured queue capacity."""
        return self._queue.maxsize

    @property
    def is_full(self) -> bool:
        """Check whether the queue is at capacity."""
        return self.maxsize > 0 and self.size >= self.maxsize

    async def put(self, request: InferenceRequest) -> None:
        """Add a request to the queue.

        Args:
            request: The inference request to queue.
        """
        if self.is_full:
            raise asyncio.QueueFull

        self._queue.put_nowait(request)
        logger.debug(f"Request {request.id} queued (queue size: {self.size})")

    async def get(self) -> InferenceRequest:
        """Get the next request from the queue.

        Returns:
            The next inference request.
        """
        request = await self._queue.get()
        logger.debug(f"Request {request.id} dequeued (queue size: {self.size})")
        return request

    def task_done(self) -> None:
        """Mark the current task as done."""
        self._queue.task_done()
