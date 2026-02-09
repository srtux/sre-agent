"""Conversational Analytics (CA) Data Agent tool for BigQuery analysis.

This tool wraps the Google Cloud Conversational Analytics API to provide
natural-language querying of BigQuery telemetry tables (_AllSpans, _AllLogs).
The CA API can:
- Execute SQL queries against BQ tables and return tabular results
- Generate Vega-Lite chart specifications for data visualisation
- Support multi-turn analytical conversations

The tool is designed to be used as part of the council's data analysis panel.
When the CA API returns a chart, the Vega-Lite spec is included in the result
so the frontend can render it in the Charts dashboard tab.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool
from sre_agent.tools.mcp.gcp import get_project_id_with_fallback

logger = logging.getLogger(__name__)

# Environment variable for persistent CA agent resource name
CA_AGENT_ENV = "SRE_AGENT_CA_DATA_AGENT"

# Default CA agent ID used by the provisioning script
DEFAULT_CA_AGENT_ID = "ca-autosre"


def _get_ca_clients() -> tuple[Any, Any]:
    """Lazily import and return (DataAgentServiceClient, DataChatServiceClient).

    Raises ImportError if the SDK is not installed.
    """
    from google.cloud import geminidataanalytics

    agent_client = geminidataanalytics.DataAgentServiceClient()
    chat_client = geminidataanalytics.DataChatServiceClient()
    return agent_client, chat_client


def _build_agent_resource_name(project_id: str, agent_id: str) -> str:
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    return f"projects/{project_id}/locations/{location}/dataAgents/{agent_id}"


def _extract_vega_config(message: Any) -> dict[str, Any] | None:
    """Extract Vega-Lite config from a CA streaming response message.

    The CA API returns chart data in ``system_message.chart.result.vega_config``.
    We convert proto map/repeated types to plain dicts/lists.
    """
    try:
        import proto
        from google.protobuf.json_format import MessageToDict

        def _convert(v: Any) -> Any:
            if isinstance(v, proto.marshal.collections.maps.MapComposite):
                return {k: _convert(val) for k, val in v.items()}
            if isinstance(v, proto.marshal.collections.RepeatedComposite):
                return [_convert(el) for el in v]
            if isinstance(v, (int, float, str, bool)):
                return v
            return MessageToDict(v)

        sm = getattr(message, "system_message", None)
        if sm is None:
            return None
        chart = getattr(sm, "chart", None)
        if chart is None:
            return None
        result = getattr(chart, "result", None)
        if result is None:
            return None
        vega = getattr(result, "vega_config", None)
        if vega is None:
            return None
        return _convert(vega)  # type: ignore[no-any-return]
    except Exception:
        logger.debug("Could not extract vega config from CA response", exc_info=True)
        return None


def _extract_text(message: Any) -> str:
    """Extract text from a CA streaming response message."""
    sm = getattr(message, "system_message", None)
    if sm is None:
        return ""
    text_msg = getattr(sm, "text", None)
    if text_msg is None:
        return ""
    return getattr(text_msg, "text", "") or ""


@adk_tool
async def query_data_agent(
    question: str,
    project_id: str | None = None,
    agent_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Query a BigQuery dataset using the Conversational Analytics Data Agent.

    This tool sends a natural-language question to the CA Data Agent which
    analyses BigQuery tables containing telemetry data (_AllSpans, _AllLogs).
    It returns a text answer and, when applicable, a Vega-Lite chart spec
    that the frontend can render.

    Use this tool to ask analytical questions like:
    - "What are the top 10 slowest spans in the last hour?"
    - "Show me error rate by service as a bar chart"
    - "What log patterns have spiked in the last 30 minutes?"

    Args:
        question: Natural-language analytical question about the telemetry data.
        project_id: GCP project ID. Auto-detected if not provided.
        agent_id: CA Data Agent ID. Defaults to env var or 'ca-autosre'.
        tool_context: ADK tool context.

    Returns:
        BaseToolResponse with text answer and optional vega_lite_chart spec.
    """
    import asyncio

    pid = project_id or get_project_id_with_fallback()
    if not pid:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="No project ID detected. Set GOOGLE_CLOUD_PROJECT.",
        )

    # Resolve agent ID
    aid = agent_id or os.environ.get(CA_AGENT_ENV) or DEFAULT_CA_AGENT_ID

    try:
        _, chat_client = _get_ca_clients()
    except ImportError:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=(
                "google-cloud-geminidataanalytics SDK not installed. "
                "Run: pip install google-cloud-geminidataanalytics"
            ),
        )

    agent_name = _build_agent_resource_name(pid, aid)
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    parent = f"projects/{pid}/locations/{location}"

    try:
        from google.cloud import geminidataanalytics

        # Build the stateless chat request
        msg = geminidataanalytics.Message()
        msg.user_message = geminidataanalytics.UserMessage(text=question)

        data_agent_ctx = geminidataanalytics.DataAgentContext()
        data_agent_ctx.data_agent = agent_name

        request = geminidataanalytics.ChatRequest(
            parent=parent,
            messages=[msg],
            data_agent_context=data_agent_ctx,
        )

        # The CA API is synchronous/streaming; run in a thread to avoid
        # blocking the async event loop.
        def _stream_chat() -> tuple[str, list[dict[str, Any]]]:
            text_parts: list[str] = []
            charts: list[dict[str, Any]] = []
            stream = chat_client.chat(request=request, timeout=120)
            for reply in stream:
                t = _extract_text(reply)
                if t:
                    text_parts.append(t)
                vc = _extract_vega_config(reply)
                if vc:
                    charts.append(vc)
            return "\n".join(text_parts), charts

        loop = asyncio.get_event_loop()
        text_answer, vega_charts = await loop.run_in_executor(None, _stream_chat)

        result: dict[str, Any] = {
            "question": question,
            "answer": text_answer or "(no text response from CA agent)",
            "agent_id": aid,
            "project_id": pid,
        }
        if vega_charts:
            result["vega_lite_charts"] = vega_charts

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
        )

    except Exception as e:
        error_str = str(e)
        logger.error(f"CA Data Agent query failed: {error_str}", exc_info=True)

        # Provide actionable fallback guidance
        if "NOT_FOUND" in error_str or "404" in error_str:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=(
                    f"CA Data Agent '{aid}' not found in project '{pid}'. "
                    "Create it with: python deploy/setup_ca_agent.py "
                    f"--project-id {pid}. "
                    "FALLBACK: Use mcp_execute_sql for direct BigQuery analysis."
                ),
            )

        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"CA Data Agent query failed: {error_str}",
        )
