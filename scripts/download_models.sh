#!/usr/bin/env bash
set -euo pipefail
mkdir -p /workspace/models/whisper /workspace/models/piper /workspace/models
# Whisper base.en model
if [ ! -f /workspace/models/whisper/ggml-base.en.bin ]; then
  curl -L --fail -o /workspace/models/whisper/ggml-base.en.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
fi
# Piper voices used by default
for voice in en_US-ryan-high en_US-lessac-high; do
  for suffix in onnx onnx.json; do
    f="/workspace/models/piper/${voice}.${suffix}"
    if [ ! -f "$f" ]; then
      curl -L --fail -o "$f" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/${voice#en_US-}/${voice}.${suffix}"
    fi
  done
done
cat <<'MSG'
Downloaded Whisper/Piper assets. Download a GGUF chat model separately, e.g. Qwen Q4_K_M, to /workspace/models/.
MSG
