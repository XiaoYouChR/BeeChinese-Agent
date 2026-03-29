---
name: beechinese-acceptance-checks
description: >-
  Acceptance and verifier guidance for BeeChinese slices. Use when deciding
  whether a change is coherent, honest, and complete enough for now.
triggers:
  - acceptance
  - verifier
  - verify
  - pass
  - fail
  - grading
  - report
  - progress
---

# BeeChinese Acceptance Checks

Cross-cutting bar:

- The change should help a real learner, teacher, or operator workflow.
- Docs must not overclaim behavior that the code does not implement.
- AI-facing outputs should be structured when downstream UI or logic depends on them.
- MVP simplifications are acceptable if they are explicit.

High-signal FAIL conditions:

- "AI tutor" is only generic chat with no scenario goal or teaching behavior.
- "AI grading" returns unstructured prose with no reusable grading fields.
- Expert AI is described as auto-replying everywhere.
- Docs claim history, progress, or reports that the implementation clearly lacks.
- An MVP slice introduces complexity that does not improve a BeeChinese learning loop.

Minimum structured outputs to preserve when relevant:

- Grading: `score`, issue summary, revision suggestions, encouraging feedback.
- Tutor report: scenario theme, completion level, speaking summary, typical problems, more natural suggestions, recommended next steps.

Open `docs/beechinese-acceptance.md` for fuller module-specific cues and verifier heuristics.

