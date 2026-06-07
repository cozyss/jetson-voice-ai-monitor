# Self-improving knowledge-base loop

Self-improving Jetson Tutor is not a model-fine-tuning project. It is a practical offline education loop: answer now with a local model, preserve the local Q&A trace, and use occasional internet access to enrich the local knowledge base for future offline use.

## Offline-first behavior

For each student question, the daemon:

1. Captures voice or typed input.
2. Transcribes voice locally with `whisper.cpp`.
3. Retrieves relevant local KB notes from `knowledge_base/kb_items.json`.
4. Prompts local Qwen through the Jetson `llama.cpp` server.
5. Speaks the answer with Piper.
6. Saves the question and answer to `qa_review_queue.json` for later review.
7. Tracks weak/gap items in `weak_answers.json` when an answer or topic needs follow-up.

The local Qwen prompt tells the tutor to be honest when it is uncertain and to prefer enriched KB notes when they are relevant. This keeps normal use fully available even without internet.

## Online review behavior

When an operator presses **Connect to Internet + Review Q&A + Enrich KB**, and online judging is configured, the daemon:

1. Opens a short "internet session" state for the dashboard.
2. Loads pending saved Q&A records.
3. Sends each Q&A to the configured online judge.
4. Asks for compact JSON: score, whether enrichment is needed, reason, missing knowledge, suggested improvement, search query, and a concise `teacher_note`.
5. Marks good answers as reviewed.
6. Writes missing facts, corrections, guidance, and external/source-backed context into `knowledge_base/kb_items.json` for answers that need improvement.
7. Leaves all generated enrichment local so later offline prompts can use it.

The latest prompt is tuned for spoken tutoring: a good answer may be short if it is accurate, clear, age-appropriate, and easy to hear.

## Runtime files

- `qa_review_queue.json` — all saved local questions/answers plus optional Internet God judgments.
- `weak_answers.json` — unresolved weak-answer or knowledge-gap records.
- `knowledge_base/kb_items.json` — enriched local facts, teacher notes, corrections, source snippets, and guidance.
- `nonsense_inputs.json` — filtered noise or accidental input records that should not pollute the learning queue.
- `conversation.json` — short rolling context for continuity.

These are runtime artifacts and are not committed. Sample shapes are in `examples/`.

## Safety boundary

Self-improvement is deliberately constrained to the **knowledge base**. The system does not automatically update model weights, change safety policy, or rewrite arbitrary code as part of the educational learning loop. That makes demos auditable and makes future classroom deployments easier to reason about.

## Why this loop fits constrained education

Afghan girls are the motivating use case because the access problem is severe and connectivity cannot be assumed. A device that only works online fails precisely when it may be most needed. A device that learns from student questions while offline, then uses rare connectivity windows to improve local teacher notes, is more resilient and better aligned with rural, low-bandwidth, or restricted-learning environments.
