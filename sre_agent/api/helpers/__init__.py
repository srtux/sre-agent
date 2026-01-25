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
    "get_workload_health_summary": "x-sre-log-entries-viewer",
    "generate_remediation_suggestions": "x-sre-remediation-plan",
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
    events: list[str] = []

    # Register as pending for later matching
    pending_tool_calls.append(
        {
            "call_id": surface_id,
            "tool_name": tool_name,
            "args": args,
            "component_id": component_id,
        }
    )

    # 1. surfaceUpdate first (components must exist before beginRendering references them)
    logger.info(f"📤 Tool Call Surface Update: {tool_name} (surface_id={surface_id})")
    events.append(
        json.dumps(
            {
                "type": "a2ui",
                "message": {
                    "surfaceUpdate": {
                        "surfaceId": surface_id,
                        "components": [
                            {
                                "id": component_id,
                                "component": {
                                    "x-sre-tool-log": {
                                        "tool_name": tool_name,
                                        "args": args,
                                        "status": "running",
                                    }
                                },
                            }
                        ],
                    }
                },
            }
        )
    )

    # 2. beginRendering with root reference (tells frontend to start rendering)
    events.append(
        json.dumps(
            {
                "type": "a2ui",
                "message": {
                    "beginRendering": {
                        "surfaceId": surface_id,
                        "root": component_id,
                    }
                },
            }
        )
    )

    return surface_id, events


def create_tool_response_events(
    tool_name: str,
    result: Any,
    pending_tool_calls: list[dict[str, Any]],
) -> tuple[str | None, list[str]]:
    """Create A2UI events for a tool response (A2UI v0.8 protocol)."""
    events: list[str] = []
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
    if isinstance(result, dict) and ("error" in result or "error_type" in result):
        status = "error"
        if "error" in result and "error_type" in result:
            result = f"{result['error_type']}: {result['error']}"
        elif "error" in result:
            result = str(result["error"])
    elif isinstance(result, dict) and len(result) == 1 and "result" in result:
        result = result["result"]

    # surfaceUpdate (completed/error status) with A2UI v0.8 format
    logger.info(
        f"📤 Tool Response Surface Update: {tool_name} (surface_id={surface_id}, status={status})"
    )
    events.append(
        json.dumps(
            {
                "type": "a2ui",
                "message": {
                    "surfaceUpdate": {
                        "surfaceId": surface_id,
                        "components": [
                            {
                                "id": component_id,
                                "component": {
                                    "x-sre-tool-log": {
                                        "tool_name": tool_name,
                                        "args": args,
                                        "result": result,
                                        "status": status,
                                    }
                                },
                            }
                        ],
                    }
                },
            }
        )
    )

    return surface_id, events


def create_widget_events(tool_name: str, result: Any) -> list[str]:
    """Create A2UI events for widget visualization (A2UI v0.8 protocol)."""
    events: list[str] = []

    widget_type = TOOL_WIDGET_MAP.get(tool_name)
    if not widget_type:
        return events

    # Normalize result
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return events

    # Transform data based on widget type
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

        if widget_data:
            surface_id = str(uuid.uuid4())
            component_id = f"widget-{surface_id[:8]}"

            # 1. surfaceUpdate first (components must exist before beginRendering)
            logger.info(
                f"📤 Widget Surface Update: {widget_type} (surface_id={surface_id})"
            )
            events.append(
                json.dumps(
                    {
                        "type": "a2ui",
                        "message": {
                            "surfaceUpdate": {
                                "surfaceId": surface_id,
                                "components": [
                                    {
                                        "id": component_id,
                                        "component": {widget_type: widget_data},
                                    }
                                ],
                            }
                        },
                    }
                )
            )

            # 2. beginRendering with root reference
            events.append(
                json.dumps(
                    {
                        "type": "a2ui",
                        "message": {
                            "beginRendering": {
                                "surfaceId": surface_id,
                                "root": component_id,
                            }
                        },
                    }
                )
            )

    except Exception as e:
        logger.warning(f"Failed to create widget for {tool_name}: {e}")

    return events
