# Pi LLM — On‑Demand LLM on Raspberry Pi 5

Turns your Raspberry Pi 5 into a personal, private AI assistant running Gemma 3 (1B) locally. This repository provides a compact REST API to run local inference with a small memory footprint.

**Features**
- Local inference of Gemma 3 (1B) with 4-bit quantization (gguf).
- Simple REST API: prompt → response (sync and streaming).
- Request management: accepts concurrent clients, queues requests, and safely serializes model access to avoid crashes.
- Small and self-hostable — no cloud required.

**Requirements**
- Raspberry Pi 5 (recommended) or a similar x86/ARM machine with enough RAM and CPU.
- Python 3.11+ (see `pyproject.toml`).
- The model file (e.g. `models/gemma-3-1b-it-Q4_K_M.gguf`) — `scripts/download_model.py` can help.

Quick overview — how to run
--------------------------------
1) Clone & enter the project on the Pi

```bash
git clone <repo-url> pi-llm
cd pi-llm
```

2) Setup (create virtualenv and install dependencies)

```bash
bash scripts/setup.sh
source .venv/bin/activate
```

3) Download the model (if you don't have it already)

```bash
python3 scripts/download_model.py
# or place your gguf model under the models/ folder
```

4) Generate an API key (writes to `.env`)

```bash
chmod +x scripts/gen_key.sh
./scripts/gen_key.sh
grep '^API_KEY=' .env
```

5) Start the server (options)

- Default (binds to 127.0.0.1):

```bash
bash scripts/start.sh
```

- Bind to all interfaces (LAN / Tailnet) so other machines can reach it:

```bash
HOST=0.0.0.0 PORT=8000 bash scripts/start.sh
```

- Run directly with `uvicorn` (for debugging):

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Run as a background service (example `systemd` unit):

Create `/etc/systemd/system/pi-llm.service` with contents:

```
[Unit]
Description=Pi LLM
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/pi-llm
Environment=PATH=/home/pi/pi-llm/.venv/bin
ExecStart=/home/pi/pi-llm/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pi-llm
sudo journalctl -u pi-llm -f
```

6) Call the API from your PC

Fetch the API key from the Pi (via Tailnet/SSH):

```bash
KEY=$(ssh pi@<PI_TAILNET_IP> "grep '^API_KEY=' /home/pi/pi-llm/.env | cut -d= -f2-")
```

Direct request (server reachable via Tailnet or LAN IP):

```bash
curl -s -X POST http://<PI_TAILNET_IP>:8000/generate \
	-H "Content-Type: application/json" \
	-H "X-API-Key: $KEY" \
	-d '{"prompt":"Hello from my PC","stream":false}'
```

If server is bound to `127.0.0.1` on the Pi, create an SSH tunnel from your PC:

```bash
ssh -L 8000:localhost:8000 pi@<PI_TAILNET_IP>
# then on your PC:
curl -s -X POST http://localhost:8000/generate -H "Content-Type: application/json" -H "X-API-Key: $KEY" -d '{"prompt":"Hi","stream":false}'
```

Notes & tuning
--------------
- The app serializes actual model calls (the underlying model library is not safe for concurrent calls on the same instance), but it still tracks and queues multiple client requests so clients don't block while waiting to be accepted.
- Tune `max_concurrent_requests` and `max_queue_size` in `app/config.py` to balance memory and responsiveness.
- If you need parallel model inference you must run multiple separate model processes (high memory cost) or a pool of machines.

Security
--------
- Keep the API key secret. Do not check `.env` into source control.
- For public access use a reverse proxy with TLS or a secure tunnel (Cloudflare Tunnel, ngrok, or SSH tunnels).

Useful files
------------
- `scripts/setup.sh` — create venv & install deps
- `scripts/start.sh` — start wrapper (reads `.env` and activates venv)
- `scripts/gen_key.sh` — generate API key and write to `.env`
- `scripts/download_model.py` — helper to download gguf model
- `app/` — application code
- `models/` — place gguf model here