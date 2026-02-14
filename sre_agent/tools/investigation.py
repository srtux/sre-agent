"""Tools for managing investigation state and findings."""

import logging
from typing import Annotated, Any

from sre_agent.memory.factory import get_memory_manager
from sre_agent.schema import BaseToolResponse, InvestigationPhase, ToolStatus
from sre_agent.tools.common.decorators import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
async def update_investigation_state(
    phase: Annotated[
        str | None,
        "The current phase of investigation. MUST be one of: initiated, triage, deep_dive, remediation, resolved.",
    ] = None,
    new_findings: Annotated[list[str] | None, "New factual findings discovered"] = None,
    hypothesis: Annotated[str | None, "New hypothesis being tested"] = None,
    root_cause: Annotated[str | None, "The confirmed root cause identity"] = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Updates the internal investigation state to track diagnostic progress.

    Use this tool whenever you successfully identify a key signal, confirm a hypothesis,
    or are ready to move to the next phase of analysis.
    """
    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session = getattr(inv_ctx, "session", None) if inv_ctx else None

    if not session:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error="No active session found."
        )

    # Get Memory Manager
    memory_manager = get_memory_manager()
    session_id = getattr(session, "id", None) if session else None

    # Update Phase in Memory Manager
    if phase:
        try:
            # Normalize phase
            try:
                new_phase = InvestigationPhase(phase.lower())
                await memory_manager.update_state(new_phase, session_id=session_id)
            except ValueError:
                logger.warning(
                    f"Invalid phase provided: {phase}. Ignoring phase update."
                )
                phase = None  # Reset phase so it doesn't pollute session state below
        except Exception as e:
            logger.warning(f"Failed to update memory manager state: {e}")

    # Add findings to Memory Manager
    if new_findings:
        from sre_agent.auth import get_user_id_from_tool_context

        user_id = get_user_id_from_tool_context(tool_context)
        for finding in new_findings:
            await memory_manager.add_finding(
                description=finding,
                source_tool="update_investigation_state",
                session_id=session_id,
                user_id=user_id,
            )

    # Maintain Session State for backward compatibility / Frontend
    if session:
        current_state = session.state.get("investigation_state", {})

        # Initialize defaults if empty
        if not current_state:
            current_state = {
                "phase": InvestigationPhase.INITIATED.value,
                "findings": [],
                "hypotheses": [],
                "confirmed_root_cause": None,
                "suggested_fix": None,
            }

        updates: dict[str, Any] = {}
        if phase:
            updates["phase"] = phase.lower()

        if new_findings:
            existing = current_state.get("findings", [])
            existing.extend(new_findings)
            updates["findings"] = list(dict.fromkeys(existing))

        if hypothesis:
            existing_hyp = current_state.get("hypotheses", [])
            existing_hyp.append(hypothesis)
            updates["hypotheses"] = list(dict.fromkeys(existing_hyp))

        if root_cause:
            updates["confirmed_root_cause"] = root_cause
            if not phase:  # Auto-switch phase if root cause found
                updates["phase"] = InvestigationPhase.REMEDIATION.value
                await memory_manager.update_state(
                    InvestigationPhase.REMEDIATION, session_id=session_id
                )

        # Apply updates
        current_state.update(updates)

        # Persist session
        from sre_agent.services import get_session_service

        session_manager = get_session_service()
        await session_manager.update_session_state(
            session, {"investigation_state": current_state}
        )

        logger.info(f"Updated investigation state for session {session.id}")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS, result="Successfully updated investigation state."
    )


@adk_tool
async def get_investigation_summary(tool_context: Any = None) -> BaseToolResponse:
    """Returns a summary of the current investigation state and findings."""
    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session = getattr(inv_ctx, "session", None) if inv_ctx else None

    if not session:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error="No active session found."
        )

    state = session.state.get("investigation_state", {})
    phase = state.get("phase", "unknown")
    findings = state.get("findings", [])
    hypotheses = state.get("hypotheses", [])
    root_cause = state.get("confirmed_root_cause")

    summary = [
        f"### Investigation Summary (Phase: {phase.upper()})",
        f"**Findings:** {', '.join(findings) if findings else 'None yet'}",
    ]

    if hypotheses:
        summary.append(f"**Hypotheses:** {', '.join(hypotheses)}")

    if root_cause:
        summary.append(f"**Confirmed Root Cause:** {root_cause}")

    result = "\n".join(summary)
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)
