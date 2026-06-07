#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "${VOICE_AI_BASE:-/workspace/voice-ai}"
exec python3 -m jetson_voice_ai_monitor.voice_daemon
