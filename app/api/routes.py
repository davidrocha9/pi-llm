"""API route definitions."""

import asyncio
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    KeyGenerateRequest,
    KeyGenerateResponse,
)
from app.config import get_settings
from app.core.auth import verify_api_key
from app.core.keys import KeyStore
from app.core.queue import InferenceRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _effective_max_tokens(requested: int | None, queue_size: int, settings) -> int:
    """Compute max_tokens with Pi-safe caps and load-aware downscaling."""
    desired = requested if requested is not None else settings.max_tokens
    capped = min(desired, settings.max_request_tokens_cap)

    # If any request is queued, prioritize responsiveness over long completions.
    if queue_size > 0:
        capped = min(capped, settings.busy_max_tokens)

    return max(1, capped)


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check(request: Request) -> HealthResponse:
    """Check the health status of the service."""
    settings = get_settings()
    llm_manager = request.app.state.llm_manager
    request_queue = request.app.state.request_queue
    inference_service = request.app.state.inference_service

    return HealthResponse(
        status="healthy" if llm_manager and llm_manager.is_loaded else "degraded",
        model_loaded=llm_manager.is_loaded if llm_manager else False,
        model_path=settings.ollama_model,
        queue_size=request_queue.size if request_queue else 0,
        active_requests=inference_service.active_count if inference_service else 0,
        max_concurrent=inference_service.max_concurrent if inference_service else 0,
    )


@router.post(
    "/generate",
    responses={
        200: {"description": "Successful generation"},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        429: {"model": ErrorResponse, "description": "Server busy"},
        503: {"model": ErrorResponse, "description": "Model not loaded"},
        504: {"model": ErrorResponse, "description": "Generation timeout"},
    },
    tags=["Generation"],
    summary="Generate text from prompt",
    description="Generate text using the LLM. Supports streaming via SSE (default) or synchronous JSON response.",
)
async def generate(
    request: Request,
    body: GenerateRequest,
    _: Annotated[str, Depends(verify_api_key)],
):
    """Generate text from the given prompt."""
    llm_manager = request.app.state.llm_manager
    inference_service = request.app.state.inference_service
    request_queue = request.app.state.request_queue

    # Check if model is loaded
    if not llm_manager or not llm_manager.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please download the model first.",
        )
    if not inference_service or not request_queue:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference service not available.",
        )

    settings = get_settings()
    max_tokens = _effective_max_tokens(
        requested=body.max_tokens,
        queue_size=request_queue.size,
        settings=settings,
    )

    # Create inference request
    inference_request = InferenceRequest(
        prompt=body.prompt,
        system=body.system,
        max_tokens=max_tokens,
        temperature=body.temperature,
        top_p=body.top_p,
        top_k=body.top_k,
        stop=body.stop or [],
        stream=body.stream,
    )

    # Submit to inference service (handles threading/queuing automatically)
    try:
        is_immediate = await inference_service.submit(inference_request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    logger.info(
        f"Request {inference_request.id} submitted "
        f"({'immediate' if is_immediate else 'queued'})"
    )

    if body.stream:
        # Streaming response via SSE
        return EventSourceResponse(
            stream_generator(inference_request),
            media_type="text/event-stream",
        )
    else:
        # Synchronous response
        try:
            return await asyncio.wait_for(
                wait_for_completion(inference_request),
                timeout=settings.sync_response_timeout_s,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    "Generation timed out. Use stream=true or a lower max_tokens "
                    "for faster responses on Raspberry Pi."
                ),
            ) from exc


@router.post(
    "/benchmark",
    response_model=BenchmarkResponse,
    responses={
        200: {"description": "Benchmark completed"},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        503: {"model": ErrorResponse, "description": "Model not loaded"},
    },
    tags=["Generation"],
    summary="Benchmark model performance",
    description=(
        "Run a small benchmark against the current model and return throughput "
        "metrics with Pi-oriented tuning recommendations."
    ),
)
async def benchmark(
    request: Request,
    body: BenchmarkRequest,
    _: Annotated[str, Depends(verify_api_key)],
) -> BenchmarkResponse:
    """Benchmark model speed and return recommended settings."""
    llm_manager = request.app.state.llm_manager
    inference_service = request.app.state.inference_service

    if not llm_manager or not llm_manager.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please download the model first.",
        )

    if not inference_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference service not available.",
        )

    try:
        result = await inference_service.benchmark(
            prompt=body.prompt,
            system=body.system,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            top_k=body.top_k,
            runs=body.runs,
            context_sizes=body.context_sizes,
        )
    except Exception as e:
        logger.error(f"Benchmark error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Benchmark failed. Check server logs for details.",
        ) from e

    return BenchmarkResponse(**result)


async def stream_generator(inference_request: InferenceRequest):
    """Generate SSE events from inference request."""
    try:
        async for token in inference_request.token_stream():
            yield {
                "event": "token",
                "data": json.dumps({"token": token, "done": False}),
            }

        # Send completion event with stats
        stats = await inference_request.get_stats()
        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "done": True,
                    "prompt_tokens": stats.get("prompt_tokens", 0),
                    "completion_tokens": stats.get("completion_tokens", 0),
                    "total_tokens": stats.get("total_tokens", 0),
                }
            ),
        }
    except asyncio.CancelledError:
        logger.info(f"Stream cancelled for request {inference_request.id}")
        raise
    except Exception as e:
        logger.error(f"Stream error for request {inference_request.id}: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}),
        }


async def wait_for_completion(inference_request: InferenceRequest) -> GenerateResponse:
    """Wait for inference to complete and return full response."""
    # Collect all tokens
    tokens = []
    async for token in inference_request.token_stream():
        tokens.append(token)

    text = "".join(tokens)
    stats = await inference_request.get_stats()

    return GenerateResponse(
        text=text,
        prompt_tokens=stats.get("prompt_tokens", 0),
        completion_tokens=stats.get("completion_tokens", 0),
        total_tokens=stats.get("total_tokens", 0),
    )


@router.post(
    "/keys/generate",
    response_model=KeyGenerateResponse,
    tags=["Management"],
    summary="Generate a new API key",
    description="Create a new API key. No authentication required.",
)
async def generate_key(
    body: KeyGenerateRequest,
) -> KeyGenerateResponse:
    """Generate and store a new secure API key."""
    new_key = secrets.token_urlsafe(32)
    settings = get_settings()

    db_path = settings.api_keys_db
    if not db_path:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SQLite key storage is not configured on this server.",
        )

    # Resolve path
    repo_root = Path(__file__).resolve().parents[2]
    p = Path(db_path)
    if not p.is_absolute():
        p = (repo_root / p).resolve()

    try:
        ks = KeyStore(p)
        ks.add_key(new_key, owner=body.owner)
        ks.close()

        return KeyGenerateResponse(
            api_key=new_key,
            owner=body.owner,
            created_at=int(time.time()),
        )
    except Exception as e:
        logger.error(f"Failed to generate API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while saving the new key.",
        )
