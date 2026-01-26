"""Tool event helpers for A2UI protocol support.

These functions handle the creation of tool call/response events
for the frontend visualization, following the GenUI A2UI protocol.
"""

import json
import logging
import uuid
from typing import Any, cast

from sre_agent.tools.analysis import genui_adapter

logger = logging.getLogger(__name__)

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

    # Register as pending for later matching
    pending_tool_calls.append(
        {
            "call_id": surface_id,
            "tool_name": tool_name,
            "args": args,
            "component_id": component_id,
        }
    )

    # Create separate events for beginRendering and surfaceUpdate for maximum compatibility
    logger.info(f"📤 Tool Call Events: {tool_name} (surface_id={surface_id})")

    # Atomic Initialization with Root-Level Type
    # This ensures the component is defined immediately with the correct type for matching.
    begin_event = json.dumps(
        {
            "type": "a2ui",
            "message": {
                "beginRendering": {
                    "surfaceId": surface_id,
                    "root": component_id,
                    "components": [
                        {
                            "id": component_id,
                            "component": {
                                "type": "x-sre-tool-log",  # Root-level type for matching
                                "x-sre-tool-log": {
                                    "type": "x-sre-tool-log",
                                    "componentName": "x-sre-tool-log",
                                    "tool_name": tool_name,
                                    "toolName": tool_name,
                                    "args": args,
                                    "status": "running",
                                },
                            },
                        }
                    ],
                },
            },
        }
    )

    # Backup update event (same structure)
    update_event = json.dumps(
        {
            "type": "a2ui",
            "message": {
                "surfaceUpdate": {
                    "surfaceId": surface_id,
                    "components": [
                        {
                            "id": component_id,
                            "component": {
                                "type": "x-sre-tool-log",
                                "x-sre-tool-log": {
                                    "type": "x-sre-tool-log",
                                    "componentName": "x-sre-tool-log",
                                    "tool_name": tool_name,
                                    "toolName": tool_name,
                                    "args": args,
                                    "status": "running",
                                },
                            },
                        }
                    ],
                },
            },
        }
    )

    return surface_id, [begin_event, update_event]


def create_tool_response_events(
    tool_name: str,
    result: Any,
    pending_tool_calls: list[dict[str, Any]],
) -> tuple[str | None, list[str]]:
    """Create A2UI events for a tool response (A2UI v0.8 protocol)."""
    surface_id: str | None = None
    component_id: str | None = None
    args: dict[str, Any] = {}

    # Find matching pending call (FIFO)
    for i, pending in enumerate(pending_tool_calls):
        if pending["tool_name"] == tool_name:
            surface_id = pending["call_id"]
            component_id = pending.get("component_id", f"tool-log-{surface_id[:8]}")
            args = pending["args"]
            pending_tool_calls.pop(i)
            break

    if not surface_id:
        return None, []

    # Normalize result
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            pass

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
    elif isinstance(result, dict) and "result" in result:
        # If it's a standard tool output dict, extract the result part
        result = result["result"]

    # Create separate surfaceUpdate event
    logger.info(
        f"📤 Tool Response Event: {tool_name} (surface_id={surface_id}, status={status})"
    )
    event = json.dumps(
        {
            "type": "a2ui",
            "message": {
                "surfaceUpdate": {
                    "surfaceId": surface_id,
                    "components": [
                        {
                            "id": component_id,
                            "component": {
                                "type": "x-sre-tool-log",
                                "x-sre-tool-log": {
                                    "type": "x-sre-tool-log",
                                    "componentName": "x-sre-tool-log",
                                    "tool_name": tool_name,
                                    "toolName": tool_name,
                                    "args": args,
                                    "result": result,
                                    "status": status,
                                },
                            },
                        }
                    ],
                }
            },
        }
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
    if not widget_type:
        return events, surface_ids

    # Handle failed tool execution (None result)
    if result is None:
        result = {"error": "Tool execution failed (timeout or internal error)"}

    # Normalize result (handles JSON strings and objects)
    result = normalize_tool_args(result)

    # Normalize result wrapper if present
    if isinstance(result, dict):
        if "status" in result and "result" in result:
            result = result["result"]
        elif len(result) == 1 and "result" in result:  # Handle simple {"result": [...]}
            result = result["result"]

    # Transformation mapping check
    try:
        widget_data = None
        if widget_type == "x-sre-trace-waterfall":
            widget_data = genui_adapter.transform_trace(result)
        elif widget_type == "x-sre-metric-chart":
            widget_data = genui_adapter.transform_metrics(result)
        elif widget_type == "x-sre-metrics-dashboard":
            widget_data = genui_adapter.transform_metrics_dashboard(result)
        elif widget_type == "x-sre-log-entries-viewer":
            widget_data = genui_adapter.transform_log_entries(result)
        elif widget_type == "x-sre-remediation-plan":
            widget_data = genui_adapter.transform_remediation(result)
        elif widget_type == "x-sre-incident-timeline":
            widget_data = genui_adapter.transform_alerts_to_timeline(result)

        if widget_data:
            surface_id = str(uuid.uuid4())
            component_id = f"widget-{surface_id[:8]}"

            # Split into separate events for compatibility
            logger.info(f"📤 Widget Events: {widget_type} (surface_id={surface_id})")

            # Atomic initialization for widgets (Root Type)
            begin_event = json.dumps(
                {
                    "type": "a2ui",
                    "message": {
                        "beginRendering": {
                            "surfaceId": surface_id,
                            "root": component_id,
                            "components": [
                                {
                                    "id": component_id,
                                    "component": {
                                        "type": widget_type,
                                        widget_type: widget_data,
                                    },
                                }
                            ],
                        },
                    },
                }
            )

            update_event = json.dumps(
                {
                    "type": "a2ui",
                    "message": {
                        "surfaceUpdate": {
                            "surfaceId": surface_id,
                            "components": [
                                {
                                    "id": component_id,
                                    "component": {
                                        "type": widget_type,
                                        widget_type: widget_data,
                                    },
                                }
                            ],
                        },
                    },
                }
            )

            logger.info(f"📊 Transformed data for {widget_type} (surface={surface_id})")
            events.extend([begin_event, update_event])
            surface_ids.append(surface_id)

    except Exception as e:
        logger.warning(f"Failed to create widget for {tool_name}: {e}")

    return events, surface_ids
