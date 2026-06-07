#!/usr/bin/env bash
set -euo pipefail
MODEL=${MODEL:-/workspace/models/Qwen3.5-9B-Q4_K_M.gguf}
LLAMA_SERVER=${LLAMA_SERVER:-/workspace/qwen-jetson/server-fa-bin/llama-server}
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8083}
CTX=${CTX:-4096}
THREADS=${THREADS:-6}
NGL=${NGL:-99}
exec "$LLAMA_SERVER" \
  -m "$MODEL" --host "$HOST" --port "$PORT" \
  -c "$CTX" -t "$THREADS" -ngl "$NGL" -fa on --parallel 1
