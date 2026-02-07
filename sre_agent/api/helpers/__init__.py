"""Tool event helpers for inline tool call display.

These functions create simple JSON events for tool calls and responses,
displayed inline in the chat. Visualization data goes through the
separate dashboard channel only.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, cast

from sre_agent.tools.analysis import genui_adapter

logger = logging.getLogger(__name__)

# Enable verbose tool event debugging with environment variable
A2UI_DEBUG = os.environ.get("A2UI_DEBUG", "").lower() in ("true", "1", "yes")


def _debug_log(message: str, data: Any = None) -> None:
    """Log tool event debug messages when A2UI_DEBUG is enabled."""
    if A2UI_DEBUG:
        if data is not None:
            if isinstance(data, (dict, list)):
                formatted = json.dumps(data, indent=2, default=str)
                logger.info(f"🔍 TOOL_EVENT: {message}\n{formatted}")
            else:
                logger.info(f"🔍 TOOL_EVENT: {message} -> {data}")
        else:
            logger.info(f"🔍 TOOL_EVENT: {message}")
    else:
        logger.info(f"📤 {message}")


# Widget mapping for tools that produce visualizations
TOOL_WIDGET_MAP = {
    "fetch_trace": "x-sre-trace-waterfall",
    "list_traces": "x-sre-trace-waterfall",
    "find_example_traces": "x-sre-trace-waterfall",
    "summarize_traces_in_sandbox": "x-sre-trace-waterfall",
    "analyze_critical_path": "x-sre-trace-waterfall",
    "analyze_trace_comprehensive": "x-sre-trace-waterfall",
    "list_time_series": "x-sre-metric-chart",
    "mcp_list_timeseries": "x-sre-metric-chart",
    "summarize_time_series_in_sandbox": "x-sre-metric-chart",
    "query_promql": "x-sre-metric-chart",
    "mcp_query_range": "x-sre-metric-chart",
    "list_log_entries": "x-sre-log-entries-viewer",
    "mcp_list_log_entries": "x-sre-log-entries-viewer",
    "summarize_log_entries_in_sandbox": "x-sre-log-entries-viewer",
    "extract_log_patterns": "x-sre-log-pattern-viewer",
    "compare_log_patterns": "x-sre-log-pattern-viewer",
    "analyze_log_anomalies": "x-sre-log-pattern-viewer",
    "run_log_pattern_analysis": "x-sre-log-pattern-viewer",
    "get_golden_signals": "x-sre-metrics-dashboard",
    "generate_remediation_suggestions": "x-sre-remediation-plan",
    "list_alerts": "x-sre-incident-timeline",
    "get_alert": "x-sre-incident-timeline",
    "run_council_investigation": "x-sre-council-synthesis",
    "query_data_agent": "x-sre-vega-chart",
}


def normalize_tool_args(raw_args: Any) -> dict[str, Any]:
    """Normalize tool arguments to a dictionary.

    Args:
        raw_args: Raw arguments from function call

    Returns:
        Normalized dictionary of arguments
    """
    if raw_args is None:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    if hasattr(raw_args, "model_dump"):
        return cast(dict[str, Any], raw_args.model_dump(mode="json"))
    if hasattr(raw_args, "dict"):
        return cast(dict[str, Any], raw_args.dict())
    if hasattr(raw_args, "to_dict"):
        return cast(dict[str, Any], raw_args.to_dict())
    try:
        # Check if it's already a JSON string
        if isinstance(raw_args, str):
            return cast(dict[str, Any], json.loads(raw_args))
    except Exception:
        pass
    return {"_raw_args": str(raw_args)}


def fully_normalize(obj: Any) -> Any:
    """Recursively normalize objects to JSON-serializable types.

    Handles Pydantic models, dicts, lists, and primitives.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, list):
        return [fully_normalize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: fully_normalize(v) for k, v in obj.items()}
    return obj


def create_tool_call_events(
    tool_name: str,
    args: dict[str, Any],
    pending_tool_calls: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    """Create a simple tool_call event for inline chat display.

    Returns a call_id and a list containing one JSON event string.
    The frontend renders this directly as an expandable tool call widget.
    """
    call_id = str(uuid.uuid4())

    _debug_log(
        "[TOOL_CALL] Creating tool call event",
        {"tool_name": tool_name, "call_id": call_id, "args_preview": str(args)[:200]},
    )

    # Register as pending for later matching with response
    pending_entry = {
        "call_id": call_id,
        "tool_name": tool_name,
        "args": args,
    }
    pending_tool_calls.append(pending_entry)

    event = {
        "type": "tool_call",
        "call_id": call_id,
        "tool_name": tool_name,
        "args": args,
    }

    return call_id, [json.dumps(event, default=str)]


def create_tool_response_events(
    tool_name: str,
    result: Any,
    pending_tool_calls: list[dict[str, Any]],
) -> tuple[str | None, list[str]]:
    """Create a simple tool_response event for inline chat display.

    Matches the response to a pending tool call by name (FIFO) and returns
    a call_id and a list containing one JSON event string.
    """
    call_id: str | None = None

    _debug_log(
        "[TOOL_RESPONSE] Processing tool response",
        {
            "tool_name": tool_name,
            "pending_count": len(pending_tool_calls),
            "pending_tools": [p["tool_name"] for p in pending_tool_calls],
        },
    )

    # Find matching pending call (FIFO)
    for i, pending in enumerate(pending_tool_calls):
        if pending["tool_name"] == tool_name:
            call_id = pending["call_id"]
            pending_tool_calls.pop(i)
            _debug_log(
                f"[TOOL_RESPONSE_MATCHED] Found pending call at index {i}",
                {"call_id": call_id},
            )
            break

    if not call_id:
        _debug_log(
            f"[TOOL_RESPONSE_NO_MATCH] No pending call for {tool_name}",
        )
        return None, []

    # Normalize result
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    elif hasattr(result, "dict"):
        result = result.dict()

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            pass

    # Determine status
    status = "completed"
    if isinstance(result, dict) and (result.get("error") or result.get("error_type")):
        status = "error"
        error_msg = result.get("error")
        error_type = result.get("error_type")
        if error_msg and error_type:
            result = f"{error_type}: {error_msg}"
        elif error_msg:
            result = str(error_msg)
        elif error_type:
            result = str(error_type)
    elif isinstance(result, dict) and "result" in result:
        result = result["result"]

    result = fully_normalize(result)

    event = {
        "type": "tool_response",
        "call_id": call_id,
        "tool_name": tool_name,
        "result": result,
        "status": status,
    }

    return call_id, [json.dumps(event, default=str)]


def create_widget_events(tool_name: str, result: Any) -> tuple[list[str], list[str]]:
    """Legacy stub - visualization data now goes through dashboard channel only.

    Returns empty lists. Kept for backward compatibility with imports.
    """
    return [], []


# Category mapping: widget type -> dashboard category string
WIDGET_CATEGORY_MAP: dict[str, str] = {
    "x-sre-trace-waterfall": "traces",
    "x-sre-metric-chart": "metrics",
    "x-sre-metrics-dashboard": "metrics",
    "x-sre-log-entries-viewer": "logs",
    "x-sre-log-pattern-viewer": "logs",
    "x-sre-incident-timeline": "alerts",
    "x-sre-remediation-plan": "remediation",
    "x-sre-council-synthesis": "council",
    "x-sre-vega-chart": "charts",
}


def create_dashboard_event(tool_name: str, result: Any) -> str | None:
    """Create a dashboard data event for the frontend investigation panel.

    This sends tool result data through a separate, simple channel that
    does not depend on the A2UI protocol. The frontend can consume this
    directly without any unwrapping logic.

    Returns:
        JSON string of dashboard event, or None if tool has no dashboard mapping.
    """
    widget_type = TOOL_WIDGET_MAP.get(tool_name)
    if not widget_type:
        return None

    category = WIDGET_CATEGORY_MAP.get(widget_type)
    if not category:
        return None

    # Handle failed tool execution
    if result is None:
        return None

    # Normalize result
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            pass

    result = fully_normalize(result)

    # Unwrap status/result wrapper
    if isinstance(result, dict):
        if "status" in result and "result" in result:
            if result.get("status") == "error":
                return None
            result = result["result"]
        elif len(result) == 1 and "result" in result:
            result = result["result"]

    # Transform data using the same adapter as widget events
    try:
        logger.info(
            f"📊 Dashboard event requested for tool: {tool_name}, widget: {widget_type}, result_type: {type(result)}"
        )
        if isinstance(result, dict):
            logger.info(f"📊 Result keys: {list(result.keys())}")

        widget_data: dict[str, Any] | list[Any] | None = None

        if widget_type == "x-sre-trace-waterfall":
            widget_data = genui_adapter.transform_trace(result)
        elif widget_type == "x-sre-metric-chart":
            widget_data = genui_adapter.transform_metrics(result)
        elif widget_type == "x-sre-metrics-dashboard":
            widget_data = genui_adapter.transform_metrics_dashboard(result)
        elif widget_type == "x-sre-log-entries-viewer":
            logger.info(f"📋 Transforming log entries for tool: {tool_name}")
            widget_data = genui_adapter.transform_log_entries(result)
            if widget_data:
                logger.info(
                    f"✅ Transformed {len(widget_data.get('entries', []))} log entries"
                )
            else:
                logger.warning(f"❌ Log transformation failed for tool: {tool_name}")
        elif widget_type == "x-sre-log-pattern-viewer":
            widget_data = genui_adapter.transform_log_patterns(result)
        elif widget_type == "x-sre-remediation-plan":
            widget_data = genui_adapter.transform_remediation(result)
        elif widget_type == "x-sre-incident-timeline":
            widget_data = genui_adapter.transform_alerts_to_timeline(result)
        elif widget_type == "x-sre-council-synthesis":
            # Council synthesis results pass through as-is (already structured)
            widget_data = result if isinstance(result, dict) else {"raw": result}
        elif widget_type == "x-sre-vega-chart":
            # CA Data Agent results: text answer + optional Vega-Lite charts
            widget_data = (
                result if isinstance(result, dict) else {"answer": str(result)}
            )

        if not widget_data:
            return None

        event = {
            "type": "dashboard",
            "category": category,
            "widget_type": widget_type,
            "tool_name": tool_name,
            "data": widget_data,
        }
        return json.dumps(event, default=str)

    except Exception as e:
        logger.error(f"Error creating dashboard event for {tool_name}: {e}")
        return None


def create_exploration_dashboard_events(result: Any) -> list[str]:
    """Create multiple dashboard events from an exploration result.

    The exploration tool returns data for every signal type at once.
    This function unpacks that into individual dashboard events so the
    frontend can populate all tabs simultaneously.

    Args:
        result: The raw tool result (may be a JSON string, dict, or wrapped
                in a status/result envelope).

    Returns:
        List of JSON-encoded dashboard event strings.
    """
    # Normalize
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            return []

    result = fully_normalize(result)

    # Unwrap status/result envelope
    if isinstance(result, dict):
        if "status" in result and "result" in result:
            if result.get("status") == "error":
                return []
            result = result["result"]
        elif len(result) == 1 and "result" in result:
            result = result["result"]

    if not isinstance(result, dict):
        return []

    # Signal key -> (widget_type, category, transform_fn)
    signal_map: list[tuple[str, str, str, Any]] = [
        (
            "alerts",
            "x-sre-incident-timeline",
            "alerts",
            genui_adapter.transform_alerts_to_timeline,
        ),
        (
            "logs",
            "x-sre-log-entries-viewer",
            "logs",
            genui_adapter.transform_log_entries,
        ),
        ("traces", "x-sre-trace-waterfall", "traces", None),  # pass-through list
        ("metrics", "x-sre-metric-chart", "metrics", genui_adapter.transform_metrics),
    ]

    events: list[str] = []
    for signal_key, widget_type, category, transform_fn in signal_map:
        signal_data = result.get(signal_key)
        if not signal_data:
            continue

        try:
            if transform_fn is not None:
                widget_data = transform_fn(signal_data)
                if not widget_data:
                    continue

                event = {
                    "type": "dashboard",
                    "category": category,
                    "widget_type": widget_type,
                    "tool_name": "explore_project_health",
                    "data": widget_data,
                }
                events.append(json.dumps(event, default=str))
            elif signal_key == "traces" and isinstance(signal_data, list):
                # Special handling for multiple traces: yield one event per trace
                for trace in signal_data:
                    widget_data = genui_adapter.transform_trace(trace)
                    if not widget_data or not widget_data.get("spans"):
                        continue

                    event = {
                        "type": "dashboard",
                        "category": category,
                        "widget_type": widget_type,
                        "tool_name": "explore_project_health",
                        "data": widget_data,
                    }
                    events.append(json.dumps(event, default=str))
            else:
                # Fallback for other signals (pass through)
                if not signal_data:
                    continue

                event = {
                    "type": "dashboard",
                    "category": category,
                    "widget_type": widget_type,
                    "tool_name": "explore_project_health",
                    "data": signal_data,
                }
                events.append(json.dumps(event, default=str))
        except Exception as e:
            logger.warning(
                "Exploration dashboard event failed for %s: %s",
                signal_key,
                e,
            )

    return events


# ---------------------------------------------------------------------------
# Trace deep-link utilities
# ---------------------------------------------------------------------------

_CLOUD_TRACE_URL_TEMPLATE = (
    "https://console.cloud.google.com/traces/list?tid={trace_id}&project={project_id}"
)


def build_cloud_trace_url(trace_id: str, project_id: str) -> str:
    """Build a Google Cloud Trace console deep-link URL.

    Args:
        trace_id: 32-character hex trace ID.
        project_id: GCP project ID.

    Returns:
        Full Cloud Trace console URL.
    """
    return _CLOUD_TRACE_URL_TEMPLATE.format(trace_id=trace_id, project_id=project_id)


# ---------------------------------------------------------------------------
# Agent Activity Event Helpers (Council Dashboard)
# ---------------------------------------------------------------------------


def create_agent_activity_event(
    investigation_id: str,
    agent_id: str,
    agent_name: str,
    agent_type: str,
    status: str,
    parent_id: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    llm_calls: list[dict[str, Any]] | None = None,
    output_summary: str = "",
    started_at: str = "",
    completed_at: str = "",
) -> str:
    """Create an agent_activity event for the council dashboard.

    This event tracks the activity of a single agent in the council hierarchy,
    including its tool calls, LLM calls, and relationships to other agents.

    Args:
        investigation_id: Unique ID for the overall investigation.
        agent_id: Unique ID for this agent instance.
        agent_name: Human-readable name of the agent.
        agent_type: Type of agent (root, orchestrator, panel, critic, synthesizer).
        status: Current status (pending, running, completed, error).
        parent_id: ID of the parent agent, or None for root.
        tool_calls: List of tool call records.
        llm_calls: List of LLM call records.
        output_summary: Brief summary of the agent's output.
        started_at: ISO timestamp when agent started.
        completed_at: ISO timestamp when agent completed.

    Returns:
        JSON string of the agent_activity event.
    """
    event = {
        "type": "agent_activity",
        "investigation_id": investigation_id,
        "agent": {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "parent_id": parent_id,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "tool_calls": tool_calls or [],
            "llm_calls": llm_calls or [],
            "output_summary": output_summary,
        },
    }
    return json.dumps(event, default=str)


def create_council_graph_event(
    investigation_id: str,
    mode: str,
    agents: list[dict[str, Any]],
    started_at: str,
    completed_at: str = "",
    debate_rounds: int = 1,
) -> str:
    """Create a council_graph event with the complete agent hierarchy.

    This event contains the full graph of all agents that participated
    in a council investigation, suitable for rendering as a visualization.

    Args:
        investigation_id: Unique ID for this investigation.
        mode: Investigation mode (fast, standard, debate).
        agents: List of all agent activity records.
        started_at: ISO timestamp when investigation started.
        completed_at: ISO timestamp when investigation completed.
        debate_rounds: Number of debate rounds completed.

    Returns:
        JSON string of the council_graph event.
    """
    # Calculate totals
    total_tool_calls = sum(len(a.get("tool_calls", [])) for a in agents)
    total_llm_calls = sum(len(a.get("llm_calls", [])) for a in agents)

    event = {
        "type": "council_graph",
        "investigation_id": investigation_id,
        "mode": mode,
        "started_at": started_at,
        "completed_at": completed_at,
        "debate_rounds": debate_rounds,
        "total_tool_calls": total_tool_calls,
        "total_llm_calls": total_llm_calls,
        "agents": agents,
    }
    return json.dumps(event, default=str)


def create_tool_call_record(
    call_id: str,
    tool_name: str,
    args: dict[str, Any] | None = None,
    result: Any = None,
    status: str = "completed",
    duration_ms: int = 0,
    timestamp: str = "",
) -> dict[str, Any]:
    """Create a tool call record for agent activity tracking.

    Args:
        call_id: Unique identifier for this tool call.
        tool_name: Name of the tool that was called.
        args: Arguments passed to the tool.
        result: Result from the tool (will be summarized).
        status: Status of the call (pending, completed, error).
        duration_ms: Time taken for the call in milliseconds.
        timestamp: ISO timestamp when the tool was called.

    Returns:
        Dictionary suitable for inclusion in an agent_activity event.
    """
    # Create args summary
    args_summary = ""
    if args:
        # Limit to first 200 chars of string representation
        args_str = str(args)
        args_summary = args_str[:200] + "..." if len(args_str) > 200 else args_str

    # Create result summary
    result_summary = ""
    if result is not None:
        if isinstance(result, dict):
            if "error" in result:
                result_summary = f"Error: {result['error']}"
            elif "result" in result:
                result_str = str(result["result"])
                result_summary = (
                    result_str[:200] + "..." if len(result_str) > 200 else result_str
                )
            else:
                result_str = str(result)
                result_summary = (
                    result_str[:200] + "..." if len(result_str) > 200 else result_str
                )
        else:
            result_str = str(result)
            result_summary = (
                result_str[:200] + "..." if len(result_str) > 200 else result_str
            )

    # Determine dashboard category from tool name
    widget_type = TOOL_WIDGET_MAP.get(tool_name)
    dashboard_category = WIDGET_CATEGORY_MAP.get(widget_type) if widget_type else None

    return {
        "call_id": call_id,
        "tool_name": tool_name,
        "args_summary": args_summary,
        "result_summary": result_summary,
        "status": status,
        "duration_ms": duration_ms,
        "timestamp": timestamp,
        "dashboard_category": dashboard_category,
    }


def get_current_trace_info(project_id: str | None = None) -> dict[str, Any] | None:
    """Extract the current OTel trace ID and build a trace_info event payload.

    Returns None if no valid trace context is available.

    Args:
        project_id: GCP project ID for deep-link construction.

    Returns:
        A dict suitable for JSON serialization as a ``trace_info`` event,
        or None when trace context is unavailable.
    """
    trace_id: str | None = None

    # 1. Try OpenTelemetry current span
    try:
        from opentelemetry import trace

        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            trace_id = trace.format_trace_id(span_context.trace_id)
    except Exception:
        pass

    # 2. Fallback to manual ContextVar
    if not trace_id:
        try:
            from sre_agent.auth import get_trace_id

            trace_id = get_trace_id()
        except Exception:
            pass

    if not trace_id:
        return None

    # Resolve project_id if not provided
    effective_project_id = project_id
    if not effective_project_id:
        effective_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GCP_PROJECT_ID"
        )

    payload: dict[str, Any] = {
        "type": "trace_info",
        "trace_id": trace_id,
    }

    if effective_project_id:
        payload["project_id"] = effective_project_id
        payload["trace_url"] = build_cloud_trace_url(trace_id, effective_project_id)

    return payload
