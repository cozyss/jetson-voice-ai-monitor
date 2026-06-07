#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y \
  git cmake build-essential python3 python3-venv python3-pip \
  alsa-utils espeak-ng curl jq pkg-config libopenblas-dev
mkdir -p /workspace/models/whisper /workspace/models/piper /workspace/voice-ai
cat <<'MSG'
Base dependencies installed.
Next:
  1. Build/install whisper.cpp and llama.cpp (see README).
  2. Download model files with scripts/download_models.sh.
  3. Copy .env.example to .env and adjust VOICE_ARECORD_DEVICE.
MSG
