# BeeChinese Acceptance Guide

## Purpose

Use this file during planning, implementation, and verification when you need a concrete bar for whether a BeeChinese slice is coherent enough.

## Cross-cutting acceptance rules

- The change should help a real BeeChinese learner, teacher, or operator workflow, not just add generic framework code.
- The change should align with the canonical BeeChinese product brief, feature map, and agent playbook.
- MVP-friendly simplification is acceptable, but it should be called out explicitly if important behavior is mocked, deferred, or placeholder-based.
- User-visible and developer-facing docs should not contradict the actual implemented behavior.
- Structured outputs are preferred for AI-facing features so that downstream surfaces can render or reason over them.
- When a task claims to support a BeeChinese module, the implementation should reflect the module's teaching intent, not merely its surface label.

## Course and learning acceptance cues

A course-learning slice is in a reasonable state when applicable work supports several of these expectations:

- course metadata is meaningful, not only title and empty placeholders
- chapter or lesson structure is explicit
- learner progress can be persisted or clearly represented
- playback-resume or completion semantics are documented or implemented when relevant
- comments or notes behavior is clearly scoped if present
- teacher-managed content editing is not contradicted by the chosen data model or UI language

## Exercise and grading acceptance cues

An exercise slice is in a reasonable state when:

- exercise types are explicitly defined
- submission and result records are retained or modeled
- objective scoring logic is deterministic when used
- AI grading output is structured enough to expose score, issues, and suggestions
- deferred capabilities are identified rather than implied to exist

### Minimum structured grading contract

Unless a task explicitly narrows scope, BeeChinese grading output should include fields equivalent to:

- `score`
- `issue_summary`
- `revision_suggestions`
- `encouraging_feedback`

Helpful optional fields include:

- `rubric_basis`
- `confidence`
- `recommended_next_step`

## Speaking drill acceptance cues

A speaking-drill slice is in a reasonable state when:

- the practice unit is clear, such as sentence or pattern based
- scoring or correction behavior is explicit
- learner history or review-list implications are considered when relevant
- pronunciation feedback is not described more strongly than the current implementation actually supports
- error localization is represented when feasible, such as character, pinyin, tone, or speech segment level

## AI tutor acceptance cues

A situational AI tutor slice is in a reasonable state when:

- the scenario goal is explicit
- the tutor behaves like a guide, not only an open-ended chatbot
- hints, redirection, or concise correction strategies are represented when relevant
- the session can end in a structured report or a clearly defined placeholder for one

### Minimum structured tutor-report contract

Unless the task explicitly narrows scope, a tutor session report should include fields equivalent to:

- `scenario_theme`
- `completion_level`
- `speaking_summary` or equivalent pronunciation / fluency / expression assessment
- `typical_problems`
- `more_natural_expression_suggestions`
- `recommended_next_steps`

Helpful optional fields include:

- `scenario_goal`
- `turn_count`
- `vocabulary_to_review`
- `confidence`

## Community and expert-AI acceptance cues

A community-related slice is in a reasonable state when:

- discussion objects, replies, and tags are modeled coherently
- the cultural-pragmatic focus is reflected where appropriate
- expert AI participation is scoped intentionally rather than assumed to auto-reply everywhere
- moderation responsibilities are not ignored when user-generated content is introduced

An expert-AI slice is stronger when it makes one of these choices explicit:

- auto-participate only on selected topic categories
- respond only when users invoke or summon expert AI
- document the trigger policy clearly if the final behavior is still placeholder-based

## Teacher/admin acceptance cues

A teacher/admin slice is in a reasonable state when:

- content-management flows are practical for an MVP
- course, chapter, and exercise editing responsibilities are explicit
- the implementation does not pretend to support complex institutional workflows that are out of scope
- admin or teacher functionality maps clearly to content operations, moderation, users, or orders

## Product-specific fail conditions

Verifier findings should usually FAIL when any of these happen:

- an "AI tutor" implementation is only a generic chat surface with no scenario goal or teaching behavior
- an "AI grading" implementation returns unstructured prose with no reusable grading fields
- expert AI is described as universally auto-replying even though BeeChinese expects selective participation
- teacher/admin work implies institution-grade collaboration that BeeChinese does not yet target
- docs claim learner history, playback progress, or structured reports exist when the implementation clearly does not support them
- a task marketed as an MVP slice introduces abstractions or infra complexity that slow delivery without improving a real learning loop

## Verification heuristics

Verifier findings should be stricter when:

- README or repo guidance implies support for product behavior that the code clearly does not implement
- product slices contradict the canonical product brief
- structured AI outputs are missing where the product direction depends on them
- tasks ignore MVP boundaries and add speculative complexity
- the implementation weakens one of BeeChinese's core differentiators into a generic SaaS feature

Verifier findings can be lighter when:

- the repository is still scaffolding-only and the task only claims to establish groundwork
- placeholders are explicit, well-documented, and aligned with future replacement points
- a task intentionally defines interfaces, schemas, or docs before full execution logic exists

## Planner-oriented acceptance hints

When planning future work, treat these as useful "done enough for now" bars:

- one visible learning loop works end-to-end
- one AI feature exposes a structured contract that later UI can safely consume
- teacher/admin work is sufficient to publish or maintain the corresponding learner experience
- community or expert-AI work preserves cultural-pragmatic focus rather than generic discussion mechanics only
