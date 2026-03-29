# BeeChinese Feature Map

## Purpose

This file translates the product brief into planning slices. Use it to decide what should be prioritized in an MVP task versus what should be deferred.

## MVP-first principles

- Prefer the narrowest end-to-end learning loop that can be demonstrated.
- Favor working vertical slices over broad but shallow scaffolding.
- Use third-party AI or pronunciation providers when that speeds delivery.
- Preserve clear extension points for later growth, but do not overbuild them now.
- If a task is large, finish one learner-visible or teacher-visible loop before moving to the next loop.

## Recommended milestone ladder

This is the default milestone order when a task does not specify a different priority:

### Milestone 0: Agent and repo control plane

- OpenHands orchestration
- repo guidance and validation
- product context docs

### Milestone 1: Course learning baseline

- learner auth baseline
- course list and course detail
- chapter and video structure
- playback progress
- chapter completion

### Milestone 2: Exercise and grading baseline

- chapter exercises
- submission persistence
- objective scoring
- structured AI grading for subjective items

### Milestone 3: Fixed-sentence speaking baseline

- drill inventory
- sentence-level practice
- pronunciation scoring integration
- error history and review list foundation

### Milestone 4: Situational AI tutor baseline

- scenario catalog
- guided dialogue flow
- tutor session persistence
- structured post-session report

### Milestone 5: Community baseline

- posts
- replies
- tags
- lightweight moderation

### Milestone 6: Expert AI augmentation

- topic-scoped expert AI participation
- user-invoked expert AI
- stronger cultural-pragmatic explanation flows

### Milestone 7: Teacher/admin enrichment

- deeper course operations
- moderation dashboards
- order and user visibility

## Closed-loop product slices

When planning, prefer slices that complete one of these loops:

### Loop A: Learn a chapter

- discover a course
- open a lesson
- watch the video
- resume progress later
- mark progress or completion

### Loop B: Practice and get corrected

- enter a chapter exercise
- submit answers
- receive structured grading
- review mistakes
- retry later

### Loop C: Repeat spoken expressions

- open a drill sentence or pattern
- record or repeat
- receive pronunciation feedback
- store errors or bookmarks
- revisit weak items

### Loop D: Finish a real-life scenario

- choose a scenario
- converse with guided AI tutor
- receive hints or light correction
- finish the scenario
- read structured next-step guidance

### Loop E: Resolve pragmatic confusion

- ask in the community
- receive peer discussion
- optionally invoke expert AI
- preserve the answer as reusable knowledge

## MVP must-have directions

### Learning and course baseline

- Basic learner authentication with email login/register
- Course list and course detail presentation
- Course metadata including title, target audience, goals, and teacher introduction
- Video lesson structure with chapters or lessons
- Basic progress persistence such as playback resume and chapter completion state

### Exercise baseline

- Chapter-level exercise attachment
- At least one objective exercise type and one subjective or AI-reviewed exercise type
- Submission persistence and result history
- Structured grading payloads that downstream surfaces can render

### Speaking and AI baseline

- A first speaking-practice entry point
- Pronunciation scoring via third-party integration or mock interface
- One scenario-based AI tutor flow with guided conversation behavior
- A structured post-session report

### Community baseline

- Post list and post detail
- Replies or comments
- Topic tags
- Initial moderation hooks

### Teacher/admin baseline

- Lightweight teacher/admin login path
- Course create/edit flow
- Chapter management
- Exercise configuration flow

## Important but can follow shortly after MVP

- Bundled course purchases
- Richer learning dashboards
- Public or private note sharing
- More exercise types
- Better error localization in pronunciation analysis
- More scenario libraries for the AI tutor
- Expert AI invocation in selected community topics
- Order visibility and lightweight operational dashboards

## Longer-term expansion

- Larger community knowledge graph around pragmatic and cultural questions
- Stronger personalized recommendations from exercise and speaking history
- More robust digital tutor/avatar presentation
- Gradual replacement of third-party AI and pronunciation providers
- Richer moderation and governance workflows

## Suggested implementation emphasis by stack

### Taro user app

- learner auth
- course browsing and detail
- video learning progress
- drill and tutor entry points
- community reading and posting

### Next.js admin app

- teacher/admin auth
- course management
- chapter and exercise management
- lightweight moderation tools

### NestJS backend

- auth
- courses
- chapters
- progress
- submissions
- community
- orders with lightweight payment interfaces

### FastAPI AI service

- grading adapters
- pronunciation-analysis integration points
- tutor orchestration
- structured report generation
- expert-AI participation logic

## Default dependency order for implementation

If a task spans multiple modules, this is the preferred order:

1. model the core domain object and persistence shape
2. add API or service boundary
3. add learner-facing or teacher-facing UI
4. add docs and operational notes
5. verify the end-to-end slice

If AI output is central to the slice, define the structured contract before wiring the final UI presentation.

## What to avoid in early tasks

- touching every frontend and backend surface in one iteration
- adding speculative abstractions for future multi-tenancy
- designing generic chat systems that ignore teaching behavior
- shipping free-form AI output when structured output is expected
- building admin complexity that is not needed to publish initial content

## Planning heuristics

- If a task is vague, choose one product loop and complete it cleanly rather than touching every module.
- If a task claims to support BeeChinese generally, check whether it helps one of the MVP must-have directions above.
- If a change adds complexity without improving an MVP learning or teaching loop, it is probably not the next best slice.
- If a task says "support AI tutor," default to scenario-guided dialogue plus structured report, not open-ended chatbot behavior.
- If a task says "support expert AI," default to topic-scoped or user-invoked participation, not always-on auto-replies.
