# BeeChinese Product Brief

## Positioning

BeeChinese is an AI-enabled Chinese-learning SaaS platform aimed primarily at English-speaking international students. It is not just a course marketplace. The intended long-term product is a connected learning system that combines:

- course learning
- speaking practice
- situational dialogue
- cultural and pragmatic understanding

The platform should help learners build a closed loop across content study, guided practice, AI feedback, and ongoing community discussion.

## North-star learning loop

Unless a task says otherwise, product-facing work should strengthen at least one part of this loop:

1. discover or enter a course, drill, or scenario
2. study content or practice an expression
3. receive structured feedback from rules, AI, or both
4. retry, review, or continue into the next learning step
5. ask cultural or pragmatic questions in the community when confusion remains
6. accumulate progress, history, and personalized next steps

If a task is vague, prefer implementing one complete mini-loop over touching every module shallowly.

## Primary users

### Learners

- English-speaking international students who need practical Chinese for study and daily life
- Users who benefit from explicit explanation of Chinese usage, not only raw exposure
- Users who need both structured study and low-friction daily speaking practice

### Teachers or content publishers

- Users who manage courses, chapters, videos, and exercises
- Users who need lightweight tooling rather than enterprise-grade institution management

### Platform operators

- Users who need visibility into content, users, orders, and community moderation

## Default working assumptions for agents

Unless a task explicitly says otherwise:

- The learner-facing product should assume English-first support copy is helpful, with Chinese as the learning target.
- BeeChinese is a single-brand platform, not a multi-tenant SaaS.
- MVP speed matters more than complete platform generality.
- AI features should produce structured, reusable outputs rather than free-form blobs.
- The teacher/admin side should stay lightweight in early versions.
- Third-party AI, pronunciation scoring, and payment integrations are acceptable early if they preserve clean replacement points.

## Product principles

- MVP and demo-readiness matter more than perfection.
- Product slices should still leave room for future expansion into a fuller SaaS platform.
- AI features should be structured and teachable, not generic chat for its own sake.
- When uncertain, prefer the smallest useful learning loop over broad but shallow surface area.
- Avoid overbuilding institution-grade LMS or generic social-network features that do not help Chinese learning.

## Core product modules

### 1. Course and content learning

BeeChinese needs an online course system that can eventually support:

- course list and course detail pages
- price, target audience, learning goals, syllabus, and teacher profile information
- single-course and bundle-style purchase flows
- online video playback
- chapter and lesson organization inside each course
- playback-progress persistence so users can resume where they left off
- chapter completion tracking and learning progress display
- course discussion and learner comments
- personal notes, with support for private notes or notes shared into the discussion area
- lightweight teacher-side course management for descriptions, videos, chapters, and exercises

Key product expectations:

- course detail pages should communicate why the course exists, who it is for, and what learners will achieve
- learning progress should feel continuous rather than stateless
- comments and notes should support learning reflection, not just generic engagement

### 2. Chapter exercises and AI grading

Each chapter can have exercises attached. Exercise support should grow over time but is expected to cover:

- multiple choice
- fill in the blank
- ordering
- sentence creation
- short answer
- voice recording

The system should preserve:

- submission history
- score
- grading result
- historical attempts

Objective items can use rules-based scoring. Subjective items should support AI grading with structured output where practical, including at least:

- score
- issue summary
- revision suggestions
- encouraging feedback

These results should later support study reports and personalized recommendations.

Key product expectations:

- AI grading should feel like teaching feedback, not only judgement
- structured grading data should be easy for the app and reports to render
- historical results should allow learners to see improvement over time

### 3. Fixed-sentence speaking drills

BeeChinese should support fixed-sentence or fixed-pattern oral practice where a learner can repeatedly imitate and rehearse Chinese expressions sentence by sentence.

Expected behaviors:

- sentence-by-sentence replay and repeated practice
- pronunciation analysis and scoring
- correction guidance
- as much localization of pronunciation problems as feasible, such as characters, pinyin, tones, or speech segments
- practice history and error history
- learner-curated review lists for frequently wrong or bookmarked sentences

This area is intended to become a high-frequency retention surface.

Key product expectations:

- the drill unit should be explicit and reusable
- learners should be able to identify what they often mispronounce
- the module should encourage repetition and review, not one-off scoring only

### 4. Real-time AI tutor and situational speaking practice

BeeChinese should support real-time spoken practice with an AI tutor or lightweight digital avatar. The tutor is expected to operate around explicit situations such as:

- hotel check-in
- restaurant ordering
- airport navigation
- campus life
- shopping
- daily social interaction

The AI tutor should not behave like a generic free chat bot. It should:

- proactively guide the conversation
- move the learner toward the scenario goal
- offer hints when the learner gets stuck
- provide short corrections or reformulations at appropriate times

The first version can use a simple 2D digital character rather than a complex 3D avatar.

After a speaking session, the system should be able to produce a structured report containing at least:

- scenario theme
- completion level
- overall speaking assessment across pronunciation, fluency, and expression
- typical problems
- more natural or socially appropriate Chinese alternatives
- recommended next study steps

This is expected to become one of BeeChinese's core differentiators.

Key product expectations:

- dialogue should have a scenario goal, not only unconstrained chatting
- teaching behavior matters as much as speech generation
- the report should feed the next practice step, not end as an isolated summary

### 5. Chinese Corner community / forum

BeeChinese should include a community space where learners can discuss Chinese language, usage, and culture.

Important discussion topics include:

- pragmatic meaning
- cultural subtext
- politeness and indirectness
- what a native speaker really implies in context
- why literal English translations can be misleading

Typical product capabilities:

- post list
- post detail
- replies and comments
- topic tags
- basic moderation and content management

This area should support questions like:

- whether `吃了吗` functions as a greeting
- whether `改天请你吃饭` is a real invitation or polite language
- why `随便` can sound unnatural in some contexts

Key product expectations:

- community should feel learning-oriented rather than like a generic forum
- posts should preserve cultural-pragmatic nuance, not flatten everything into dictionary definitions
- valuable discussions should be reusable as future learning content

### 6. Expert AI for cross-language cultural-pragmatic explanation

BeeChinese plans to combine the community with an expert AI that can explain:

- literal meaning
- real native-speaker usage context
- hidden implications
- politeness strategies
- cultural nuance
- differences from direct English translation
- more natural Chinese alternatives

This expert AI can participate in forum threads, but should not auto-reply everywhere by default. It is most relevant for topics such as:

- hidden cultural meaning
- pragmatic differences
- natural or idiomatic expression
- Chinese phrasing that is easy to misinterpret

The capability can strengthen over time through curated bilingual-pragmatic corpora, high-quality historical answers, and structured prompting.

Key product expectations:

- expert AI participation should be intentionally triggered, topic-scoped, or user-invoked
- responses should explain why an expression works in context, not only what it literally means
- the system should preserve room for future corpus-backed improvements

### 7. Teacher side and admin direction

BeeChinese needs a lightweight teacher/admin surface. The first version should focus on practical content operations rather than heavy institution-grade workflows.

Expected scope:

- teacher or content-manager account support
- course upload and editing
- chapter management
- exercise configuration
- foundational user, order, and moderation visibility over time

Key product expectations:

- the first teacher/admin version should optimize for getting content online quickly
- complex institution collaboration, permissions matrices, and workflow engines are not immediate priorities

## Cross-module product objects

The following concepts are useful defaults when agents need to design models, APIs, or pages:

- `Learner`
- `Teacher`
- `AdminOperator`
- `Course`
- `CourseChapter`
- `LessonVideo`
- `CourseEnrollment`
- `PlaybackProgress`
- `ChapterCompletion`
- `CourseComment`
- `LearningNote`
- `Exercise`
- `ExerciseSubmission`
- `GradingResult`
- `DrillSentence`
- `DrillAttempt`
- `PronunciationIssue`
- `Scenario`
- `TutorSession`
- `TutorTurn`
- `TutorSessionReport`
- `CommunityPost`
- `CommunityReply`
- `TopicTag`
- `ExpertAIResponse`

These names are not strict schema mandates, but they are the right conceptual building blocks for future BeeChinese work.

## Engineering constraints that shape product work

- User app: Taro + React + TypeScript for Web and WeChat Mini Program
- Admin app: Next.js + React + TypeScript
- Main backend: NestJS
- AI backend: FastAPI
- Data: PostgreSQL + Redis + MinIO
- Payment: prioritize WeChat Pay compatibility, but interface placeholders or mock flows are acceptable early
- Login: email registration and login
- Single-brand platform for now, not multi-tenant
- Video authorization can stay simple in early versions
- AI and pronunciation scoring can start with third-party providers before self-hosted replacement
- Teacher backend can stay lightweight in the first release

## Delivery priorities

- Competition and MVP delivery speed come first.
- The repo should optimize for quickly proving the product and business model.
- Even when building MVP slices, designs should not contradict the longer-term shape described here.

## Explicit early non-goals

In early tasks, do not assume BeeChinese needs:

- multi-tenant SaaS abstractions
- institution-grade scheduling or class management
- complex workflow orchestration for teacher collaboration
- highly customized payment clearing systems
- advanced DRM or media pipeline work
- 3D digital human rendering
- fully autonomous expert AI participation across all community posts

## What this repository means today

This repository is currently the OpenHands-based autonomous coding layer for BeeChinese, not the full product codebase itself. The product brief exists so that planning, scaffolding, implementation, and verification can all stay aligned with the real target product instead of drifting into generic language-learning assumptions.
