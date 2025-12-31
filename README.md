# Pi LLM

On-Demand LLM service optimized for **Raspberry Pi 5**, featuring Google's **Gemma 3 1B** model with 4-bit quantization.

This project provides a lightweight FastAPI server that allows you to run a local Large Language Model and access it via a REST API. It is specifically tuned for the `aarch64` architecture and limited resources of a Raspberry Pi, while remaining compatible with standard x86 systems.

## 🚀 Features

- **Gemma 3 1B (GGUF)**: High-performance small language model optimized for edge devices.
- **FastAPI Interface**: Clean RESTful API for text generation and system health monitoring.
- **SSE Streaming**: Real-time token streaming using Server-Sent Events (SSE).
- **SQLite Authentication**: Robust API key management with SQLite storage and HMAC-SHA256 hashing.
- **Request Queuing**: Built-in concurrency management to handle multiple requests without crashing the Pi.
- **Tailscale Friendly**: Defaults to `0.0.0.0` for easy access over Tailscale or local networks.
- **Pi 5 Optimized**: Automated setup for `llama-cpp-python` with OpenBLAS accelerations on ARM.

## 🛠 Tech Stack

- **Python 3.11+**
- **FastAPI** & **Uvicorn**
- **llama-cpp-python** (GGML/GGUF backend)
- **SQLite** (API Key Store)
- **Pydantic Settings** (Configuration management)

## 📋 Prerequisites

- **Raspberry Pi 5** (recommended) or any Linux/macOS/Windows machine.
- **Python 3.11** or higher.
- (Optional) **Tailscale** for remote access.

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd pi-llm
   ```

2. **Run the setup script**:
   The setup script creates a virtual environment, installs dependencies, and **automatically downloads the Gemma 3 model**.
   
   - **For Standard PC**:
     ```bash
     bash scripts/setup.sh
     ```
   - **For Raspberry Pi (ARM)**:
     ```bash
     bash scripts/setup.sh --pi
     ```

3. **(Optional) Manual Model Download**:
   If you need to re-download or pick a specific model version:
   ```bash
   python3 scripts/download_model.py
   ```

## 🔑 Key Generation

The API is protected by API key authentication. You must generate a key before making requests:

```bash
python3 scripts/gen_key.py
```
*Save the output key; it is stored securely in `api_keys.db`.*

## 🚀 Starting the Server

Start the FastAPI server:

```bash
bash scripts/start.sh
```
The server will start on `http://0.0.0.0:8000`.

## 📡 API Usage

### Health Check
Check if the model is loaded and see queue statistics.

```bash
curl http://localhost:8000/health
```

### Generate Text
Generate a response from the model. Supports both streaming (default) and non-streaming.

**Streaming (SSE):**
```bash
curl -N -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_GENERATED_KEY" \
  -d '{"prompt":"Explain gravity in one sentence.", "stream": true}'
```

**Non-Streaming:**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_GENERATED_KEY" \
  -d '{"prompt":"What is 2+2?", "stream": false}'
```

### Key Management
Generate a new API key via the API.

```bash
curl -X POST http://localhost:8000/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"owner": "External Device 1"}'
```

## ⚙️ Configuration

You can customize the server by creating a `.env` file in the root directory:

```env
HOST=0.0.0.0
PORT=8000
MODEL_PATH=models/gemma-3-1b-it-Q4_K_M.gguf
N_CTX=2048
N_THREADS=4
API_KEYS_DB=api_keys.db
```

## 📝 Notes on Pi 5 Performance

- **Thermal Throttling**: Running LLMs is CPU intensive. Ensure your Pi 5 has adequate cooling (Active Cooler).
- **Memory**: The Gemma 3 1B model with 4-bit quantization fits comfortably within 1GB of RAM, leaving plenty of room for the system.
- **Inference Speed**: You can expect ~10-15 tokens per second on a Pi 5 with the optimized OpenBLAS build.
