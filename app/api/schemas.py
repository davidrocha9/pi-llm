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
    system: str | None = Field(
        default=None,
        description="System prompt to guide the model's behavior",
        max_length=4096,
        examples=["You are a helpful assistant that provides concise answers."],
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


class BenchmarkRequest(BaseModel):
    """Request model for benchmark endpoint."""

    prompt: str = Field(
        default="Explain photosynthesis in two short sentences.",
        description="Prompt used for the benchmark run",
        min_length=1,
        max_length=2048,
    )
    system: str | None = Field(
        default=None,
        description="Optional system prompt used during benchmarking",
        max_length=2048,
    )
    max_tokens: int = Field(
        default=160,
        description="Maximum completion tokens per benchmark run",
        ge=1,
        le=512,
    )
    temperature: float = Field(
        default=0.2,
        description="Sampling temperature for benchmark stability",
        ge=0.0,
        le=2.0,
    )
    top_p: float = Field(
        default=0.9,
        description="Top-p sampling parameter",
        ge=0.0,
        le=1.0,
    )
    top_k: int = Field(
        default=40,
        description="Top-k sampling parameter",
        ge=1,
        le=100,
    )
    runs: int = Field(
        default=2,
        description="How many runs to execute per context size",
        ge=1,
        le=5,
    )
    context_sizes: list[int] | None = Field(
        default=None,
        description="Optional list of context sizes to test (e.g. [512, 1024])",
        max_length=4,
    )


class BenchmarkProfile(BaseModel):
    """Average benchmark metrics for a context size."""

    context_size: int = Field(..., description="Context size used for this profile")
    runs: int = Field(..., description="Number of runs in this profile")
    avg_latency_ms: float = Field(..., description="Average wall clock latency in ms")
    avg_ttft_ms: float | None = Field(
        default=None,
        description="Average approximate time-to-first-token in ms",
    )
    avg_completion_tokens: float = Field(
        ..., description="Average generated completion tokens"
    )
    avg_completion_tokens_per_second: float = Field(
        ..., description="Average completion throughput (tokens/s)"
    )


class BenchmarkEnvRecommendation(BaseModel):
    """Recommended environment variables based on benchmark results."""

    N_CTX: int = Field(..., description="Recommended context size")
    MAX_TOKENS: int = Field(..., description="Recommended default max tokens")
    N_THREADS: int = Field(..., description="Recommended thread count")
    OLLAMA_KEEP_ALIVE: str = Field(..., description="Recommended Ollama keep-alive")


class BenchmarkRequestDefaultsRecommendation(BaseModel):
    """Recommended per-request defaults."""

    max_tokens: int = Field(..., description="Recommended request max_tokens")
    stream: bool = Field(..., description="Whether streaming is recommended")


class BenchmarkRecommendation(BaseModel):
    """Benchmark recommendation payload."""

    env: BenchmarkEnvRecommendation
    request_defaults: BenchmarkRequestDefaultsRecommendation
    reason: str = Field(..., description="Explanation for this recommendation")


class BenchmarkResponse(BaseModel):
    """Response model for benchmark endpoint."""

    model: str = Field(..., description="Model used for benchmarking")
    runs: int = Field(..., description="Number of runs performed per profile")
    prompt_chars: int = Field(..., description="Prompt size in characters")
    profiles: list[BenchmarkProfile] = Field(
        ..., description="Measured profiles for each tested context size"
    )
    recommended: BenchmarkRecommendation


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
        default=0, description="Number of requests currently being processed"
    )
    max_concurrent: int = Field(
        default=0, description="Maximum concurrent requests allowed"
    )


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(default=None, description="Additional error details")


class KeyGenerateRequest(BaseModel):
    """Request model for API key generation."""

    owner: str = Field(
        default="",
        description="Owner name for the API key",
        examples=["Device 1"],
    )


class KeyGenerateResponse(BaseModel):
    """Response model for API key generation."""

    api_key: str = Field(..., description="The generated API key")
    owner: str = Field(..., description="Owner of the API key")
    created_at: int = Field(..., description="Unix timestamp of creation")
