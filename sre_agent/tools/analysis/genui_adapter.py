"""Adapter for transforming ADK tool outputs into GenUI-compatible schemas."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def transform_trace(trace_data: dict[str, Any]) -> dict[str, Any]:
    """Transform Trace data for TraceWaterfall widget."""
    trace_id = trace_data.get("trace_id", "unknown")
    spans = []
    for span in trace_data.get("spans", []):
        # Ensure trace_id is present in each span for Flutter SpanInfo model
        span["trace_id"] = trace_id
        # Map labels to attributes
        span["attributes"] = span.pop("labels", {})
        # Derive status (Flutter model expects 'OK' or 'ERROR')
        status_code = span["attributes"].get("/http/status_code", "200")
        span["status"] = "ERROR" if str(status_code).startswith(("4", "5")) else "OK"
        spans.append(span)
    return {"trace_id": trace_id, "spans": spans}


def transform_metrics(metric_data: Any) -> dict[str, Any]:
    """Transform Metric data for MetricCorrelationChart widget."""
    # If it's a list from list_time_series, take the first one
    if isinstance(metric_data, list) and metric_data:
        series = metric_data[0]
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
        return {
            "metric_name": metric_data.get("metric_name", "Metric"),
            "points": metric_data.get("points", []),
            "labels": metric_data.get("labels", {}),
        }
    return {"metric_name": "Metric", "points": [], "labels": {}}


def transform_remediation(remediation_data: dict[str, Any]) -> dict[str, Any]:
    """Transform Remediation data for RemediationPlanWidget."""
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
