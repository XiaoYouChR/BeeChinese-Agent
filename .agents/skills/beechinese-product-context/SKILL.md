---
name: beechinese-product-context
description: >-
  BeeChinese product identity and learning-loop context. Use when a task touches
  courses, exercises, speaking drills, the AI tutor, community, expert AI, or
  teacher/admin behavior.
triggers:
  - beechinese
  - course
  - exercise
  - speaking
  - tutor
  - scenario
  - community
  - expert ai
  - teacher
  - admin
---

# BeeChinese Product Context

BeeChinese is not a generic LMS, generic chatbot, or generic forum. It is an AI-enabled Chinese-learning SaaS for primarily English-speaking international students.

Default product lens:

- Strengthen one real learning loop at a time.
- Prefer teaching behavior over generic content display or generic chat.
- Keep outputs structured when AI features are involved.
- Stay MVP-friendly, but do not claim learner history, reports, or progress behavior that the implementation does not actually support.

The main product loops are:

1. Course learning: discover course -> study lesson -> persist progress.
2. Exercise feedback: answer -> grade -> review -> retry.
3. Speaking drill: repeat sentence -> score/correct -> revisit weak items.
4. Scenario tutor: guided dialogue -> hint/correct -> structured session report.
5. Community pragmatics: ask about real Chinese usage -> discussion and selective expert-AI help.

Common BeeChinese failure modes:

- Building a generic course website instead of a learning loop.
- Treating the AI tutor like unrestricted chat instead of guided teaching.
- Returning unstructured prose for AI grading.
- Ignoring cultural-pragmatic nuance in community or expert-AI work.
- Overbuilding teacher/admin flows before learner value exists.

Open these docs when you need full detail:

- `docs/beechinese-product-brief.md`
- `docs/beechinese-feature-map.md`
- `docs/beechinese-acceptance.md`

