# Self-improving knowledge-base loop

Self-improving Jetson Tutor is designed for students who can physically access the device but may not have internet. The local Qwen model must be strong enough to answer from the available offline knowledge base, but it also needs a way to admit when the local knowledge base is missing coverage.

## Offline behavior

For every student question:

1. Transcribe the question locally.
2. Retrieve or reference local educational knowledge-base material when available.
3. Generate an answer with the local Qwen model.
4. Ask the local model to judge the answer quality.
5. If the answer is weak, save an improvement record.

A weak answer can mean:

- The model is uncertain.
- The answer is too vague or incomplete.
- The answer depends on facts not present in the local knowledge base.
- The student asked a topic the current knowledge base does not cover.
- The model could not explain the concept at the right level.

## Improvement queue

The queue should preserve enough information to improve later without requiring the student to repeat themselves:

```json
{
  "question": "student's original question",
  "answer_summary": "what the tutor answered",
  "self_judgment": "why the answer was not good enough",
  "missing_topics": ["topic or curriculum area"],
  "timestamp": "local device time"
}
```

The prototype already exposes weak-answer / self-improvement state in the dashboard and keeps runtime artifacts out of git.

## Online behavior

When the device later has internet access, an online agent reviews the queued weak-answer records and creates a knowledge-base enrichment request. The online step should:

1. Group similar student questions.
2. Identify missing curriculum topics.
3. Download, summarize, or transform reliable educational resources.
4. Store the new material in the local knowledge base.
5. Mark the queue items as addressed.
6. Keep generated sources/metadata local so future offline answers can cite or ground against them.

## Scope boundary

Self-improvement is intentionally limited to the **knowledge base**. The system should not automatically rewrite arbitrary code, change safety policies, or update model weights. The goal is to make offline tutoring coverage better for the real questions students ask, while keeping the device understandable and safe to operate.
