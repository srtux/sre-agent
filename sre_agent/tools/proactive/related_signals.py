"""Proactive signal fetching and suggestion tools."""

from typing import Any

from sre_agent.memory.factory import get_memory_manager
from sre_agent.schema import InvestigationPhase
from sre_agent.tools.common.decorators import adk_tool


@adk_tool
async def suggest_next_steps(
    tool_context: Any,
) -> str:
    """Suggest the next best steps based on the current investigation state.

    This tool analyzes the current phase and recent findings to recommend
    what signals to look at next (e.g., specific logs, metrics, or traces).
    """
    manager = get_memory_manager()
    state = manager.get_state()

    # Base suggestions on global state
    suggestions = []

    if state == InvestigationPhase.INITIATED:
        suggestions.append("- Run `run_aggregate_analysis` to get a high-level view.")
        suggestions.append("- Use `list_alerts` to check for active incidents.")

    elif state == InvestigationPhase.TRIAGE:
        suggestions.append(
            "- Identify the specific failing service using `find_bottleneck_services`."
        )
        suggestions.append(
            "- Compare bad traces with good traces using `run_triage_analysis`."
        )
        suggestions.append("- Check `get_golden_signals` for the suspected service.")

    elif state == InvestigationPhase.DEEP_DIVE:
        suggestions.append("- Run `run_deep_dive_analysis` to find root cause.")
        suggestions.append(
            "- Correlate logs with the trace using `run_log_pattern_analysis`."
        )
        suggestions.append("- Check for recent deployments or config changes.")

    elif state == InvestigationPhase.REMEDIATION:
        suggestions.append(
            "- Generate fix suggestions with `generate_remediation_suggestions`."
        )
        suggestions.append("- Estimate risk using `estimate_remediation_risk`.")

    # Fetch recent memory to refine suggestions (simple heuristic for now)
    # In future, this could use an LLM call with memory context

    return "\n".join(["### Suggested Next Steps", *suggestions])
