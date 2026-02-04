"""Factory functions for council specialist panel agents.

Each panel is a focused LlmAgent with:
- Domain-specific tools from the tool registry
- A structured output_key for writing findings to session state
- An output_schema for validated PanelFinding JSON
"""

from google.adk.agents import LlmAgent

from sre_agent.model_config import get_model_name

from .prompts import (
    ALERTS_PANEL_PROMPT,
    LOGS_PANEL_PROMPT,
    METRICS_PANEL_PROMPT,
    TRACE_PANEL_PROMPT,
)
from .schemas import PanelFinding
from .tool_registry import (
    ALERTS_PANEL_TOOLS,
    LOGS_PANEL_TOOLS,
    METRICS_PANEL_TOOLS,
    TRACE_PANEL_TOOLS,
)


def create_trace_panel() -> LlmAgent:
    """Create the Trace specialist panel agent.

    Analyzes distributed traces, latency, errors, structural anomalies,
    and resiliency anti-patterns. Writes findings to session state
    under the key 'trace_finding'.

    Returns:
        Configured LlmAgent for trace analysis.
    """
    return LlmAgent(
        name="trace_panel",
        model=get_model_name("fast"),
        description=(
            "Trace specialist panel. Analyzes distributed traces for "
            "latency bottlenecks, errors, and resiliency anti-patterns."
        ),
        instruction=TRACE_PANEL_PROMPT,
        tools=list(TRACE_PANEL_TOOLS),
        output_key="trace_finding",
        output_schema=PanelFinding,
    )


def create_metrics_panel() -> LlmAgent:
    """Create the Metrics specialist panel agent.

    Analyzes time-series metrics, SLO violations, anomalies,
    and correlates metric spikes with traces via exemplars.
    Writes findings to session state under 'metrics_finding'.

    Returns:
        Configured LlmAgent for metrics analysis.
    """
    return LlmAgent(
        name="metrics_panel",
        model=get_model_name("fast"),
        description=(
            "Metrics specialist panel. Analyzes time-series data, "
            "detects anomalies, and correlates metrics with traces."
        ),
        instruction=METRICS_PANEL_PROMPT,
        tools=list(METRICS_PANEL_TOOLS),
        output_key="metrics_finding",
        output_schema=PanelFinding,
    )


def create_logs_panel() -> LlmAgent:
    """Create the Logs specialist panel agent.

    Analyzes log patterns for anomalies, new error signatures,
    and emerging issues. Writes findings to session state under
    'logs_finding'.

    Returns:
        Configured LlmAgent for log analysis.
    """
    return LlmAgent(
        name="logs_panel",
        model=get_model_name("fast"),
        description=(
            "Logs specialist panel. Analyzes log patterns, "
            "error signatures, and emerging log anomalies."
        ),
        instruction=LOGS_PANEL_PROMPT,
        tools=list(LOGS_PANEL_TOOLS),
        output_key="logs_finding",
        output_schema=PanelFinding,
    )


def create_alerts_panel() -> LlmAgent:
    """Create the Alerts specialist panel agent.

    Analyzes active alerts, alert policies, and incident signals.
    Writes findings to session state under 'alerts_finding'.

    Returns:
        Configured LlmAgent for alert analysis.
    """
    return LlmAgent(
        name="alerts_panel",
        model=get_model_name("fast"),
        description=(
            "Alerts specialist panel. Analyzes active alerts, "
            "alert policies, and proposes remediation actions."
        ),
        instruction=ALERTS_PANEL_PROMPT,
        tools=list(ALERTS_PANEL_TOOLS),
        output_key="alerts_finding",
        output_schema=PanelFinding,
    )
