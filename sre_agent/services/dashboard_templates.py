"""Out-of-the-box (OOTB) dashboard templates for cloud services.

Provides pre-configured dashboard templates for GKE, Cloud Run, BigQuery,
and Vertex Agent Engine. Each template includes panels for metrics, logs,
and traces to give users an instant overview of service health.

Templates are provisioned into the local dashboard store and can be
customized after creation.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Panel helper factories
# ---------------------------------------------------------------------------


def _metric_panel(
    title: str,
    metric_type: str,
    *,
    description: str = "",
    resource_type: str | None = None,
    aggregation: str = "ALIGN_MEAN",
    group_by: list[str] | None = None,
    unit: str | None = None,
    panel_type: str = "time_series",
    grid_x: int = 0,
    grid_y: int = 0,
    grid_w: int = 12,
    grid_h: int = 4,
    thresholds: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a metric panel specification."""
    filter_parts = [f'metric.type="{metric_type}"']
    if resource_type:
        filter_parts.append(f'resource.type="{resource_type}"')
    filter_str = " AND ".join(filter_parts)

    query: dict[str, Any] = {
        "datasource": {"type": "cloud_monitoring"},
        "cloud_monitoring": {
            "filter_str": filter_str,
            "aggregation": aggregation,
        },
    }
    if group_by:
        query["cloud_monitoring"]["group_by_fields"] = group_by

    panel: dict[str, Any] = {
        "title": title,
        "type": panel_type,
        "description": description,
        "grid_position": {
            "x": grid_x,
            "y": grid_y,
            "width": grid_w,
            "height": grid_h,
        },
        "queries": [query],
    }
    if unit:
        panel["unit"] = unit
    if thresholds:
        panel["thresholds"] = thresholds
    return panel


def _log_panel(
    title: str,
    log_filter: str,
    *,
    description: str = "",
    severity_levels: list[str] | None = None,
    resource_type: str | None = None,
    grid_x: int = 0,
    grid_y: int = 0,
    grid_w: int = 24,
    grid_h: int = 4,
) -> dict[str, Any]:
    """Build a log panel specification."""
    query: dict[str, Any] = {
        "datasource": {"type": "loki"},
        "logs": {
            "filter_str": log_filter,
        },
    }
    if severity_levels:
        query["logs"]["severity_levels"] = severity_levels
    if resource_type:
        query["logs"]["resource_type"] = resource_type

    return {
        "title": title,
        "type": "logs",
        "description": description,
        "grid_position": {
            "x": grid_x,
            "y": grid_y,
            "width": grid_w,
            "height": grid_h,
        },
        "queries": [query],
    }


def _trace_panel(
    title: str,
    service_filter: str,
    *,
    description: str = "",
    grid_x: int = 0,
    grid_y: int = 0,
    grid_w: int = 24,
    grid_h: int = 4,
) -> dict[str, Any]:
    """Build a trace panel specification."""
    return {
        "title": title,
        "type": "traces",
        "description": description,
        "grid_position": {
            "x": grid_x,
            "y": grid_y,
            "width": grid_w,
            "height": grid_h,
        },
        "queries": [
            {
                "datasource": {"type": "tempo"},
                "logs": {
                    "filter_str": service_filter,
                },
            }
        ],
    }


def _text_panel(
    title: str,
    content: str,
    *,
    grid_x: int = 0,
    grid_y: int = 0,
    grid_w: int = 24,
    grid_h: int = 2,
) -> dict[str, Any]:
    """Build a text/markdown panel specification."""
    return {
        "title": title,
        "type": "text",
        "grid_position": {
            "x": grid_x,
            "y": grid_y,
            "width": grid_w,
            "height": grid_h,
        },
        "text_content": {"content": content, "mode": "markdown"},
    }


# ---------------------------------------------------------------------------
# OOTB Dashboard Templates
# ---------------------------------------------------------------------------


def _gke_dashboard_template() -> dict[str, Any]:
    """GKE cluster and workload overview dashboard."""
    return {
        "id": "ootb-gke",
        "display_name": "GKE Overview",
        "description": (
            "Google Kubernetes Engine cluster health dashboard with "
            "container metrics, pod logs, and distributed traces."
        ),
        "service": "gke",
        "labels": {"service": "gke", "type": "ootb"},
        "variables": [
            {
                "name": "cluster_name",
                "type": "query",
                "label": "Cluster",
                "query": "label_values(kubernetes.io/container/cpu/core_usage_time, cluster_name)",
            },
            {
                "name": "namespace",
                "type": "query",
                "label": "Namespace",
                "query": "label_values(kubernetes.io/container/cpu/core_usage_time, namespace_name)",
            },
        ],
        "panels": [
            # -- Header --
            _text_panel(
                "GKE Cluster Overview",
                "### Kubernetes Engine\nReal-time cluster health, "
                "workload metrics, pod logs, and distributed traces.",
                grid_w=24,
                grid_h=2,
            ),
            # -- Row 1: Container CPU & Memory --
            _metric_panel(
                "Container CPU Usage",
                "kubernetes.io/container/cpu/core_usage_time",
                description="CPU core-seconds consumed by containers",
                resource_type="k8s_container",
                aggregation="ALIGN_RATE",
                group_by=["resource.label.container_name"],
                unit="cores",
                grid_x=0,
                grid_y=2,
                grid_w=12,
                grid_h=4,
            ),
            _metric_panel(
                "Container Memory Usage",
                "kubernetes.io/container/memory/used_bytes",
                description="Memory used by containers",
                resource_type="k8s_container",
                group_by=["resource.label.container_name"],
                unit="bytes",
                grid_x=12,
                grid_y=2,
                grid_w=12,
                grid_h=4,
            ),
            # -- Row 2: Container Restarts & Pod Network --
            _metric_panel(
                "Container Restarts",
                "kubernetes.io/container/restart_count",
                description="Container restart count (spikes indicate CrashLoopBackOff)",
                resource_type="k8s_container",
                aggregation="ALIGN_DELTA",
                group_by=["resource.label.container_name"],
                grid_x=0,
                grid_y=6,
                grid_w=8,
                grid_h=4,
                thresholds=[
                    {"value": 5, "color": "yellow", "label": "Warning"},
                    {"value": 10, "color": "red", "label": "Critical"},
                ],
            ),
            _metric_panel(
                "Pod Network Received",
                "kubernetes.io/pod/network/received_bytes_count",
                description="Bytes received by pods",
                resource_type="k8s_pod",
                aggregation="ALIGN_RATE",
                group_by=["resource.label.pod_name"],
                unit="bytes/s",
                grid_x=8,
                grid_y=6,
                grid_w=8,
                grid_h=4,
            ),
            _metric_panel(
                "Pod Network Sent",
                "kubernetes.io/pod/network/sent_bytes_count",
                description="Bytes sent by pods",
                resource_type="k8s_pod",
                aggregation="ALIGN_RATE",
                group_by=["resource.label.pod_name"],
                unit="bytes/s",
                grid_x=16,
                grid_y=6,
                grid_w=8,
                grid_h=4,
            ),
            # -- Row 3: Node CPU & Memory --
            _metric_panel(
                "Node CPU Allocatable",
                "kubernetes.io/node/cpu/allocatable_cores",
                description="CPU cores available for scheduling on nodes",
                resource_type="k8s_node",
                group_by=["resource.label.node_name"],
                unit="cores",
                grid_x=0,
                grid_y=10,
                grid_w=12,
                grid_h=4,
            ),
            _metric_panel(
                "Node Memory Usage",
                "kubernetes.io/node/memory/used_bytes",
                description="Memory used on cluster nodes",
                resource_type="k8s_node",
                group_by=["resource.label.node_name"],
                unit="bytes",
                grid_x=12,
                grid_y=10,
                grid_w=12,
                grid_h=4,
            ),
            # -- Row 4: Volume Usage --
            _metric_panel(
                "Pod Volume Usage",
                "kubernetes.io/pod/volume/used_bytes",
                description="Persistent volume usage per pod",
                resource_type="k8s_pod",
                group_by=["resource.label.pod_name"],
                unit="bytes",
                grid_x=0,
                grid_y=14,
                grid_w=12,
                grid_h=4,
            ),
            # -- Row 5: Logs --
            _log_panel(
                "GKE Workload Logs",
                'resource.type="k8s_container"',
                description="Container stdout/stderr logs from all workloads",
                severity_levels=["WARNING", "ERROR", "CRITICAL"],
                resource_type="k8s_container",
                grid_x=0,
                grid_y=18,
                grid_w=24,
                grid_h=5,
            ),
            # -- Row 6: Traces --
            _trace_panel(
                "GKE Service Traces",
                '+resource.type:"k8s_container"',
                description="Distributed traces from GKE workloads",
                grid_x=0,
                grid_y=23,
                grid_w=24,
                grid_h=5,
            ),
        ],
    }


def _cloud_run_dashboard_template() -> dict[str, Any]:
    """Cloud Run service overview dashboard."""
    return {
        "id": "ootb-cloud-run",
        "display_name": "Cloud Run Overview",
        "description": (
            "Cloud Run service health dashboard with request metrics, "
            "container utilization, service logs, and request traces."
        ),
        "service": "cloud_run",
        "labels": {"service": "cloud_run", "type": "ootb"},
        "variables": [
            {
                "name": "service_name",
                "type": "query",
                "label": "Service",
                "query": "label_values(run.googleapis.com/request_count, service_name)",
            },
            {
                "name": "revision_name",
                "type": "query",
                "label": "Revision",
                "query": "label_values(run.googleapis.com/request_count, revision_name)",
            },
        ],
        "panels": [
            _text_panel(
                "Cloud Run Service Overview",
                "### Cloud Run\nReal-time service health including request rates, "
                "latencies, instance scaling, and error tracking.",
                grid_w=24,
                grid_h=2,
            ),
            # -- Row 1: Request Count & Latencies --
            _metric_panel(
                "Request Count",
                "run.googleapis.com/request_count",
                description="Total HTTP requests by response code",
                resource_type="cloud_run_revision",
                aggregation="ALIGN_RATE",
                group_by=["metric.label.response_code_class"],
                unit="req/s",
                grid_x=0,
                grid_y=2,
                grid_w=12,
                grid_h=4,
            ),
            _metric_panel(
                "Request Latency (p50/p95/p99)",
                "run.googleapis.com/request_latencies",
                description="Request latency distribution",
                resource_type="cloud_run_revision",
                aggregation="ALIGN_PERCENTILE_99",
                unit="ms",
                grid_x=12,
                grid_y=2,
                grid_w=12,
                grid_h=4,
                thresholds=[
                    {"value": 500, "color": "yellow", "label": "Slow"},
                    {"value": 2000, "color": "red", "label": "Very Slow"},
                ],
            ),
            # -- Row 2: CPU & Memory Utilization --
            _metric_panel(
                "CPU Utilization",
                "run.googleapis.com/container/cpu/utilizations",
                description="Container CPU utilization across revisions",
                resource_type="cloud_run_revision",
                group_by=["resource.label.revision_name"],
                unit="%",
                grid_x=0,
                grid_y=6,
                grid_w=12,
                grid_h=4,
                thresholds=[
                    {"value": 0.8, "color": "yellow", "label": "High"},
                    {"value": 0.95, "color": "red", "label": "Critical"},
                ],
            ),
            _metric_panel(
                "Memory Utilization",
                "run.googleapis.com/container/memory/utilizations",
                description="Container memory utilization across revisions",
                resource_type="cloud_run_revision",
                group_by=["resource.label.revision_name"],
                unit="%",
                grid_x=12,
                grid_y=6,
                grid_w=12,
                grid_h=4,
                thresholds=[
                    {"value": 0.8, "color": "yellow", "label": "High"},
                    {"value": 0.95, "color": "red", "label": "Critical"},
                ],
            ),
            # -- Row 3: Instance Count & Startup Latency --
            _metric_panel(
                "Instance Count",
                "run.googleapis.com/container/instance_count",
                description="Active container instances (autoscaling indicator)",
                resource_type="cloud_run_revision",
                group_by=["resource.label.revision_name"],
                grid_x=0,
                grid_y=10,
                grid_w=8,
                grid_h=4,
            ),
            _metric_panel(
                "Startup Latency",
                "run.googleapis.com/container/startup_latencies",
                description="Cold start latency distribution",
                resource_type="cloud_run_revision",
                aggregation="ALIGN_PERCENTILE_99",
                unit="ms",
                grid_x=8,
                grid_y=10,
                grid_w=8,
                grid_h=4,
            ),
            _metric_panel(
                "Billable Instance Time",
                "run.googleapis.com/container/billable_instance_time",
                description="Billable container instance time in seconds",
                resource_type="cloud_run_revision",
                aggregation="ALIGN_RATE",
                unit="s",
                grid_x=16,
                grid_y=10,
                grid_w=8,
                grid_h=4,
            ),
            # -- Row 4: Logs --
            _log_panel(
                "Cloud Run Service Logs",
                'resource.type="cloud_run_revision"',
                description="Application logs from Cloud Run services",
                severity_levels=["WARNING", "ERROR", "CRITICAL"],
                resource_type="cloud_run_revision",
                grid_x=0,
                grid_y=14,
                grid_w=24,
                grid_h=5,
            ),
            # -- Row 5: Traces --
            _trace_panel(
                "Cloud Run Request Traces",
                '+resource.type:"cloud_run_revision"',
                description="Distributed traces for Cloud Run HTTP requests",
                grid_x=0,
                grid_y=19,
                grid_w=24,
                grid_h=5,
            ),
        ],
    }


def _bigquery_dashboard_template() -> dict[str, Any]:
    """BigQuery analytics overview dashboard."""
    return {
        "id": "ootb-bigquery",
        "display_name": "BigQuery Overview",
        "description": (
            "BigQuery service dashboard with query performance, "
            "slot utilization, storage metrics, and audit logs."
        ),
        "service": "bigquery",
        "labels": {"service": "bigquery", "type": "ootb"},
        "variables": [
            {
                "name": "project_id",
                "type": "textbox",
                "label": "Project ID",
            },
        ],
        "panels": [
            _text_panel(
                "BigQuery Overview",
                "### BigQuery\nQuery performance, slot utilization, "
                "storage growth, and job monitoring.",
                grid_w=24,
                grid_h=2,
            ),
            # -- Row 1: Query Count & Execution Time --
            _metric_panel(
                "Query Count",
                "bigquery.googleapis.com/query/count",
                description="Number of in-flight queries",
                resource_type="bigquery_project",
                aggregation="ALIGN_MEAN",
                grid_x=0,
                grid_y=2,
                grid_w=8,
                grid_h=4,
            ),
            _metric_panel(
                "Query Execution Time",
                "bigquery.googleapis.com/query/execution_times",
                description="Distribution of query execution times",
                resource_type="bigquery_project",
                aggregation="ALIGN_PERCENTILE_99",
                unit="s",
                grid_x=8,
                grid_y=2,
                grid_w=8,
                grid_h=4,
                thresholds=[
                    {"value": 30, "color": "yellow", "label": "Slow"},
                    {"value": 120, "color": "red", "label": "Very Slow"},
                ],
            ),
            _metric_panel(
                "Job Error Count",
                "bigquery.googleapis.com/job/num_in_flight",
                description="Number of in-flight BigQuery jobs",
                resource_type="bigquery_project",
                grid_x=16,
                grid_y=2,
                grid_w=8,
                grid_h=4,
            ),
            # -- Row 2: Slots & Scanned Bytes --
            _metric_panel(
                "Slot Utilization",
                "bigquery.googleapis.com/slots/total_available",
                description="Total slots available in the project",
                resource_type="bigquery_project",
                grid_x=0,
                grid_y=6,
                grid_w=8,
                grid_h=4,
            ),
            _metric_panel(
                "Slots Allocated",
                "bigquery.googleapis.com/slots/allocated",
                description="Slots currently allocated for query execution",
                resource_type="bigquery_project",
                grid_x=8,
                grid_y=6,
                grid_w=8,
                grid_h=4,
            ),
            _metric_panel(
                "Bytes Scanned",
                "bigquery.googleapis.com/query/scanned_bytes",
                description="Total bytes scanned by queries (cost driver)",
                resource_type="bigquery_project",
                aggregation="ALIGN_SUM",
                unit="bytes",
                grid_x=16,
                grid_y=6,
                grid_w=8,
                grid_h=4,
            ),
            # -- Row 3: Storage --
            _metric_panel(
                "Stored Bytes",
                "bigquery.googleapis.com/storage/stored_bytes",
                description="Total bytes stored in BigQuery tables",
                resource_type="bigquery_dataset",
                unit="bytes",
                grid_x=0,
                grid_y=10,
                grid_w=12,
                grid_h=4,
            ),
            _metric_panel(
                "Uploaded Bytes",
                "bigquery.googleapis.com/storage/uploaded_bytes",
                description="Bytes uploaded to BigQuery tables",
                resource_type="bigquery_dataset",
                aggregation="ALIGN_RATE",
                unit="bytes/s",
                grid_x=12,
                grid_y=10,
                grid_w=12,
                grid_h=4,
            ),
            # -- Row 4: Logs --
            _log_panel(
                "BigQuery Audit Logs",
                'resource.type="bigquery_resource" OR '
                'protoPayload.serviceName="bigquery.googleapis.com"',
                description="BigQuery data access and admin audit logs",
                severity_levels=["WARNING", "ERROR", "CRITICAL"],
                resource_type="bigquery_resource",
                grid_x=0,
                grid_y=14,
                grid_w=24,
                grid_h=5,
            ),
            # -- Row 5: Traces --
            _trace_panel(
                "BigQuery Job Traces",
                '+labels:"bigquery"',
                description="Traces for BigQuery job execution",
                grid_x=0,
                grid_y=19,
                grid_w=24,
                grid_h=5,
            ),
        ],
    }


def _vertex_agent_engine_dashboard_template() -> dict[str, Any]:
    """Vertex AI Agent Engine (Reasoning Engine) overview dashboard."""
    return {
        "id": "ootb-vertex-agent-engine",
        "display_name": "Vertex Agent Engine Overview",
        "description": (
            "Vertex AI Agent Engine (Reasoning Engine) dashboard with "
            "request metrics, resource utilization, agent logs, and traces."
        ),
        "service": "vertex_agent_engine",
        "labels": {"service": "vertex_agent_engine", "type": "ootb"},
        "variables": [
            {
                "name": "reasoning_engine_id",
                "type": "textbox",
                "label": "Reasoning Engine ID",
            },
        ],
        "panels": [
            _text_panel(
                "Vertex Agent Engine Overview",
                "### Vertex AI Agent Engine (Reasoning Engine)\n"
                "Request throughput, latency, resource allocation, "
                "and agent execution traces.",
                grid_w=24,
                grid_h=2,
            ),
            # -- Row 1: Request Count & Latencies --
            _metric_panel(
                "Request Count",
                "aiplatform.googleapis.com/ReasoningEngine/request_count",
                description="Total requests to Reasoning Engine",
                resource_type="aiplatform.googleapis.com/ReasoningEngine",
                aggregation="ALIGN_RATE",
                unit="req/s",
                grid_x=0,
                grid_y=2,
                grid_w=12,
                grid_h=4,
            ),
            _metric_panel(
                "Request Latency",
                "aiplatform.googleapis.com/ReasoningEngine/request_latencies",
                description="Request latency distribution for agent invocations",
                resource_type="aiplatform.googleapis.com/ReasoningEngine",
                aggregation="ALIGN_PERCENTILE_99",
                unit="ms",
                grid_x=12,
                grid_y=2,
                grid_w=12,
                grid_h=4,
                thresholds=[
                    {"value": 5000, "color": "yellow", "label": "Slow"},
                    {"value": 30000, "color": "red", "label": "Very Slow"},
                ],
            ),
            # -- Row 2: CPU & Memory Allocation --
            _metric_panel(
                "CPU Allocation Time",
                "aiplatform.googleapis.com/ReasoningEngine/container/cpu/allocation_time",
                description="CPU allocation time for agent containers",
                resource_type="aiplatform.googleapis.com/ReasoningEngine",
                aggregation="ALIGN_RATE",
                unit="s",
                grid_x=0,
                grid_y=6,
                grid_w=12,
                grid_h=4,
            ),
            _metric_panel(
                "Memory Allocation Time",
                "aiplatform.googleapis.com/ReasoningEngine/container/memory/allocation_time",
                description="Memory allocation time for agent containers",
                resource_type="aiplatform.googleapis.com/ReasoningEngine",
                aggregation="ALIGN_RATE",
                unit="s",
                grid_x=12,
                grid_y=6,
                grid_w=12,
                grid_h=4,
            ),
            # -- Row 3: Online Prediction (if applicable) --
            _metric_panel(
                "Prediction Request Count",
                "aiplatform.googleapis.com/prediction/online/request_count",
                description="Online prediction requests (for model-serving endpoints)",
                resource_type="aiplatform.googleapis.com/Endpoint",
                aggregation="ALIGN_RATE",
                unit="req/s",
                grid_x=0,
                grid_y=10,
                grid_w=8,
                grid_h=4,
            ),
            _metric_panel(
                "Prediction CPU Utilization",
                "aiplatform.googleapis.com/prediction/online/cpu/utilization",
                description="CPU utilization for online prediction endpoints",
                resource_type="aiplatform.googleapis.com/Endpoint",
                unit="%",
                grid_x=8,
                grid_y=10,
                grid_w=8,
                grid_h=4,
                thresholds=[
                    {"value": 0.8, "color": "yellow", "label": "High"},
                    {"value": 0.95, "color": "red", "label": "Critical"},
                ],
            ),
            _metric_panel(
                "Replica Count",
                "aiplatform.googleapis.com/prediction/online/replica_count",
                description="Number of active prediction replicas",
                resource_type="aiplatform.googleapis.com/Endpoint",
                grid_x=16,
                grid_y=10,
                grid_w=8,
                grid_h=4,
            ),
            # -- Row 4: Logs --
            _log_panel(
                "Agent Engine Logs",
                'resource.type="aiplatform.googleapis.com/ReasoningEngine" OR '
                '(resource.type="cloud_run_revision" AND '
                'labels."reasoning_engine_id"!="")',
                description="Logs from Reasoning Engine and backing Cloud Run services",
                severity_levels=["INFO", "WARNING", "ERROR", "CRITICAL"],
                resource_type="aiplatform.googleapis.com/ReasoningEngine",
                grid_x=0,
                grid_y=14,
                grid_w=24,
                grid_h=5,
            ),
            # -- Row 5: Traces --
            _trace_panel(
                "Agent Execution Traces",
                '+span_name:"invoke_agent" OR +span_name:"execute_tool"',
                description="Distributed traces for agent invocations and tool executions",
                grid_x=0,
                grid_y=19,
                grid_w=24,
                grid_h=5,
            ),
        ],
    }


# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------

_TEMPLATE_BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "ootb-gke": _gke_dashboard_template,
    "ootb-cloud-run": _cloud_run_dashboard_template,
    "ootb-bigquery": _bigquery_dashboard_template,
    "ootb-vertex-agent-engine": _vertex_agent_engine_dashboard_template,
}


def list_templates() -> list[dict[str, Any]]:
    """Return summary metadata for all available OOTB templates.

    Returns:
        List of template summaries with id, display_name, description,
        service, and panel_count.
    """
    summaries: list[dict[str, Any]] = []
    for builder in _TEMPLATE_BUILDERS.values():
        template = builder()
        summaries.append(
            {
                "id": template["id"],
                "display_name": template["display_name"],
                "description": template["description"],
                "service": template["service"],
                "panel_count": len(template.get("panels", [])),
                "labels": template.get("labels", {}),
            }
        )
    return summaries


def get_template(template_id: str) -> dict[str, Any] | None:
    """Get a full template definition by ID.

    Args:
        template_id: Template identifier (e.g. ``"ootb-gke"``).

    Returns:
        Full template dict or None if not found.
    """
    builder = _TEMPLATE_BUILDERS.get(template_id)
    if builder is None:
        return None
    result: dict[str, Any] = builder()
    return result


def get_template_ids() -> list[str]:
    """Return all available template IDs.

    Returns:
        List of template ID strings.
    """
    return list(_TEMPLATE_BUILDERS.keys())
