"""Factory functions for council specialist panel agents.

Each panel is a focused LlmAgent with:
- Domain-specific tools from the tool registry
- A structured output_key for writing findings to session state
- An output_schema for validated PanelFinding JSON
- An after_agent_callback that writes a completion marker to session state,
  enabling progressive UI updates as each panel finishes.
"""

import json
import logging
from typing import Any

from google.adk.agents import LlmAgent

from sre_agent.core.model_callbacks import after_model_callback, before_model_callback
from sre_agent.model_config import get_model_name

from .prompts import (
    ALERTS_PANEL_PROMPT,
    DATA_PANEL_PROMPT,
    LOGS_PANEL_PROMPT,
    METRICS_PANEL_PROMPT,
    TRACE_PANEL_PROMPT,
)
from .schemas import PanelFinding
from .state import (
    ALERTS_FINDING,
    DATA_FINDING,
    LOGS_FINDING,
    METRICS_FINDING,
    PANEL_COMPLETIONS,
    TRACE_FINDING,
)
from .tool_registry import (
    ALERTS_PANEL_TOOLS,
    DATA_PANEL_TOOLS,
    LOGS_PANEL_TOOLS,
    METRICS_PANEL_TOOLS,
    TRACE_PANEL_TOOLS,
)

logger = logging.getLogger(__name__)


def _make_panel_completion_callback(panel_name: str, finding_key: str) -> Any:
    """Return an ``after_agent_callback`` that records panel completion in state.

    When a panel agent finishes, this callback reads its structured finding
    from session state and writes a compact summary to ``_panel_completions``.
    Downstream consumers (e.g. the API dashboard channel) can poll this key
    to stream progressive updates to the UI as each panel completes.

    The callback never raises — any error is swallowed silently so a logging
    failure cannot abort the panel's result.

    Args:
        panel_name: Short identifier used as the dict key (e.g. ``"trace"``).
        finding_key: Session state key where the panel wrote its ``PanelFinding``.

    Returns:
        A sync ``after_agent_callback`` compatible with ADK ``LlmAgent``.
    """

    def panel_completion_callback(
        callback_context: Any,
    ) -> None:
        try:
            state = callback_context.state
            finding_raw = state.get(finding_key)
            if finding_raw is None:
                return None

            finding_data: dict[str, Any] = (
                json.loads(finding_raw) if isinstance(finding_raw, str) else finding_raw
            )

            # Write compact summary into the shared completions dict
            completions: dict[str, Any] = dict(state.get(PANEL_COMPLETIONS) or {})
            completions[panel_name] = {
                "severity": finding_data.get("severity", "info"),
                "confidence": finding_data.get("confidence", 0.0),
                "summary": (finding_data.get("summary") or "")[:300],
            }
            state[PANEL_COMPLETIONS] = completions

            logger.info(
                "Panel '%s' completed: severity=%s confidence=%.2f",
                panel_name,
                completions[panel_name]["severity"],
                completions[panel_name]["confidence"],
            )
        except Exception:
            # Never let a progress-tracking failure abort the panel result.
            logger.debug(
                "Panel completion callback failed for '%s'", panel_name, exc_info=True
            )
        return None

    return panel_completion_callback


def create_trace_panel() -> LlmAgent:
    """Create the Trace specialist panel agent.

    Analyzes distributed traces, latency, errors, structural anomalies,
    and resiliency anti-patterns. Writes findings to session state
    under the key ``TRACE_FINDING``.

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
        output_key=TRACE_FINDING,
        output_schema=PanelFinding,
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
        after_agent_callback=_make_panel_completion_callback("trace", TRACE_FINDING),
    )


def create_metrics_panel() -> LlmAgent:
    """Create the Metrics specialist panel agent.

    Analyzes time-series metrics, SLO violations, anomalies,
    and correlates metric spikes with traces via exemplars.
    Writes findings to session state under ``METRICS_FINDING``.

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
        output_key=METRICS_FINDING,
        output_schema=PanelFinding,
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
        after_agent_callback=_make_panel_completion_callback(
            "metrics", METRICS_FINDING
        ),
    )


def create_logs_panel() -> LlmAgent:
    """Create the Logs specialist panel agent.

    Analyzes log patterns for anomalies, new error signatures,
    and emerging issues. Writes findings to session state under
    ``LOGS_FINDING``.

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
        output_key=LOGS_FINDING,
        output_schema=PanelFinding,
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
        after_agent_callback=_make_panel_completion_callback("logs", LOGS_FINDING),
    )


def create_alerts_panel() -> LlmAgent:
    """Create the Alerts specialist panel agent.

    Analyzes active alerts, alert policies, and incident signals.
    Writes findings to session state under ``ALERTS_FINDING``.

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
        output_key=ALERTS_FINDING,
        output_schema=PanelFinding,
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
        after_agent_callback=_make_panel_completion_callback("alerts", ALERTS_FINDING),
    )


def create_data_panel() -> LlmAgent:
    """Create the Data specialist panel agent.

    Uses the Conversational Analytics Data Agent to run analytical
    queries against BigQuery telemetry tables (_AllSpans, _AllLogs).
    Writes findings to session state under ``DATA_FINDING``.

    Returns:
        Configured LlmAgent for BigQuery data analysis.
    """
    return LlmAgent(
        name="data_panel",
        model=get_model_name("fast"),
        description=(
            "Data specialist panel. Runs analytical queries against "
            "BigQuery telemetry tables using the CA Data Agent."
        ),
        instruction=DATA_PANEL_PROMPT,
        tools=list(DATA_PANEL_TOOLS),
        output_key=DATA_FINDING,
        output_schema=PanelFinding,
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
        after_agent_callback=_make_panel_completion_callback("data", DATA_FINDING),
    )
