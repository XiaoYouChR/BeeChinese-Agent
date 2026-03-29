# BeeChinese OpenHands Agent Layer

This repository is the autonomous coding layer for BeeChinese. It does not contain the BeeChinese product codebase yet; instead, it provides the OpenHands SDK-based agent framework that will later help us build and evolve the BeeChinese platform across Taro, Next.js, NestJS, and FastAPI services.

## What is included

- A BeeChinese-specific OpenHands orchestration runtime with a verifier-driven repair loop.
- A preferred-docs toolset that queries official framework documentation more efficiently than generic browser navigation.
- File-based specialist agents defined in Markdown + YAML frontmatter under `.agents/agents/`.
- Repo-level OpenHands guidance under `.openhands/`.
- A runnable CLI entry point at `tools/run_beechinese_agent.py`.
- Lightweight setup and validation scripts for a mostly empty repository.

## BeeChinese product direction

The agent layer is tuned for a long-term BeeChinese roadmap where the platform grows into:

- A structured Chinese course and content platform.
- A spoken-Chinese training product with pronunciation feedback.
- A real-time AI tutor / situational conversation system.
- A community and cultural-pragmatics discussion forum.
- A teacher/admin management surface for course and exercise publishing.

The future engineering target assumed by this repo is:

- User app: Taro + React + TypeScript for Web + WeChat Mini Program.
- Admin app: Next.js + React + TypeScript.
- Primary business backend: NestJS.
- AI backend: FastAPI.
- Data and infrastructure: PostgreSQL + Redis + MinIO.
- MVP-first delivery, with third-party AI / pronunciation providers before self-hosted replacements.

## Repository layout

```text
.
├── .agents/
│   └── agents/                  # File-based OpenHands specialist agents
├── .openhands/
│   ├── AGENTS.md                # Repo-level BeeChinese guidance
│   ├── pre-commit.sh            # Lightweight local verification script
│   └── setup.sh                 # Environment bootstrap helper
├── beechinese_agent/
│   ├── config.py                # Static config and agent lists
│   ├── docs_tool.py             # Preferred docs lookup toolset
│   └── orchestrator.py          # Parent orchestration + verifier loop
├── docs/
│   ├── beechinese-agent-playbook.md # Task-splitting and owner guidance for agent runs
│   ├── beechinese-acceptance.md # Cross-cutting product acceptance cues
│   ├── beechinese-feature-map.md # MVP/phase roadmap for product capabilities
│   ├── beechinese-product-brief.md # Canonical BeeChinese product scope
│   └── example-tasks.md         # Suggested prompts for future runs
├── tools/
│   └── run_beechinese_agent.py  # Main CLI entry point
├── main.py                      # Thin compatibility wrapper
└── requirements.txt             # Python dependencies
```

## Agent set

The repo ships with these specialist agents:

- `repo-study`: read-only repository/context analysis.
- `planner`: small execution plan + acceptance criteria.
- `sdk-platform`: OpenHands SDK / Python / repo-bootstrap specialist.
- `taro-frontend`: future user-facing Taro app work.
- `admin-nextjs`: future teacher/admin Next.js work.
- `nestjs-api`: future main business backend work.
- `fastapi-ai`: future AI-service work.
- `verifier`: strict non-implementing validation agent.
- `docs-writer`: README / docs / interface note updates.

## Canonical Product Context

The detailed BeeChinese product context is intentionally centralized instead of duplicated across every agent prompt.

- `docs/beechinese-product-brief.md`: the canonical product brief and module-level expectations.
- `docs/beechinese-feature-map.md`: MVP vs later-phase slicing for planning decisions.
- `docs/beechinese-acceptance.md`: cross-cutting acceptance cues for planning, implementation, and verification.
- `docs/beechinese-agent-playbook.md`: task-splitting heuristics, owner mapping, and common failure modes for agent runs.

`.openhands/AGENTS.md` remains the shorter repository entry point, but when product intent matters these docs should be treated as the default source of truth.

## Workflow

The orchestrator now runs in goal-driven outer cycles. Each cycle follows:

1. `repo-study` inspects the workspace.
2. `planner` emits a small plan with ownership and checks.
3. The parent orchestrator delegates implementation through `TaskToolSet`.
4. `verifier` runs as a strict, non-editing reviewer.
5. If verification fails, the verifier feedback is fed back into the implementation round.
6. If verification passes but the overall goal is still incomplete, the system starts another outer cycle with fresh study and planning.
7. The run stops when the planner marks the goal complete, verification fails irrecoverably, or the configured outer-cycle safety limit is reached.

The final report always includes:

- Modified summary
- Changed file list
- Checks run
- Unresolved risks
- Next-step suggestions

## Quick start

### 1. Install dependencies

If `.venv` already exists, it will be reused.

```bash
bash .openhands/setup.sh
```

### 2. Validate the scaffolding

This does not require LLM login.

```bash
./.venv/bin/python tools/run_beechinese_agent.py validate
```

### 3. Run a task

The runtime uses the OpenHands SDK subscription login flow by default:

```python
LLM.subscription_login(vendor="openai", model="gpt-5.3-codex")
```

Example:

```bash
./.venv/bin/python tools/run_beechinese_agent.py run \
  --task "Review the BeeChinese agent framework and tighten any inconsistent docs or validation scripts." \
  --success-criteria "The repo guidance, validation scripts, and orchestrator behavior are aligned and the verifier passes." \
  --max-goal-cycles 5
```

You can swap vendor/model later with CLI arguments:

```bash
./.venv/bin/python tools/run_beechinese_agent.py run \
  --vendor openai \
  --model gpt-5.3-codex
```

Key continuous-run controls:

- `--success-criteria`: explicit completion bar for the overall goal.
- `--max-goal-cycles`: maximum number of outer `study -> plan -> implement -> verify` cycles.
- `--max-fix-rounds`: maximum repair rounds inside each outer cycle.

If the installed OpenHands SDK rejects a model for subscription access, rerun with a supported value such as `gpt-5.3-codex`, or inspect the CLI error message for the supported model list detected from the installed SDK.

## Browsing policy

Browsing is allowed but intentionally constrained:

- Local repo context first.
- Prefer `docs_tool_set` for documentation lookup.
- Browse only when the repo is insufficient, the docs tool is insufficient, or a real page needs validation.
- Prefer official docs for OpenHands SDK, Taro, Next.js, NestJS, FastAPI, React, TypeScript, PostgreSQL, Redis, and MinIO, but do not hard-ban other sources.
- Avoid third-party blogs unless official docs do not answer the question.

The current implementation exposes both `docs_tool_set` and `BrowserToolSet`. `verifier` keeps browser access intentionally so it can test or inspect real pages when needed.

## Notes on OpenHands SDK usage

This scaffold is intentionally close to current OpenHands SDK patterns:

- File-based agents are loaded with `load_agents_from_dir(...)`.
- They are registered via `register_agent_if_absent(...)`.
- The parent orchestrator uses `TaskToolSet` for delegation.
- Documentation lookup now prefers a custom `docs_tool_set` backed by preferred official docs sources and cached sitemap discovery.
- For docs sites with weak sitemap support, the docs tool can fall back to official source metadata such as the NestJS docs repository tree before using browser fallback.
- Repo guidance, canonical BeeChinese product docs, and the agent playbook are loaded as skills/context for the agent runtime.
- The verifier loop is implemented at the Python orchestration layer for determinism.
- An outer goal loop keeps repeating full cycles until the goal is complete or a safe stop condition is reached.

That means we get both:

- Official SDK-native file-based agent registration.
- A predictable goal loop for `study -> plan -> implement -> verify -> repair -> repeat`.

## Current scope

This repo intentionally stops at the autonomous coding layer. It does **not** yet scaffold the actual BeeChinese apps/services such as:

- `apps/taro-user`
- `apps/admin-web`
- `services/nest-api`
- `services/fastapi-ai`

Those can be introduced in later tasks, using this agent framework as the control plane.
