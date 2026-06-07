# Self-improving Jetson Tutor

Offline-first voice tutor for NVIDIA Jetson, built for students who may have access to a local device but little or no internet connectivity.

The motivating use case is helping Afghan girls continue learning in places where reliable internet access is not available. The system keeps the full question-answering loop on the Jetson: speech input, local transcription, Qwen reasoning, answer playback, and a local dashboard. When it later gets internet access, it can use the questions it failed to answer well to improve the local knowledge base for the next offline session.

## Core idea

A powerful local Qwen model should do more than answer questions. After each answer, it should judge whether it answered well enough using the available local knowledge base.

- If the answer is good, the session continues normally.
- If the answer is weak, uncertain, incomplete, or outside the current local knowledge base, the system saves the question and context to an offline improvement queue.
- When internet is available again, the system reviews the queued weak-answer questions, creates a self-improvement request, downloads/enriches relevant educational knowledge-base material, and prepares it for future offline use.
- The self-improvement scope is intentionally limited to the **knowledge base**, not arbitrary model weights or unrestricted code changes.

This makes the device more useful over time for the real questions students ask, while preserving an offline-first learning experience.

## What is included

- **Push-to-talk audio capture** using Linux input/media keys and ALSA `arecord`.
- **Local speech-to-text** with `whisper.cpp`.
- **Local reasoning** with a Qwen GGUF model served by `llama.cpp` on Jetson GPU.
- **Answer-quality judgment** so the local model can decide whether it answered the student well.
- **Weak-answer queue** for questions that need knowledge-base improvement once internet is available.
- **Knowledge-base self-improvement loop** for online enrichment of offline educational content.
- **Local speech output** with Piper TTS.
- **Live dashboard** showing transcript, routing, tool calls, Qwen answer, runtime state, and the improvement queue.

This repo is designed for hackathon review: checked-in code is reusable tutor/voice-agent infrastructure; model weights, recordings, logs, generated knowledge-base artifacts, and secrets are intentionally excluded.

## Demo hardware

Prototype environment:

- NVIDIA Jetson Orin-class device, Ubuntu 24.04 / L4T R39.
- USB EMEET OfficeCore speakerphone.
- Qwen3.5 9B Q4_K_M GGUF.
- `llama.cpp` CUDA build with Flash Attention enabled.
- `whisper.cpp` base.en model.
- Piper local TTS voices.

## How it works

1. Student presses **Volume Up** to start recording a question.
2. Student presses **Volume Down** to stop recording.
3. The daemon transcribes the utterance locally with Whisper.
4. A local judge/router decides whether the request can be answered from local capability and knowledge.
5. Qwen answers through an OpenAI-compatible `llama.cpp` server running on the Jetson.
6. Qwen also evaluates whether its answer was good enough.
7. If the answer was not good enough, the question is saved to the weak-answer/self-improvement queue.
8. Piper speaks the response.
9. The dashboard displays every step for debugging and demoing.
10. When internet becomes available, the queued questions guide knowledge-base enrichment for future offline sessions.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/SELF_IMPROVEMENT.md`](docs/SELF_IMPROVEMENT.md) for details.

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
{"action":"ask","text":"Explain photosynthesis at a middle-school level."}
```

## Runtime files

By default runtime state lives in `/workspace/voice-ai`:

- `state.json` — current dashboard state.
- `events.jsonl` — event log.
- `commands.jsonl` — command queue.
- `conversation.json` — optional short chat history.
- `recordings/` — local audio snippets.
- improvement queue files — weak/uncertain questions to revisit when online.

These are ignored by git.

## Privacy / offline-first design

The normal tutoring loop runs locally: audio capture, STT, Qwen inference, tools, answer-quality judgment, and TTS. Optional online enrichment happens only when internet is available and is scoped to updating the local educational knowledge base.

## Hackathon submission

See [`HACKATHON_SUBMISSION.md`](HACKATHON_SUBMISSION.md) for copy/paste submission text.

## License

MIT
