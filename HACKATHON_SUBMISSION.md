# Hackathon submission draft

## Project name
Jetson Voice AI Monitor

## Short description
An offline-first voice AI companion running on an NVIDIA Jetson: press-to-talk audio capture, Whisper speech-to-text, local Qwen reasoning through llama.cpp CUDA/Flash Attention, Piper text-to-speech, tool calling, and a live web dashboard that shows the full decision pipeline.

## What it does
- Turns a Jetson + USB speakerphone into a local voice AI agent.
- Uses hardware/media keys for push-to-talk recording.
- Transcribes voice locally with whisper.cpp.
- Routes requests through a transparent system judge: answer locally, use a local tool, or queue a self-improvement request.
- Answers with a local Qwen GGUF model served by llama.cpp on Jetson GPU.
- Speaks responses with Piper TTS using separate voices for system/tool status and final Qwen answers.
- Provides a live dashboard for transcripts, routing decisions, tool calls, weak-answer/self-improvement queue, and runtime state.

## Why it matters
Most voice assistants depend on cloud services. This project demonstrates a privacy-preserving edge AI architecture where audio, transcripts, and reasoning can stay on the device, while still exposing enough telemetry to debug and improve the assistant.

## Built with
NVIDIA Jetson Orin, Ubuntu/L4T, CUDA, llama.cpp, Qwen GGUF, whisper.cpp, Piper TTS, ALSA, Python stdlib HTTP server.

## Demo notes
The working prototype ran on a Jetson Orin-class device with:
- Qwen3.5 9B Q4_K_M served by llama.cpp with CUDA + Flash Attention.
- Whisper base.en for local STT.
- Piper voices for local TTS.
- EMEET OfficeCore USB speakerphone for capture/playback.
- Live browser dashboard exposed from the Jetson.

## Repository
https://github.com/cozyss/jetson-voice-ai-monitor
