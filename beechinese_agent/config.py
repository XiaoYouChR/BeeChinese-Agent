"""Static configuration for the BeeChinese OpenHands agent layer."""

from pathlib import Path


DEFAULT_VENDOR = "openai"
DEFAULT_MODEL = "gpt-5.3-codex"
DEFAULT_MAX_FIX_ROUNDS = 3
DEFAULT_MAX_GOAL_CYCLES = 5
DEFAULT_SUCCESS_CRITERIA = (
    "The stated user task is implemented to a practically complete state in the current repository, "
    "the verifier passes, and there is no clearly necessary next engineering slice blocking the goal."
)

DEFAULT_EXAMPLE_TASK = (
    "Review the BeeChinese OpenHands agent layer in this repository, "
    "tighten the documentation or validation scripts if anything is inconsistent, "
    "and leave the workspace in a verified state."
)

REQUIRED_AGENT_NAMES = (
    "repo-study",
    "planner",
    "sdk-platform",
    "taro-frontend",
    "admin-nextjs",
    "nestjs-api",
    "fastapi-ai",
    "verifier",
    "docs-writer",
)

IMPLEMENTATION_AGENT_NAMES = (
    "sdk-platform",
    "taro-frontend",
    "admin-nextjs",
    "nestjs-api",
    "fastapi-ai",
    "docs-writer",
)

AGENTS_DIR = Path(".agents/agents")
REPO_GUIDANCE_PATH = Path(".openhands/AGENTS.md")
PRODUCT_BRIEF_PATH = Path("docs/beechinese-product-brief.md")
FEATURE_MAP_PATH = Path("docs/beechinese-feature-map.md")
ACCEPTANCE_GUIDANCE_PATH = Path("docs/beechinese-acceptance.md")
AGENT_PLAYBOOK_PATH = Path("docs/beechinese-agent-playbook.md")
CANONICAL_CONTEXT_PATHS = (
    REPO_GUIDANCE_PATH,
    PRODUCT_BRIEF_PATH,
    FEATURE_MAP_PATH,
    ACCEPTANCE_GUIDANCE_PATH,
    AGENT_PLAYBOOK_PATH,
)

OFFICIAL_DOC_HINT = (
    "When browsing is needed, prefer official docs for OpenHands SDK, Taro, Next.js, "
    "NestJS, FastAPI, React, TypeScript, PostgreSQL, Redis, and MinIO. Avoid third-party blogs "
    "unless the official docs are missing the required detail."
)
