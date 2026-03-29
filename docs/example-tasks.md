# Example Tasks

These are safe starter tasks for the BeeChinese OpenHands agent layer.

## Repo bootstrap hardening

```text
Review the current BeeChinese OpenHands agent framework, fix any broken validation paths, and align the README plus repo guidance with the implementation.
```

Likely owners:

- `repo-study`
- `planner`
- `sdk-platform`
- `docs-writer`
- `verifier`

## Scaffold the first backend slice

```text
Create a minimal future-facing backend skeleton for BeeChinese with placeholder directories for NestJS and FastAPI, and document how the autonomous agents should work against those services.
```

Likely owners:

- `nestjs-api`
- `fastapi-ai`
- `docs-writer`
- `verifier`

## Build the first course-learning slice

```text
Create the first BeeChinese course-learning MVP slice: define a course domain shape, course detail metadata, chapter or lesson structure, and a simple progress model for video resume or chapter completion. Keep the work honest about placeholders and align learner-facing docs with the implementation.
```

Likely owners:

- `planner`
- `nestjs-api`
- `taro-frontend`
- `docs-writer`
- `verifier`

## Build the first exercise plus grading slice

```text
Implement a minimal BeeChinese exercise and grading slice with at least one objective exercise type and one structured AI-grading contract for subjective feedback. Preserve submission history and keep the grading output reusable by future UI.
```

Likely owners:

- `planner`
- `nestjs-api`
- `fastapi-ai`
- `docs-writer`
- `verifier`

## Build the first situational tutor slice

```text
Create a BeeChinese scenario-based AI tutor MVP slice for one situation such as restaurant ordering or hotel check-in. The tutor must guide the learner toward a scenario goal and end with a structured session report rather than only a raw transcript.
```

Likely owners:

- `planner`
- `fastapi-ai`
- `taro-frontend`
- `docs-writer`
- `verifier`

## Scaffold the first frontend slice

```text
Create MVP-friendly placeholder directories and README notes for the Taro learner app and the Next.js admin app, while keeping the repo conventions consistent with BeeChinese architecture.
```

Likely owners:

- `taro-frontend`
- `admin-nextjs`
- `docs-writer`
- `verifier`
