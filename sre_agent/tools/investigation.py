"""Tools for managing investigation state and findings."""

import logging
from typing import Annotated, Any

from sre_agent.models.investigation import InvestigationPhase, InvestigationState
from sre_agent.tools.common.decorators import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
async def update_investigation_state(
    tool_context: Any,
    phase: Annotated[
        str | None,
        "The current phase of investigation (triage, analysis, root_cause, remediation)",
    ] = None,
    new_findings: Annotated[list[str] | None, "New factual findings discovered"] = None,
    hypothesis: Annotated[str | None, "New hypothesis being tested"] = None,
    root_cause: Annotated[str | None, "The confirmed root cause identity"] = None,
) -> str:
    """Updates the internal investigation state to track diagnostic progress.

    Use this tool whenever you successfully identify a key signal, confirm a hypothesis,
    or are ready to move to the next phase of analysis.
    """
    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session = getattr(inv_ctx, "session", None) if inv_ctx else None
    if not session:
        return "Error: No active session found in tool context."

    # Get current state
    current_state_dict = session.state.get("investigation_state", {})
    state = InvestigationState.from_dict(current_state_dict)

    # Apply updates
    if phase:
        try:
            state.phase = InvestigationPhase(phase.lower())
        except ValueError:
            return f"Error: Invalid phase '{phase}'. Valid phases: {[p.value for p in InvestigationPhase]}"

    if new_findings:
        state.findings.extend(new_findings)
        # Unique findings only
        state.findings = list(dict.fromkeys(state.findings))

    if hypothesis:
        state.hypotheses.append(hypothesis)

    if root_cause:
        state.confirmed_root_cause = root_cause
        state.phase = InvestigationPhase.ROOT_CAUSE

    # Save back to session
    from sre_agent.services import get_session_service

    session_manager = get_session_service()
    await session_manager.update_session_state(
        session, {"investigation_state": state.to_dict()}
    )

    logger.info(f"Investigation state updated for session {session.id}: {state.phase}")
    return (
        f"Successfully updated investigation state. Current Phase: {state.phase.value}"
    )


@adk_tool
async def get_investigation_summary(tool_context: Any) -> str:
    """Returns a summary of the current investigation state and findings."""
    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session = getattr(inv_ctx, "session", None) if inv_ctx else None
    if not session:
        return "Error: No active session found."

    state_dict = session.state.get("investigation_state", {})
    state = InvestigationState.from_dict(state_dict)

    summary = [
        f"### Investigation Summary (Phase: {state.phase.value.upper()})",
        f"**Findings:** {', '.join(state.findings) if state.findings else 'None yet'}",
    ]

    if state.hypotheses:
        summary.append(f"**Hypotheses:** {', '.join(state.hypotheses)}")

    if state.confirmed_root_cause:
        summary.append(f"**Confirmed Root Cause:** {state.confirmed_root_cause}")

    return "\n".join(summary)
