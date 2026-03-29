# BeeChinese Repo Guidance

This repository is the autonomous coding layer for BeeChinese. Treat it as the control plane that coordinates future full-stack development, not as the BeeChinese product codebase itself.

## Product context

BeeChinese is a Chinese-learning SaaS for primarily English-speaking international students. The long-term product shape includes:

- Course catalog and video-based learning
- Chapter exercises with AI grading
- Fixed-sentence speaking drills
- Real-time AI tutor / situational dialogue
- Chinese-language community / forum
- Cross-language cultural-pragmatics expert AI
- Lightweight teacher/admin tooling

Detailed product scope, priorities, and acceptance cues live in these canonical docs:

- `docs/beechinese-product-brief.md`
- `docs/beechinese-feature-map.md`
- `docs/beechinese-acceptance.md`
- `docs/beechinese-agent-playbook.md`

For product-facing work:

- Read the product brief first when you need concrete feature expectations.
- Use the feature map to distinguish MVP-now work from later-phase scope.
- Use the acceptance guide when planning, reviewing, or deciding whether a slice is complete enough.
- Use the agent playbook when a task is broad, cross-cutting, or likely to drift into generic product decisions.

## Target technical architecture

Unless a task explicitly says otherwise, optimize for this future stack:

- User app: Taro + React + TypeScript, targeting Web + WeChat Mini Program
- Admin app: Next.js + React + TypeScript
- Main backend: NestJS
- AI backend: FastAPI
- Data: PostgreSQL + Redis + MinIO
- Delivery: MVP-first, demo-friendly, fast validation of business assumptions

## Working rules

- Local repository context comes first.
- Treat the canonical BeeChinese product docs in `docs/` as the default source of truth for product intent.
- Prefer `docs_tool_set` for framework documentation lookup and use browser tools as fallback or for real-page validation.
- Do not assume real BeeChinese app code already exists.
- Prefer small, reviewable changes over speculative framework work.
- Keep README, repo guidance, validation scripts, and agent definitions aligned.
- When repo context is insufficient, browsing is allowed on a minimal-necessary basis and should prefer official documentation, without hard-banning other sources.
- For OpenHands usage, stay close to SDK-native patterns: file-based agents, TaskToolSet delegation, and verifier-driven repair loops.

## Default orchestration flow

1. Study the repo and existing context.
2. Produce a short implementation plan with acceptance criteria.
3. Delegate work to the smallest suitable specialist.
4. Run a strict verifier that does not edit files.
5. Feed verifier findings back into a repair round if needed.
6. If the verifier passes but the broader goal is still incomplete, start another outer cycle with fresh repo study and planning.
7. Stop after the goal is complete, verification fails irrecoverably, or the configured outer-cycle safety limit is reached.

## Repository conventions

- `.agents/agents/`: file-based specialist agents
- `.openhands/`: repo-specific OpenHands guidance and scripts
- `beechinese_agent/`: Python orchestration runtime
- `tools/`: runnable entry points
- `docs/`: human-readable docs and examples

## Future directory intent

When product code is introduced later, prefer a structure along these lines:

- `apps/taro-user/`
- `apps/admin-web/`
- `services/nest-api/`
- `services/fastapi-ai/`
- `packages/shared/`

Do not create those directories unless the task actually calls for them.
