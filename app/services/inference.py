"""Inference service - manages concurrent inference with thread pool and queue fallback."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from statistics import mean

from app.core.llm import LLMManager
from app.core.queue import InferenceRequest, RequestQueue

logger = logging.getLogger(__name__)


class InferenceService:
    """Service that manages inference requests with multithreading and queue fallback.

    This service attempts to process requests immediately using available threads.
    When all threads are busy, requests are queued and processed as threads become available.
    """

    def __init__(
        self,
        llm_manager: LLMManager,
        request_queue: RequestQueue,
        max_concurrent: int = 2,
    ):
        """Initialize the inference service.

        Args:
            llm_manager: The LLM manager instance.
            request_queue: The request queue for overflow.
            max_concurrent: Maximum concurrent inference requests.
        """
        self.llm_manager = llm_manager
        self.request_queue = request_queue
        self.max_concurrent = max_concurrent
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._active_count = 0
        self._lock = asyncio.Lock()
        self._llm_lock = asyncio.Lock()  # Serialize LLM access (not thread-safe)
        self._running = False
        self._queue_worker_task: asyncio.Task | None = None

    @property
    def active_count(self) -> int:
        """Get the number of currently active inference requests."""
        return self._active_count

    @property
    def has_capacity(self) -> bool:
        """Check if there's capacity for immediate processing."""
        return self._active_count < self.max_concurrent

    async def submit(self, request: InferenceRequest) -> bool:
        """Submit a request for processing.

        If threads are available, processes immediately. Otherwise queues.

        Args:
            request: The inference request to process.

        Returns:
            True if processing immediately, False if queued.
        """
        async with self._lock:
            if self._active_count < self.max_concurrent:
                self._active_count += 1
                # Process immediately in background
                asyncio.create_task(self._process_with_tracking(request))
                logger.info(
                    f"Request {request.id} processing immediately "
                    f"(active: {self._active_count}/{self.max_concurrent})"
                )
                return True
            else:
                # Queue for later processing
                await self.request_queue.put(request)
                logger.info(
                    f"Request {request.id} queued "
                    f"(queue size: {self.request_queue.size}, "
                    f"active: {self._active_count}/{self.max_concurrent})"
                )
                return False

    async def _process_with_tracking(self, request: InferenceRequest) -> None:
        """Process a request and track completion."""
        try:
            await self._process_request(request)
        finally:
            async with self._lock:
                self._active_count -= 1
            # Check if there are queued requests to process
            await self._process_next_queued()

    async def _process_next_queued(self) -> None:
        """Check queue and process next request if capacity available."""
        async with self._lock:
            if self._active_count < self.max_concurrent and self.request_queue.size > 0:
                try:
                    request = await asyncio.wait_for(
                        self.request_queue.get(),
                        timeout=0.1,
                    )
                    self._active_count += 1
                    asyncio.create_task(self._process_with_tracking(request))
                    self.request_queue.task_done()
                    logger.info(
                        f"Request {request.id} dequeued for processing "
                        f"(active: {self._active_count}/{self.max_concurrent})"
                    )
                except asyncio.TimeoutError:
                    pass

    async def start_queue_worker(self) -> None:
        """Start background worker to process queued requests."""
        self._running = True
        logger.info("Inference service queue worker started")

        while self._running:
            try:
                # Wait a bit then check for queued work
                await asyncio.sleep(0.1)

                if self.request_queue.size > 0:
                    await self._process_next_queued()

            except asyncio.CancelledError:
                logger.info("Queue worker cancelled")
                break
            except Exception as e:
                logger.error(f"Queue worker error: {e}")

        logger.info("Inference service queue worker stopped")

    async def run(self) -> None:
        """Start the background queue processing worker."""
        await self.start_queue_worker()

    async def _process_request(self, request: InferenceRequest) -> None:
        """Process a single inference request.

        Args:
            request: The inference request to process.
        """
        if not self.llm_manager or not self.llm_manager.is_loaded:
            await request.fail(RuntimeError("Model not loaded"))
            return

        try:
            if request.stream:
                await self._process_streaming(request)
            else:
                await self._process_sync(request)
            logger.info(f"Request {request.id} completed")
        except Exception as e:
            logger.error(f"Inference error for request {request.id}: {e}")
            await request.fail(e)

    async def _process_streaming(self, request: InferenceRequest) -> None:
        """Process a streaming inference request.

        Args:
            request: The inference request to process.
        """
        loop = asyncio.get_event_loop()

        # Run inference in thread pool to avoid blocking
        def generate():
            tokens = []
            for token in self.llm_manager.generate_stream(
                prompt=request.prompt,
                system=request.system,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=request.stop,
            ):
                tokens.append(token)
                # Schedule token delivery on the event loop
                asyncio.run_coroutine_threadsafe(
                    request.put_token(token),
                    loop,
                )
            return tokens

        # Acquire LLM lock - llama-cpp is not thread-safe for concurrent inference
        async with self._llm_lock:
            tokens = await loop.run_in_executor(self._executor, generate)

        # Calculate stats
        prompt_tokens = self.llm_manager.get_token_count(request.prompt)
        completion_tokens = len(tokens)

        stats = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

        await request.complete(stats)

    async def _process_sync(self, request: InferenceRequest) -> None:
        """Process a non-streaming inference request.

        Args:
            request: The inference request to process.
        """
        loop = asyncio.get_event_loop()

        # Run inference in thread pool
        def generate():
            return self.llm_manager.generate(
                prompt=request.prompt,
                system=request.system,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=request.stop,
            )

        # Acquire LLM lock - llama-cpp is not thread-safe for concurrent inference
        async with self._llm_lock:
            result = await loop.run_in_executor(self._executor, generate)

        # Put the full text as a single token
        await request.put_token(result["text"])

        stats = {
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
        }

        await request.complete(stats)

    def stop(self) -> None:
        """Stop the service."""
        self._running = False
        self._executor.shutdown(wait=False)

    async def benchmark(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 160,
        temperature: float = 0.2,
        top_p: float = 0.9,
        top_k: int = 40,
        runs: int = 2,
        context_sizes: list[int] | None = None,
    ) -> dict:
        """Benchmark inference speed and return tuning recommendations."""
        if not self.llm_manager or not self.llm_manager.is_loaded:
            raise RuntimeError("Model not loaded")

        loop = asyncio.get_event_loop()
        base_ctx = self.llm_manager.settings.n_ctx
        candidates = context_sizes or [max(512, min(base_ctx, 1024)), base_ctx]

        # Keep valid, unique context sizes while preserving order.
        seen = set()
        valid_contexts = []
        for ctx in candidates:
            if ctx < 256 or ctx > 8192 or ctx in seen:
                continue
            seen.add(ctx)
            valid_contexts.append(ctx)

        if not valid_contexts:
            valid_contexts = [base_ctx]

        profiles = []
        async with self._llm_lock:
            for ctx in valid_contexts:
                run_results = []
                for _ in range(runs):
                    result = await loop.run_in_executor(
                        self._executor,
                        lambda target_ctx=ctx: self.llm_manager.generate_with_metrics(
                            prompt=prompt,
                            system=system,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                            top_k=top_k,
                            stop=[],
                            n_ctx=target_ctx,
                        ),
                    )
                    run_results.append(result)

                profile = {
                    "context_size": ctx,
                    "runs": runs,
                    "avg_latency_ms": round(mean(r["latency_ms"] for r in run_results), 2),
                    "avg_ttft_ms": round(
                        mean(
                            r["time_to_first_token_ms"]
                            for r in run_results
                            if r["time_to_first_token_ms"] is not None
                        ),
                        2,
                    )
                    if any(r["time_to_first_token_ms"] is not None for r in run_results)
                    else None,
                    "avg_completion_tokens": round(
                        mean(r["completion_tokens"] for r in run_results),
                        2,
                    ),
                    "avg_completion_tokens_per_second": round(
                        mean(r["completion_tokens_per_second"] for r in run_results),
                        2,
                    ),
                }
                profiles.append(profile)

        best_profile = max(
            profiles,
            key=lambda p: (
                p["avg_completion_tokens_per_second"],
                -p["avg_latency_ms"],
            ),
        )
        recommended_max_tokens = self._recommend_max_tokens(
            requested_max_tokens=max_tokens,
            completion_tokens_per_second=best_profile["avg_completion_tokens_per_second"],
        )

        return {
            "model": self.llm_manager.model_name,
            "runs": runs,
            "prompt_chars": len(prompt),
            "profiles": profiles,
            "recommended": {
                "env": {
                    "N_CTX": best_profile["context_size"],
                    "MAX_TOKENS": recommended_max_tokens,
                    "N_THREADS": self.llm_manager.settings.n_threads,
                    "OLLAMA_KEEP_ALIVE": self.llm_manager.settings.ollama_keep_alive,
                },
                "request_defaults": {
                    "max_tokens": recommended_max_tokens,
                    "stream": True,
                },
                "reason": (
                    "Recommendation favors the profile with the highest measured completion token throughput."
                ),
            },
        }

    @staticmethod
    def _recommend_max_tokens(
        requested_max_tokens: int,
        completion_tokens_per_second: float,
    ) -> int:
        """Pick a practical default max_tokens based on measured throughput."""
        cap = max(32, requested_max_tokens)
        if completion_tokens_per_second < 4:
            return min(cap, 64)
        if completion_tokens_per_second < 8:
            return min(cap, 96)
        if completion_tokens_per_second < 12:
            return min(cap, 128)
        return min(cap, 160)


# Keep backward compatibility alias
InferenceWorker = InferenceService
