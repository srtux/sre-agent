"""Tools for interacting with SRE Agent Memory and Self-Improvement.

This module provides tools for:
- Searching past findings and learnings
- Explicitly adding discoveries to memory
- Completing investigations and learning patterns
- Analyzing past agent traces for self-improvement
"""

import logging
from typing import Annotated, Any

from sre_agent.memory.factory import get_memory_manager
from sre_agent.schema import (
    BaseToolResponse,
    Confidence,
    InvestigationPhase,
    ToolStatus,
)
from sre_agent.tools.common.decorators import adk_tool

logger = logging.getLogger(__name__)


def _get_context(tool_context: Any) -> tuple[str | None, str | None]:
    """Extract session_id and user_id from tool context."""
    from sre_agent.auth import get_user_id_from_tool_context

    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session_id = getattr(inv_ctx, "session_id", None) if inv_ctx else None
    if inv_ctx and not session_id and hasattr(inv_ctx, "session"):
        session_id = getattr(inv_ctx.session, "id", None)

    user_id = get_user_id_from_tool_context(tool_context)
    return session_id, user_id


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
    - You want to find patterns that match the current symptom.
    """
    manager = get_memory_manager()
    session_id, user_id = _get_context(tool_context)

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
    - You learn correct API syntax that worked.
    """
    manager = get_memory_manager()
    session_id, user_id = _get_context(tool_context)

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


@adk_tool
async def complete_investigation(
    symptom_type: Annotated[
        str,
        "Category of the initial symptom (e.g., 'high_latency', 'error_rate_spike', 'oom_killed')",
    ],
    root_cause_category: Annotated[
        str,
        "Category of the root cause found (e.g., 'connection_pool_exhaustion', 'memory_leak', 'config_change')",
    ],
    resolution_summary: Annotated[
        str,
        "Brief description of how the issue was resolved or what was recommended",
    ],
    tool_context: Any = None,
) -> BaseToolResponse:
    """Mark an investigation as complete and learn from the pattern.

    Call this when you have successfully identified the root cause of an incident.
    This records the investigation pattern (symptom → tool sequence → resolution)
    to memory, making future similar investigations faster.

    The tool sequence is automatically tracked during the investigation.

    Args:
        symptom_type: Category of the symptom (e.g., 'high_latency_checkout',
            'error_rate_spike_api', 'oom_killed_worker')
        root_cause_category: Category of the root cause (e.g., 'connection_pool_exhaustion',
            'memory_leak', 'bad_deployment', 'upstream_dependency_failure')
        resolution_summary: What fixed it or what was recommended
        tool_context: ADK tool context (auto-injected)
    """
    manager = get_memory_manager()
    session_id, user_id = _get_context(tool_context)

    # Update investigation state to RESOLVED
    await manager.update_state(InvestigationPhase.RESOLVED, session_id=session_id)

    # Learn from the investigation
    await manager.learn_from_investigation(
        symptom_type=symptom_type,
        root_cause_category=root_cause_category,
        resolution_summary=resolution_summary,
        session_id=session_id,
        user_id=user_id,
    )

    # Sync session to long-term memory
    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    if inv_ctx and hasattr(inv_ctx, "session"):
        try:
            await manager.add_session_to_memory(inv_ctx.session)
            logger.info(f"Session {session_id} synced to memory bank")
        except Exception as e:
            logger.warning(f"Failed to sync session to memory: {e}")

    # Reset for next investigation
    manager.reset_session_tracking()

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "message": "Investigation pattern learned and stored to memory.",
            "pattern": {
                "symptom_type": symptom_type,
                "root_cause_category": root_cause_category,
                "resolution_summary": resolution_summary,
            },
        },
    )


@adk_tool
async def get_recommended_investigation_strategy(
    symptom_description: Annotated[
        str,
        "Description of the current symptom or issue to investigate",
    ],
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get recommended investigation strategies based on past learnings.

    Search memory for similar past investigations and return the tool sequences
    that successfully resolved them. This helps you start with a proven approach.

    Args:
        symptom_description: Description of what you're investigating
            (e.g., 'checkout service has high latency', 'API returning 500 errors')
        tool_context: ADK tool context (auto-injected)
    """
    manager = get_memory_manager()
    session_id, user_id = _get_context(tool_context)

    patterns = await manager.get_recommended_strategy(
        symptom_description=symptom_description,
        session_id=session_id,
        user_id=user_id,
    )

    if not patterns:
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "message": "No matching patterns found. Use standard investigation workflow.",
                "patterns": [],
                "suggestion": "Start with explore_project_health, then follow the symptom to the appropriate tool.",
            },
        )

    # Format patterns for display
    formatted_patterns = []
    for p in patterns:
        formatted_patterns.append(
            {
                "symptom_type": p.symptom_type,
                "root_cause_category": p.root_cause_category,
                "tool_sequence": p.tool_sequence,
                "resolution_summary": p.resolution_summary,
                "confidence": p.confidence,
                "occurrence_count": p.occurrence_count,
            }
        )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "message": f"Found {len(patterns)} matching investigation pattern(s).",
            "patterns": formatted_patterns,
            "suggestion": "Consider following the highest-confidence pattern's tool sequence.",
        },
    )


@adk_tool
async def analyze_and_learn_from_traces(
    trace_project_id: Annotated[
        str,
        "GCP project ID where the agent's traces are stored",
    ],
    hours_back: Annotated[
        int,
        "How many hours of traces to analyze (default: 24)",
    ] = 24,
    focus_on_errors: Annotated[
        bool,
        "If True, focus on traces with errors to learn from mistakes",
    ] = True,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Analyze past agent traces to learn and self-improve.

    This tool examines the agent's own execution traces from Cloud Trace/BigQuery
    to identify:
    - Tool sequences that succeeded or failed
    - Anti-patterns (excessive retries, redundant calls)
    - Efficient investigation patterns worth remembering

    Call this periodically to improve your investigation strategies.

    NOTE: Requires access to the project where agent traces are stored.
    Ask the user which project contains the AutoSRE agent traces.

    Args:
        trace_project_id: Project ID where traces are stored
        hours_back: How many hours of history to analyze
        focus_on_errors: Whether to prioritize learning from errors
        tool_context: ADK tool context (auto-injected)
    """
    from datetime import datetime, timedelta, timezone

    from sre_agent.tools.analysis.agent_trace.queries import (
        get_agent_traces_query,
    )
    from sre_agent.tools.mcp.gcp import get_project_id_with_fallback

    pid = trace_project_id or get_project_id_with_fallback()
    if not pid:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="trace_project_id is required. Ask the user which project contains the agent traces.",
        )

    # Build the query for agent traces
    table = f"{pid}.otel._AllSpans"
    now = datetime.now(timezone.utc)
    start_dt = (now - timedelta(hours=hours_back)).isoformat()
    end_dt = now.isoformat()

    # Generate SQL for listing recent agent traces
    list_sql = get_agent_traces_query(
        table,
        agent_name="sre_agent",
        error_only=focus_on_errors,
        limit=20,
    )
    list_sql = list_sql.replace("@start", f"TIMESTAMP('{start_dt}')").replace(
        "@end", f"TIMESTAMP('{end_dt}')"
    )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "analysis_type": "self_improvement",
            "sql_query": list_sql.strip(),
            "description": (
                f"Query to find recent agent traces for self-analysis. "
                f"Looking back {hours_back} hours"
                f"{', focusing on errors' if focus_on_errors else ''}."
            ),
            "workflow": [
                "1. Execute the SQL using mcp_execute_sql to list agent traces",
                "2. Pick interesting trace IDs (errors or complex investigations)",
                "3. Use detect_agent_anti_patterns to find inefficiencies",
                "4. Use add_finding_to_memory to record lessons learned",
                "5. Store patterns with complete_investigation if applicable",
            ],
            "next_steps": [
                "Execute this query using mcp_execute_sql tool",
                "Analyze the traces for patterns worth learning",
                "Store insights using add_finding_to_memory",
            ],
        },
        metadata={
            "project_id": pid,
            "table": table,
            "hours_back": hours_back,
            "focus_on_errors": focus_on_errors,
        },
    )
