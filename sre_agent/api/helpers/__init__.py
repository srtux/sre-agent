"""Tool event helpers for A2UI protocol support.

These functions handle the creation of tool call/response events
for the frontend visualization, following the GenUI A2UI protocol.
"""

import json
import logging
import os
import uuid
from typing import Any, cast

from sre_agent.tools.analysis import genui_adapter

logger = logging.getLogger(__name__)

# Enable verbose A2UI debugging with environment variable
A2UI_DEBUG = os.environ.get("A2UI_DEBUG", "").lower() in ("true", "1", "yes")


def _debug_log(message: str, data: Any = None) -> None:
    """Log A2UI debug messages when A2UI_DEBUG is enabled.

    Always logs to logger.info, but adds extra detail when debugging is enabled.
    Set A2UI_DEBUG=true environment variable for verbose output.
    """
    if A2UI_DEBUG:
        if data is not None:
            # Pretty print JSON for readability
            if isinstance(data, (dict, list)):
                formatted = json.dumps(data, indent=2, default=str)
                logger.info(f"🔍 A2UI_DEBUG: {message}\n{formatted}")
            else:
                logger.info(f"🔍 A2UI_DEBUG: {message} -> {data}")
        else:
            logger.info(f"🔍 A2UI_DEBUG: {message}")
    else:
        # Standard logging (less verbose)
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


def create_tool_call_events(
    tool_name: str,
    args: dict[str, Any],
    pending_tool_calls: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    """Create A2UI events for a tool call (A2UI v0.8 protocol).

    The A2UI v0.8 specification requires:
    - Components must have an 'id' field and wrap the type in a 'component' object
    - beginRendering must include a 'root' field pointing to the root component ID
    """
    surface_id = str(uuid.uuid4())
    component_id = f"tool-log-{surface_id[:8]}"

    _debug_log(
        "[TOOL_CALL_START] Creating tool call event",
        {
            "tool_name": tool_name,
            "surface_id": surface_id,
            "component_id": component_id,
            "args_preview": str(args)[:200] if args else "{}",
        },
    )

    # Register as pending for later matching
    pending_entry = {
        "call_id": surface_id,
        "tool_name": tool_name,
        "args": args,
        "component_id": component_id,
    }
    pending_tool_calls.append(pending_entry)

    _debug_log(
        "[TOOL_CALL_PENDING] Registered pending call",
        {"pending_count": len(pending_tool_calls), "entry": pending_entry},
    )

    # Hybrid Initialization (Wrapper + Root Type)
    # We wrap the data in a key matching the component type to ensure GenUI matches it
    # regardless of whether it uses key-based or type-based matching.
    component_data = {
        "type": "x-sre-tool-log",
        "componentName": "x-sre-tool-log",
        "tool_name": tool_name,
        "toolName": tool_name,
        "args": args,
        "status": "running",
    }

    begin_event_obj = {
        "type": "a2ui",
        "message": {
            "beginRendering": {
                "surfaceId": surface_id,
                "root": component_id,
                "components": [
                    {
                        "id": component_id,
                        "type": "x-sre-tool-log",  # Root Level Type (v0.8+)
                        "component": {
                            "type": "x-sre-tool-log",  # Component Level Type
                            "x-sre-tool-log": component_data,  # Named Wrapper (Hybrid)
                        },
                    }
                ],
            },
        },
    }

    begin_event = json.dumps(begin_event_obj)

    _debug_log(
        "[TOOL_CALL_EVENT] Created beginRendering event",
        {
            "surface_id": surface_id,
            "component_id": component_id,
            "event_type": "beginRendering",
            "component_type": "x-sre-tool-log",
            "event_size_bytes": len(begin_event),
            "full_event": begin_event_obj,
        },
    )

    return surface_id, [begin_event]


def create_tool_response_events(
    tool_name: str,
    result: Any,
    pending_tool_calls: list[dict[str, Any]],
) -> tuple[str | None, list[str]]:
    """Create A2UI events for a tool response (A2UI v0.8 protocol)."""
    surface_id: str | None = None
    component_id: str | None = None
    args: dict[str, Any] = {}

    _debug_log(
        "[TOOL_RESPONSE_START] Processing tool response",
        {
            "tool_name": tool_name,
            "pending_count": len(pending_tool_calls),
            "pending_tools": [p["tool_name"] for p in pending_tool_calls],
            "result_type": type(result).__name__,
            "result_preview": str(result)[:200] if result else "None",
        },
    )

    # Find matching pending call (FIFO)
    for i, pending in enumerate(pending_tool_calls):
        if pending["tool_name"] == tool_name:
            surface_id = pending["call_id"]
            component_id = pending.get("component_id", f"tool-log-{surface_id[:8]}")
            args = pending["args"]
            pending_tool_calls.pop(i)
            _debug_log(
                f"[TOOL_RESPONSE_MATCHED] Found matching pending call at index {i}",
                {"surface_id": surface_id, "component_id": component_id},
            )
            break

    if not surface_id:
        _debug_log(
            f"[TOOL_RESPONSE_NO_MATCH] No matching pending call found for {tool_name}",
            {"searched_tools": [p["tool_name"] for p in pending_tool_calls]},
        )
        return None, []

    # Handle Pydantic models
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    elif hasattr(result, "dict"):
        result = result.dict()

    # Normalize result
    if isinstance(result, str):
        try:
            result = json.loads(result)
            _debug_log("[TOOL_RESPONSE_PARSED] Parsed JSON string result")
        except json.JSONDecodeError:
            _debug_log("[TOOL_RESPONSE_RAW] Keeping result as raw string")

    # Status determination
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
        _debug_log("[TOOL_RESPONSE_ERROR] Tool returned error", {"error": result})
    elif isinstance(result, dict) and "result" in result:
        # If it's a standard tool output dict, extract the result part
        result = result["result"]
        _debug_log("[TOOL_RESPONSE_UNWRAPPED] Extracted result from wrapper")

    # Create separate surfaceUpdate event (Hybrid Structure)
    # Ensure all nested fields in component_data are normalized to dicts/primitives
    def _normalize_for_json(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "dict"):
            return obj.dict()
        if isinstance(obj, list):
            return [_normalize_for_json(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _normalize_for_json(v) for k, v in obj.items()}
        return obj

    component_data = {
        "type": "x-sre-tool-log",
        "componentName": "x-sre-tool-log",
        "tool_name": tool_name,
        "toolName": tool_name,
        "args": _normalize_for_json(args),
        "result": _normalize_for_json(result),
        "status": status,
    }

    event_obj = {
        "type": "a2ui",
        "message": {
            "surfaceUpdate": {
                "surfaceId": surface_id,
                "components": [
                    {
                        "id": component_id,
                        "type": "x-sre-tool-log",  # Root Level Type (v0.8+)
                        "component": {
                            "type": "x-sre-tool-log",  # Component Level Type
                            "x-sre-tool-log": component_data,
                        },
                    }
                ],
            }
        },
    }

    # json.dumps defaults explicitly set to str to handle any remaining weird types (like UUID)
    event = json.dumps(event_obj, default=str)

    _debug_log(
        "[TOOL_RESPONSE_EVENT] Created surfaceUpdate event",
        {
            "surface_id": surface_id,
            "component_id": component_id,
            "status": status,
            "event_type": "surfaceUpdate",
            "event_size_bytes": len(event),
            "full_event": event_obj,
        },
    )

    return surface_id, [event]


def create_widget_events(tool_name: str, result: Any) -> tuple[list[str], list[str]]:
    """Create A2UI events for widget visualization (A2UI v0.8 protocol).

    Returns:
        tuple (list of event JSON strings, list of surface IDs created)
    """
    events: list[str] = []
    surface_ids: list[str] = []

    widget_type = TOOL_WIDGET_MAP.get(tool_name)

    _debug_log(
        "[WIDGET_START] Processing widget creation",
        {
            "tool_name": tool_name,
            "widget_type": widget_type,
            "has_mapping": widget_type is not None,
            "result_type": type(result).__name__,
        },
    )

    if not widget_type:
        _debug_log(f"[WIDGET_SKIP] No widget mapping for tool: {tool_name}")
        return events, surface_ids

    # Handle failed tool execution (None result)
    if result is None:
        result = {"error": "Tool execution failed (timeout or internal error)"}
        _debug_log("[WIDGET_NULL_RESULT] Using error placeholder for None result")

    # Normalize result (handles JSON strings and objects)
    original_result = result
    result = normalize_tool_args(result)

    _debug_log(
        "[WIDGET_NORMALIZED] Result after normalization",
        {
            "original_type": type(original_result).__name__,
            "result_keys": list(result.keys()) if isinstance(result, dict) else "N/A",
        },
    )

    # Normalize result wrapper if present
    if isinstance(result, dict):
        if "status" in result and "result" in result:
            result = result["result"]
            _debug_log("[WIDGET_UNWRAPPED] Extracted from status/result wrapper")
        elif len(result) == 1 and "result" in result:  # Handle simple {"result": [...]}
            result = result["result"]
            _debug_log("[WIDGET_UNWRAPPED] Extracted from simple result wrapper")

    # Transformation mapping check
    try:
        widget_data = None
        _debug_log(f"[WIDGET_TRANSFORM] Attempting transformation for {widget_type}")

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

        if widget_data:
            surface_id = str(uuid.uuid4())
            component_id = f"widget-{surface_id[:8]}"

            _debug_log(
                "[WIDGET_TRANSFORMED] Successfully transformed data",
                {
                    "widget_type": widget_type,
                    "surface_id": surface_id,
                    "component_id": component_id,
                    "data_keys": list(widget_data.keys())
                    if isinstance(widget_data, dict)
                    else "N/A",
                    "data_preview": str(widget_data)[:300],
                },
            )

            # Atomic initialization for widgets (Root Type)
            begin_event_obj = {
                "type": "a2ui",
                "message": {
                    "beginRendering": {
                        "surfaceId": surface_id,
                        "root": component_id,
                        "components": [
                            {
                                "id": component_id,
                                "type": widget_type,  # Root Level Type (v0.8+)
                                "component": {
                                    "type": widget_type,  # Component Level Type
                                    widget_type: widget_data,
                                },
                            }
                        ],
                    },
                },
            }

            update_event_obj = {
                "type": "a2ui",
                "message": {
                    "surfaceUpdate": {
                        "surfaceId": surface_id,
                        "components": [
                            {
                                "id": component_id,
                                "type": widget_type,  # Root Level Type
                                "component": {
                                    "type": widget_type,
                                    widget_type: widget_data,
                                },
                            }
                        ],
                    },
                },
            }

            begin_event = json.dumps(begin_event_obj)
            update_event = json.dumps(update_event_obj)

            _debug_log(
                "[WIDGET_EVENTS] Created widget events",
                {
                    "widget_type": widget_type,
                    "surface_id": surface_id,
                    "begin_event_size": len(begin_event),
                    "update_event_size": len(update_event),
                    "begin_event": begin_event_obj,
                    "update_event": update_event_obj,
                },
            )

            events.extend([begin_event, update_event])
            surface_ids.append(surface_id)
        else:
            _debug_log(
                f"[WIDGET_NO_DATA] Transformation returned None/empty for {widget_type}",
                {"result_preview": str(result)[:200]},
            )

    except Exception as e:
        _debug_log(
            "[WIDGET_ERROR] Error creating widget events",
            {"tool_name": tool_name, "widget_type": widget_type, "error": str(e)},
        )
        logger.error(
            f"❌ Error creating widget events for {tool_name}: {e}", exc_info=True
        )

    _debug_log(
        "[WIDGET_COMPLETE] Widget creation finished",
        {"events_count": len(events), "surface_ids": surface_ids},
    )

    return events, surface_ids


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
    result = normalize_tool_args(result)

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
