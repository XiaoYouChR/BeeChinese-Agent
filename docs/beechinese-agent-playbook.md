# BeeChinese Agent Playbook

## Purpose

This document exists to improve future agent runs. It turns the BeeChinese product docs into practical operating guidance for:

- `repo-study`
- `planner`
- the parent orchestrator
- implementation specialists
- `verifier`

Use this file when the task is broad, ambiguous, or likely to drift into generic edtech or generic AI-chat behavior.

## Canonical reading order

When product intent matters, read documents in this order:

1. `.openhands/AGENTS.md`
2. `docs/beechinese-product-brief.md`
3. `docs/beechinese-feature-map.md`
4. `docs/beechinese-acceptance.md`
5. this playbook

If these docs appear to disagree, prefer the more specific product-facing document over the shorter summary document.

## Default planning algorithm

When a task is not fully specified:

1. identify the target user
2. identify the product loop being improved
3. choose the smallest vertical slice that creates visible progress
4. decide which specialist agents own the slice
5. define a concrete stop condition
6. define verifier checks that prove the slice is real

In BeeChinese, the target user is usually one of:

- learner
- teacher/content publisher
- admin/operator

## Which product loop is this task serving?

Map vague tasks to one of these default loops:

- `course-learning`: discover course -> watch lesson -> persist progress
- `exercise-feedback`: answer -> grade -> review -> retry
- `speaking-drill`: repeat sentence -> score -> track weakness -> review
- `scenario-tutor`: choose scenario -> guided dialogue -> structured report
- `community-pragmatics`: ask cultural/pragmatic question -> receive discussion or expert explanation
- `teacher-publishing`: create/edit content -> publish to learner flow

If a task cannot be mapped to one of these loops, question whether it is actually a BeeChinese product task.

## Default ownership map

Use this map unless the repo state strongly suggests another split:

- `repo-study`: current workspace shape, blockers, constraints, existing patterns
- `planner`: small execution plan, acceptance criteria, owner assignment
- `sdk-platform`: Python/OpenHands/runtime/docs plumbing, repo bootstrap, shared scaffolding
- `taro-frontend`: learner-facing pages, flows, state, and UX for Web + WeChat Mini Program
- `admin-nextjs`: teacher/admin pages, content operations, moderation surfaces
- `nestjs-api`: core business entities, APIs, persistence, auth, progress, community, orders
- `fastapi-ai`: grading logic, pronunciation integration points, tutor orchestration, structured reports, expert-AI logic
- `docs-writer`: README, docs, developer guidance, interface notes, product-doc synchronization
- `verifier`: strict review only, never implementation

## Recommended decomposition patterns

### Pattern A: learner-visible vertical slice

Use when the task should create a user-facing feature quickly.

- Taro or Next.js surface for entry and display
- NestJS API for persistence and business state
- FastAPI only if AI output is essential to the slice
- Docs updates only if behavior or setup changed materially

### Pattern B: AI contract first

Use when the most important uncertainty is AI output shape.

- define a structured schema first
- implement FastAPI or service contract
- expose that contract to NestJS or frontend
- verify docs do not overclaim full intelligence before it exists

### Pattern C: teacher-to-learner publishing flow

Use when content operations matter.

- admin-nextjs owns teacher workflow
- nestjs-api owns content models and publish boundaries
- taro-frontend only joins when learner consumption is part of the same slice

### Pattern D: scaffolding-only task

Use when the repo still lacks real product code.

- sdk-platform owns structure and runtime glue
- docs-writer keeps future product intent visible
- verifier ensures scaffolding is honest about current limitations

## Common BeeChinese failure modes to avoid

- building a generic course website instead of a learning loop
- treating the AI tutor like unrestricted chat instead of guided teaching
- treating AI grading like one paragraph of prose instead of structured feedback
- treating pronunciation practice as one-time scoring instead of repeated improvement
- treating the community like a generic forum without cultural-pragmatic focus
- making expert AI answer everything automatically instead of selective participation
- overbuilding admin workflows before learner value exists
- trying to launch all modules in one task instead of finishing one slice

## What planner should optimize for

- one meaningful slice per cycle
- visible progress toward a BeeChinese learning loop
- minimal but real cross-service contracts
- verifier checks that can actually fail if the work is hollow
- explicit deferral of non-MVP requirements rather than vague future promises

## What verifier should challenge aggressively

- claims that a feature exists when only placeholder docs exist
- AI features without structured outputs
- scenario tutor flows with no scenario goal or guidance behavior
- community or expert-AI work that ignores pragmatic or cultural focus
- progress, history, or reports described in docs but absent from implementation
- infra-heavy or abstraction-heavy work that does not improve a BeeChinese product loop

## Default success-criteria examples

These examples help when the user gives a broad task but not a strong completion bar.

### Course slice

`A learner can open a course, inspect meaningful course metadata, and see lesson or chapter structure documented or implemented with verifier-confirmed consistency.`

### Exercise slice

`A learner can submit at least one exercise type and the system returns a stored, structured grading result that the verifier can inspect.`

### Speaking drill slice

`A learner can practice a fixed sentence, receive scoring or correction feedback, and the system preserves enough result structure for later review.`

### AI tutor slice

`A learner can enter a named scenario, receive guided dialogue behavior, and finish with a structured report rather than only a raw transcript.`

### Community plus expert-AI slice

`A learner can open a topic-focused discussion thread and expert AI participation is either topic-scoped or user-invoked, not indiscriminate.`

## How to handle ambiguity

When a task is ambiguous:

- prefer course, exercise, speaking, tutor, community, and teacher/admin interpretations over generic SaaS interpretations
- prefer Chinese-learning specificity over generic learning-platform abstractions
- prefer explicit docs and schema contracts over hidden assumptions
- prefer a narrow shipping slice over broad speculative scaffolding

## Relationship to the other product docs

- The product brief defines what BeeChinese is.
- The feature map defines what to prioritize and in what order.
- The acceptance guide defines what good enough looks like.
- This playbook defines how agents should reason with those docs while running tasks.
