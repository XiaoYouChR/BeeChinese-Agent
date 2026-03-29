"""Orchestration runtime for the BeeChinese OpenHands agent layer."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
warnings.simplefilter("ignore", DeprecationWarning)
warnings.filterwarnings(
    "ignore",
    message=".*There is no current event loop.*",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"litellm\.llms\.custom_httpx\.async_client_cleanup",
)

from openhands.sdk import (
    Agent,
    AgentContext,
    Conversation,
    LLM,
    Tool,
    agent_definition_to_factory,
    load_agents_from_dir,
    load_project_skills,
)
from openhands.sdk.context import Skill
from openhands.sdk.context.condenser import LLMSummarizingCondenser
from openhands.sdk.context.skills import load_skills_from_dir
from openhands.sdk.conversation import get_agent_final_response
from openhands.sdk.subagent import AgentDefinition, register_agent_if_absent
from openhands.tools.apply_patch import ApplyPatchTool
from openhands.tools.browser_use import BrowserToolSet
from openhands.tools.task import TaskToolSet
from openhands.tools.task.manager import TaskManager
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool

from beechinese_agent.config import (
    AGENTS_DIR,
    CANONICAL_CONTEXT_PATHS,
    CONTROL_SKILLS_DIR,
    DEFAULT_EXAMPLE_TASK,
    DEFAULT_MAX_FIX_ROUNDS,
    DEFAULT_MAX_GOAL_CYCLES,
    DEFAULT_MODEL,
    DEFAULT_SUCCESS_CRITERIA,
    DEFAULT_VENDOR,
    DEFAULT_WORKSPACE,
    FRAMEWORK_ROOT,
    IMPLEMENTATION_AGENT_NAMES,
    OFFICIAL_DOC_HINT,
    REPO_GUIDANCE_PATH,
    ROOT_AGENTS_PATH,
    REQUIRED_AGENT_NAMES,
)
from beechinese_agent.docs_tool import DocsToolSet


LOGGER = logging.getLogger("beechinese_agent")
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_LEVEL_HELP = (
    "Logging level for BeeChinese runtime logs, such as DEBUG, INFO, WARNING, or ERROR."
)


ORCHESTRATOR_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are the BeeChinese orchestration parent agent for this repository.

    Your job is to coordinate work instead of editing files directly.
    Use this workflow by default:
    1. Understand the task and reuse repo context first.
    2. Delegate implementation to the smallest suitable specialist agent via task_tool_set.
    3. Prefer docs_tool_set for documentation lookup and use browser_tool_set as fallback or for real page validation.
    4. Keep work scoped, concrete, and aligned with the current plan.
    5. Let the external verifier phase decide PASS / FAIL. If verifier feedback is provided, coordinate targeted repairs only.

    Constraints:
    - Do not make direct code edits yourself in this role.
    - Delegate coding to specialist agents named in the plan.
    - Do not ask the verifier agent to implement fixes.
    - Treat the canonical BeeChinese product docs in docs/ as the source of truth for product scope, priorities, and acceptance expectations.
    - Prefer official documentation domains first, but do not treat them as a hard ban on all other sources.
    - Keep summaries concise and actionable.
    """
).strip()


class OrchestratorError(RuntimeError):
    """Raised when the BeeChinese orchestrator cannot continue safely."""


def _llm_requires_streaming(llm: LLM) -> bool:
    """Return True when the current LLM transport must keep stream enabled."""
    base_url = str(getattr(llm, "base_url", "") or "")
    return bool(getattr(llm, "stream", False)) and (
        bool(getattr(llm, "_is_subscription", False))
        or "chatgpt.com/backend-api/codex" in base_url
    )


def patch_task_manager_stream_handling() -> None:
    """Patch OpenHands TaskManager to preserve stream=True for subscription LLMs.

    OpenHands SDK v1.15.0 hardcodes `stream=False` for delegated sub-agents in
    TaskToolSet. That breaks the OpenAI subscription/Codex transport, which
    requires streaming requests. We keep the SDK default for normal models and
    only override the behavior when the parent LLM clearly requires streaming.
    """
    if getattr(TaskManager, "_beechinese_stream_patch_applied", False):
        return

    original_method = TaskManager._get_sub_agent_from_factory

    def _patched_get_sub_agent_from_factory(
        self: TaskManager,
        factory: Any,
    ) -> Agent:
        parent_llm = self.parent_conversation.agent.llm
        if not _llm_requires_streaming(parent_llm):
            return original_method(self, factory)

        LOGGER.debug(
            "Preserving stream=True for TaskToolSet sub-agent llm model=%s",
            getattr(parent_llm, "model", "unknown"),
        )
        sub_agent_llm = parent_llm.model_copy(update={"stream": True})
        sub_agent_llm.reset_metrics()

        sub_agent = factory.factory_func(sub_agent_llm)
        return sub_agent.model_copy(
            update={"llm": sub_agent.llm.model_copy(update={"stream": True})}
        )

    TaskManager._get_sub_agent_from_factory = _patched_get_sub_agent_from_factory
    TaskManager._beechinese_stream_patch_applied = True


def configure_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=level, format=LOG_FORMAT, datefmt="%H:%M:%S")
    else:
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)
    LOGGER.setLevel(level)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        result.append(cleaned)
        seen.add(cleaned)
    return result


def _extract_json_object(text: str) -> dict[str, Any]:
    candidates: list[str] = []
    fenced = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidates.extend(fenced)
    fenced_generic = re.findall(r"```\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidates.extend(fenced_generic)
    candidates.append(text.strip())

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue

    raise ValueError("No JSON object found in agent response.")


def _git_changed_paths(workspace: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return set()

    changed: set[str] = set()
    for line in result.stdout.splitlines():
        if not line:
            continue
        payload = line[3:].strip()
        if " -> " in payload:
            payload = payload.split(" -> ", maxsplit=1)[1]
        changed.add(payload)
    return changed


def _build_condenser(llm: LLM, usage_id: str) -> LLMSummarizingCondenser:
    return LLMSummarizingCondenser(
        llm=llm.model_copy(update={"usage_id": usage_id}),
        max_size=80,
        keep_first=4,
    )


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _append_unique_skills(skills: list[Skill], additions: list[Skill]) -> list[Skill]:
    seen = {skill.name for skill in skills}
    for skill in additions:
        if skill.name in seen:
            continue
        skills.append(skill)
        seen.add(skill.name)
    return skills


def _load_control_plane_skills(control_root: Path) -> list[Skill]:
    """Load the control-repo guidance using official OpenHands skill conventions.

    Keep always-on guidance small via a root-level AGENTS.md, and expose larger
    BeeChinese product/context references through file-based AgentSkills under
    .agents/skills for progressive disclosure.
    """
    skills: list[Skill] = []

    root_agents = control_root / ROOT_AGENTS_PATH
    if root_agents.exists():
        skills.append(Skill.load(root_agents))

    skill_dir = control_root / CONTROL_SKILLS_DIR
    if skill_dir.exists():
        repo_skills, knowledge_skills, agent_skills = load_skills_from_dir(skill_dir)
        _append_unique_skills(
            skills,
            list(repo_skills.values())
            + list(knowledge_skills.values())
            + list(agent_skills.values()),
        )

    return skills


def load_repo_skills(*, control_root: Path, workspace: Path) -> list[Skill]:
    """Load runtime skills for the target workspace plus BeeChinese control-plane skills."""
    skills = load_project_skills(workspace)
    if control_root.resolve() != workspace.resolve():
        _append_unique_skills(skills, _load_control_plane_skills(control_root))
    return skills


@dataclass(slots=True)
class PlanStep:
    """A single planner step."""

    id: str
    owner: str
    title: str
    deliverable: str
    acceptance_criteria: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], index: int) -> "PlanStep":
        owner = str(data.get("owner", "sdk-platform")).strip()
        if owner not in REQUIRED_AGENT_NAMES:
            owner = "sdk-platform"
        return cls(
            id=str(data.get("id", f"step-{index}")).strip(),
            owner=owner,
            title=str(data.get("title", f"Step {index}")).strip(),
            deliverable=str(data.get("deliverable", "")).strip(),
            acceptance_criteria=[
                str(item).strip()
                for item in data.get("acceptance_criteria", [])
                if str(item).strip()
            ],
            dependencies=[
                str(item).strip()
                for item in data.get("dependencies", [])
                if str(item).strip()
            ],
        )


@dataclass(slots=True)
class PlanArtifact:
    """Planner output normalized into Python objects."""

    goal: str
    summary: str
    goal_complete: bool
    completion_confidence: float
    goal_completion_reason: str
    remaining_work: list[str]
    steps: list[PlanStep]
    checks: list[str]
    risks: list[str]
    notes_for_orchestrator: list[str]
    raw_response: str

    @classmethod
    def from_response(cls, response: str, user_task: str) -> "PlanArtifact":
        try:
            payload = _extract_json_object(response)
            goal_complete = _coerce_bool(payload.get("goal_complete", False))
            steps = [
                PlanStep.from_dict(step, index)
                for index, step in enumerate(payload.get("steps", []), start=1)
            ]
            if not steps and not goal_complete:
                raise ValueError("Planner returned zero steps.")
            return cls(
                goal=str(payload.get("goal", user_task)).strip() or user_task,
                summary=str(payload.get("summary", "")).strip(),
                goal_complete=goal_complete,
                completion_confidence=_coerce_float(
                    payload.get("completion_confidence", 0.0)
                ),
                goal_completion_reason=str(
                    payload.get("goal_completion_reason", "")
                ).strip(),
                remaining_work=_dedupe(
                    [str(item) for item in payload.get("remaining_work", [])]
                ),
                steps=steps,
                checks=_dedupe([str(item) for item in payload.get("checks", [])]),
                risks=_dedupe([str(item) for item in payload.get("risks", [])]),
                notes_for_orchestrator=_dedupe(
                    [str(item) for item in payload.get("notes_for_orchestrator", [])]
                ),
                raw_response=response,
            )
        except Exception:
            fallback_steps = [
                PlanStep(
                    id="step-1",
                    owner="sdk-platform",
                    title="Stabilize the OpenHands / Python infrastructure layer",
                    deliverable="Repair or implement the BeeChinese agent framework files.",
                    acceptance_criteria=[
                        "The Python runner can validate the workspace.",
                        "Core orchestration code is internally consistent.",
                    ],
                ),
                PlanStep(
                    id="step-2",
                    owner="docs-writer",
                    title="Align developer-facing documentation",
                    deliverable="README and repo guidance match the implemented framework.",
                    acceptance_criteria=[
                        "README explains setup, validate, and run flow.",
                        "Repo guidance reflects BeeChinese architecture targets.",
                    ],
                    dependencies=["step-1"],
                ),
            ]
            return cls(
                goal=user_task,
                summary="Fallback plan generated because the planner response was not parseable JSON.",
                goal_complete=False,
                completion_confidence=0.0,
                goal_completion_reason="Planner output could not be parsed, so the goal cannot be considered complete yet.",
                remaining_work=["Review and execute the fallback implementation plan."],
                steps=fallback_steps,
                checks=["python tools/run_beechinese_agent.py validate"],
                risks=[
                    "Planner output was unstructured; review the generated plan manually if task scope is high risk."
                ],
                notes_for_orchestrator=[
                    "Prefer sdk-platform for Python/OpenHands repo bootstrap tasks.",
                    "Use docs-writer for README, docs, and repo-handbook alignment.",
                ],
                raw_response=response,
            )


@dataclass(slots=True)
class VerifierIssue:
    """A single verifier finding."""

    severity: str
    title: str
    details: str
    repair_suggestion: str
    files: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerifierIssue":
        return cls(
            severity=str(data.get("severity", "medium")).strip(),
            title=str(data.get("title", "Verifier issue")).strip(),
            details=str(data.get("details", "")).strip(),
            repair_suggestion=str(data.get("repair_suggestion", "")).strip(),
            files=[str(item).strip() for item in data.get("files", []) if str(item).strip()],
        )


@dataclass(slots=True)
class VerifierArtifact:
    """Verifier output normalized into Python objects."""

    status: str
    severity: str
    summary: str
    confidence: float
    checks_run: list[str]
    issues: list[VerifierIssue]
    unresolved_risks: list[str]
    raw_response: str

    @property
    def passed(self) -> bool:
        return self.status.upper() == "PASS"

    @classmethod
    def from_response(cls, response: str) -> "VerifierArtifact":
        try:
            payload = _extract_json_object(response)
            confidence_raw = payload.get("confidence", 0.0)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.0
            return cls(
                status=str(payload.get("status", "FAIL")).strip().upper(),
                severity=str(payload.get("severity", "medium")).strip().lower(),
                summary=str(payload.get("summary", "")).strip(),
                confidence=confidence,
                checks_run=_dedupe([str(item) for item in payload.get("checks_run", [])]),
                issues=[
                    VerifierIssue.from_dict(issue)
                    for issue in payload.get("issues", [])
                    if isinstance(issue, dict)
                ],
                unresolved_risks=_dedupe(
                    [str(item) for item in payload.get("unresolved_risks", [])]
                ),
                raw_response=response,
            )
        except Exception:
            return cls(
                status="FAIL",
                severity="high",
                summary="Verifier output was not parseable JSON.",
                confidence=0.0,
                checks_run=[],
                issues=[
                    VerifierIssue(
                        severity="high",
                        title="Verifier protocol violation",
                        details="The verifier did not return the required JSON payload.",
                        repair_suggestion="Re-run verification and ensure the verifier follows the expected output schema.",
                    )
                ],
                unresolved_risks=["Verification protocol broke, so repo quality is uncertain."],
                raw_response=response,
            )


@dataclass(slots=True)
class CycleArtifact:
    """One outer goal cycle containing planning, implementation, and verification."""

    cycle_number: int
    repo_summary: str
    plan: PlanArtifact
    execution_summaries: list[str]
    verifier_results: list[VerifierArtifact]

    @property
    def final_verifier(self) -> VerifierArtifact | None:
        if not self.verifier_results:
            return None
        return self.verifier_results[-1]

    def render_summary(self) -> str:
        parts = [f"Cycle {self.cycle_number}: {self.plan.summary}"]
        if self.plan.goal_completion_reason:
            parts.append(f"Goal signal: {self.plan.goal_completion_reason}")
        parts.extend(self.execution_summaries)
        if self.final_verifier is not None:
            parts.append(
                f"Verifier result: {self.final_verifier.status} - {self.final_verifier.summary}"
            )
        return "\n".join(part.strip() for part in parts if part.strip())


@dataclass(slots=True)
class RunReport:
    """Human-facing summary emitted after each orchestrator run."""

    task: str
    success_criteria: str
    status: str
    cycles_run: int
    goal_complete: bool
    goal_reason: str
    modified_summary: str
    changed_files: list[str]
    checks_run: list[str]
    unresolved_risks: list[str]
    next_steps: list[str]

    def render(self) -> str:
        lines = [
            "BeeChinese OpenHands Orchestrator Report",
            f"Status: {self.status}",
            f"Cycles run: {self.cycles_run}",
            f"Goal complete: {'yes' if self.goal_complete else 'no'}",
            "",
            "Success criteria:",
            self.success_criteria,
            "",
            "Goal status reason:",
            self.goal_reason or "- No explicit goal-reason was captured.",
            "",
            "Modified summary:",
            self.modified_summary or "- No implementation summary was captured.",
            "",
            "Changed files:",
        ]
        if self.changed_files:
            lines.extend(f"- {path}" for path in self.changed_files)
        else:
            lines.append("- No new file deltas were detected against the starting git status snapshot.")

        lines.extend(["", "Checks run:"])
        if self.checks_run:
            lines.extend(f"- {check}" for check in self.checks_run)
        else:
            lines.append("- No checks were recorded.")

        lines.extend(["", "Unresolved risks:"])
        if self.unresolved_risks:
            lines.extend(f"- {risk}" for risk in self.unresolved_risks)
        else:
            lines.append("- None reported.")

        lines.extend(["", "Next step suggestions:"])
        if self.next_steps:
            lines.extend(f"- {step}" for step in self.next_steps)
        else:
            lines.append("- No explicit next steps were generated.")
        return "\n".join(lines)


class FileAgentRegistry:
    """Loads, validates, and registers file-based agent definitions."""

    def __init__(self, *, control_root: Path, workspace: Path):
        self.control_root = control_root
        self.workspace = workspace
        self.agents_dir = control_root / AGENTS_DIR
        self.definitions = {
            definition.name: definition
            for definition in load_agents_from_dir(self.agents_dir)
        }

    def validate_required_agents(self) -> None:
        missing = [name for name in REQUIRED_AGENT_NAMES if name not in self.definitions]
        if missing:
            raise OrchestratorError(
                "Missing required file-based agents: " + ", ".join(sorted(missing))
            )

    def register_all(self) -> list[str]:
        self.validate_required_agents()
        registered: list[str] = []
        for definition in self.definitions.values():
            factory = agent_definition_to_factory(definition, work_dir=self.workspace)
            was_registered = register_agent_if_absent(
                name=definition.name,
                factory_func=factory,
                description=definition,
            )
            if was_registered:
                registered.append(definition.name)
        return sorted(registered)

    def definition_for(self, name: str) -> AgentDefinition:
        try:
            return self.definitions[name]
        except KeyError as exc:
            raise OrchestratorError(f"Unknown agent name: {name}") from exc

    def build_agent(self, name: str, llm: LLM) -> Agent:
        definition = self.definition_for(name)
        factory = agent_definition_to_factory(definition, work_dir=self.workspace)
        return factory(llm)


class BeeChineseOrchestrator:
    """Coordinates repo study, planning, implementation, verification, and repair."""

    def __init__(
        self,
        *,
        workspace: Path,
        control_root: Path = FRAMEWORK_ROOT,
        llm: LLM,
        max_fix_rounds: int = DEFAULT_MAX_FIX_ROUNDS,
        max_goal_cycles: int = DEFAULT_MAX_GOAL_CYCLES,
        enable_browser: bool = True,
    ) -> None:
        self.workspace = workspace
        self.control_root = control_root
        self.llm = llm
        self.max_fix_rounds = max_fix_rounds
        self.max_goal_cycles = max_goal_cycles
        self.enable_browser = enable_browser
        patch_task_manager_stream_handling()
        self.registry = FileAgentRegistry(control_root=control_root, workspace=workspace)
        self.registered_agents = self.registry.register_all()
        self.repo_skills = load_repo_skills(control_root=self.control_root, workspace=self.workspace)
        LOGGER.info(
            "Initialized BeeChineseOrchestrator control_root=%s workspace=%s model=%s browser=%s max_goal_cycles=%s max_fix_rounds=%s registered_agents=%s repo_skills=%s",
            self.control_root,
            self.workspace,
            getattr(self.llm, "model", "unknown"),
            self.enable_browser,
            self.max_goal_cycles,
            self.max_fix_rounds,
            ", ".join(self.registered_agents),
            len(self.repo_skills),
        )

    def _phase_llm(self, usage_id: str) -> LLM:
        return self.llm.model_copy(update={"usage_id": usage_id})

    def _run_named_agent(self, name: str, prompt: str) -> str:
        definition = self.registry.definition_for(name)
        agent = self.registry.build_agent(name, self._phase_llm(name))
        LOGGER.info(
            "Starting agent=%s max_iterations=%s",
            name,
            definition.max_iteration_per_run or 120,
        )
        started_at = time.monotonic()
        conversation = Conversation(
            agent=agent,
            workspace=self.workspace,
            visualizer=None,
            hook_config=definition.hooks,
            max_iteration_per_run=definition.max_iteration_per_run or 120,
            delete_on_close=True,
        )
        try:
            conversation.send_message(prompt)
            conversation.run()
            response = get_agent_final_response(conversation.state.events).strip()
            if not response:
                raise OrchestratorError(f"Agent '{name}' returned an empty response.")
            LOGGER.info(
                "Completed agent=%s duration=%.2fs response_chars=%s",
                name,
                time.monotonic() - started_at,
                len(response),
            )
            return response
        finally:
            conversation.close()

    def _render_cycle_history(self, cycles: list[CycleArtifact]) -> str:
        if not cycles:
            return "No completed goal cycles yet."

        history_payload: list[dict[str, Any]] = []
        for cycle in cycles:
            final_verifier = cycle.final_verifier
            history_payload.append(
                {
                    "cycle_number": cycle.cycle_number,
                    "plan_summary": cycle.plan.summary,
                    "goal_complete": cycle.plan.goal_complete,
                    "goal_completion_reason": cycle.plan.goal_completion_reason,
                    "remaining_work": cycle.plan.remaining_work,
                    "verifier_status": final_verifier.status if final_verifier else "NOT_RUN",
                    "verifier_summary": final_verifier.summary if final_verifier else "",
                    "issues": [
                        issue.title for issue in (final_verifier.issues if final_verifier else [])
                    ],
                }
            )
        return json.dumps(history_payload, ensure_ascii=False, indent=2)

    def _build_orchestrator_agent(self, usage_id: str) -> Agent:
        tools = [
            Tool(name=TaskToolSet.name),
            Tool(name=TaskTrackerTool.name),
            Tool(name=DocsToolSet.name),
        ]
        if self.enable_browser:
            tools.append(Tool(name=BrowserToolSet.name))

        agent_context = AgentContext(
            skills=self.repo_skills,
            system_message_suffix=ORCHESTRATOR_SYSTEM_PROMPT,
        )
        return Agent(
            llm=self._phase_llm(usage_id),
            tools=tools,
            agent_context=agent_context,
            condenser=_build_condenser(self.llm, f"{usage_id}-condenser"),
        )

    def _run_orchestrator_execution(
        self,
        *,
        goal: str,
        success_criteria: str,
        cycle_number: int,
        repo_summary: str,
        plan: PlanArtifact,
        verifier_feedback: VerifierArtifact | None,
        round_number: int,
    ) -> str:
        applicable_steps = [
            {
                "id": step.id,
                "owner": step.owner,
                "title": step.title,
                "deliverable": step.deliverable,
                "acceptance_criteria": step.acceptance_criteria,
                "dependencies": step.dependencies,
            }
            for step in plan.steps
            if step.owner in IMPLEMENTATION_AGENT_NAMES
        ]

        verifier_json = None
        if verifier_feedback is not None:
            verifier_json = {
                "status": verifier_feedback.status,
                "severity": verifier_feedback.severity,
                "summary": verifier_feedback.summary,
                "confidence": verifier_feedback.confidence,
                "issues": [
                    {
                        "severity": issue.severity,
                        "title": issue.title,
                        "details": issue.details,
                        "repair_suggestion": issue.repair_suggestion,
                        "files": issue.files,
                    }
                    for issue in verifier_feedback.issues
                ],
                "unresolved_risks": verifier_feedback.unresolved_risks,
            }

        prompt = textwrap.dedent(
            f"""
            Execute BeeChinese goal cycle {cycle_number}, implementation round {round_number + 1}.

            Overall goal:
            {goal}

            Success criteria:
            {success_criteria}

            Repo summary:
            {repo_summary}

            Plan summary:
            {plan.summary}

            Goal completion hint from planner:
            {plan.goal_completion_reason or "The planner still considers the goal incomplete."}

            Implementation steps JSON:
            {json.dumps(applicable_steps, ensure_ascii=False, indent=2)}

            Notes for the orchestrator:
            {json.dumps(plan.notes_for_orchestrator, ensure_ascii=False, indent=2)}

            Repair feedback:
            {json.dumps(verifier_json, ensure_ascii=False, indent=2) if verifier_json else "No verifier feedback yet. This is the first implementation pass."}

            Execution rules:
            - Use task_tool_set to delegate each implementation step to the named owner agent.
            - Delegate code / doc changes to specialists instead of editing directly.
            - Do not ask the verifier agent to implement fixes.
            - Prefer docs_tool_set for documentation lookup.
            - Only browse when docs_tool_set and local repo context are insufficient, or when a real web page needs validation.
            - {OFFICIAL_DOC_HINT}
            - When verifier feedback exists, repair the listed issues first and avoid unrelated refactors.
            - Finish with a concise summary covering completed work, any specialist-run checks, remaining unknowns, and what is still left for the overall goal if anything.
            """
        ).strip()

        agent = self._build_orchestrator_agent(
            f"goal-cycle-{cycle_number}-round-{round_number + 1}"
        )
        LOGGER.info(
            "Starting implementation cycle=%s round=%s step_count=%s repair=%s",
            cycle_number,
            round_number + 1,
            len(applicable_steps),
            verifier_feedback is not None,
        )
        started_at = time.monotonic()
        conversation = Conversation(
            agent=agent,
            workspace=self.workspace,
            visualizer=None,
            max_iteration_per_run=200,
            delete_on_close=True,
        )
        try:
            conversation.send_message(prompt)
            conversation.run()
            response = get_agent_final_response(conversation.state.events).strip()
            if not response:
                raise OrchestratorError("Orchestrator execution returned an empty response.")
            LOGGER.info(
                "Completed implementation cycle=%s round=%s duration=%.2fs response_chars=%s",
                cycle_number,
                round_number + 1,
                time.monotonic() - started_at,
                len(response),
            )
            return response
        finally:
            conversation.close()

    def _build_repo_study_prompt(
        self,
        *,
        goal: str,
        success_criteria: str,
        cycle_number: int,
        cycle_history: str,
    ) -> str:
        return textwrap.dedent(
            f"""
            Study the current repository before BeeChinese goal cycle {cycle_number} begins.

            Overall goal:
            {goal}

            Success criteria:
            {success_criteria}

            Prior cycle history:
            {cycle_history}

            Produce a concise report with these sections:
            1. Current repo structure and what already exists
            2. What remains between the current repo state and the stated goal
            3. Risks or constraints that the planner should respect this cycle
            4. Suggested owners among: {", ".join(REQUIRED_AGENT_NAMES)}

            Rules:
            - Read local files first.
            - Treat the canonical BeeChinese product docs in docs/ as the default source of truth for product-facing scope and priorities.
            - Do not modify files.
            - Mention if the repo is mostly blank or scaffold-only.
            - Account for prior cycle progress and do not ignore already completed work.
            """
        ).strip()

    def _build_planner_prompt(
        self,
        *,
        goal: str,
        success_criteria: str,
        cycle_number: int,
        repo_summary: str,
        cycle_history: str,
    ) -> str:
        return textwrap.dedent(
            f"""
            Create the plan for BeeChinese goal cycle {cycle_number}.

            Overall goal:
            {goal}

            Success criteria:
            {success_criteria}

            Repo summary:
            {repo_summary}

            Prior cycle history:
            {cycle_history}

            Allowed owners:
            {", ".join(REQUIRED_AGENT_NAMES)}

            Return exactly one JSON object in a fenced ```json block with this schema:
            {{
              "goal": "string",
              "summary": "string",
              "goal_complete": false,
              "completion_confidence": 0.0,
              "goal_completion_reason": "string",
              "remaining_work": ["string"],
              "steps": [
                {{
                  "id": "step-1",
                  "owner": "sdk-platform",
                  "title": "string",
                  "deliverable": "string",
                  "acceptance_criteria": ["string"],
                  "dependencies": ["step-x"]
                }}
              ],
              "checks": ["string"],
              "risks": ["string"],
              "notes_for_orchestrator": ["string"]
            }}

            Planning rules:
            - This planner runs every outer goal cycle, not just once.
            - If the overall goal is already satisfied, set "goal_complete" to true, explain why, and return an empty "steps" list.
            - Otherwise set "goal_complete" to false and plan only the next smallest meaningful slice.
            - Keep steps small, concrete, and execution-ready.
            - Prefer sdk-platform for Python/OpenHands/bootstrap work.
            - Use docs-writer for README, docs, and repo guidance alignment.
            - Do not assign verifier as an implementation owner.
            - Include the most useful validation commands in "checks".
            - Reflect the long-term BeeChinese stack: Taro + Next.js + NestJS + FastAPI + PostgreSQL + Redis + MinIO.
            - Keep the plan aligned with the canonical BeeChinese product docs in docs/ instead of inventing a conflicting product direction.
            """
        ).strip()

    def _build_verifier_prompt(
        self,
        *,
        goal: str,
        success_criteria: str,
        cycle_number: int,
        repo_summary: str,
        plan: PlanArtifact,
        execution_summaries: list[str],
    ) -> str:
        return textwrap.dedent(
            f"""
            Verify the current workspace strictly for BeeChinese goal cycle {cycle_number}. You must not edit files.

            Overall goal:
            {goal}

            Success criteria:
            {success_criteria}

            Repo summary:
            {repo_summary}

            Planned checks:
            {json.dumps(plan.checks, ensure_ascii=False, indent=2)}

            Execution summaries:
            {json.dumps(execution_summaries, ensure_ascii=False, indent=2)}

            Use terminal commands as needed and review the resulting workspace state.

            Return exactly one JSON object in a fenced ```json block with this schema:
            {{
              "status": "PASS or FAIL",
              "severity": "low | medium | high | critical",
              "summary": "string",
              "confidence": 0.0,
              "checks_run": ["string"],
              "issues": [
                {{
                  "severity": "low | medium | high | critical",
                  "title": "string",
                  "details": "string",
                  "repair_suggestion": "string",
                  "files": ["relative/path"]
                }}
              ],
              "unresolved_risks": ["string"]
            }}

            Verification rules:
            - Be strict and specific.
            - FAIL if required files are missing, scripts are broken, or docs contradict behavior.
            - Check the canonical BeeChinese product docs in docs/ when product intent or acceptance expectations are relevant.
            - If there are no material issues, return PASS with an empty issues list.
            - Confidence must be a number between 0 and 1.
            - Focus on whether this cycle's implementation is correct and whether it advances the stated goal safely.
            """
        ).strip()

    def _run_goal_cycle(
        self,
        *,
        goal: str,
        success_criteria: str,
        cycle_number: int,
        cycle_history: str,
    ) -> CycleArtifact:
        LOGGER.info("Starting goal cycle=%s", cycle_number)
        repo_summary = self._run_named_agent(
            "repo-study",
            self._build_repo_study_prompt(
                goal=goal,
                success_criteria=success_criteria,
                cycle_number=cycle_number,
                cycle_history=cycle_history,
            ),
        )
        LOGGER.info("Completed repo-study cycle=%s", cycle_number)
        plan = PlanArtifact.from_response(
            self._run_named_agent(
                "planner",
                self._build_planner_prompt(
                    goal=goal,
                    success_criteria=success_criteria,
                    cycle_number=cycle_number,
                    repo_summary=repo_summary,
                    cycle_history=cycle_history,
                ),
            ),
            user_task=goal,
        )
        LOGGER.info(
            "Planner result cycle=%s goal_complete=%s step_count=%s summary=%s",
            cycle_number,
            plan.goal_complete,
            len(plan.steps),
            plan.summary or "(no summary)",
        )
        if plan.goal_complete:
            LOGGER.info(
                "Cycle=%s marked complete by planner reason=%s",
                cycle_number,
                plan.goal_completion_reason or "(no reason provided)",
            )
            return CycleArtifact(
                cycle_number=cycle_number,
                repo_summary=repo_summary,
                plan=plan,
                execution_summaries=[],
                verifier_results=[],
            )

        execution_summaries: list[str] = []
        verifier_results: list[VerifierArtifact] = []
        verifier_feedback: VerifierArtifact | None = None

        for round_number in range(self.max_fix_rounds + 1):
            LOGGER.info(
                "Entering cycle=%s implementation_round=%s",
                cycle_number,
                round_number + 1,
            )
            execution_summaries.append(
                self._run_orchestrator_execution(
                    goal=goal,
                    success_criteria=success_criteria,
                    cycle_number=cycle_number,
                    repo_summary=repo_summary,
                    plan=plan,
                    verifier_feedback=verifier_feedback,
                    round_number=round_number,
                )
            )
            verifier = VerifierArtifact.from_response(
                self._run_named_agent(
                    "verifier",
                    self._build_verifier_prompt(
                        goal=goal,
                        success_criteria=success_criteria,
                        cycle_number=cycle_number,
                        repo_summary=repo_summary,
                        plan=plan,
                        execution_summaries=execution_summaries,
                    ),
                )
            )
            verifier_results.append(verifier)
            LOGGER.info(
                "Verifier result cycle=%s round=%s status=%s severity=%s issues=%s summary=%s",
                cycle_number,
                round_number + 1,
                verifier.status,
                verifier.severity,
                len(verifier.issues),
                verifier.summary or "(no summary)",
            )
            if verifier.passed:
                break
            verifier_feedback = verifier

        final_verifier = verifier_results[-1] if verifier_results else None
        LOGGER.info(
            "Finished goal cycle=%s verifier_status=%s goal_complete=%s remaining_work_items=%s",
            cycle_number,
            final_verifier.status if final_verifier else "NOT_RUN",
            plan.goal_complete,
            len(plan.remaining_work),
        )

        return CycleArtifact(
            cycle_number=cycle_number,
            repo_summary=repo_summary,
            plan=plan,
            execution_summaries=execution_summaries,
            verifier_results=verifier_results,
        )

    def _build_next_steps(
        self,
        *,
        status: str,
        cycles: list[CycleArtifact],
    ) -> list[str]:
        if not cycles:
            return ["Run the orchestrator with a concrete task and success criteria."]

        last_cycle = cycles[-1]
        last_verifier = last_cycle.final_verifier

        if status == "PASS":
            return _dedupe(
                [
                    "Use this agent layer as the control plane before introducing real BeeChinese product apps under dedicated app/service directories.",
                    "Add the first concrete BeeChinese feature task, such as email auth, course catalog modeling, or a NestJS/FastAPI service skeleton.",
                    "Keep README, .openhands guidance, and agent definitions aligned as the repo evolves.",
                ]
            )

        if status == "PARTIAL":
            return _dedupe(
                last_cycle.plan.remaining_work
                + [
                    f"Increase --max-goal-cycles above {self.max_goal_cycles} if you want the orchestrator to keep advancing this goal automatically.",
                    "Narrow the task or add more specific success criteria if the planner keeps finding additional slices.",
                ]
            )

        issue_hints = []
        if last_verifier is not None:
            issue_hints.extend(
                issue.repair_suggestion
                for issue in last_verifier.issues
                if issue.repair_suggestion.strip()
            )
        return _dedupe(
            issue_hints
            + last_cycle.plan.remaining_work
            + [
                "Re-run the orchestrator after resolving the failing verifier issues.",
                "Review the failing files manually if the verifier confidence is low.",
            ]
        )

    def run(
        self,
        task: str,
        *,
        success_criteria: str = DEFAULT_SUCCESS_CRITERIA,
    ) -> RunReport:
        LOGGER.info(
            "Starting BeeChinese run task=%s success_criteria=%s",
            task,
            success_criteria,
        )
        before_paths = _git_changed_paths(self.workspace)
        cycles: list[CycleArtifact] = []
        status = "PARTIAL"
        goal_complete = False
        goal_reason = ""

        for cycle_number in range(1, self.max_goal_cycles + 1):
            cycle = self._run_goal_cycle(
                goal=task,
                success_criteria=success_criteria,
                cycle_number=cycle_number,
                cycle_history=self._render_cycle_history(cycles),
            )
            cycles.append(cycle)

            if cycle.plan.goal_complete:
                status = "PASS"
                goal_complete = True
                goal_reason = cycle.plan.goal_completion_reason or (
                    f"The planner marked the goal complete at cycle {cycle_number}."
                )
                LOGGER.info("Run completed by planner at cycle=%s", cycle_number)
                break

            final_verifier = cycle.final_verifier
            if final_verifier is None:
                status = "FAIL"
                goal_reason = (
                    f"Cycle {cycle_number} ended before a verifier result was captured."
                )
                LOGGER.error("Run failed because no verifier result was captured in cycle=%s", cycle_number)
                break

            if not final_verifier.passed:
                status = "FAIL"
                goal_reason = (
                    f"Cycle {cycle_number} failed verification after "
                    f"{len(cycle.verifier_results)} implementation round(s)."
                )
                LOGGER.error(
                    "Run failed verification at cycle=%s rounds=%s issues=%s",
                    cycle_number,
                    len(cycle.verifier_results),
                    len(final_verifier.issues),
                )
                break

            goal_reason = cycle.plan.goal_completion_reason or (
                f"Cycle {cycle_number} passed verification, but the planner still sees remaining work."
            )
            LOGGER.info(
                "Cycle=%s passed verification but goal remains incomplete",
                cycle_number,
            )
        else:
            if cycles and cycles[-1].final_verifier and cycles[-1].final_verifier.passed:
                status = "PARTIAL"
                goal_reason = (
                    f"Reached the safety limit of {self.max_goal_cycles} goal cycles "
                    "before the planner marked the goal complete."
                )
                LOGGER.warning(
                    "Run reached goal-cycle safety limit=%s with partial completion",
                    self.max_goal_cycles,
                )
            else:
                status = "FAIL"
                goal_reason = (
                    f"Reached the safety limit of {self.max_goal_cycles} goal cycles "
                    "without a clean completion."
                )
                LOGGER.error(
                    "Run reached goal-cycle safety limit=%s without clean completion",
                    self.max_goal_cycles,
                )

        after_paths = _git_changed_paths(self.workspace)
        changed_files = sorted(after_paths - before_paths)

        checks_run = _dedupe(
            [
                check
                for cycle in cycles
                for check in (
                    cycle.plan.checks
                    + (cycle.final_verifier.checks_run if cycle.final_verifier else [])
                )
            ]
        )
        last_cycle = cycles[-1] if cycles else None
        if status == "PASS":
            unresolved_risks = _dedupe(
                (
                    last_cycle.plan.risks
                    if last_cycle is not None
                    else []
                )
                + (
                    last_cycle.final_verifier.unresolved_risks
                    if last_cycle is not None and last_cycle.final_verifier is not None
                    else []
                )
            )
        else:
            unresolved_risks = _dedupe(
                (
                    last_cycle.plan.risks + last_cycle.plan.remaining_work
                    if last_cycle is not None
                    else []
                )
                + (
                    last_cycle.final_verifier.unresolved_risks
                    if last_cycle is not None and last_cycle.final_verifier is not None
                    else []
                )
                + (
                    [
                        f"{issue.severity}: {issue.title}"
                        for issue in last_cycle.final_verifier.issues
                    ]
                    if last_cycle is not None and last_cycle.final_verifier is not None
                    else []
                )
            )
        modified_summary = "\n\n".join(
            cycle.render_summary() for cycle in cycles if cycle.render_summary().strip()
        )

        LOGGER.info(
            "Finished BeeChinese run status=%s cycles_run=%s changed_files=%s checks=%s unresolved_risks=%s",
            status,
            len(cycles),
            len(changed_files),
            len(checks_run),
            len(unresolved_risks),
        )

        return RunReport(
            task=task,
            success_criteria=success_criteria,
            status=status,
            cycles_run=len(cycles),
            goal_complete=goal_complete,
            goal_reason=goal_reason,
            modified_summary=modified_summary,
            changed_files=changed_files,
            checks_run=checks_run,
            unresolved_risks=unresolved_risks,
            next_steps=self._build_next_steps(status=status, cycles=cycles),
        )


def validate_workspace(control_root: Path) -> str:
    registry = FileAgentRegistry(control_root=control_root, workspace=control_root)
    registry.validate_required_agents()
    skills = load_repo_skills(control_root=control_root, workspace=control_root)
    root_agents_path = control_root / ROOT_AGENTS_PATH
    guidance_path = control_root / REPO_GUIDANCE_PATH
    control_skills_dir = control_root / CONTROL_SKILLS_DIR
    product_context_paths = [path for path in CANONICAL_CONTEXT_PATHS if path != REPO_GUIDANCE_PATH]
    canonical_docs_present = sum(
        1 for relative_path in product_context_paths if (control_root / relative_path).exists()
    )
    control_skill_packages = 0
    if control_skills_dir.exists():
        control_skill_packages = len(list(control_skills_dir.rglob("SKILL.md")))

    lines = [
        "BeeChinese agent workspace validation passed.",
        f"Framework root: {control_root}",
        f"Agents loaded: {', '.join(sorted(registry.definitions))}",
        f"Project skills loaded: {len(skills)}",
        f"Root AGENTS.md present: {'yes' if root_agents_path.exists() else 'no'}",
        f"Repo guidance present: {'yes' if guidance_path.exists() else 'no'}",
        f"Control skill packages present: {control_skill_packages}",
        "Canonical product-context docs present: "
        f"{canonical_docs_present}/{len(product_context_paths)}",
        "Registered tool names available in code: "
        f"{TerminalTool.name}, {ApplyPatchTool.name}, {TaskTrackerTool.name}, "
        f"{TaskToolSet.name}, {BrowserToolSet.name}, {DocsToolSet.name}",
    ]
    return "\n".join(lines)


def _supported_openai_subscription_models() -> tuple[str, ...]:
    try:
        from openhands.sdk.llm.auth.openai import OPENAI_CODEX_MODELS
    except Exception:
        return ()
    return tuple(sorted(OPENAI_CODEX_MODELS))


def build_llm(vendor: str, model: str) -> LLM:
    LOGGER.info("Building LLM vendor=%s model=%s", vendor, model)
    if vendor == "openai":
        supported_models = _supported_openai_subscription_models()
        if supported_models and model not in supported_models:
            supported = ", ".join(supported_models)
            raise ValueError(
                f"Model '{model}' is not supported by the installed OpenHands SDK subscription flow. "
                f"Supported models: {supported}. "
                f"Try '--model {DEFAULT_MODEL}' or another supported value."
            )

    try:
        return LLM.subscription_login(vendor=vendor, model=model)
    except ValueError as exc:
        message = str(exc)
        if vendor == "openai" and "not supported for subscription access" in message:
            supported_models = _supported_openai_subscription_models()
            supported = ", ".join(supported_models) if supported_models else "unknown"
            raise ValueError(
                f"OpenHands subscription login rejected model '{model}'. "
                f"Supported models for this installed SDK: {supported}. "
                f"Try '--model {DEFAULT_MODEL}'."
            ) from exc
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or validate the BeeChinese OpenHands agent framework."
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("BEECHINESE_AGENT_LOG_LEVEL", "INFO"),
        help=LOG_LEVEL_HELP,
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    run_parser = subparsers.add_parser("run", help="Run a BeeChinese orchestrated task.")
    run_parser.add_argument(
        "--log-level",
        default=os.environ.get("BEECHINESE_AGENT_LOG_LEVEL", "INFO"),
        help=LOG_LEVEL_HELP,
    )
    run_parser.add_argument(
        "--task",
        default=DEFAULT_EXAMPLE_TASK,
        help="Task instruction given to the orchestrator.",
    )
    run_parser.add_argument(
        "--vendor",
        default=DEFAULT_VENDOR,
        help="LLM vendor used with LLM.subscription_login(...).",
    )
    run_parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model name used with LLM.subscription_login(...).",
    )
    run_parser.add_argument(
        "--workspace",
        default=os.environ.get("BEECHINESE_AGENT_WORKSPACE", str(DEFAULT_WORKSPACE)),
        help="Target BeeChinese workspace path. Defaults to ~/BeeChinese or BEECHINESE_AGENT_WORKSPACE.",
    )
    run_parser.add_argument(
        "--max-fix-rounds",
        type=int,
        default=DEFAULT_MAX_FIX_ROUNDS,
        help="Maximum verifier-driven repair rounds after the first implementation pass.",
    )
    run_parser.add_argument(
        "--max-goal-cycles",
        type=int,
        default=DEFAULT_MAX_GOAL_CYCLES,
        help="Maximum outer goal cycles that repeat study/plan/implement/verify.",
    )
    run_parser.add_argument(
        "--success-criteria",
        default=DEFAULT_SUCCESS_CRITERIA,
        help="Explicit completion criteria for the overall task goal.",
    )
    run_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Disable browser access for the parent orchestrator agent.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate repository structure, agent files, and guidance without using an LLM.",
    )
    validate_parser.add_argument(
        "--log-level",
        default=os.environ.get("BEECHINESE_AGENT_LOG_LEVEL", "INFO"),
        help=LOG_LEVEL_HELP,
    )
    validate_parser.add_argument(
        "--workspace",
        default=str(FRAMEWORK_ROOT),
        help="Framework repository path to validate. Defaults to the current BeeChinese-Agent repository root.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(getattr(args, "log_level", "INFO"))
    command = args.command or "run"
    workspace = Path(getattr(args, "workspace")).resolve()
    control_root = FRAMEWORK_ROOT.resolve()

    try:
        if command == "validate":
            print(validate_workspace(workspace))
            return 0

        if not workspace.exists():
            raise ValueError(
                f"Workspace '{workspace}' does not exist. Create it first or pass --workspace explicitly."
            )

        llm = build_llm(vendor=args.vendor, model=args.model)
        orchestrator = BeeChineseOrchestrator(
            workspace=workspace,
            control_root=control_root,
            llm=llm,
            max_fix_rounds=args.max_fix_rounds,
            max_goal_cycles=args.max_goal_cycles,
            enable_browser=not args.no_browser,
        )
        report = orchestrator.run(
            task=args.task,
            success_criteria=args.success_criteria,
        )
        print(report.render())
        return 0 if report.status == "PASS" else 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"BeeChinese agent run failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
