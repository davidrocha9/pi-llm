# Pi LLM

On-Demand LLM service optimized for **Raspberry Pi 5**, featuring **Qwen 2.5 3B** via Ollama.

This project provides a lightweight FastAPI server that allows you to run a local Large Language Model and access it via a REST API. It is specifically tuned for the `aarch64` architecture and limited resources of a Raspberry Pi, while remaining compatible with standard x86 systems.

## 🚀 Features

- **Qwen 2.5 3B via Ollama**: Smarter multilingual small model optimized for edge devices.
- **Ollama Integration**: Automatic model management with Ollama (no manual GGUF downloads).
- **FastAPI Interface**: Clean RESTful API for text generation and system health monitoring.
- **System Prompts**: Guide model behavior with dedicated system prompts.
- **SSE Streaming**: Real-time token streaming using Server-Sent Events (SSE).
- **Benchmark & Auto-Tuning**: Measure token throughput and get recommended Pi settings.
- **SQLite Authentication**: Robust API key management with SQLite storage and HMAC-SHA256 hashing.
- **Request Queuing**: Built-in concurrency management to handle multiple requests without crashing the Pi.
- **Tailscale Friendly**: Defaults to `0.0.0.0` for easy access over Tailscale or local networks.
- **Pi 5 Optimized**: Automated setup and Ollama configuration for ARM architecture.

## 🛠 Tech Stack

- **Python 3.11+**
- **FastAPI** & **Uvicorn**
- **Ollama** (LLM runtime and model management)
- **SQLite** (API Key Store)
- **Pydantic Settings** (Configuration management)

## 📁 Project Structure

```
pi-llm/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # API endpoint definitions
│   │   └── schemas.py       # Pydantic request/response models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py          # API key authentication
│   │   ├── keys.py          # Key storage and management
│   │   ├── llm.py           # Ollama LLM manager
│   │   └── queue.py         # Request queuing system
│   ├── services/
│   │   ├── __init__.py
│   │   └── inference.py     # Inference service with threading
│   ├── __init__.py
│   ├── config.py            # Settings and configuration
│   └── main.py              # FastAPI application entry point
├── scripts/
│   ├── setup.sh             # Install Ollama, setup environment
│   ├── start.sh             # Start Ollama and FastAPI server
│   ├── uninstall.sh         # Remove all downloaded/configured data
│   └── gen_key.py           # CLI tool to generate API keys
├── configs/
│   └── pi5-fast.env         # Default Pi 5 low-latency runtime profile
├── .venv/                   # Python virtual environment (created by setup)
├── api_keys.db              # SQLite database for API keys
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project metadata
└── README.md               # This file
```

## 📋 Prerequisites

- **Raspberry Pi 5** (recommended) or any Linux/macOS/Windows machine.
- **Python 3.11** or higher.
- **curl** (for installation and API requests).
- (Optional) **Tailscale** for remote access.

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd pi-llm
   ```

2. **Run the setup script**:
   The setup script installs Ollama, creates a virtual environment, installs dependencies, and **pulls the default Qwen 2.5 3B model**.
   
   ```bash
   bash scripts/setup.sh
   ```

   The `--pi` flag is no longer needed as Ollama handles ARM optimizations automatically.

## 🔑 Key Generation

The API is protected by API key authentication. You must generate a key before making requests:

```bash
python3 scripts/gen_key.py
```

Or via the API (no auth required for this endpoint):

```bash
curl -X POST http://localhost:8000/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"owner": "my-device"}'
```

*Save the output key; it is stored securely in `api_keys.db`.*

## 🚀 Starting the Server

Start the server (automatically starts Ollama in the background):

```bash
bash scripts/start.sh
```

By default, `start.sh` loads `configs/pi5-fast.env`, which includes a Pi-optimized model and latency settings:
- `OLLAMA_MODEL=qwen2.5:3b`
- `N_CTX=512`
- `MAX_TOKENS=96`
- `N_THREADS=4`

The server will start on `http://0.0.0.0:8000`.
Startup now blocks until the configured `OLLAMA_MODEL` is available and warmed up.

Use a different profile file if needed:

```bash
bash scripts/start.sh --config /path/to/your.env
```

## 📡 Quick Start with cURL

Once the server is running, you can interact with it using curl:

### 1. Check Health

```bash
curl http://localhost:8000/health
```

### 2. Generate an API Key

```bash
curl -X POST http://localhost:8000/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"owner": "my-device"}'
```

Save the returned API key (e.g., `your_api_key_here`) for the next steps.

### 3. Generate Text (Streaming)

```bash
curl -N -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "prompt": "Explain gravity in one sentence.",
    "max_tokens": 96,
    "stream": true
  }'
```

### 4. Generate Text (Non-Streaming)

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "prompt": "What is 2+2?",
    "max_tokens": 32,
    "stream": false
  }'
```

### 5. Generate with System Prompt

Guide the model's behavior with a system prompt:

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "prompt": "What is photosynthesis?",
    "system": "You are a science teacher explaining to a 5-year-old. Use simple words and be enthusiastic.",
    "max_tokens": 96,
    "stream": false
  }'
```

### 6. Benchmark and Auto-Tune (Pi 5)

Run a quick benchmark and get recommended `.env` + request defaults:

```bash
curl -X POST http://localhost:8000/benchmark \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "prompt": "Explain photosynthesis in two short sentences.",
    "max_tokens": 160,
    "runs": 2,
    "context_sizes": [512, 1024]
  }'
```

### Full Example with All Parameters

```bash
curl -N -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "prompt": "Write a haiku about coding",
    "system": "You are a creative writing assistant",
    "max_tokens": 100,
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40,
    "stop": ["\n\n"],
    "stream": true
  }'
```

## 📡 API Endpoints

### Health Check

**Endpoint:** `GET /health`

Check if the service is running and see current queue statistics.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_path": "qwen2.5:3b",
  "queue_size": 0,
  "active_requests": 0,
  "max_concurrent": 4
}
```

### Generate Text

**Endpoint:** `POST /generate`

Generate text from a prompt. Supports both streaming (default) and non-streaming responses.

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: YOUR_API_KEY`

**Request Body:**
```json
{
  "prompt": "Explain gravity in one sentence.",
  "system": "You are a helpful assistant",
  "max_tokens": 160,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "stop": ["\n"],
  "stream": true
}
```

**Parameters:**
- `prompt` (string, required): The input prompt (1-8192 characters)
- `system` (string, optional): System prompt to guide model behavior (max 4096 characters)
- `max_tokens` (integer, optional): Maximum tokens to generate (1-2048, default: 160)
- `temperature` (float, optional): Sampling temperature 0.0-2.0 (default: 0.7)
- `top_p` (float, optional): Top-p sampling 0.0-1.0 (default: 0.9)
- `top_k` (integer, optional): Top-k sampling 1-100 (default: 40)
- `stop` (array of strings, optional): Stop sequences (max 4 items)
- `stream` (boolean, optional): Stream response via SSE (default: true)

#### Streaming Response (SSE)

```bash
curl -N -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"prompt": "Explain gravity in one sentence.", "stream": true}'
```

**Events:**
- `event: token` - Contains a generated token chunk
- `event: done` - Sent when generation is complete, includes token counts
- `event: error` - Sent if an error occurs

#### Non-Streaming Response

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"prompt": "What is 2+2?", "stream": false}'
```

**Response:**
```json
{
  "text": "2+2 equals 4.",
  "prompt_tokens": 5,
  "completion_tokens": 5,
  "total_tokens": 10
}
```

#### Using System Prompts

System prompts guide the model's behavior and style:

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "prompt": "Tell me about the solar system",
    "system": "You are an enthusiastic astronomy professor. Be engaging and use analogies.",
    "stream": false
  }'
```

### Benchmark Model Performance

**Endpoint:** `POST /benchmark`

Run controlled benchmark requests and get measured throughput with recommended Pi settings.

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: YOUR_API_KEY`

**Request Body:**
```json
{
  "prompt": "Explain photosynthesis in two short sentences.",
  "max_tokens": 160,
  "temperature": 0.2,
  "top_p": 0.9,
  "top_k": 40,
  "runs": 2,
  "context_sizes": [512, 1024]
}
```

**Response:**
```json
{
  "model": "qwen2.5:3b",
  "runs": 2,
  "prompt_chars": 47,
  "profiles": [
    {
      "context_size": 512,
      "runs": 2,
      "avg_latency_ms": 1840.17,
      "avg_ttft_ms": 311.89,
      "avg_completion_tokens": 78.0,
      "avg_completion_tokens_per_second": 9.42
    },
    {
      "context_size": 1024,
      "runs": 2,
      "avg_latency_ms": 2124.63,
      "avg_ttft_ms": 356.21,
      "avg_completion_tokens": 78.5,
      "avg_completion_tokens_per_second": 8.11
    }
  ],
  "recommended": {
    "env": {
      "N_CTX": 512,
      "MAX_TOKENS": 128,
      "N_THREADS": 4,
      "OLLAMA_KEEP_ALIVE": "30m"
    },
    "request_defaults": {
      "max_tokens": 128,
      "stream": true
    },
    "reason": "Recommendation favors the profile with the highest measured completion token throughput."
  }
}
```

### Generate API Key

**Endpoint:** `POST /keys/generate`

Generate a new API key (no authentication required for this endpoint).

**Request Body:**
```json
{
  "owner": "Device Name"
}
```

```bash
curl -X POST http://localhost:8000/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"owner": "External Device 1"}'
```

**Response:**
```json
{
  "api_key": "abc123...xyz",
  "owner": "External Device 1",
  "created_at": 1700000000
}
```

## ⚙️ Configuration

Default runtime profile (`configs/pi5-fast.env`) used by `start.sh`:

```env
HOST=0.0.0.0
PORT=8000
OLLAMA_PORT=11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_KEEP_ALIVE=30m
OLLAMA_WARMUP=true
N_CTX=512
N_THREADS=4
MAX_TOKENS=96
API_KEYS_DB=api_keys.db
```

You can still create a `.env` file for extra overrides/secrets, or pass a different profile:

```bash
bash scripts/start.sh --config configs/pi5-fast.env
```

## 🗑️ Uninstall

To remove all downloaded data, models, and configurations:

```bash
bash scripts/uninstall.sh
```

This removes:
- Virtual environment (`.venv`)
- Ollama models
- API keys database and configuration
- Python cache files

Source code and git repository are preserved.

## 📝 Notes on Pi 5 Performance

- **Thermal Throttling**: Running LLMs is CPU intensive. Ensure your Pi 5 has adequate cooling (Active Cooler).
- **Memory**: `qwen2.5:3b` is heavier than `gemma:2b`; on Pi 5, 8GB RAM is recommended for smoother multitasking.
- **Inference Speed**: Long answers are expensive on Pi. Keep `max_tokens` low (for example `64-160`) for much faster responses.
- **Streaming**: Use `"stream": true` to start receiving output immediately instead of waiting for the full completion.
- **Model Residency**: `OLLAMA_KEEP_ALIVE=30m` keeps the model in memory and avoids repeated cold-start delays.
