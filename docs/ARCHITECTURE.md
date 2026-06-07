# Architecture

```mermaid
flowchart LR
  A[Student voice question] --> B[USB microphone / EMEET]
  B --> C[ALSA arecord]
  C --> D[Whisper.cpp local STT]
  D --> E[Local judge / router]
  E --> F[Qwen GGUF via llama.cpp server on Jetson GPU]
  K[Local educational knowledge base] --> F
  F --> G[Answer-quality self-judge]
  G -->|good answer| H[Piper TTS]
  G -->|weak / incomplete / outside KB| I[Weak-answer queue]
  I --> J[Online knowledge-base enrichment agent]
  J -->|when internet is available| K
  H --> L[USB speaker]
  D --> M[Dashboard state/events]
  E --> M
  F --> M
  G --> M
  I --> M
```

The daemon is offline-first: speech capture, transcription, local Qwen inference, answer-quality judgment, and TTS run on the Jetson. The self-improvement path is deliberately narrow: weakly answered student questions are queued offline, and later connectivity is used to enrich the local educational knowledge base so future offline answers improve.
