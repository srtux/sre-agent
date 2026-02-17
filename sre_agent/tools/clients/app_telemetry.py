"""App-Aware Telemetry Client.

This module provides tools for querying telemetry data (metrics, logs, traces)
in an application-centric way using AppHub topology information.

It enables the SRE agent to:
- Query metrics across all services/workloads in an application
- Get aggregated logs for an entire application
- Find traces that span application components
- Get a unified health view of an application

Reference: https://cloud.google.com/app-hub/docs/overview
"""

import logging
from typing import Any

from ...auth import get_current_project_id
from ...schema import BaseToolResponse, ToolStatus
from ..common import adk_tool
from .apphub import _get_application_topology_sync

logger = logging.getLogger(__name__)


def _extract_resource_filters(
    topology: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    """Extract resource identifiers from AppHub topology for telemetry filtering.

    Returns a dict with resource types and their identifiers that can be used
    to construct telemetry queries.
    """
    resources: dict[str, list[dict[str, str]]] = {
        "gke_clusters": [],
        "cloud_run_services": [],
        "gce_instances": [],
        "cloud_sql_instances": [],
        "load_balancers": [],
        "gke_workloads": [],
    }

    # Process services
    services = topology.get("topology", {}).get("services", [])
    for svc in services:
        svc_ref = svc.get("service_reference", {})
        uri = svc_ref.get("uri", "")

        # Parse GCP resource URI
        # Format: //service.googleapis.com/projects/PROJECT/locations/LOCATION/...
        if uri.startswith("//run.googleapis.com/"):
            # Cloud Run service
            parts = uri.split("/")
            if len(parts) >= 8:
                project = parts[4] if len(parts) > 4 else ""
                location = parts[6] if len(parts) > 6 else ""
                service_name = parts[8] if len(parts) > 8 else ""
                resources["cloud_run_services"].append(
                    {
                        "project": project,
                        "location": location,
                        "service": service_name,
                        "uri": uri,
                    }
                )
        elif uri.startswith("//compute.googleapis.com/") and "forwardingRules" in uri:
            # Load balancer forwarding rule
            parts = uri.split("/")
            resources["load_balancers"].append(
                {
                    "uri": uri,
                    "name": parts[-1] if parts else "",
                }
            )

    # Process workloads
    workloads = topology.get("topology", {}).get("workloads", [])
    for wl in workloads:
        wl_ref = wl.get("workload_reference", {})
        uri = wl_ref.get("uri", "")

        if uri.startswith("//container.googleapis.com/"):
            # GKE workload
            parts = uri.split("/")
            if len(parts) >= 8:
                project = parts[4] if len(parts) > 4 else ""
                location = parts[6] if len(parts) > 6 else ""
                cluster = parts[8] if len(parts) > 8 else ""
                resources["gke_clusters"].append(
                    {
                        "project": project,
                        "location": location,
                        "cluster": cluster,
                        "uri": uri,
                    }
                )
                # Extract workload details if available
                if "namespaces" in uri:
                    ns_idx = parts.index("namespaces") if "namespaces" in parts else -1
                    if ns_idx > 0 and ns_idx + 1 < len(parts):
                        namespace = parts[ns_idx + 1]
                        workload_type = (
                            parts[ns_idx + 2] if ns_idx + 2 < len(parts) else ""
                        )
                        workload_name = (
                            parts[ns_idx + 3] if ns_idx + 3 < len(parts) else ""
                        )
                        resources["gke_workloads"].append(
                            {
                                "cluster": cluster,
                                "namespace": namespace,
                                "type": workload_type,
                                "name": workload_name,
                            }
                        )
        elif uri.startswith("//compute.googleapis.com/") and "instanceGroups" in uri:
            # Managed Instance Group
            parts = uri.split("/")
            resources["gce_instances"].append(
                {
                    "uri": uri,
                    "name": parts[-1] if parts else "",
                }
            )
        elif uri.startswith("//sqladmin.googleapis.com/"):
            # Cloud SQL instance
            parts = uri.split("/")
            if len(parts) >= 6:
                project = parts[4] if len(parts) > 4 else ""
                instance = parts[6] if len(parts) > 6 else ""
                resources["cloud_sql_instances"].append(
                    {
                        "project": project,
                        "instance": instance,
                        "uri": uri,
                    }
                )

    return resources


def _build_metrics_filter(resources: dict[str, list[dict[str, str]]]) -> list[str]:
    """Build Cloud Monitoring filter strings for application resources."""
    filters = []

    # GKE container metrics
    for cluster in resources.get("gke_clusters", []):
        cluster_name = cluster.get("cluster", "")
        if cluster_name:
            filters.append(
                f'resource.type="k8s_container" AND '
                f'resource.labels.cluster_name="{cluster_name}"'
            )

    # Cloud Run metrics
    for svc in resources.get("cloud_run_services", []):
        service_name = svc.get("service", "")
        location = svc.get("location", "")
        if service_name:
            filter_parts = [
                'resource.type="cloud_run_revision"',
                f'resource.labels.service_name="{service_name}"',
            ]
            if location:
                filter_parts.append(f'resource.labels.location="{location}"')
            filters.append(" AND ".join(filter_parts))

    # Cloud SQL metrics
    for sql in resources.get("cloud_sql_instances", []):
        instance = sql.get("instance", "")
        if instance:
            filters.append(
                f'resource.type="cloudsql_database" AND '
                f'resource.labels.database_id="{instance}"'
            )

    return filters


def _build_logs_filter(resources: dict[str, list[dict[str, str]]]) -> str:
    """Build Cloud Logging filter string for application resources."""
    filter_parts = []

    # GKE container logs
    for cluster in resources.get("gke_clusters", []):
        cluster_name = cluster.get("cluster", "")
        if cluster_name:
            filter_parts.append(
                f'(resource.type="k8s_container" AND '
                f'resource.labels.cluster_name="{cluster_name}")'
            )

    # GKE workload-specific logs
    for wl in resources.get("gke_workloads", []):
        namespace = wl.get("namespace", "")
        if namespace:
            filter_parts.append(
                f'(resource.type="k8s_container" AND '
                f'resource.labels.namespace_name="{namespace}")'
            )

    # Cloud Run logs
    for svc in resources.get("cloud_run_services", []):
        service_name = svc.get("service", "")
        if service_name:
            filter_parts.append(
                f'(resource.type="cloud_run_revision" AND '
                f'resource.labels.service_name="{service_name}")'
            )

    # Cloud SQL logs
    for sql in resources.get("cloud_sql_instances", []):
        instance = sql.get("instance", "")
        if instance:
            filter_parts.append(
                f'(resource.type="cloudsql_database" AND '
                f'resource.labels.database_id="{instance}")'
            )

    if filter_parts:
        return " OR ".join(filter_parts)
    return ""


@adk_tool
async def get_application_metrics(
    application_id: str,
    metric_type: str,
    minutes_ago: int = 60,
    project_id: str | None = None,
    apphub_project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get metrics for all services and workloads in an AppHub application.

    This tool queries metrics across all components of an application,
    providing a unified view of application health.

    Args:
        application_id: ID of the AppHub application.
        metric_type: Metric type to query (e.g., "compute.googleapis.com/instance/cpu/utilization").
        minutes_ago: Time range in minutes (default 60).
        project_id: Project ID for metrics queries. Uses current context if not provided.
        apphub_project_id: AppHub host project ID. Defaults to project_id.
        location: AppHub location (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with metrics data for each application component.

    Example:
        get_application_metrics("my-app", "run.googleapis.com/request_count")
    """
    from fastapi.concurrency import run_in_threadpool

    from .monitoring import _list_time_series_sync

    if not project_id:
        project_id = get_current_project_id()

    if not project_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Project ID is required.",
        )

    if not apphub_project_id:
        apphub_project_id = project_id

    # Get application topology
    topology = await run_in_threadpool(
        _get_application_topology_sync,
        apphub_project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(topology, dict) and "error" in topology:
        return BaseToolResponse(status=ToolStatus.ERROR, error=topology["error"])

    # Extract resource filters
    resources = _extract_resource_filters(topology)
    metric_filters = _build_metrics_filter(resources)

    if not metric_filters:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="No monitorable resources found in application topology.",
        )

    # Query metrics for each resource filter
    results: dict[str, Any] = {
        "application_id": application_id,
        "metric_type": metric_type,
        "time_range_minutes": minutes_ago,
        "components": [],
    }

    for resource_filter in metric_filters:
        full_filter = f'metric.type="{metric_type}" AND {resource_filter}'
        metric_data = await run_in_threadpool(
            _list_time_series_sync,
            project_id,
            full_filter,
            minutes_ago,
            tool_context,
        )

        if isinstance(metric_data, list):
            results["components"].append(
                {
                    "filter": resource_filter,
                    "time_series_count": len(metric_data),
                    "data": metric_data,
                }
            )
        elif isinstance(metric_data, dict) and "error" not in metric_data:
            results["components"].append(
                {
                    "filter": resource_filter,
                    "data": metric_data,
                }
            )

    results["total_time_series"] = sum(
        c.get("time_series_count", 0) for c in results["components"]
    )

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=results)


@adk_tool
async def get_application_logs(
    application_id: str,
    severity: str = "ERROR",
    minutes_ago: int = 60,
    limit: int = 100,
    project_id: str | None = None,
    apphub_project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get logs for all services and workloads in an AppHub application.

    This tool aggregates logs from all application components,
    making it easy to see issues across the entire application.

    Args:
        application_id: ID of the AppHub application.
        severity: Minimum severity to filter (DEFAULT, DEBUG, INFO, WARNING, ERROR, CRITICAL).
        minutes_ago: Time range in minutes (default 60).
        limit: Maximum number of log entries to return.
        project_id: Project ID for log queries. Uses current context if not provided.
        apphub_project_id: AppHub host project ID. Defaults to project_id.
        location: AppHub location (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with log entries from all application components.

    Example:
        get_application_logs("my-app", severity="ERROR", limit=50)
    """
    from fastapi.concurrency import run_in_threadpool

    from .logging import _list_log_entries_sync

    if not project_id:
        project_id = get_current_project_id()

    if not project_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Project ID is required.",
        )

    if not apphub_project_id:
        apphub_project_id = project_id

    # Get application topology
    topology = await run_in_threadpool(
        _get_application_topology_sync,
        apphub_project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(topology, dict) and "error" in topology:
        return BaseToolResponse(status=ToolStatus.ERROR, error=topology["error"])

    # Extract resource filters
    resources = _extract_resource_filters(topology)
    resource_filter = _build_logs_filter(resources)

    if not resource_filter:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="No loggable resources found in application topology.",
        )

    # Build full filter with severity
    from datetime import datetime, timedelta, timezone

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes_ago)

    full_filter = (
        f"({resource_filter}) AND "
        f"severity>={severity} AND "
        f'timestamp>="{start_time.isoformat()}" AND '
        f'timestamp<="{end_time.isoformat()}"'
    )

    # Query logs
    log_data = await run_in_threadpool(
        _list_log_entries_sync,
        project_id,
        full_filter,
        limit,
        None,
        tool_context,
    )

    if isinstance(log_data, dict) and "error" in log_data:
        return BaseToolResponse(status=ToolStatus.ERROR, error=log_data["error"])

    results: dict[str, Any] = {
        "application_id": application_id,
        "severity_filter": severity,
        "time_range_minutes": minutes_ago,
        "entry_count": len(log_data.get("entries", [])),
        "entries": log_data.get("entries", []),
        "next_page_token": log_data.get("next_page_token"),
    }

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=results)


@adk_tool
async def get_application_health(
    application_id: str,
    project_id: str | None = None,
    apphub_project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get a unified health overview for an AppHub application.

    This tool provides a comprehensive health view by checking:
    - Error rate from logs
    - Key metrics from each component
    - Recent error events
    - Component status

    Args:
        application_id: ID of the AppHub application.
        project_id: Project ID for telemetry queries. Uses current context if not provided.
        apphub_project_id: AppHub host project ID. Defaults to project_id.
        location: AppHub location (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with unified health overview.

    Example:
        get_application_health("my-app")
    """
    from fastapi.concurrency import run_in_threadpool

    from .logging import _list_log_entries_sync

    if not project_id:
        project_id = get_current_project_id()

    if not project_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Project ID is required.",
        )

    if not apphub_project_id:
        apphub_project_id = project_id

    # Get application topology
    topology = await run_in_threadpool(
        _get_application_topology_sync,
        apphub_project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(topology, dict) and "error" in topology:
        return BaseToolResponse(status=ToolStatus.ERROR, error=topology["error"])

    # Extract resource filters
    resources = _extract_resource_filters(topology)

    # Initialize health result
    health: dict[str, Any] = {
        "application_id": application_id,
        "application_name": topology.get("application", {}).get("display_name"),
        "criticality": topology.get("summary", {}).get("criticality", "UNSPECIFIED"),
        "environment": topology.get("summary", {}).get("environment", "UNSPECIFIED"),
        "component_count": topology.get("summary", {}).get("total_components", 0),
        "status": "HEALTHY",
        "issues": [],
        "components": [],
    }

    # Check each Cloud Run service
    for svc in resources.get("cloud_run_services", []):
        service_name = svc.get("service", "")
        location_name = svc.get("location", "")
        if not service_name:
            continue

        component_health: dict[str, Any] = {
            "type": "cloud_run",
            "name": service_name,
            "location": location_name,
            "status": "HEALTHY",
            "issues": [],
        }

        # Check for recent errors
        error_filter = (
            f'resource.type="cloud_run_revision" AND '
            f'resource.labels.service_name="{service_name}" AND '
            f"severity>=ERROR"
        )
        errors = await run_in_threadpool(
            _list_log_entries_sync,
            project_id,
            error_filter,
            10,
            None,
            tool_context,
        )

        if isinstance(errors, dict) and "entries" in errors:
            error_count = len(errors.get("entries", []))
            if error_count > 0:
                component_health["status"] = "DEGRADED"
                component_health["issues"].append(f"{error_count} recent errors")
                health["issues"].append(
                    f"Cloud Run {service_name}: {error_count} errors"
                )

        health["components"].append(component_health)

    # Check GKE clusters
    seen_clusters: set[str] = set()
    for cluster in resources.get("gke_clusters", []):
        cluster_name = cluster.get("cluster", "")
        if not cluster_name or cluster_name in seen_clusters:
            continue
        seen_clusters.add(cluster_name)

        component_health = {
            "type": "gke_cluster",
            "name": cluster_name,
            "status": "HEALTHY",
            "issues": [],
        }

        # Check for pod errors
        error_filter = (
            f'resource.type="k8s_container" AND '
            f'resource.labels.cluster_name="{cluster_name}" AND '
            f"severity>=ERROR"
        )
        errors = await run_in_threadpool(
            _list_log_entries_sync,
            project_id,
            error_filter,
            10,
            None,
            tool_context,
        )

        if isinstance(errors, dict) and "entries" in errors:
            error_count = len(errors.get("entries", []))
            if error_count > 0:
                component_health["status"] = "DEGRADED"
                component_health["issues"].append(f"{error_count} recent errors")
                health["issues"].append(f"GKE {cluster_name}: {error_count} errors")

        health["components"].append(component_health)

    # Check Cloud SQL instances
    for sql in resources.get("cloud_sql_instances", []):
        instance = sql.get("instance", "")
        if not instance:
            continue

        component_health = {
            "type": "cloud_sql",
            "name": instance,
            "status": "HEALTHY",
            "issues": [],
        }

        health["components"].append(component_health)

    # Determine overall health status
    degraded_count = sum(
        1 for c in health["components"] if c.get("status") == "DEGRADED"
    )
    if degraded_count > 0:
        if degraded_count >= len(health["components"]) / 2:
            health["status"] = "CRITICAL"
        else:
            health["status"] = "DEGRADED"

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=health)


@adk_tool
async def find_application_traces(
    application_id: str,
    limit: int = 10,
    min_latency_ms: int | None = None,
    error_only: bool = False,
    project_id: str | None = None,
    apphub_project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Find traces that involve components of an AppHub application.

    This tool searches for traces that span the application's services,
    useful for understanding end-to-end request flow.

    Args:
        application_id: ID of the AppHub application.
        limit: Maximum number of traces to return.
        min_latency_ms: Minimum latency filter in milliseconds.
        error_only: If True, only return traces with errors.
        project_id: Project ID for trace queries. Uses current context if not provided.
        apphub_project_id: AppHub host project ID. Defaults to project_id.
        location: AppHub location (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with traces involving application components.

    Example:
        find_application_traces("my-app", min_latency_ms=1000, error_only=True)
    """
    from fastapi.concurrency import run_in_threadpool

    from .trace import _list_traces_sync

    if not project_id:
        project_id = get_current_project_id()

    if not project_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Project ID is required.",
        )

    if not apphub_project_id:
        apphub_project_id = project_id

    # Get application topology
    topology = await run_in_threadpool(
        _get_application_topology_sync,
        apphub_project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(topology, dict) and "error" in topology:
        return BaseToolResponse(status=ToolStatus.ERROR, error=topology["error"])

    # For now, just list traces with filters
    # In a full implementation, we could filter by service names from the topology
    traces = await run_in_threadpool(
        _list_traces_sync,
        project_id,
        limit,
        min_latency_ms,
        error_only,
        None,
        None,
        None,
    )

    if isinstance(traces, dict) and "error" in traces:
        return BaseToolResponse(status=ToolStatus.ERROR, error=traces["error"])

    # Extract service names from topology for context
    resources = _extract_resource_filters(topology)
    service_names = [
        svc.get("service") for svc in resources.get("cloud_run_services", [])
    ] + [wl.get("name") for wl in resources.get("gke_workloads", [])]

    results: dict[str, Any] = {
        "application_id": application_id,
        "application_services": [s for s in service_names if s],
        "trace_count": len(traces) if isinstance(traces, list) else 0,
        "filters_applied": {
            "min_latency_ms": min_latency_ms,
            "error_only": error_only,
        },
        "traces": traces if isinstance(traces, list) else [],
    }

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=results)
