"""SRE Agent Router — 3-tier request routing for the agent orchestrator.

Routes incoming user queries to the appropriate handling tier:

1. **DIRECT**: Simple data retrieval (logs, metrics, traces, alerts)
   — calls individual tools directly without sub-agent overhead.
2. **SUB_AGENT**: Focused analysis (anomaly detection, pattern analysis, etc.)
   — delegates to a specialist sub-agent (trace_analyst, log_analyst, etc.).
3. **COUNCIL**: Complex multi-signal investigation (root cause analysis,
   incident investigation, etc.) — starts a council meeting with the
   appropriate mode (fast/standard/debate).

The router is exposed as an ``@adk_tool`` so the root agent can call it
as the first step of every user turn to decide the best handling strategy.
"""

import logging
from typing import Any

from sre_agent.council.intent_classifier import classify_routing
from sre_agent.council.schemas import RoutingDecision
from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)

# Human-readable descriptions for each routing tier
_TIER_DESCRIPTIONS: dict[RoutingDecision, str] = {
    RoutingDecision.GREETING: (
        "Greeting or conversational message — respond directly without "
        "calling any tools. Keep it brief, friendly, and mention your "
        "key capabilities. Use the GREETING_PROMPT personality."
    ),
    RoutingDecision.DIRECT: (
        "Simple data retrieval — call the suggested tools directly "
        "to fetch the requested data. No sub-agent delegation needed."
    ),
    RoutingDecision.SUB_AGENT: (
        "Analysis task — delegate to the suggested specialist sub-agent "
        "for focused single-signal analysis."
    ),
    RoutingDecision.COUNCIL: (
        "Complex investigation — start a council meeting with the "
        "recommended mode for multi-signal parallel analysis."
    ),
}


@adk_tool
async def route_request(
    query: str,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Route a user query to the appropriate handling tier.

    Classifies the query into one of three tiers and returns routing
    guidance that the agent should follow:

    - **direct**: Call the suggested tools to fetch raw data (logs, metrics,
      traces, or alerts). No sub-agent needed.
    - **sub_agent**: Delegate to the suggested specialist sub-agent for
      focused analysis of a single signal type.
    - **council**: Start a council investigation with the recommended mode
      (fast, standard, or debate) for complex multi-signal analysis.

    Call this tool FIRST for every user request to determine the optimal
    handling strategy before taking action.

    Args:
        query: The user's query or request to route.
        tool_context: ADK tool context.
    """
    try:
        result = classify_routing(query)

        response_data: dict[str, Any] = {
            "decision": result.decision.value,
            "description": _TIER_DESCRIPTIONS[result.decision],
            "signal_type": result.signal_type.value,
            "query": query,
        }

        # Add tier-specific guidance
        if result.decision == RoutingDecision.GREETING:
            response_data["guidance"] = (
                "This is a greeting or conversational message. "
                "Respond directly — do NOT call any tools. "
                "Be warm, concise, and lightly witty. "
                "Briefly mention your key capabilities "
                "(trace analysis, log investigation, metrics monitoring, "
                "alert triage, incident RCA). "
                "Keep the response under 4 sentences."
            )
        elif result.decision == RoutingDecision.DIRECT:
            response_data["suggested_tools"] = list(result.suggested_tools)
            response_data["guidance"] = (
                f"Call the {result.signal_type.value} tools directly: "
                f"{', '.join(result.suggested_tools)}. "
                "Do NOT delegate to sub-agents for this simple retrieval."
            )
        elif result.decision == RoutingDecision.SUB_AGENT:
            response_data["suggested_agent"] = result.suggested_agent
            response_data["guidance"] = (
                f"Delegate to the '{result.suggested_agent}' sub-agent "
                f"for {result.signal_type.value} analysis. "
                "The sub-agent has the specialized tools needed."
            )
        elif result.decision == RoutingDecision.COUNCIL:
            response_data["investigation_mode"] = result.investigation_mode.value
            response_data["guidance"] = (
                f"Start a council investigation with mode='{result.investigation_mode.value}'. "
                "Use run_council_investigation to launch parallel specialist panels."
            )

        logger.info(
            f"🚦 Routed query to {result.decision.value} tier "
            f"(signal={result.signal_type.value}): {query[:60]}..."
        )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=response_data,
            metadata={"router": "rule_based", "tier": result.decision.value},
        )

    except Exception as e:
        logger.error(f"Request routing failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=str(e),
            metadata={"router": "rule_based"},
        )
