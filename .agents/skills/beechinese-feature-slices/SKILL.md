---
name: beechinese-feature-slices
description: >-
  BeeChinese milestone ladder and MVP slicing guidance. Use when planning or
  executing the next smallest vertical slice.
triggers:
  - milestone
  - mvp
  - roadmap
  - slice
  - phase
  - vertical slice
---

# BeeChinese Feature Slices

Default milestone order:

1. Agent control plane
2. Course learning baseline
3. Exercise and grading baseline
4. Fixed-sentence speaking baseline
5. Situational AI tutor baseline
6. Community baseline
7. Expert-AI augmentation
8. Teacher/admin enrichment

When the task is broad, prefer one complete vertical slice over shallow work across every module.

Good early slices:

- Course list/detail plus lesson structure and progress semantics
- Exercise submission plus structured grading result
- Speaking drill entry plus scoring/correction contract
- One guided scenario plus structured tutor report
- One community discussion loop with selective expert-AI behavior

Default dependency order:

1. Model the core domain or schema.
2. Add API or service boundary.
3. Add learner-facing or teacher-facing UI only as needed.
4. Update docs and operational notes.
5. Verify the slice end to end.

Avoid in early tasks:

- Broad multi-module scaffolding with no usable loop
- Institution-grade admin complexity
- Infra-heavy abstractions that slow MVP delivery

Open `docs/beechinese-feature-map.md` for the full milestone ladder and stack-by-stack emphasis.

