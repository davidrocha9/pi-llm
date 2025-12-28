"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.core.llm import LLMManager
from app.core.queue import RequestQueue
from app.services.inference import InferenceService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
llm_manager: LLMManager | None = None
request_queue: RequestQueue | None = None
inference_service: InferenceService | None = None
worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - loads model on startup."""
    global llm_manager, request_queue, inference_service, worker_task

    settings = get_settings()
    logger.info("Starting Pi LLM service...")

    # Initialize LLM
    logger.info(f"Loading model from {settings.model_path}...")
    llm_manager = LLMManager(settings)

    try:
        llm_manager.load_model()
        logger.info("Model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.warning("Server starting without model - download model first!")

    # Initialize request queue (for overflow when all threads are busy)
    request_queue = RequestQueue(maxsize=settings.max_queue_size)

    # Initialize inference service with multithreading support
    inference_service = InferenceService(
        llm_manager,
        request_queue,
        max_concurrent=settings.max_concurrent_requests,
    )
    worker_task = asyncio.create_task(inference_service.run())
    logger.info(
        f"Inference service started "
        f"(max concurrent: {settings.max_concurrent_requests}, "
        f"queue size: {settings.max_queue_size})"
    )

    # Store in app state for access in routes
    app.state.llm_manager = llm_manager
    app.state.request_queue = request_queue
    app.state.inference_service = inference_service

    yield

    # Cleanup
    logger.info("Shutting down Pi LLM service...")
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    if inference_service:
        inference_service.stop()

    if llm_manager:
        llm_manager.unload_model()

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Pi LLM",
    description="On-Demand LLM on Raspberry Pi 5 - Gemma 3 1B with 4-bit quantization",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(router)


def run():
    """Run the server (entry point for CLI)."""
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
