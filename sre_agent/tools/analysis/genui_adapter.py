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


def transform_trace(trace_data: dict[str, Any]) -> dict[str, Any]:
    """Transform Trace data for TraceWaterfall widget."""
    # Unwrap if wrapped in status/result (MCP format)
    if "status" in trace_data and "result" in trace_data:
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
            "trace_id": trace_data.get("trace_id", "unknown"),
            "spans": [],
            "error": err_msg,
        }

    trace_id = (
        trace_data.get("trace_id", "unknown")
        if isinstance(trace_data, dict)
        else "unknown"
    )
    spans = []
    raw_spans = trace_data.get("spans", []) if isinstance(trace_data, dict) else []
    for span in raw_spans:
        # Ensure it's a dict
        if not isinstance(span, dict):
            continue
        # Ensure trace_id is present in each span for Flutter SpanInfo model
        span["trace_id"] = trace_id
        # Map labels to attributes (Flutter model expects 'attributes')
        if "labels" in span:
            span["attributes"] = span.pop("labels", {})
        elif "attributes" not in span:
            span["attributes"] = {}

        # Derive status (Flutter model expects 'OK' or 'ERROR')
        status_code = span.get("attributes", {}).get("/http/status_code", "200")
        span["status"] = "ERROR" if str(status_code).startswith(("4", "5")) else "OK"
        spans.append(span)
    return {"trace_id": trace_id, "spans": spans}


def transform_metrics(metric_data: Any) -> dict[str, Any]:
    """Transform Metric data for MetricCorrelationChart widget."""
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

    # If it's a list from list_time_series, take the first one
    if isinstance(metric_data, list) and metric_data:
        series = metric_data[0]
        if not isinstance(series, dict):
            return {"metric_name": "Metric", "points": [], "labels": {}}
        return {
            "metric_name": series.get("metric", {}).get("type", "Metric"),
            "points": series.get("points", []),
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
        raw_entries = log_data.get("entries", [])
    else:
        raw_entries = []

    for entry in raw_entries:
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
