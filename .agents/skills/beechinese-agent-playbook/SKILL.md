---
name: beechinese-agent-playbook
description: >-
  Practical BeeChinese planning and ownership playbook. Use when a task is
  ambiguous, cross-cutting, or needs a clear repo-study -> planner -> implement
  -> verify decomposition.
triggers:
  - plan
  - planner
  - owner
  - decompose
  - loop
  - task split
---

# BeeChinese Agent Playbook

When a task is ambiguous:

1. Identify the target user.
2. Identify the product loop being improved.
3. Choose the smallest slice that creates visible progress.
4. Assign the right specialist agent.
5. Define a concrete stop condition.
6. Define verifier checks that can actually fail.

Default ownership map:

- `sdk-platform`: OpenHands runtime, Python infra, shared scaffolding
- `taro-frontend`: learner-facing Taro flows
- `admin-nextjs`: teacher/admin surfaces
- `nestjs-api`: core business models, auth, progress, community, orders
- `fastapi-ai`: grading, pronunciation integration, tutor orchestration, expert AI
- `docs-writer`: README, repo guidance, interface notes
- `verifier`: strict review only

Default decomposition patterns:

- learner-visible vertical slice
- AI contract first
- teacher-to-learner publishing flow
- scaffolding-only task

Challenge these failure modes aggressively:

- Generic edtech interpretations instead of Chinese-learning specificity
- Generic forum mechanics without cultural-pragmatic focus
- Broad work across many modules without a finished loop

Open `docs/beechinese-agent-playbook.md` when the task needs the full planning algorithm, success-criteria examples, or ambiguity-handling guidance.
