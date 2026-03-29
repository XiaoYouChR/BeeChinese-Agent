# BeeChinese-Agent Control Plane

This repository is the BeeChinese agent control plane, not the BeeChinese product workspace itself.

- Treat the target workspace, defaulting to `~/BeeChinese`, as the place where real product code is studied and edited.
- Keep this repo focused on orchestration, agent definitions, docs lookup, setup, and verification flow.
- Use `.agents/skills/` for the BeeChinese product context and planning heuristics; those skills are intentionally lighter-weight than injecting the full product docs into every prompt.
- Prefer `docs_tool_set` for framework documentation lookup and use browser tools as fallback or for real-page checks.
- Keep implementation close to OpenHands SDK conventions: file-based agents, repo-root `AGENTS.md`, custom tools registered via the tool registry, and verifier-driven repair loops.
- Detailed repository guidance still lives in `.openhands/AGENTS.md`.
