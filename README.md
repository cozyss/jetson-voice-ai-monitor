# Self-improving Jetson Tutor

> A pocket classroom for places where the internet disappears: local voice tutoring on NVIDIA Jetson, plus an online review loop that makes the offline knowledge base better every time the device reconnects.

Self-improving Jetson Tutor is an offline-first AI tutor built on an NVIDIA Jetson. A student asks a question out loud, Whisper transcribes it locally, Qwen answers locally, Piper speaks the answer, and a dashboard shows the whole learning loop. Every local question and answer can be saved. When internet is later available, an "Internet God" review pass judges the saved Q&A and enriches the **local knowledge base** with corrections, teacher notes, and external educational knowledge for future offline sessions.

The motivating story is Afghan girls' education: students may need a learning companion that works even when classrooms, connectivity, and formal access are constrained. The project is not a replacement for teachers or schools. It is a resilient edge-learning prototype: a small device that can keep answering questions today, remember where it was weak, and come back tomorrow with better local guidance.

## Why this matters

Education access in Afghanistan is not an abstract problem:

- UNICEF reported in March 2025 that the ban on girls' secondary education had deprived **2.2 million girls** of their right to education, and warned that if the ban continues through 2030, **over 4 million girls** could be denied education beyond primary school. ([UNICEF ROSA, 2025](https://www.unicef.org/rosa/press-releases/new-school-year-starts-afghanistan-almost-400000-more-girls-deprived-their-right))
- UNESCO reported that Afghanistan is the only country where girls over 12 and women are prohibited from education, and estimated **1.4 million girls** had been deliberately denied secondary schooling since 2021; including girls already out of school, nearly **2.5 million girls** were deprived of their right to education. ([UNESCO, 2024](https://www.unesco.org/en/articles/afghanistan-14-million-girls-still-banned-school-de-facto-authorities))
- UNICEF and UNESCO's 2025 Afghanistan education analysis found that more than **2.13 million primary-school-aged children** were out of school in 2024 and that more than **90% of 10-year-olds** could not read a simple text. ([UNICEF Afghanistan, 2025](https://www.unicef.org/afghanistan/press-releases/afghanistans-education-system-facing-deepening-crisis-both-girls-and-boys-warn))
- The World Bank has described Afghanistan's education system as a learning crisis, with inequitable access, rural attendance gaps, and many students not gaining basic reading and writing skills even when enrolled. ([World Bank, 2018](https://www.worldbank.org/en/country/afghanistan/publication/afghanistan-promoting-education-during-times-of-increased-fragility))

That context shaped the design: do as much as possible locally, assume the network is unreliable, and use rare internet windows to improve the device for the actual questions students ask.

## The hackathon idea in one sentence

**A Jetson-powered voice tutor that saves every offline Q&A, lets an online reviewer judge what was weak when connectivity returns, and writes the resulting guidance into a local knowledge base so future offline answers improve without retraining the model.**

## What makes it self-improving

The self-improvement loop is intentionally narrow and reviewable:

1. **Answer locally first.** Qwen runs through a local `llama.cpp` server on the Jetson.
2. **Save the learning trace.** The daemon stores local questions and answers in `qa_review_queue.json` and tracks weak/gap items in `weak_answers.json`.
3. **Reconnect intentionally.** The dashboard exposes **Connect to Internet + Review Q&A + Enrich KB**.
4. **Judge with internet available.** An optional online judge reviews saved Q&A for accuracy, clarity, age-appropriateness, and missing knowledge.
5. **Enrich local knowledge only.** The system writes teacher notes, corrected short answers, missing facts, and source-backed guidance to `knowledge_base/kb_items.json`.
6. **Use the enriched KB offline.** Later prompts inject relevant local KB notes before Qwen answers, so the tutor becomes better on repeated topics.

It does **not** automatically fine-tune model weights or rewrite arbitrary code. The self-improvement target is the local educational knowledge base.


## Hackathon tracing and build workflow

For the hackathon demo, the repo includes optional **Weights & Biases telemetry** support. When `VOICE_WANDB_ENABLED=1` and `WANDB_API_KEY` is configured, daemon events are mirrored to W&B so reviewers can trace the learning loop: local question, local answer, saved Q&A, weak-answer counts, Internet God review status, and KB enrichment progress. Telemetry is opt-in because the default deployment goal is privacy-preserving offline learning.

The project was also built with an AI-native developer workflow:

- **Cursor** was used as the coding environment for rapid iteration, refactors, and repo packaging.
- **OpenAI models** supported product reasoning, implementation planning, README/report drafting, and review of the hackathon narrative.
- **Weights & Biases** provides observability for the demo traces, making the self-improvement loop visible rather than a black box.

## Demo behavior

Current repo code mirrors the live Jetson demo:

- Push-to-talk voice capture using Linux input/media keys and ALSA `arecord`.
- Local STT with `whisper.cpp`.
- Local Qwen inference through an OpenAI-compatible `llama.cpp` server.
- Local Piper TTS for spoken answers.
- Conversation memory saved locally in `conversation.json`.
- Saved Q&A review queue in `qa_review_queue.json`.
- Weak-answer / knowledge-gap queue in `weak_answers.json`.
- Optional nonsense/noise input filter with `nonsense_inputs.json` for demo cleanup.
- Local KB enrichment file in `knowledge_base/kb_items.json`.
- Dashboard view for live status, transcript, local answer, saved Q&A, online judgments, KB items, and delete/reset controls.
- Optional W&B telemetry/tracing for hackathon observability when explicitly enabled.

Runtime queues, recordings, logs, generated KB artifacts, API keys, and model weights are ignored by git. Example JSON structures live in [`examples/`](examples/).

## Architecture

```text
student voice
   │
   ▼
ALSA arecord ──► whisper.cpp ──► local router / prompt builder
                                  │
                                  ├─► local KB retrieval from knowledge_base/kb_items.json
                                  │
                                  ▼
                           Qwen on llama.cpp
                                  │
                      ┌───────────┴───────────┐
                      ▼                       ▼
               Piper spoken answer       saved Q&A queue
                                              │
                                              ▼
                         when online: Internet God review
                                              │
                                              ▼
                              local KB enrichment for next offline use
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/SELF_IMPROVEMENT.md`](docs/SELF_IMPROVEMENT.md) for implementation details.

## Demo hardware

Prototype environment:

- NVIDIA Jetson Orin-class device, Ubuntu 24.04 / L4T R39.
- USB EMEET OfficeCore speakerphone.
- Qwen 9B-class GGUF model served by `llama.cpp` with CUDA/Flash Attention.
- `whisper.cpp` base.en model.
- Piper local TTS voices.

## Quick start on Jetson

```bash
git clone https://github.com/cozyss/jetson-voice-ai-monitor.git
cd jetson-voice-ai-monitor

./scripts/install_deps_jetson.sh
cp .env.example .env
# Edit .env: set VOICE_ARECORD_DEVICE and VOICE_TTS_AUDIO_DEVICE from `arecord -l` / `aplay -l`.
```

Build or provide these binaries/assets:

- `/workspace/whisper.cpp/build/bin/whisper-cli` or set `VOICE_WHISPER_BIN`.
- `/workspace/qwen-jetson/server-fa-bin/llama-server` or set `LLAMA_SERVER`.
- `/workspace/piper/piper/piper` or set `VOICE_PIPER_BIN`.
- Whisper model at `/workspace/models/whisper/ggml-base.en.bin` or set `VOICE_WHISPER_MODEL`.
- Piper voices under `/workspace/models/piper/`.
- Qwen GGUF at `/workspace/models/Qwen3.5-9B-Q4_K_M.gguf` or set `MODEL`.

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

## Dashboard actions

- **Ask typed question**: sends text through the same local tutor path as voice.
- **Connect to Internet + Review Q&A + Enrich KB**: runs the online review/enrichment path for saved Q&A when `VOICE_SYSTEM_JUDGE_ENABLED=1` and an API key is available.
- **Delete**: removes individual saved Q&A, weak/gap, nonsense, or KB items for demo reset.

## Systemd install

After editing `.env`:

```bash
sudo ./scripts/install_systemd.sh
```

## Runtime files

By default runtime state lives in `/workspace/voice-ai`:

- `state.json` — current dashboard state.
- `events.jsonl` — event log.
- `commands.jsonl` — command queue.
- `conversation.json` — short local chat history.
- `recordings/` — local audio snippets.
- `qa_review_queue.json` — saved local Q&A awaiting or containing online judgment.
- `weak_answers.json` — unresolved weak-answer / knowledge-gap records.
- `nonsense_inputs.json` — filtered noise/accidental input records.
- `knowledge_base/kb_items.json` — enriched local teacher notes and external knowledge snippets.

These files are ignored by git.

## Privacy / offline-first design

The normal tutoring loop runs locally: audio capture, transcription, Qwen inference, local KB retrieval, answer playback, and dashboard state. Optional internet use is explicit and scoped to review/enrichment. For real deployments, student data in the review queue should be minimized, consented, and protected before any online review.

## Hackathon submission

See [`HACKATHON_SUBMISSION.md`](HACKATHON_SUBMISSION.md) for copy/paste submission text.

## License

MIT
