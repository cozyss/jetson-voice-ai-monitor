#!/usr/bin/env bash
set -euo pipefail
mkdir -p /workspace/models/whisper /workspace/models/piper /workspace/models
# Whisper base.en model
if [ ! -f /workspace/models/whisper/ggml-base.en.bin ]; then
  curl -L --fail -o /workspace/models/whisper/ggml-base.en.bin     https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
fi
# Piper voices used by default. Path layout: en/en_US/<speaker>/<quality>/<voice>.(onnx|onnx.json)
download_piper_voice() {
  local speaker="$1" quality="$2" voice="en_US-${speaker}-${quality}"
  for suffix in onnx onnx.json; do
    local f="/workspace/models/piper/${voice}.${suffix}"
    if [ ! -f "$f" ]; then
      curl -L --fail -o "$f"         "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/${speaker}/${quality}/${voice}.${suffix}"
    fi
  done
}
download_piper_voice ryan high
download_piper_voice lessac high
cat <<'MSG'
Downloaded Whisper/Piper assets. Download a GGUF chat model separately, e.g. Qwen Q4_K_M, to /workspace/models/.
MSG
