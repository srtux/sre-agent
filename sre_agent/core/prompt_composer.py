"""Three-Tier Prompt Composition System.

Implements the Unrolled Codex pattern for dynamic prompt construction
with clear separation between System, Developer, and User roles.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from google.genai import types

logger = logging.getLogger(__name__)


class PromptRole(str, Enum):
    """The three tiers of prompt composition."""

    SYSTEM = "system"  # Immutable personality and physics
    DEVELOPER = "developer"  # Hard constraints and domain context
    USER = "user"  # Session history and current request


@dataclass
class DomainContext:
    """Domain-specific context to inject into Developer role."""

    project_id: str | None = None
    active_alerts: list[str] = field(default_factory=list)
    runbook_content: str | None = None
    investigation_phase: str | None = None
    custom_constraints: list[str] = field(default_factory=list)
    mistake_lessons: str | None = None


@dataclass
class SessionSummary:
    """Compressed summary of session history."""

    summary_text: str
    key_findings: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    last_compaction_turn: int = 0


class PromptComposer:
    """Composes prompts using the three-tier system.

    Tiers:
    1. System Role: Immutable agent personality and operating principles
    2. Developer Role: Hard constraints, domain context, and injected runbooks
    3. User Role: Session history (summary + recent) and current request
    """

    # System Role - Immutable personality and physics
    SYSTEM_ROLE_TEMPLATE = """You are an SRE Agent specialized in Google Cloud Observability.

## Core Identity
- You are a Site Reliability Engineer AI assistant
- You analyze telemetry data (traces, logs, metrics) to identify root causes
- You operate in a SANDBOXED environment with READ-ONLY access by default
- You follow evidence-based reasoning and never guess

## Operating Principles
1. **Safety First**: All tool calls are intercepted by a Policy Engine
2. **Epistemic Honesty**: State confidence levels, admit uncertainty
3. **Evidence-Based**: Follow the OODA loop (Observe → Orient → Decide → Act)
4. **Minimal Impact**: Prefer observation over action, read over write

## Communication Style
- Use clear, structured responses with headers and tables
- Include confidence levels for conclusions
- Use emojis sparingly for visual scanning
- Format technical data in code blocks"""

    # Developer Role - Hard constraints template
    DEVELOPER_ROLE_TEMPLATE = """## Hard Constraints (MANDATORY)

### Access Control
- You may NOT execute write operations without explicit human approval
- All tool calls are validated by the Policy Engine before execution
- Unknown tools will be rejected automatically

### Reasoning Protocol (OODA Loop)
For every investigation step:
1. **Observe**: Gather telemetry signals (traces, logs, metrics)
2. **Orient**: Map findings to the dependency graph, form hypotheses
3. **Decide**: Select the most promising hypothesis to test
4. **Act**: Execute a synthetic test (read-only query) to validate
5. **Evaluate**: Did the test confirm or refute? Update confidence.

### Error Handling
- If a tool fails with "DO NOT retry", switch to alternative immediately
- Never retry the same failing tool more than twice
- Report tool failures clearly to the user

{domain_context}
"""

    # User Role - Session context template
    USER_ROLE_TEMPLATE = """## Working Context

{session_summary}

## Recent Events
{recent_events}

## Current Request
{user_message}
"""

    def __init__(self) -> None:
        """Initialize the prompt composer."""
        self._custom_system_additions: list[str] = []

    def compose_system_role(self) -> types.Content:
        """Compose the immutable System role content.

        Returns:
            Content object for the system role
        """
        system_text = self.SYSTEM_ROLE_TEMPLATE

        # Add any custom additions
        if self._custom_system_additions:
            system_text += "\n\n## Additional Capabilities\n"
            system_text += "\n".join(self._custom_system_additions)

        return types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"[SYSTEM CONTEXT]\n{system_text}")],
        )

    def compose_developer_role(
        self, domain_context: DomainContext | None = None
    ) -> types.Content:
        """Compose the Developer role with domain context.

        Args:
            domain_context: Domain-specific context to inject

        Returns:
            Content object for the developer role
        """
        context_parts = []

        if domain_context:
            # Project context
            if domain_context.project_id:
                context_parts.append(
                    f"### Project Context\n[CURRENT PROJECT: {domain_context.project_id}]\n"
                    "All queries must target this project unless explicitly requested otherwise."
                )

            # Active alerts
            if domain_context.active_alerts:
                alerts_text = "\n".join(
                    f"- {alert}" for alert in domain_context.active_alerts[:5]
                )
                context_parts.append(f"### Active Alerts\n{alerts_text}")

            # Investigation phase
            if domain_context.investigation_phase:
                context_parts.append(
                    f"### Investigation Phase\n"
                    f"Current phase: **{domain_context.investigation_phase}**\n"
                    "Adjust your analysis depth accordingly."
                )

            # Runbook content
            if domain_context.runbook_content:
                context_parts.append(
                    f"### Runbook Context\n```\n{domain_context.runbook_content}\n```"
                )

            # Custom constraints
            if domain_context.custom_constraints:
                constraints_text = "\n".join(
                    f"- {c}" for c in domain_context.custom_constraints
                )
                context_parts.append(f"### Custom Constraints\n{constraints_text}")

            # Mistake lessons from past sessions
            if domain_context.mistake_lessons:
                context_parts.append(domain_context.mistake_lessons)

        domain_context_text = (
            "\n\n".join(context_parts)
            if context_parts
            else "No additional domain context."
        )

        developer_text = self.DEVELOPER_ROLE_TEMPLATE.format(
            domain_context=domain_context_text
        )

        # Add current time
        now = datetime.now(timezone.utc)
        developer_text += f"\n\n### Current Time\n{now.isoformat()}"

        return types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"[DEVELOPER CONTEXT]\n{developer_text}")],
        )

    def compose_user_role(
        self,
        user_message: str,
        session_summary: SessionSummary | None = None,
        recent_events: list[dict[str, Any]] | None = None,
    ) -> types.Content:
        """Compose the User role with session context.

        Args:
            user_message: The current user message
            session_summary: Compressed summary of earlier session history
            recent_events: Recent raw events to include

        Returns:
            Content object for the user role
        """
        # Format session summary
        if session_summary:
            summary_text = f"""### Session Summary (Compacted)
{session_summary.summary_text}

**Key Findings**: {", ".join(session_summary.key_findings) if session_summary.key_findings else "None yet"}
**Tools Used**: {", ".join(session_summary.tools_used) if session_summary.tools_used else "None yet"}
"""
        else:
            summary_text = "### Session Summary\nThis is a new session."

        # Format recent events
        if recent_events:
            events_text = self._format_recent_events(recent_events)
        else:
            events_text = "No recent events."

        user_text = self.USER_ROLE_TEMPLATE.format(
            session_summary=summary_text,
            recent_events=events_text,
            user_message=user_message,
        )

        return types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        )

    def compose_full_prompt(
        self,
        user_message: str,
        domain_context: DomainContext | None = None,
        session_summary: SessionSummary | None = None,
        recent_events: list[dict[str, Any]] | None = None,
    ) -> list[types.Content]:
        """Compose the full three-tier prompt.

        Args:
            user_message: The current user message
            domain_context: Domain-specific context for Developer role
            session_summary: Compressed session summary for User role
            recent_events: Recent events for User role

        Returns:
            List of Content objects representing the full prompt
        """
        return [
            self.compose_system_role(),
            self.compose_developer_role(domain_context),
            self.compose_user_role(user_message, session_summary, recent_events),
        ]

    def _format_recent_events(
        self, events: list[dict[str, Any]], max_events: int = 5
    ) -> str:
        """Format recent events for display.

        Args:
            events: List of event dictionaries
            max_events: Maximum number of events to include

        Returns:
            Formatted events string
        """
        formatted = []

        for event in events[-max_events:]:
            event_type = event.get("type", "unknown")
            timestamp = event.get("timestamp", "")
            content = event.get("content", "")

            # Truncate long content
            if len(content) > 500:
                content = content[:500] + "... [truncated]"

            formatted.append(f"**[{event_type}]** ({timestamp})\n{content}")

        return "\n\n".join(formatted)

    def add_system_capability(self, capability: str) -> None:
        """Add a capability to the System role.

        Args:
            capability: Description of the capability
        """
        self._custom_system_additions.append(f"- {capability}")

    def create_tool_guidance(self, tool_name: str, context: str) -> str:
        """Create guidance text for a specific tool call.

        Args:
            tool_name: Name of the tool
            context: Context about why the tool is being called

        Returns:
            Guidance text for the tool
        """
        return f"""### Tool Guidance: {tool_name}
Context: {context}

Remember:
- Validate output format matches expected schema
- Check for errors in the response
- If the tool fails, consider alternatives
"""


# Singleton instance
_prompt_composer: PromptComposer | None = None


def get_prompt_composer() -> PromptComposer:
    """Get the singleton prompt composer instance."""
    global _prompt_composer
    if _prompt_composer is None:
        _prompt_composer = PromptComposer()
    return _prompt_composer
