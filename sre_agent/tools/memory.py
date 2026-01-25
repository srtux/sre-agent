"""Tools for interacting with SRE Agent Memory."""

from typing import Annotated, Any

from sre_agent.memory.factory import get_memory_manager
from sre_agent.schema import BaseToolResponse, Confidence, ToolStatus
from sre_agent.tools.common.decorators import adk_tool


@adk_tool
async def search_memory(
    query: Annotated[str, "Semantic search query to find relevant past findings"],
    limit: Annotated[int, "Maximum number of results to return"] = 5,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Search the agent's memory for relevant findings from past investigations.

    Use this when:
    - You need to recall details about a trace or service analyzed earlier.
    - You want to check if similar issues have been seen before.
    """
    from sre_agent.auth import get_user_id_from_tool_context

    manager = get_memory_manager()
    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session_id = getattr(inv_ctx, "session_id", None) if inv_ctx else None
    if inv_ctx and not session_id and hasattr(inv_ctx, "session"):
        session_id = getattr(inv_ctx.session, "id", None)

    user_id = get_user_id_from_tool_context(tool_context)

    results = await manager.get_relevant_findings(
        query, session_id=session_id, limit=limit, user_id=user_id
    )
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=results)


@adk_tool
async def add_finding_to_memory(
    description: Annotated[str, "Human-readable description of the finding"],
    source_tool: Annotated[str, "Name of the tool that generated this finding"],
    confidence: Annotated[
        Confidence, "Confidence level (high, medium, low)"
    ] = Confidence.MEDIUM,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Explicitly add a finding to the agent's memory.

    Use this when:
    - You discover something important that should be remembered.
    - You confirm a hypothesis.
    """
    from sre_agent.auth import get_user_id_from_tool_context

    manager = get_memory_manager()
    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session_id = getattr(inv_ctx, "session_id", None) if inv_ctx else None
    if inv_ctx and not session_id and hasattr(inv_ctx, "session"):
        session_id = getattr(inv_ctx.session, "id", None)

    user_id = get_user_id_from_tool_context(tool_context)

    await manager.add_finding(
        description=description,
        source_tool=source_tool,
        confidence=confidence,
        session_id=session_id,
        user_id=user_id,
    )
    return BaseToolResponse(
        status=ToolStatus.SUCCESS, result="Finding added to memory."
    )
