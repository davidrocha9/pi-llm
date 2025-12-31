"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request model for text generation."""

    prompt: str = Field(
        ...,
        description="The input prompt for the LLM",
        min_length=1,
        max_length=8192,
        examples=["What is the capital of France?"],
    )
    max_tokens: int | None = Field(
        default=None,
        description="Maximum number of tokens to generate (uses server default if not specified)",
        ge=1,
        le=2048,
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature (higher = more creative, lower = more focused)",
        ge=0.0,
        le=2.0,
    )
    top_p: float = Field(
        default=0.9,
        description="Top-p (nucleus) sampling parameter",
        ge=0.0,
        le=1.0,
    )
    top_k: int = Field(
        default=40,
        description="Top-k sampling parameter",
        ge=1,
        le=100,
    )
    stop: list[str] | None = Field(
        default=None,
        description="Stop sequences to end generation",
        max_length=4,
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response via SSE",
    )


class GenerateResponse(BaseModel):
    """Response model for text generation (non-streaming)."""

    text: str = Field(..., description="The generated text")
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens generated")
    total_tokens: int = Field(..., description="Total tokens (prompt + completion)")


class StreamChunk(BaseModel):
    """Model for streaming response chunks."""

    token: str = Field(..., description="The generated token")
    done: bool = Field(default=False, description="Whether generation is complete")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether the LLM is loaded")
    model_path: str = Field(..., description="Path to the model file")
    queue_size: int = Field(..., description="Number of requests waiting in queue")
    active_requests: int = Field(
        default=0,
        description="Number of requests currently being processed"
    )
    max_concurrent: int = Field(
        default=0,
        description="Maximum concurrent requests allowed"
    )


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(default=None, description="Additional error details")

