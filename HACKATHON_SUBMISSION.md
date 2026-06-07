# Hackathon submission draft

## Project name
Self-improving Jetson Tutor

## Short description
An offline-first voice tutor on NVIDIA Jetson for students without reliable internet access. It uses local Whisper, Qwen, llama.cpp CUDA/Flash Attention, and Piper TTS to answer questions offline, judges whether each answer was good enough, queues weakly answered questions, and later enriches its local educational knowledge base when internet access returns.

## What it does
- Helps Afghan girls continue learning on a local Jetson device even when internet access is unavailable.
- Turns a Jetson + USB speakerphone into a local voice tutor.
- Uses hardware/media keys for push-to-talk recording.
- Transcribes student questions locally with whisper.cpp.
- Answers with a local Qwen GGUF model served by llama.cpp on Jetson GPU.
- Asks the local model to judge whether the answer was complete, grounded, and useful.
- Saves questions that were not answered well to a weak-answer/self-improvement queue.
- When internet is available, reviews the queue and creates a self-improvement request to download/enrich the local knowledge base.
- Limits self-improvement scope to the educational knowledge base, not unrestricted code or model-weight changes.
- Speaks responses with Piper TTS and exposes a live dashboard for transcripts, routing decisions, tool calls, weak-answer queue, and runtime state.

## Why it matters
Many students cannot depend on continuous internet access. For Afghan girls facing severe barriers to education, an offline tutor can preserve access to learning material and personalized explanations. This project demonstrates a practical edge-AI pattern: keep tutoring private and local during offline use, then use occasional connectivity to improve the local knowledge base based on the actual questions students asked.

## Built with
NVIDIA Jetson Orin, Ubuntu/L4T, CUDA, llama.cpp, Qwen GGUF, whisper.cpp, Piper TTS, ALSA, Python stdlib HTTP server.

## Demo notes
The working prototype ran on a Jetson Orin-class device with:
- Qwen3.5 9B Q4_K_M served by llama.cpp with CUDA + Flash Attention.
- Whisper base.en for local STT.
- Piper voices for local TTS.
- EMEET OfficeCore USB speakerphone for capture/playback.
- Live browser dashboard exposed from the Jetson.

## Self-improvement loop
1. Student asks a question offline.
2. Qwen answers using local model + local knowledge base.
3. Qwen judges its own answer quality.
4. If weak, the system records the question and why the answer was insufficient.
5. Later, when online, an agent reviews the queue and downloads/enriches relevant local knowledge-base content.
6. Future offline answers can cover the questions students actually needed help with.

## Repository
https://github.com/cozyss/jetson-voice-ai-monitor
