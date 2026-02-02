"""Tool event helpers for inline tool call display.

These functions create simple JSON events for tool calls and responses,
displayed inline in the chat. Visualization data goes through the
separate dashboard channel only.
"""

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
    "analyze_critical_path": "x-sre-trace-waterfall",
    "analyze_trace_comprehensive": "x-sre-trace-waterfall",
    "list_time_series": "x-sre-metric-chart",
    "mcp_list_timeseries": "x-sre-metric-chart",
    "query_promql": "x-sre-metric-chart",
    "mcp_query_range": "x-sre-metric-chart",
    "list_log_entries": "x-sre-log-entries-viewer",
    "mcp_list_log_entries": "x-sre-log-entries-viewer",
    "extract_log_patterns": "x-sre-log-pattern-viewer",
    "compare_log_patterns": "x-sre-log-pattern-viewer",
    "analyze_log_anomalies": "x-sre-log-pattern-viewer",
    "run_log_pattern_analysis": "x-sre-log-pattern-viewer",
    "get_golden_signals": "x-sre-metrics-dashboard",
    "generate_remediation_suggestions": "x-sre-remediation-plan",
    "list_alerts": "x-sre-incident-timeline",
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
        widget_data: dict[str, Any] | list[Any] | None = None

        if widget_type == "x-sre-trace-waterfall":
            widget_data = genui_adapter.transform_trace(result)
        elif widget_type == "x-sre-metric-chart":
            widget_data = genui_adapter.transform_metrics(result)
        elif widget_type == "x-sre-metrics-dashboard":
            widget_data = genui_adapter.transform_metrics_dashboard(result)
        elif widget_type == "x-sre-log-entries-viewer":
            widget_data = genui_adapter.transform_log_entries(result)
        elif widget_type == "x-sre-log-pattern-viewer":
            widget_data = genui_adapter.transform_log_patterns(result)
        elif widget_type == "x-sre-remediation-plan":
            widget_data = genui_adapter.transform_remediation(result)
        elif widget_type == "x-sre-incident-timeline":
            widget_data = genui_adapter.transform_alerts_to_timeline(result)

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
