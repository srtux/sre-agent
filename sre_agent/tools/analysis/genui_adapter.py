"""Adapter for transforming ADK tool outputs into GenUI-compatible schemas."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# Constants for component names
COMPONENT_TRACE_WATERFALL = "x-sre-trace-waterfall"
COMPONENT_METRIC_CHART = "x-sre-metric-chart"
COMPONENT_REMEDIATION_PLAN = "x-sre-remediation-plan"
COMPONENT_LOG_PATTERN_VIEWER = "x-sre-log-pattern-viewer"
COMPONENT_LOG_ENTRIES_VIEWER = "x-sre-log-entries-viewer"
COMPONENT_TOOL_LOG = "x-sre-tool-log"
COMPONENT_AGENT_ACTIVITY = "x-sre-agent-activity"
COMPONENT_SERVICE_TOPOLOGY = "x-sre-service-topology"
COMPONENT_INCIDENT_TIMELINE = "x-sre-incident-timeline"
COMPONENT_METRICS_DASHBOARD = "x-sre-metrics-dashboard"
COMPONENT_AI_REASONING = "x-sre-ai-reasoning"
COMPONENT_AGENT_TRACE = "x-sre-agent-trace"
COMPONENT_AGENT_GRAPH = "x-sre-agent-graph"


def transform_trace(trace_data: Any) -> dict[str, Any]:
    """Transform Trace data for TraceWaterfall widget."""
    logger.info(f"📊 Transforming trace data, type: {type(trace_data)}")

    # Unwrap if wrapped in status/result (MCP format)
    if (
        isinstance(trace_data, dict)
        and "status" in trace_data
        and "result" in trace_data
    ):
        trace_data = trace_data["result"]

    # Handle error state
    if isinstance(trace_data, dict) and (
        "error" in trace_data or trace_data.get("status") == "error"
    ):
        err_msg = (
            trace_data.get("error") or trace_data.get("message") or "Unknown error"
        )
        logger.warning(f"❌ Trace transformation error: {err_msg}")
        return {
            "trace_id": trace_data.get("trace_id", "unknown")
            if isinstance(trace_data, dict)
            else "unknown",
            "spans": [],
            "error": err_msg,
        }

    # Handle sandbox results or single trace nested in a result dict
    if isinstance(trace_data, dict):
        if "top_items" in trace_data or "items" in trace_data:
            trace_data = trace_data.get("top_items") or trace_data.get("items")
            logger.info("📊 Extracted traces from sandbox result")
        elif "anomaly" in trace_data or "baseline" in trace_data:
            # find_example_traces returns both, pick anomaly for visualization
            trace_data = trace_data.get("anomaly") or trace_data.get("baseline")
            logger.info("📊 Selected anomaly/baseline trace from discovery result")

    # If it's a list (from list_traces), pick the first one for now
    # TODO: Add a TracesData model to support multiple traces in one tool call
    if isinstance(trace_data, list) and trace_data:
        logger.info(
            f"📊 Received list of {len(trace_data)} traces, picking the first one"
        )
        trace_data = trace_data[0]

    if not isinstance(trace_data, dict):
        return {"trace_id": "unknown", "spans": []}

    trace_id = trace_data.get("trace_id", "unknown")
    spans = []

    # If we have spans, use them
    raw_spans = trace_data.get("spans", [])
    if not raw_spans and "critical_path" in trace_data:
        # analyze_critical_path returns spans under critical_path.spans
        raw_spans = trace_data.get("critical_path", {}).get("spans", [])
        logger.info("📊 Extracted spans from critical_path result")

    if isinstance(raw_spans, list) and raw_spans:
        for span in raw_spans:
            if not isinstance(span, dict):
                continue

            # Normalize fields
            span_id = str(span.get("span_id", uuid.uuid4().hex[:16]))
            parent_id = span.get("parent_span_id")
            if parent_id is not None:
                parent_id = str(parent_id)

            spans.append(
                {
                    "span_id": span_id,
                    "trace_id": trace_id,
                    "name": span.get("name", "unnamed-span"),
                    "start_time": span.get("start_time"),
                    "end_time": span.get("end_time"),
                    "parent_span_id": parent_id,
                    "attributes": span.get("labels") or span.get("attributes", {}),
                    "status": "ERROR"
                    if str(
                        span.get("labels", {}).get("/http/status_code", "200")
                    ).startswith(("4", "5"))
                    else "OK",
                }
            )
    else:
        # Synthesize a root span for trace summaries (list_traces output)
        logger.info(f"📊 Synthesizing root span for summary trace {trace_id}")
        start_time = trace_data.get("start_time")
        duration_ms = trace_data.get("duration_ms") or 0

        if start_time and duration_ms >= 0:
            try:
                # Calculate end_time
                s_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
                from datetime import timedelta

                e_dt = s_dt + timedelta(milliseconds=float(duration_ms))
                end_time = e_dt.isoformat()

                spans.append(
                    {
                        "span_id": "root-" + trace_id[:8],
                        "trace_id": trace_id,
                        "name": trace_data.get("name", "Summary Trace"),
                        "start_time": start_time,
                        "end_time": end_time,
                        "parent_span_id": None,
                        "attributes": {
                            "/http/url": trace_data.get("url", ""),
                            "/http/status_code": str(trace_data.get("status", "200")),
                            "is_summary": "true",
                        },
                        "status": "ERROR"
                        if str(trace_data.get("status", "200")).startswith(("4", "5"))
                        else "OK",
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to synthesize span: {e}")

    # Add Trace Quality Analysis
    span_map = {s.get("span_id"): s for s in spans if s.get("span_id")}

    for span in spans:
        # Check specific trace quality issues
        issue_type = None
        issue_message = None

        # 1. Orphaned Span check
        parent_id = span.get("parent_span_id")
        if parent_id and parent_id not in span_map:
            issue_type = "orphaned_span"
            issue_message = f"Parent span {parent_id} not found in this trace"

        # 2. Clock Skew check (if not already orphaned)
        elif parent_id and parent_id in span_map:
            parent = span_map[parent_id]
            try:

                def parse_time(t: Any) -> datetime | None:
                    if not t:
                        return None
                    return datetime.fromisoformat(str(t).replace("Z", "+00:00"))

                s_start = parse_time(span.get("start_time"))
                s_end = parse_time(span.get("end_time"))
                p_start = parse_time(parent.get("start_time"))
                p_end = parse_time(parent.get("end_time"))

                if s_start and s_end and p_start and p_end:
                    if s_start < p_start or s_end > p_end:
                        issue_type = "clock_skew"
                        issue_message = "Child span outside parent timespan"
            except (ValueError, TypeError):
                pass

        # Inject attributes if issue detected
        if issue_type:
            if "attributes" not in span:
                span["attributes"] = {}
            span["attributes"]["/agent/quality/type"] = issue_type
            span["attributes"]["/agent/quality/issue"] = issue_message

    return {"trace_id": trace_id, "spans": spans}


def transform_metrics(metric_data: Any) -> dict[str, Any]:
    """Transform Metric data for MetricCorrelationChart widget."""
    logger.info(f"📊 Transforming metric data, type: {type(metric_data)}")

    # Unwrap if wrapped in status/result (MCP format)
    if (
        isinstance(metric_data, dict)
        and "status" in metric_data
        and "result" in metric_data
    ):
        metric_data = metric_data["result"]

    # Handle error state
    if isinstance(metric_data, dict) and (
        "error" in metric_data or metric_data.get("status") == "error"
    ):
        err_msg = (
            metric_data.get("error") or metric_data.get("message") or "Unknown error"
        )
        logger.warning(f"❌ Metric transformation error: {err_msg}")
        return {
            "metric_name": "Error",
            "points": [],
            "labels": {},
            "error": err_msg,
        }

    # Handle sandbox results (DataProcessingResult) or standard dict with top_items/items
    if isinstance(metric_data, dict):
        if "top_items" in metric_data or "items" in metric_data:
            metric_data = metric_data.get("top_items") or metric_data.get("items")
            logger.info("📊 Extracted metric series from sandbox result")

    # If it's a list from list_time_series or extracted from sandbox, take the first one
    if isinstance(metric_data, list) and metric_data:
        # Find first series with points
        series = None
        for s in metric_data:
            if isinstance(s, dict) and s.get("points"):
                series = s
                break

        if not series and metric_data:
            series = metric_data[0]

        if not isinstance(series, dict):
            return {"metric_name": "Metric", "points": [], "labels": {}}

        raw_points = series.get("points", [])
        points = []
        for p in raw_points:
            if not isinstance(p, dict):
                continue

            # Handle standard format: {"timestamp": "...", "value": ...}
            if "timestamp" in p and "value" in p:
                points.append(p)
            # Handle raw Cloud Monitoring API format: {"interval": {"endTime": "..."}, "value": {"doubleValue": ...}}
            elif "interval" in p and "value" in p:
                try:
                    ts = p["interval"].get("endTime")
                    v_dict = p["value"]
                    # Support different value types in Monitoring API
                    v = (
                        v_dict.get("doubleValue")
                        or v_dict.get("int64Value")
                        or v_dict.get(
                            "distributionValue"
                        )  # Not fully supported but avoid crash
                        or 0.0
                    )
                    if ts:
                        points.append(
                            {
                                "timestamp": ts,
                                "value": float(v) if not isinstance(v, dict) else 0.0,
                            }
                        )
                except (ValueError, TypeError, KeyError):
                    continue

        return {
            "metric_name": series.get("metric", {}).get("type", "Metric"),
            "points": points,
            "labels": {
                **series.get("metric", {}).get("labels", {}),
                **series.get("resource", {}).get("labels", {}),
            },
        }
    # If it's a dictionary (like from query_promql), handle it accordingly
    if isinstance(metric_data, dict):
        # Check for PromQL response format
        # {"status": "success", "data": {"resultType": "matrix", "result": [...]}}
        if (
            "status" in metric_data
            and "data" in metric_data
            and isinstance(metric_data["data"], dict)
            and "result" in metric_data["data"]
        ):
            results = metric_data["data"]["result"]
            if not results or not isinstance(results, list):
                return {"metric_name": "No Data", "points": [], "labels": {}}

            # Take the first series
            series = results[0]
            metric_info = series.get("metric", {})
            values = series.get("values", [])
            points = []

            for val in values:
                # PromQL values are [timestamp(float), value(string)]
                if isinstance(val, list) and len(val) >= 2:
                    try:
                        ts = float(val[0])
                        v = float(val[1])
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        points.append(
                            {
                                "timestamp": dt.isoformat(),
                                "value": v,
                                "is_anomaly": False,
                            }
                        )
                    except (ValueError, TypeError):
                        continue

            return {
                "metric_name": metric_info.get("__name__", "Metric"),
                "points": points,
                "labels": metric_info,
            }

        # Standard ADK format
        return {
            "metric_name": metric_data.get("metric_name", "Metric")
            if isinstance(metric_data, dict)
            else "Metric",
            "points": metric_data.get("points", [])
            if isinstance(metric_data, dict)
            else [],
            "labels": metric_data.get("labels", {})
            if isinstance(metric_data, dict)
            else {},
        }
    return {"metric_name": "Metric", "points": [], "labels": {}}


def transform_remediation(remediation_data: dict[str, Any]) -> dict[str, Any]:
    """Transform Remediation data for RemediationPlanWidget."""
    # Unwrap if wrapped in status/result (MCP format)
    if (
        isinstance(remediation_data, dict)
        and "status" in remediation_data
        and "result" in remediation_data
    ):
        remediation_data = remediation_data["result"]

    # Handle error state
    if isinstance(remediation_data, dict) and (
        "error" in remediation_data or remediation_data.get("status") == "error"
    ):
        return {
            "issue": "Error generating remediation plan",
            "risk": "unknown",
            "steps": [],
            "error": remediation_data.get("error")
            or remediation_data.get("message")
            or "Unknown error",
        }

    suggestions = remediation_data.get("suggestions", [])
    steps = []
    for s in suggestions:
        main_desc = f"{s.get('action')}: {s.get('description')}"
        sub_steps = s.get("steps", [])
        if not sub_steps:
            steps.append(
                {
                    "description": main_desc,
                    "command": s.get("action", "")
                    if "gcloud" in main_desc.lower()
                    else "",
                }
            )
        for step_txt in sub_steps:
            steps.append(
                {
                    "description": step_txt,
                    "command": s.get("action", "")
                    if "gcloud" in step_txt.lower()
                    else "",
                }
            )

    return {
        "issue": remediation_data.get("finding_summary", "Detected Issue"),
        "risk": remediation_data.get("recommended_first_action", {}).get(
            "risk", "medium"
        ),
        "steps": steps,
    }


def transform_agent_activity(activity_data: dict[str, Any]) -> dict[str, Any]:
    """Transform agent activity data for AgentActivityCanvas widget.

    Args:
        activity_data: Dictionary containing:
            - nodes: List of agent/tool nodes
            - current_phase: Current analysis phase
            - active_node_id: Currently active node
            - completed_steps: List of completed step IDs
            - message: Optional status message

    Returns:
        Dictionary formatted for the AgentActivityCanvas widget.
    """
    # Unwrap if wrapped in status/result (MCP format)
    if (
        isinstance(activity_data, dict)
        and "status" in activity_data
        and "result" in activity_data
    ):
        activity_data = activity_data["result"]

    nodes = []
    for node in activity_data.get("nodes", []):
        nodes.append(
            {
                "id": node.get("id", ""),
                "name": node.get("name", ""),
                "type": node.get(
                    "type", "tool"
                ),  # coordinator, sub_agent, tool, data_source
                "status": node.get("status", "idle"),  # idle, active, completed, error
                "connections": node.get("connections", []),
                "metadata": node.get("metadata"),
            }
        )

    return {
        "nodes": nodes,
        "current_phase": activity_data.get("current_phase", "Analyzing"),
        "active_node_id": activity_data.get("active_node_id"),
        "completed_steps": activity_data.get("completed_steps", []),
        "message": activity_data.get("message"),
    }


def transform_service_topology(topology_data: dict[str, Any]) -> dict[str, Any]:
    """Transform service topology data for ServiceTopologyCanvas widget.

    Args:
        topology_data: Dictionary containing:
            - services: List of service nodes
            - highlighted_service_id: Optional highlighted service
            - incident_source_id: Optional incident source service
            - affected_path: List of affected service IDs

    Returns:
        Dictionary formatted for the ServiceTopologyCanvas widget.
    """
    # Unwrap if wrapped in status/result (MCP format)
    if (
        isinstance(topology_data, dict)
        and "status" in topology_data
        and "result" in topology_data
    ):
        topology_data = topology_data["result"]

    services = []
    for svc in topology_data.get("services", []):
        connections = []
        for conn in svc.get("connections", []):
            connections.append(
                {
                    "target_id": conn.get("target_id", ""),
                    "traffic_percent": conn.get("traffic_percent", 0),
                    "latency_ms": conn.get("latency_ms", 0),
                    "error_rate": conn.get("error_rate", 0),
                }
            )

        services.append(
            {
                "id": svc.get("id", ""),
                "name": svc.get("name", ""),
                "type": svc.get(
                    "type", "backend"
                ),  # frontend, backend, database, cache, queue, external
                "health": svc.get(
                    "health", "unknown"
                ),  # healthy, degraded, unhealthy, unknown
                "latency_ms": svc.get("latency_ms", 0),
                "error_rate": svc.get("error_rate", 0),
                "requests_per_sec": svc.get("requests_per_sec", 0),
                "connections": connections,
            }
        )

    return {
        "services": services,
        "highlighted_service_id": topology_data.get("highlighted_service_id"),
        "incident_source_id": topology_data.get("incident_source_id"),
        "affected_path": topology_data.get("affected_path", []),
    }


def transform_incident_timeline(incident_data: dict[str, Any]) -> dict[str, Any]:
    """Transform incident timeline data for IncidentTimelineCanvas widget.

    Args:
        incident_data: Dictionary containing:
            - incident_id: Incident identifier
            - title: Incident title
            - start_time: Incident start time (ISO format)
            - end_time: Optional incident end time (ISO format)
            - status: ongoing, mitigated, resolved
            - events: List of timeline events
            - root_cause: Optional root cause description
            - ttd_seconds: Time to detect in seconds
            - ttm_seconds: Time to mitigate in seconds

    Returns:
        Dictionary formatted for the IncidentTimelineCanvas widget.
    """
    # Unwrap if wrapped in status/result (MCP format)
    if (
        isinstance(incident_data, dict)
        and "status" in incident_data
        and "result" in incident_data
    ):
        incident_data = incident_data["result"]

    events = []
    for event in incident_data.get("events", []):
        events.append(
            {
                "id": event.get("id", ""),
                "timestamp": event.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                "type": event.get(
                    "type", "info"
                ),  # alert, deployment, config_change, scaling, incident, recovery, agent_action
                "title": event.get("title", ""),
                "description": event.get("description"),
                "severity": event.get(
                    "severity", "info"
                ),  # critical, high, medium, low, info
                "metadata": event.get("metadata"),
                "is_correlated": event.get("is_correlated", False),
            }
        )

    return {
        "incident_id": incident_data.get("incident_id", ""),
        "title": incident_data.get("title", "Incident"),
        "start_time": incident_data.get(
            "start_time", datetime.now(timezone.utc).isoformat()
        ),
        "end_time": incident_data.get("end_time"),
        "status": incident_data.get("status", "ongoing"),
        "events": events,
        "root_cause": incident_data.get("root_cause"),
        "ttd_seconds": incident_data.get("ttd_seconds"),
        "ttm_seconds": incident_data.get("ttm_seconds"),
    }


def transform_alerts_to_timeline(alerts_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Transform list_alerts output for IncidentTimelineCanvas widget.

    Args:
        alerts_data: List of alert dictionaries from list_alerts tool.

    Returns:
        Dictionary formatted for the IncidentTimelineCanvas widget.
    """
    # Unwrap if in result format
    if (
        isinstance(alerts_data, dict)
        and "status" in alerts_data
        and "result" in alerts_data
    ):
        alerts_data = alerts_data["result"]

    # Handle error or empty
    if not isinstance(alerts_data, list):
        if isinstance(alerts_data, dict):
            # Probably a single alert from get_alert, wrap in a list
            alerts_data = [alerts_data]
        else:
            return {
                "title": "Alerts Analysis",
                "status": "unknown",
                "events": [],
                "error": "Invalid alerts data format",
            }

    events = []
    # If no alerts, return empty timeline
    if not alerts_data:
        return {
            "title": "No Active Alerts",
            "status": "resolved",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "events": [],
        }

    # Sort by open time
    try:
        sorted_alerts = sorted(
            alerts_data,
            key=lambda x: x.get("openTime", ""),
            reverse=True,  # Newest first
        )
    except Exception:
        sorted_alerts = alerts_data

    # Helper to map state to severity
    def map_severity(severity_str: str) -> str:
        s = severity_str.upper()
        if s == "CRITICAL":
            return "critical"
        if s in ("ERROR", "HIGH"):
            return "high"
        if s == "WARNING":
            return "medium"
        return "info"

    for alert in sorted_alerts:
        policy = alert.get("policy", {})
        resource = alert.get("resource", {})
        metric = alert.get("metric", {})

        events.append(
            {
                "id": alert.get("name", str(uuid.uuid4())),
                "timestamp": alert.get(
                    "openTime", datetime.now(timezone.utc).isoformat()
                ),
                "type": "alert",
                "title": policy.get("displayName", "Unknown Alert"),
                "description": (
                    f"State: {alert.get('state', 'UNKNOWN')}\n"
                    f"Resource: {resource.get('type')} ({resource.get('labels', {}).get('service_name', 'unknown')})\n"
                    f"Metric: {metric.get('type', 'unknown')}"
                ),
                "severity": map_severity(alert.get("severity", "info")),
                "is_correlated": True,
                "metadata": {
                    "alert_id": alert.get("name"),
                    "close_time": alert.get("closeTime"),
                    "url": alert.get("url"),
                    "state": alert.get("state", "UNKNOWN"),
                    "resource_type": resource.get("type", "unknown"),
                    "service_name": resource.get("labels", {}).get(
                        "service_name", "unknown"
                    ),
                    "metric_type": metric.get("type", "unknown"),
                },
            }
        )

    # Determine overall status based on most recent alert
    overall_status = "mitigated"
    if sorted_alerts:
        latest = sorted_alerts[0]
        if latest.get("state") == "OPEN":
            overall_status = "ongoing"
        elif latest.get("state") == "CLOSED":
            overall_status = "resolved"

    return {
        "incident_id": f"ALERTS-{datetime.now().strftime('%Y%m%d')}",
        "title": "Active Alerts Timeline",
        "start_time": (
            sorted_alerts[-1].get("openTime")
            if sorted_alerts
            else datetime.now(timezone.utc).isoformat()
        ),
        "status": overall_status,
        "events": events,
        "root_cause": "Aggregated view of active alerts from Cloud Monitoring",
    }


def transform_metrics_dashboard(dashboard_data: dict[str, Any]) -> dict[str, Any]:
    """Transform metrics dashboard data for MetricsDashboardCanvas widget.

    Args:
        dashboard_data: Dictionary containing:
            - title: Dashboard title
            - service_name: Optional service name
            - metrics: List of metric objects
            - last_updated: Optional last update time (ISO format)

    Returns:
        Dictionary formatted for the MetricsDashboardCanvas widget.
    """
    # Unwrap if wrapped in status/result (MCP format)
    if (
        isinstance(dashboard_data, dict)
        and "status" in dashboard_data
        and "result" in dashboard_data
    ):
        dashboard_data = dashboard_data["result"]

    metrics = []
    for metric in dashboard_data.get("metrics", []):
        history = []
        for point in metric.get("history", []):
            history.append(
                {
                    "timestamp": point.get(
                        "timestamp", datetime.now(timezone.utc).isoformat()
                    ),
                    "value": point.get("value", 0),
                }
            )

        metrics.append(
            {
                "id": metric.get("id", ""),
                "name": metric.get("name", ""),
                "unit": metric.get("unit", ""),
                "current_value": metric.get("current_value", 0),
                "previous_value": metric.get("previous_value"),
                "threshold": metric.get("threshold"),
                "history": history,
                "status": metric.get("status", "normal"),  # normal, warning, critical
                "anomaly_description": metric.get("anomaly_description"),
            }
        )

    return {
        "title": dashboard_data.get("title", "Metrics Dashboard"),
        "service_name": dashboard_data.get("service_name"),
        "metrics": metrics,
        "last_updated": dashboard_data.get("last_updated"),
    }


def transform_golden_signals(data: dict[str, Any]) -> dict[str, Any]:
    """Transform Golden Signals data for MetricsDashboardCanvas widget.

    Args:
        data: Dictionary from get_golden_signals tool.

    Returns:
        Dictionary formatted for the MetricsDashboardCanvas widget.
    """
    signals = data.get("signals", {})
    metrics = []

    # Map signals to the dashboard metric format
    # 1. Latency
    latency = signals.get("latency", {})
    metrics.append(
        {
            "id": "latency",
            "name": "Latency",
            "unit": "ms",
            "current_value": latency.get("value_ms", 0),
            "status": latency.get("status", "normal").lower(),
            "anomaly_description": latency.get("hint"),
        }
    )

    # 2. Traffic
    traffic = signals.get("traffic", {})
    metrics.append(
        {
            "id": "traffic",
            "name": "Traffic",
            "unit": "req/s",
            "current_value": traffic.get("requests_per_second", 0),
            "status": traffic.get("status", "normal").lower(),
        }
    )

    # 3. Errors
    errors = signals.get("errors", {})
    metrics.append(
        {
            "id": "errors",
            "name": "Errors",
            "unit": "%",
            "current_value": errors.get("error_rate_percent", 0),
            "status": errors.get("status", "normal").lower(),
        }
    )

    # 4. Saturation
    saturation = signals.get("saturation", {})
    metrics.append(
        {
            "id": "saturation",
            "name": "Saturation",
            "unit": "%",
            "current_value": saturation.get("cpu_utilization_avg_percent", 0),
            "status": saturation.get("status", "normal").lower(),
        }
    )

    return {
        "title": f"Golden Signals: {data.get('service_name', 'Service')}",
        "service_name": data.get("service_name"),
        "metrics": metrics,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def transform_ai_reasoning(reasoning_data: dict[str, Any]) -> dict[str, Any]:
    """Transform AI reasoning data for AIReasoningCanvas widget.

    Args:
        reasoning_data: Dictionary containing:
            - agent_name: Name of the agent
            - current_task: Current task description
            - steps: List of reasoning steps
            - evidence: List of evidence/data points
            - conclusion: Optional final conclusion
            - overall_confidence: Confidence score (0-1)
            - status: analyzing, reasoning, concluding, complete

    Returns:
        Dictionary formatted for the AIReasoningCanvas widget.
    """
    steps = []
    for step in reasoning_data.get("steps", []):
        steps.append(
            {
                "id": step.get("id", ""),
                "type": step.get(
                    "type", "observation"
                ),  # observation, analysis, hypothesis, conclusion, action
                "content": step.get("content", ""),
                "confidence": step.get("confidence", 0.0),
                "evidence_ids": step.get("evidence_ids", []),
                "outcome": step.get("outcome"),
                "is_active": step.get("is_active", False),
            }
        )

    evidence = []
    for ev in reasoning_data.get("evidence", []):
        evidence.append(
            {
                "id": ev.get("id", ""),
                "source": ev.get("source", ""),
                "type": ev.get("type", "log"),  # metric, log, trace, alert, config
                "summary": ev.get("summary", ""),
                "relevance": ev.get("relevance", 0.0),
                "data": ev.get("data"),
            }
        )

    return {
        "agent_name": reasoning_data.get("agent_name", "SRE Agent"),
        "current_task": reasoning_data.get("current_task", ""),
        "steps": steps,
        "evidence": evidence,
        "conclusion": reasoning_data.get("conclusion"),
        "overall_confidence": reasoning_data.get("overall_confidence", 0.0),
        "status": reasoning_data.get("status", "analyzing"),
    }


def create_demo_agent_activity() -> dict[str, Any]:
    """Create demo data for Agent Activity Canvas."""
    return transform_agent_activity(
        {
            "nodes": [
                {
                    "id": "coordinator",
                    "name": "Root Agent",
                    "type": "coordinator",
                    "status": "active",
                    "connections": ["trace-agent", "metrics-agent", "logs-agent"],
                },
                {
                    "id": "trace-agent",
                    "name": "Trace Analyzer",
                    "type": "sub_agent",
                    "status": "completed",
                    "connections": ["trace-client"],
                },
                {
                    "id": "metrics-agent",
                    "name": "Metrics Analyzer",
                    "type": "sub_agent",
                    "status": "active",
                    "connections": ["monitoring-client"],
                },
                {
                    "id": "logs-agent",
                    "name": "Log Analyzer",
                    "type": "sub_agent",
                    "status": "idle",
                    "connections": ["logging-client"],
                },
                {
                    "id": "trace-client",
                    "name": "Cloud Trace",
                    "type": "data_source",
                    "status": "completed",
                    "connections": [],
                },
                {
                    "id": "monitoring-client",
                    "name": "Cloud Monitoring",
                    "type": "data_source",
                    "status": "active",
                    "connections": [],
                },
                {
                    "id": "logging-client",
                    "name": "Cloud Logging",
                    "type": "data_source",
                    "status": "idle",
                    "connections": [],
                },
            ],
            "current_phase": "Analyzing Metrics",
            "active_node_id": "metrics-agent",
            "completed_steps": ["trace-agent", "trace-client"],
            "message": "Correlating metric anomalies with trace data...",
        }
    )


def create_demo_service_topology() -> dict[str, Any]:
    """Create demo data for Service Topology Canvas."""
    return transform_service_topology(
        {
            "services": [
                {
                    "id": "api-gateway",
                    "name": "API Gateway",
                    "type": "frontend",
                    "health": "healthy",
                    "latency_ms": 45,
                    "error_rate": 0.001,
                    "requests_per_sec": 1500,
                    "connections": [
                        {"target_id": "auth-service", "latency_ms": 12},
                        {"target_id": "order-service", "latency_ms": 35},
                    ],
                },
                {
                    "id": "auth-service",
                    "name": "Auth Service",
                    "type": "backend",
                    "health": "healthy",
                    "latency_ms": 25,
                    "error_rate": 0.0005,
                    "requests_per_sec": 800,
                    "connections": [{"target_id": "user-db", "latency_ms": 8}],
                },
                {
                    "id": "order-service",
                    "name": "Order Service",
                    "type": "backend",
                    "health": "degraded",
                    "latency_ms": 450,
                    "error_rate": 0.05,
                    "requests_per_sec": 600,
                    "connections": [
                        {"target_id": "order-db", "latency_ms": 380},
                        {"target_id": "cache", "latency_ms": 5},
                    ],
                },
                {
                    "id": "user-db",
                    "name": "User DB",
                    "type": "database",
                    "health": "healthy",
                    "latency_ms": 8,
                    "error_rate": 0,
                    "requests_per_sec": 500,
                    "connections": [],
                },
                {
                    "id": "order-db",
                    "name": "Order DB",
                    "type": "database",
                    "health": "unhealthy",
                    "latency_ms": 850,
                    "error_rate": 0.1,
                    "requests_per_sec": 300,
                    "connections": [],
                },
                {
                    "id": "cache",
                    "name": "Redis Cache",
                    "type": "cache",
                    "health": "healthy",
                    "latency_ms": 2,
                    "error_rate": 0,
                    "requests_per_sec": 2000,
                    "connections": [],
                },
            ],
            "incident_source_id": "order-db",
            "affected_path": ["api-gateway", "order-service", "order-db"],
        }
    )


def create_demo_incident_timeline() -> dict[str, Any]:
    """Create demo data for Incident Timeline Canvas."""
    from datetime import timedelta

    base_time = datetime.now(timezone.utc)
    return transform_incident_timeline(
        {
            "incident_id": "INC-2024-001",
            "title": "Order Service Latency Degradation",
            "start_time": (base_time - timedelta(hours=2)).isoformat(),
            "status": "mitigated",
            "events": [
                {
                    "id": "e1",
                    "timestamp": (base_time - timedelta(hours=2)).isoformat(),
                    "type": "alert",
                    "title": "High latency alert triggered",
                    "severity": "high",
                    "is_correlated": True,
                },
                {
                    "id": "e2",
                    "timestamp": (
                        base_time - timedelta(hours=2, minutes=-5)
                    ).isoformat(),
                    "type": "deployment",
                    "title": "v2.3.1 deployed to order-service",
                    "severity": "info",
                    "is_correlated": True,
                },
                {
                    "id": "e3",
                    "timestamp": (
                        base_time - timedelta(hours=1, minutes=15)
                    ).isoformat(),
                    "type": "agent_action",
                    "title": "SRE Agent started investigation",
                    "severity": "info",
                },
                {
                    "id": "e4",
                    "timestamp": (
                        base_time - timedelta(hours=1, minutes=30)
                    ).isoformat(),
                    "type": "config_change",
                    "title": "DB connection pool exhausted",
                    "severity": "critical",
                    "is_correlated": True,
                },
                {
                    "id": "e5",
                    "timestamp": (base_time - timedelta(hours=1)).isoformat(),
                    "type": "scaling",
                    "title": "Auto-scaled DB connections",
                    "severity": "medium",
                },
                {
                    "id": "e6",
                    "timestamp": (base_time - timedelta(minutes=30)).isoformat(),
                    "type": "recovery",
                    "title": "Latency returning to normal",
                    "severity": "low",
                },
            ],
            "root_cause": "Database connection pool limit reached after v2.3.1 deployment increased query complexity",
            "ttd_seconds": 300,
            "ttm_seconds": 5400,
        }
    )


def transform_log_entries(
    log_data: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Transform log entries data for LogEntriesViewer widget.

    Args:
        log_data: Dictionary containing:
            - entries: List of log entry objects from list_log_entries
            - filter: Optional filter string used
            - project_id: Optional project ID
            - next_page_token: Optional pagination token

    Returns:
        Dictionary formatted for the LogEntriesViewer widget.
    """
    # Unwrap if wrapped in status/result (MCP format)
    if isinstance(log_data, dict) and "status" in log_data and "result" in log_data:
        log_data = log_data["result"]

    # Handle error state
    if isinstance(log_data, dict) and (
        "error" in log_data or log_data.get("status") == "error"
    ):
        err_msg = log_data.get("error") or log_data.get("message") or "Unknown error"
        logger.warning(f"❌ Log transformation error: {err_msg}")
        return {
            "entries": [],
            "error": err_msg,
            "filter": log_data.get("filter"),
        }

    entries = []
    # Handle case where log_data is the raw entries list
    if isinstance(log_data, list):
        raw_entries = log_data
    elif isinstance(log_data, dict):
        # Regular list_log_entries result
        raw_entries = log_data.get("entries", [])

        # Handle sandbox results (DataProcessingResult)
        if not raw_entries:
            raw_entries = log_data.get("top_items") or log_data.get("items") or []

        # Handle case where result is a single log entry
        if not raw_entries and log_data.get("insert_id"):
            raw_entries = [log_data]
    else:
        raw_entries = []

    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue

        # Extract payload (can be text, JSON, or proto)
        payload = entry.get("payload")
        if payload is None:
            # Try different payload formats from Cloud Logging
            payload = (
                entry.get("textPayload")
                or entry.get("jsonPayload")
                or entry.get("protoPayload", {})
            )

        # Extract resource information
        resource = entry.get("resource", {})
        resource_type = resource.get("type", "unknown")
        resource_labels = resource.get("labels", {})

        # Extract trace correlation if present
        trace = entry.get("trace")
        trace_id = None
        if trace:
            # Extract trace ID from full resource name
            # Format: projects/{project}/traces/{trace_id}
            parts = trace.split("/")
            if len(parts) >= 4:
                trace_id = parts[-1]

        entries.append(
            {
                "insert_id": entry.get("insertId", entry.get("insert_id", "")),
                "timestamp": entry.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                "severity": entry.get("severity", "INFO"),
                "payload": payload,
                "resource_type": resource_type,
                "resource_labels": {str(k): str(v) for k, v in resource_labels.items()},
                "trace_id": trace_id,
                "span_id": entry.get("spanId") or entry.get("span_id"),
                "http_request": entry.get("httpRequest") or entry.get("http_request"),
            }
        )

    return {
        "entries": entries,
        "filter": log_data.get("filter") if isinstance(log_data, dict) else None,
        "project_id": log_data.get("project_id")
        if isinstance(log_data, dict)
        else None,
        "next_page_token": log_data.get("next_page_token")
        if isinstance(log_data, dict)
        else None,
    }


def create_demo_log_entries() -> dict[str, Any]:
    """Create demo data for Log Entries Viewer."""
    from datetime import timedelta

    base_time = datetime.now(timezone.utc)
    return transform_log_entries(
        {
            "entries": [
                {
                    "insertId": "log-001",
                    "timestamp": base_time.isoformat(),
                    "severity": "ERROR",
                    "payload": {
                        "message": "Connection pool exhausted",
                        "error_code": "POOL_EXHAUSTED",
                        "pool_size": 100,
                        "active_connections": 100,
                        "waiting_requests": 45,
                    },
                    "resource": {
                        "type": "k8s_container",
                        "labels": {
                            "cluster_name": "prod-cluster",
                            "namespace_name": "order-service",
                            "pod_name": "order-service-7d8f9c6b5-xk2p4",
                        },
                    },
                    "trace": "projects/my-project/traces/abc123def456",
                    "spanId": "span-789",
                },
                {
                    "insertId": "log-002",
                    "timestamp": (base_time - timedelta(seconds=5)).isoformat(),
                    "severity": "WARNING",
                    "payload": "High latency detected: 450ms > threshold 200ms",
                    "resource": {
                        "type": "k8s_container",
                        "labels": {
                            "cluster_name": "prod-cluster",
                            "namespace_name": "order-service",
                            "pod_name": "order-service-7d8f9c6b5-xk2p4",
                        },
                    },
                },
                {
                    "insertId": "log-003",
                    "timestamp": (base_time - timedelta(seconds=10)).isoformat(),
                    "severity": "INFO",
                    "payload": {
                        "message": "Request processed",
                        "request_id": "req-12345",
                        "method": "POST",
                        "path": "/api/orders",
                        "status": 200,
                        "duration_ms": 125,
                    },
                    "resource": {
                        "type": "k8s_container",
                        "labels": {
                            "cluster_name": "prod-cluster",
                            "namespace_name": "order-service",
                            "pod_name": "order-service-7d8f9c6b5-abc12",
                        },
                    },
                    "httpRequest": {
                        "requestMethod": "POST",
                        "status": 200,
                        "latency": "0.125s",
                    },
                },
                {
                    "insertId": "log-004",
                    "timestamp": (base_time - timedelta(seconds=15)).isoformat(),
                    "severity": "DEBUG",
                    "payload": "Cache miss for key: order:12345",
                    "resource": {
                        "type": "k8s_container",
                        "labels": {
                            "cluster_name": "prod-cluster",
                            "namespace_name": "order-service",
                            "pod_name": "order-service-7d8f9c6b5-abc12",
                        },
                    },
                },
                {
                    "insertId": "log-005",
                    "timestamp": (base_time - timedelta(seconds=20)).isoformat(),
                    "severity": "CRITICAL",
                    "payload": {
                        "message": "Database connection failed",
                        "error": "ECONNREFUSED",
                        "host": "order-db.internal",
                        "port": 5432,
                        "retry_count": 3,
                    },
                    "resource": {
                        "type": "k8s_container",
                        "labels": {
                            "cluster_name": "prod-cluster",
                            "namespace_name": "order-service",
                            "pod_name": "order-service-7d8f9c6b5-xk2p4",
                        },
                    },
                },
            ],
            "filter": 'severity>=WARNING AND resource.type="k8s_container"',
            "project_id": "my-gcp-project",
        }
    )


def transform_log_patterns(
    pattern_data: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Transform log pattern data for LogPatternViewer widget.

    Args:
        pattern_data: Data from extract_log_patterns or compare_log_patterns.

    Returns:
        List of log patterns formatted for the LogPatternViewer.
    """
    # Unwrap if wrapped
    if (
        isinstance(pattern_data, dict)
        and "status" in pattern_data
        and "result" in pattern_data
    ):
        pattern_data = pattern_data["result"]

    # Case 1: Comparison format (from compare_log_patterns or run_log_pattern_analysis)
    if isinstance(pattern_data, dict) and "anomalies" in pattern_data:
        anomalies = pattern_data["anomalies"]
        # Merge new and significantly increased patterns
        new_p = anomalies.get("new_patterns", [])
        inc_p = [
            x["pattern"]
            for x in anomalies.get("increased_patterns", [])
            if isinstance(x, dict) and "pattern" in x
        ]
        # Avoid duplicates just in case
        seen_ids = set()
        result = []
        for p in new_p + inc_p:
            pid = p.get("pattern_id")
            if pid not in seen_ids:
                result.append(p)
                seen_ids.add(pid)
        return {"patterns": result, "count": len(result)}

    # Case 2: Summary format (from extract_log_patterns)
    if isinstance(pattern_data, dict):
        patterns = (
            pattern_data.get("error_patterns")
            or pattern_data.get("top_patterns")
            or pattern_data.get("patterns")
            or []
        )
        return {"patterns": patterns, "count": len(patterns)}

    # Case 3: Raw list
    if isinstance(pattern_data, list):
        patterns = [p for p in pattern_data if isinstance(p, dict)]
        return {"patterns": patterns, "count": len(patterns)}

    return {"patterns": [], "count": 0}


def create_demo_log_patterns() -> list[dict[str, Any]]:
    """Create demo data for Log Pattern Viewer."""
    return [
        {
            "pattern_id": "p1",
            "template": "Connection to database <*> failed after <DNS_TIMEOUT>",
            "count": 145,
            "severity_counts": {"ERROR": 145},
            "sample_messages": ["Connection to database db-1 failed after 5000ms"],
        },
        {
            "pattern_id": "p2",
            "template": "User <ID> logged in from <IP>",
            "count": 5230,
            "severity_counts": {"INFO": 5230},
            "sample_messages": ["User 12345 logged in from 10.0.0.1"],
        },
        {
            "pattern_id": "p3",
            "template": "Request processed in <DURATION>",
            "count": 12450,
            "severity_counts": {"INFO": 12450},
            "sample_messages": ["Request processed in 125ms"],
        },
    ]


# =============================================================================
# Agent Trace / Graph Transforms
# =============================================================================


def transform_agent_trace(data: dict[str, Any]) -> dict[str, Any]:
    """Transform AgentInteractionGraph into a flattened timeline for the widget.

    Flattens the span tree into an ordered list with depth, suitable for
    the waterfall-style agent trace widget. Each node carries kind, operation,
    agent_name, tool_name, model, tokens, duration, and depth.

    Args:
        data: AgentInteractionGraph dict (or wrapped in status/result).

    Returns:
        Dict with trace metadata and flattened node list.
    """
    # Unwrap if wrapped in status/result (MCP format)
    if "status" in data and "result" in data:
        data = data["result"]

    if isinstance(data, dict) and ("error" in data or data.get("status") == "error"):
        return {
            "trace_id": data.get("trace_id", "unknown"),
            "nodes": [],
            "error": data.get("error") or data.get("message") or "Unknown error",
        }

    trace_id = data.get("trace_id", "unknown")
    root_agent = data.get("root_agent_name")
    root_spans = data.get("root_spans", [])

    # Compute the earliest start time for offset calculation
    min_start_iso: str | None = None

    def _find_min_start(spans: list[dict[str, Any]]) -> None:
        nonlocal min_start_iso
        for span in spans:
            start = span.get("start_time_iso", "")
            if start and (min_start_iso is None or start < min_start_iso):
                min_start_iso = start
            _find_min_start(span.get("children", []))

    _find_min_start(root_spans)

    # Flatten the tree with depth
    nodes: list[dict[str, Any]] = []

    def _flatten(span: dict[str, Any], depth: int) -> None:
        start_iso = span.get("start_time_iso", "")
        start_offset_ms = 0.0
        if min_start_iso and start_iso:
            try:
                from datetime import datetime

                s0 = datetime.fromisoformat(min_start_iso.replace("Z", "+00:00"))
                s1 = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                start_offset_ms = (s1 - s0).total_seconds() * 1000
            except (ValueError, AttributeError):
                pass

        nodes.append(
            {
                "span_id": span.get("span_id", ""),
                "parent_span_id": span.get("parent_span_id"),
                "name": span.get("name", ""),
                "kind": span.get("kind", "unknown"),
                "operation": span.get("operation", "unknown"),
                "agent_name": span.get("agent_name"),
                "tool_name": span.get("tool_name"),
                "model_used": span.get("model_used") or span.get("model_requested"),
                "input_tokens": span.get("input_tokens"),
                "output_tokens": span.get("output_tokens"),
                "duration_ms": span.get("duration_ms", 0),
                "start_offset_ms": start_offset_ms,
                "depth": depth,
                "has_error": span.get("status_code", 0) == 2,
                "status_code": span.get("status_code", 0),
            }
        )
        for child in span.get("children", []):
            _flatten(child, depth + 1)

    for root in root_spans:
        _flatten(root, 0)

    return {
        "trace_id": trace_id,
        "root_agent_name": root_agent,
        "nodes": nodes,
        "total_input_tokens": data.get("total_input_tokens", 0),
        "total_output_tokens": data.get("total_output_tokens", 0),
        "total_duration_ms": data.get("total_duration_ms", 0),
        "llm_call_count": data.get("total_llm_calls", 0),
        "tool_call_count": data.get("total_tool_executions", 0),
        "unique_agents": data.get("unique_agents", []),
        "unique_tools": data.get("unique_tools", []),
        "anti_patterns": [],
    }


def transform_agent_graph(data: dict[str, Any]) -> dict[str, Any]:
    """Transform AgentInteractionGraph into nodes + edges for the graph widget.

    Deduplicates agents, tools, and models into graph nodes, and extracts
    relationships from the span tree into directed edges.

    Args:
        data: AgentInteractionGraph dict (or wrapped in status/result).

    Returns:
        Dict with nodes and edges lists for the graph widget.
    """
    # Unwrap
    if "status" in data and "result" in data:
        data = data["result"]

    if isinstance(data, dict) and ("error" in data or data.get("status") == "error"):
        return {"nodes": [], "edges": [], "error": data.get("error")}

    root_spans = data.get("root_spans", [])
    root_agent = data.get("root_agent_name")

    # Collect unique entities and relationships
    node_map: dict[str, dict[str, Any]] = {}
    edge_map: dict[str, dict[str, Any]] = {}

    # Always add a "user" node
    node_map["user"] = {
        "id": "user",
        "label": "User",
        "type": "user",
        "total_tokens": None,
        "call_count": None,
        "has_error": False,
    }

    def _ensure_node(node_id: str, label: str, node_type: str) -> dict[str, Any]:
        if node_id not in node_map:
            node_map[node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,
                "total_tokens": 0,
                "call_count": 0,
                "has_error": False,
            }
        return node_map[node_id]

    def _add_edge(
        source: str,
        target: str,
        label: str,
        duration_ms: float = 0.0,
        tokens: int = 0,
        has_error: bool = False,
    ) -> None:
        key = f"{source}->{target}"
        if key not in edge_map:
            edge_map[key] = {
                "source_id": source,
                "target_id": target,
                "label": label,
                "call_count": 0,
                "avg_duration_ms": 0.0,
                "total_tokens": 0,
                "has_error": False,
                "_total_duration": 0.0,
            }
        edge = edge_map[key]
        edge["call_count"] += 1
        edge["_total_duration"] += duration_ms
        edge["avg_duration_ms"] = edge["_total_duration"] / edge["call_count"]
        edge["total_tokens"] += tokens
        if has_error:
            edge["has_error"] = True

    def _walk(span: dict[str, Any], parent_agent: str | None = None) -> None:
        kind = span.get("kind", "unknown")
        agent_name = span.get("agent_name")
        tool_name = span.get("tool_name")
        model = span.get("model_used") or span.get("model_requested")
        tokens = (span.get("input_tokens") or 0) + (span.get("output_tokens") or 0)
        has_error = span.get("status_code", 0) == 2
        duration = span.get("duration_ms", 0)

        if kind in ("agent_invocation", "sub_agent_delegation") and agent_name:
            node = _ensure_node(f"agent:{agent_name}", agent_name, "agent")
            node["total_tokens"] = (node["total_tokens"] or 0) + tokens
            node["call_count"] = (node["call_count"] or 0) + 1
            if has_error:
                node["has_error"] = True

            if parent_agent:
                _add_edge(
                    f"agent:{parent_agent}",
                    f"agent:{agent_name}",
                    "delegates_to",
                    duration,
                    tokens,
                    has_error,
                )
            elif span.get("parent_span_id") is None:
                # Root agent invoked by user
                _add_edge(
                    "user",
                    f"agent:{agent_name}",
                    "invokes",
                    duration,
                    tokens,
                    has_error,
                )

            parent_agent = agent_name

        elif kind == "tool_execution" and tool_name:
            node = _ensure_node(f"tool:{tool_name}", tool_name, "tool")
            node["call_count"] = (node["call_count"] or 0) + 1
            if has_error:
                node["has_error"] = True

            if parent_agent:
                _add_edge(
                    f"agent:{parent_agent}",
                    f"tool:{tool_name}",
                    "calls",
                    duration,
                    tokens,
                    has_error,
                )

        elif kind == "llm_call" and model:
            node = _ensure_node(f"model:{model}", model, "llm_model")
            node["total_tokens"] = (node["total_tokens"] or 0) + tokens
            node["call_count"] = (node["call_count"] or 0) + 1

            if parent_agent:
                _add_edge(
                    f"agent:{parent_agent}",
                    f"model:{model}",
                    "generates",
                    duration,
                    tokens,
                    has_error,
                )

        for child in span.get("children", []):
            _walk(child, parent_agent)

    for root in root_spans:
        _walk(root)

    # Clean up internal tracking fields from edges
    edges = []
    for edge in edge_map.values():
        edges.append(
            {
                "source_id": edge["source_id"],
                "target_id": edge["target_id"],
                "label": edge["label"],
                "call_count": edge["call_count"],
                "avg_duration_ms": round(edge["avg_duration_ms"], 2),
                "total_tokens": edge["total_tokens"],
                "has_error": edge["has_error"],
            }
        )

    return {
        "nodes": list(node_map.values()),
        "edges": edges,
        "root_agent_name": root_agent,
    }
