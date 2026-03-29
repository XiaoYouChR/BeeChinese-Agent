"""Conversation event logging helpers for BeeChinese OpenHands runs."""

from __future__ import annotations

import logging
import re
from typing import Literal

from openhands.sdk.conversation.visualizer.base import ConversationVisualizerBase
from openhands.sdk.event import (
    ACPToolCallEvent,
    ActionEvent,
    AgentErrorEvent,
    Condensation,
    CondensationRequest,
    ConversationStateUpdateEvent,
    Event,
    MessageEvent,
    ObservationEvent,
    PauseEvent,
    SystemPromptEvent,
    UserRejectObservation,
)
from openhands.sdk.event.hook_execution import HookExecutionEvent
from openhands.sdk.llm import content_to_str


EventStreamMode = Literal["off", "summary", "full"]

EVENT_LOGGER = logging.getLogger("beechinese_agent.events")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_preview(text: str, limit: int) -> str:
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _observation_exit_code(observation: object) -> str:
    exit_code = getattr(observation, "exit_code", None)
    if exit_code is None:
        return ""
    return f" exit={exit_code}"


def _observation_error_suffix(observation: object) -> str:
    is_error = getattr(observation, "is_error", False)
    return " error=true" if is_error else ""


def _render_terminal_summary(text: str, limit: int) -> str:
    preview = _clean_preview(text, limit)
    if not preview:
        return "[no output]"
    first_line = preview.splitlines()[0].strip()
    return first_line or "[no output]"


class LoggingConversationVisualizer(ConversationVisualizerBase):
    """Log conversation events to the BeeChinese runtime logger."""

    def __init__(
        self,
        *,
        label: str,
        mode: EventStreamMode = "summary",
        preview_chars: int | None = None,
    ):
        super().__init__()
        self._label = label
        self._mode = mode
        if preview_chars is None:
            preview_chars = 120 if mode == "summary" else 1200
        self._preview_chars = preview_chars

    def create_sub_visualizer(self, agent_id: str) -> "LoggingConversationVisualizer":
        return LoggingConversationVisualizer(
            label=f"{self._label} > {agent_id}",
            mode=self._mode,
            preview_chars=self._preview_chars,
        )

    def on_event(self, event: Event) -> None:
        if self._mode == "off":
            return

        message = self._format_event(event)
        if not message:
            return

        EVENT_LOGGER.info("[%s] %s", self._label, message)

    def _format_event(self, event: Event) -> str:
        if isinstance(event, SystemPromptEvent):
            if self._mode == "summary":
                return ""
            tools = ", ".join(sorted(tool.name for tool in event.tools))
            return f"system_prompt tools=[{tools}]"

        if isinstance(event, MessageEvent):
            role = getattr(event.llm_message, "role", "unknown")
            text = "".join(content_to_str(event.llm_message.content))
            preview = _clean_preview(text, self._preview_chars)
            sender = f" sender={event.sender}" if event.sender else ""
            skills = (
                f" skills={','.join(event.activated_skills)}"
                if event.activated_skills
                else ""
            )
            if self._mode == "full":
                return (
                    f"message role={role} source={event.source}{sender}{skills}\n"
                    f"{preview or '[no text content]'}"
                )
            return (
                f"message role={role} source={event.source}{sender}{skills}"
                f" preview={preview or '[no text content]'}"
            )

        if isinstance(event, ACPToolCallEvent):
            preview = _clean_preview(
                f"{event.title} input={event.raw_input} output={event.raw_output}",
                self._preview_chars,
            )
            return (
                f"acp_tool_call status={event.status} kind={event.tool_kind}"
                f" preview={preview}"
            )

        if isinstance(event, ActionEvent):
            preview_parts = []
            if event.summary:
                preview_parts.append(event.summary)
            if event.action is not None:
                action_preview = _clean_preview(
                    event.action.visualize.plain,
                    self._preview_chars,
                )
                if action_preview:
                    preview_parts.append(action_preview)
            elif event.tool_call is not None:
                preview_parts.append(
                    _clean_preview(
                        f"{event.tool_call.name} {event.tool_call.arguments}",
                        self._preview_chars,
                    )
                )
            preview = " | ".join(part for part in preview_parts if part)
            tool_name = event.tool_name or (
                event.action.__class__.__name__ if event.action is not None else "unknown"
            )
            if self._mode == "full":
                return (
                    f"action tool={tool_name} risk={event.security_risk}"
                    f" preview={preview or '[no preview]'}"
                )
            return (
                f"action tool={tool_name}"
                + (f" summary={preview}" if preview else "")
            )

        if isinstance(event, ObservationEvent):
            raw_text = event.observation.visualize.plain
            preview = _clean_preview(raw_text, self._preview_chars)
            suffix = (
                _observation_exit_code(event.observation)
                + _observation_error_suffix(event.observation)
            )
            if self._mode == "full":
                return f"observation tool={event.tool_name}{suffix}\n{preview or '[no output]'}"
            if event.tool_name == "terminal":
                return (
                    f"observation tool={event.tool_name}{suffix}"
                    f" preview={_render_terminal_summary(raw_text, self._preview_chars)}"
                )
            return (
                f"observation tool={event.tool_name}{suffix}"
                f" preview={preview or '[no output]'}"
            )

        if isinstance(event, UserRejectObservation):
            preview = _clean_preview(event.rejection_reason, self._preview_chars)
            return (
                f"rejection tool={event.tool_name} source={event.rejection_source}"
                f" preview={preview or '[no reason]'}"
            )

        if isinstance(event, AgentErrorEvent):
            preview = _clean_preview(event.error, self._preview_chars)
            return f"agent_error tool={event.tool_name} preview={preview or '[no details]'}"

        if isinstance(event, PauseEvent):
            return "pause"

        if isinstance(event, HookExecutionEvent):
            preview = _clean_preview(str(event.model_dump()), self._preview_chars)
            return f"hook_execution preview={preview}"

        if isinstance(event, CondensationRequest):
            return "" if self._mode == "summary" else "condensation_request"

        if isinstance(event, Condensation):
            if self._mode == "summary":
                return ""
            preview = _clean_preview(event.visualize.plain, self._preview_chars)
            return f"condensation preview={preview or '[no details]'}"

        if isinstance(event, ConversationStateUpdateEvent):
            return ""

        preview = _clean_preview(getattr(event.visualize, "plain", str(event)), self._preview_chars)
        return f"{event.__class__.__name__} preview={preview or '[no details]'}"
