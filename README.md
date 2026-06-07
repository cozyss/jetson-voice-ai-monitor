# Jetson Voice AI Monitor

Offline-first voice AI monitor for NVIDIA Jetson. It turns a Jetson + USB speakerphone into a transparent local voice assistant with:

- **Push-to-talk audio capture** using Linux input/media keys and ALSA `arecord`.
- **Local speech-to-text** with `whisper.cpp`.
- **Local reasoning** with a Qwen GGUF model served by `llama.cpp` on Jetson GPU.
- **Tool calling** for safe local Python/shell tasks, weather lookup, and improvement requests.
- **Local speech output** with Piper TTS.
- **Live dashboard** showing transcript, judge routing, tool calls, Qwen answer, runtime state, and weak-answer improvement queue.

This repo is designed for hackathon review: the checked-in code is the reusable monitor and dashboard; model weights, recordings, logs, and secrets are intentionally excluded.

## Demo hardware

Prototype environment:

- NVIDIA Jetson Orin-class device, Ubuntu 24.04 / L4T R39.
- USB EMEET OfficeCore speakerphone.
- Qwen3.5 9B Q4_K_M GGUF.
- `llama.cpp` CUDA build with Flash Attention enabled.
- `whisper.cpp` base.en model.
- Piper local TTS voices.

## How it works

1. User presses **Volume Up** to start recording.
2. User presses **Volume Down** to stop recording.
3. The daemon transcribes the utterance locally with Whisper.
4. A system judge decides whether the request can be handled locally or should be queued for self-improvement.
5. Local requests go to Qwen through an OpenAI-compatible `llama.cpp` server.
6. Qwen can call local tools, then returns a final answer.
7. Piper speaks the response.
8. The dashboard displays every step for debugging and demoing.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a diagram.

## Quick start on Jetson

```bash
git clone https://github.com/cozyss/jetson-voice-ai-monitor.git
cd jetson-voice-ai-monitor

./scripts/install_deps_jetson.sh
cp .env.example .env
# Edit .env: set VOICE_ARECORD_DEVICE and VOICE_TTS_AUDIO_DEVICE from `arecord -l` / `aplay -l`.
```

Build or provide these binaries/assets:

- `/workspace/whisper.cpp/build/bin/whisper-cli`
- `/workspace/qwen-jetson/server-fa-bin/llama-server` or set `LLAMA_SERVER`
- `/workspace/piper/piper/piper`
- Whisper model at `/workspace/models/whisper/ggml-base.en.bin`
- Piper voices under `/workspace/models/piper/`
- Qwen GGUF at `/workspace/models/Qwen3.5-9B-Q4_K_M.gguf` or set `MODEL`

Download the small STT/TTS assets:

```bash
./scripts/download_models.sh
```

Start the Qwen server:

```bash
MODEL=/workspace/models/Qwen3.5-9B-Q4_K_M.gguf ./scripts/start_llama_server.sh
```

In another terminal, start the daemon and dashboard:

```bash
./scripts/run_voice_daemon.sh
./scripts/run_dashboard.sh
```

Open the dashboard:

```text
http://JETSON_IP:7862
```

## Systemd install

After editing `.env`:

```bash
sudo ./scripts/install_systemd.sh
```

## Commands

Queue spoken status from a terminal:

```bash
PYTHONPATH=src python3 -m jetson_voice_ai_monitor.say_status "System online"
```

Send text through the same pipeline from the dashboard input box, or write JSONL commands to:

```text
$VOICE_AI_BASE/commands.jsonl
```

Example:

```json
{"action":"ask","text":"What can you see in your runtime state?"}
```

## Runtime files

By default runtime state lives in `/workspace/voice-ai`:

- `state.json` — current dashboard state.
- `events.jsonl` — event log.
- `commands.jsonl` — command queue.
- `conversation.json` — optional short chat history.
- `recordings/` — local audio snippets.

These are ignored by git.

## Privacy / offline-first design

The normal voice loop runs locally: audio capture, STT, LLM inference, tools, and TTS. Optional online integrations are disabled unless corresponding environment variables/API keys are provided.

## Hackathon submission

See [`HACKATHON_SUBMISSION.md`](HACKATHON_SUBMISSION.md) for copy/paste submission text.

## License

MIT
