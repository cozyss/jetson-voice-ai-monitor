# Hackathon submission draft

## Project

**Self-improving Jetson Tutor** — an offline-first voice tutor for NVIDIA Jetson that saves local student Q&A, reviews weak answers when internet is available, and enriches a local knowledge base for future offline learning.

## Problem

Many students cannot rely on stable connectivity or consistent classroom access. The motivating use case is Afghan girls' education: UNICEF reported that 2.2 million Afghan girls had been deprived of education beyond primary school by March 2025, and UNESCO estimated that nearly 2.5 million Afghan school-age girls were deprived of their right to education when including those already out of school before the bans. At the same time, UNICEF/UNESCO reported that more than 90% of Afghan 10-year-olds cannot read a simple text.

## Solution

A local Jetson device acts as a voice-first tutor:

1. Student asks a question aloud.
2. Whisper transcribes locally.
3. Qwen answers locally from the device and its local knowledge base.
4. Piper speaks the answer.
5. The device saves the Q&A.
6. Later, when internet is intentionally connected, an online review pass judges the saved answers and writes corrections, teacher notes, and external educational knowledge into the local KB.
7. Future offline answers retrieve those notes first.

## What is novel

The demo is not just "LLM on edge." It adds a practical self-improvement loop for constrained environments: every offline interaction can become a signal for what the device should learn next, but the update target is limited to auditable local knowledge-base content rather than opaque model retraining.

## Built with

- NVIDIA Jetson Orin-class device
- `llama.cpp` CUDA/Flash Attention server
- Qwen GGUF model
- `whisper.cpp`
- Piper TTS
- Python daemon and local dashboard

## Current status

Working prototype code is packaged in this repo. Runtime logs, recordings, API keys, generated queue data, and model weights are excluded. Example JSON files document the review queue and local KB shapes.
