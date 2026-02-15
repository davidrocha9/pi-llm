# Pi LLM

On-Demand LLM service optimized for **Raspberry Pi 5**, featuring Google's **Gemma 2B** model via Ollama.

This project provides a lightweight FastAPI server that allows you to run a local Large Language Model and access it via a REST API. It is specifically tuned for the `aarch64` architecture and limited resources of a Raspberry Pi, while remaining compatible with standard x86 systems.

## 🚀 Features

- **Gemma 2B via Ollama**: High-performance small language model optimized for edge devices.
- **Ollama Integration**: Automatic model management with Ollama (no manual GGUF downloads).
- **FastAPI Interface**: Clean RESTful API for text generation and system health monitoring.
- **SSE Streaming**: Real-time token streaming using Server-Sent Events (SSE).
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
├── .venv/                   # Python virtual environment (created by setup)
├── api_keys.db              # SQLite database for API keys
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project metadata
└── README.md               # This file
```

## 📋 Prerequisites

- **Raspberry Pi 5** (recommended) or any Linux/macOS/Windows machine.
- **Python 3.11** or higher.
- **curl** (for Ollama installation).
- (Optional) **Tailscale** for remote access.

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd pi-llm
   ```

2. **Run the setup script**:
   The setup script installs Ollama, creates a virtual environment, installs dependencies, and **pulls the Gemma 2B model**.
   
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

The server will start on `http://0.0.0.0:8000` (configurable via environment variables).

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
  "model_path": "gemma:2b",
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
  "max_tokens": 512,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "stop": ["\n"],
  "stream": true
}
```

**Parameters:**
- `prompt` (string, required): The input prompt (1-8192 characters)
- `max_tokens` (integer, optional): Maximum tokens to generate (1-2048, default: 512)
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

You can customize the server by creating a `.env` file in the root directory:

```env
HOST=0.0.0.0
PORT=8000
OLLAMA_PORT=11434
MODEL_NAME=gemma:2b
MAX_TOKENS=512
TEMPERATURE=0.7
API_KEYS_DB=api_keys.db
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
- **Memory**: The Gemma 2B model fits comfortably within 2GB of RAM.
- **Inference Speed**: You can expect ~5-10 tokens per second on a Pi 5.
- **Ollama**: Automatically handles ARM optimizations and model caching.
