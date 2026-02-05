"""Dependency Graph Visualization for GCP Applications.

This module provides tools for building and visualizing dependency graphs
between services and workloads using:
- Cloud Trace data for service-to-service call relationships
- Cloud Asset Inventory for resource dependencies
- AppHub topology for application-centric views

The dependency graph helps SRE agents understand:
- How services communicate with each other
- Impact analysis for failures (what depends on failing component?)
- Root cause analysis (what does the failing component depend on?)
"""

import logging
from collections import defaultdict
from typing import Any

from ...auth import get_current_project_id
from ...schema import BaseToolResponse, ToolStatus
from ..common import adk_tool

logger = logging.getLogger(__name__)


def _extract_service_from_span(span: dict[str, Any]) -> str | None:
    """Extract service name from a span's labels/attributes."""
    labels = span.get("labels", {})

    # Try common label patterns
    service = (
        labels.get("g.co/gae/app/module")
        or labels.get("service.name")
        or labels.get("/http/host")
        or labels.get("grpc.host")
        or labels.get("cloud.run.service")
    )

    if service:
        return str(service)

    # Try to extract from span name
    name = span.get("name", "")
    if "/" in name:
        # Common patterns: "ServiceName/Method" or "http://host/path"
        parts = name.split("/")
        if parts[0] and not parts[0].startswith("http"):
            return str(parts[0])

    return None


def _build_graph_from_traces(
    traces: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a dependency graph from trace data.

    Analyzes spans within traces to identify caller-callee relationships
    between services.
    """
    # Track edges: (source, target) -> count
    edges: dict[tuple[str, str], int] = defaultdict(int)
    # Track nodes with metadata
    nodes: dict[str, dict[str, Any]] = {}
    # Track latencies for edges
    edge_latencies: dict[tuple[str, str], list[float]] = defaultdict(list)

    for trace in traces:
        spans = trace.get("spans", [])
        if not spans:
            continue

        # Build span tree
        span_by_id: dict[str, dict[str, Any]] = {}
        for span in spans:
            span_id = span.get("span_id")
            if span_id:
                span_by_id[span_id] = span

        # Analyze parent-child relationships
        for span in spans:
            child_service = _extract_service_from_span(span)
            parent_span_id = span.get("parent_span_id")

            if child_service:
                # Update node info
                if child_service not in nodes:
                    nodes[child_service] = {
                        "name": child_service,
                        "span_count": 0,
                        "total_latency_ms": 0,
                        "error_count": 0,
                    }
                nodes[child_service]["span_count"] += 1

                # Calculate span duration
                start = span.get("start_time_unix", 0)
                end = span.get("end_time_unix", 0)
                duration_ms = (end - start) * 1000 if start and end else 0
                nodes[child_service]["total_latency_ms"] += duration_ms

                # Check for errors
                labels = span.get("labels", {})
                if labels.get("/http/status_code", "").startswith(("4", "5")):
                    nodes[child_service]["error_count"] += 1
                if labels.get("error") == "true":
                    nodes[child_service]["error_count"] += 1

            if parent_span_id and parent_span_id in span_by_id:
                parent_span = span_by_id[parent_span_id]
                parent_service = _extract_service_from_span(parent_span)

                if parent_service and child_service and parent_service != child_service:
                    edge_key = (parent_service, child_service)
                    edges[edge_key] += 1

                    # Track latency
                    start = span.get("start_time_unix", 0)
                    end = span.get("end_time_unix", 0)
                    if start and end:
                        edge_latencies[edge_key].append((end - start) * 1000)

    # Format output
    graph: dict[str, Any] = {
        "nodes": [],
        "edges": [],
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "trace_count": len(traces),
        },
    }

    for name, data in nodes.items():
        avg_latency = (
            data["total_latency_ms"] / data["span_count"]
            if data["span_count"] > 0
            else 0
        )
        graph["nodes"].append(
            {
                "id": name,
                "name": name,
                "span_count": data["span_count"],
                "avg_latency_ms": round(avg_latency, 2),
                "error_count": data["error_count"],
            }
        )

    for (source, target), count in edges.items():
        latencies = edge_latencies.get((source, target), [])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        graph["edges"].append(
            {
                "source": source,
                "target": target,
                "call_count": count,
                "avg_latency_ms": round(avg_latency, 2),
            }
        )

    return graph


def _merge_with_asset_relationships(
    graph: dict[str, Any],
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge trace-derived graph with asset inventory relationships."""
    # Track existing nodes
    existing_nodes = {n["id"] for n in graph["nodes"]}

    # Add infrastructure relationships from assets
    for asset in assets:
        asset_name = asset.get("name", "")
        asset_type = asset.get("asset_type", "")

        # Skip if not a relevant asset type
        if not any(
            t in asset_type for t in ["compute", "container", "run", "sql", "storage"]
        ):
            continue

        # Extract a short name for the node
        short_name = asset_name.split("/")[-1] if "/" in asset_name else asset_name

        if short_name not in existing_nodes:
            graph["nodes"].append(
                {
                    "id": short_name,
                    "name": short_name,
                    "type": asset_type,
                    "asset_source": True,
                }
            )
            existing_nodes.add(short_name)

        # Check for dependencies in resource data
        resource_data = asset.get("resource", {}).get("data", {})

        # Network dependencies
        network = resource_data.get("network")
        if network:
            network_name = network.split("/")[-1] if "/" in network else network
            if network_name not in existing_nodes:
                graph["nodes"].append(
                    {
                        "id": network_name,
                        "name": network_name,
                        "type": "network",
                        "asset_source": True,
                    }
                )
                existing_nodes.add(network_name)
            graph["edges"].append(
                {
                    "source": short_name,
                    "target": network_name,
                    "relationship": "uses_network",
                }
            )

        # Service account dependencies
        service_account = resource_data.get("serviceAccount")
        if service_account:
            sa_name = (
                service_account.split("/")[-1]
                if "/" in service_account
                else service_account
            )
            if sa_name not in existing_nodes:
                graph["nodes"].append(
                    {
                        "id": sa_name,
                        "name": sa_name,
                        "type": "service_account",
                        "asset_source": True,
                    }
                )
                existing_nodes.add(sa_name)
            graph["edges"].append(
                {
                    "source": short_name,
                    "target": sa_name,
                    "relationship": "uses_identity",
                }
            )

    # Update summary
    graph["summary"]["node_count"] = len(graph["nodes"])
    graph["summary"]["edge_count"] = len(graph["edges"])

    return graph


def _add_apphub_context(
    graph: dict[str, Any],
    topology: dict[str, Any],
) -> dict[str, Any]:
    """Add AppHub application context to the graph."""
    app_info = topology.get("application", {})

    graph["application"] = {
        "id": app_info.get("id"),
        "name": app_info.get("display_name"),
        "criticality": topology.get("summary", {}).get("criticality"),
        "environment": topology.get("summary", {}).get("environment"),
    }

    # Map services and workloads to graph nodes
    services = topology.get("topology", {}).get("services", [])
    workloads = topology.get("topology", {}).get("workloads", [])

    existing_nodes = {n["id"] for n in graph["nodes"]}

    for svc in services:
        svc_name = svc.get("display_name") or svc.get("name", "").split("/")[-1]
        if svc_name and svc_name not in existing_nodes:
            graph["nodes"].append(
                {
                    "id": svc_name,
                    "name": svc_name,
                    "type": "apphub_service",
                    "apphub_source": True,
                    "state": svc.get("state"),
                }
            )
            existing_nodes.add(svc_name)

    for wl in workloads:
        wl_name = wl.get("display_name") or wl.get("name", "").split("/")[-1]
        if wl_name and wl_name not in existing_nodes:
            graph["nodes"].append(
                {
                    "id": wl_name,
                    "name": wl_name,
                    "type": "apphub_workload",
                    "apphub_source": True,
                    "state": wl.get("state"),
                }
            )
            existing_nodes.add(wl_name)

    graph["summary"]["node_count"] = len(graph["nodes"])

    return graph


def _render_mermaid(graph: dict[str, Any]) -> str:
    """Render the dependency graph as a Mermaid diagram."""
    lines = ["graph LR"]

    # Add nodes with styling
    for node in graph["nodes"]:
        node_id = node["id"].replace("-", "_").replace(".", "_")
        label = node["name"]

        # Add error indicator
        if node.get("error_count", 0) > 0:
            lines.append(f"    {node_id}[{label} ⚠️]")
            lines.append(f"    style {node_id} fill:#ffcccc,stroke:#ff0000")
        elif node.get("asset_source"):
            lines.append(f"    {node_id}[({label})]")
            lines.append(f"    style {node_id} fill:#e6e6e6,stroke:#666666")
        elif node.get("apphub_source"):
            lines.append(f"    {node_id}[{label}]")
            lines.append(f"    style {node_id} fill:#d4edda,stroke:#28a745")
        else:
            lines.append(f"    {node_id}[{label}]")

    # Add edges
    for edge in graph["edges"]:
        source_id = edge["source"].replace("-", "_").replace(".", "_")
        target_id = edge["target"].replace("-", "_").replace(".", "_")

        relationship = edge.get("relationship", "")
        call_count = edge.get("call_count", 0)
        latency = edge.get("avg_latency_ms", 0)

        if relationship:
            lines.append(f"    {source_id} -->|{relationship}| {target_id}")
        elif call_count > 0:
            label = f"{call_count}x"
            if latency > 0:
                label += f" {latency:.0f}ms"
            lines.append(f"    {source_id} -->|{label}| {target_id}")
        else:
            lines.append(f"    {source_id} --> {target_id}")

    return "\n".join(lines)


def _render_ascii(graph: dict[str, Any]) -> str:
    """Render a simple ASCII representation of the graph."""
    lines = []
    lines.append("=" * 60)
    lines.append("DEPENDENCY GRAPH")
    lines.append("=" * 60)

    if "application" in graph:
        app = graph["application"]
        lines.append(f"\nApplication: {app.get('name', 'Unknown')}")
        lines.append(f"Criticality: {app.get('criticality', 'N/A')}")
        lines.append(f"Environment: {app.get('environment', 'N/A')}")

    lines.append(f"\nNodes ({graph['summary']['node_count']}):")
    lines.append("-" * 40)
    for node in graph["nodes"]:
        status = ""
        if node.get("error_count", 0) > 0:
            status = f" [⚠ {node['error_count']} errors]"
        if node.get("avg_latency_ms", 0) > 0:
            status += f" [{node['avg_latency_ms']:.1f}ms avg]"
        lines.append(f"  • {node['name']}{status}")

    lines.append(f"\nEdges ({graph['summary']['edge_count']}):")
    lines.append("-" * 40)
    for edge in graph["edges"]:
        arrow = "→"
        label = ""
        if edge.get("relationship"):
            label = f" ({edge['relationship']})"
        elif edge.get("call_count"):
            label = f" [{edge['call_count']}x]"
            if edge.get("avg_latency_ms", 0) > 0:
                label += f" {edge['avg_latency_ms']:.1f}ms"
        lines.append(f"  {edge['source']} {arrow} {edge['target']}{label}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


@adk_tool
async def build_dependency_graph(
    project_id: str | None = None,
    application_id: str | None = None,
    apphub_project_id: str | None = None,
    apphub_location: str = "global",
    include_assets: bool = True,
    trace_limit: int = 50,
    output_format: str = "json",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Build a dependency graph for services in a GCP project or AppHub application.

    This tool analyzes Cloud Trace data and optionally Cloud Asset Inventory
    to build a graph showing how services depend on each other.

    Args:
        project_id: Project ID for trace and asset queries.
        application_id: Optional AppHub application ID for app-centric view.
        apphub_project_id: AppHub host project ID. Defaults to project_id.
        apphub_location: AppHub location (default: global).
        include_assets: Include Cloud Asset Inventory relationships (default: True).
        trace_limit: Number of traces to analyze (default: 50).
        output_format: Output format - "json", "mermaid", or "ascii" (default: json).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with dependency graph in requested format.

    Example:
        build_dependency_graph(project_id="my-project", output_format="mermaid")
        build_dependency_graph(application_id="my-app", output_format="ascii")
    """
    from fastapi.concurrency import run_in_threadpool

    from .apphub import _get_application_topology_sync
    from .asset_inventory import _search_assets_sync
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

    # Fetch traces
    traces = await run_in_threadpool(
        _list_traces_sync,
        project_id,
        trace_limit,
        None,  # min_latency_ms
        False,  # error_only
        None,  # start_time
        None,  # end_time
        None,  # attributes_json
    )

    if isinstance(traces, dict) and "error" in traces:
        # If trace fetching fails, continue with empty traces
        logger.warning(f"Failed to fetch traces: {traces['error']}")
        traces = []

    # If we have trace IDs, fetch full trace data
    full_traces = []
    if isinstance(traces, list):
        from ...auth import (
            GLOBAL_CONTEXT_CREDENTIALS,
            get_credentials_from_tool_context,
        )
        from .trace import (
            _clear_thread_credentials,
            _fetch_trace_sync,
            _set_thread_credentials,
        )

        user_creds = get_credentials_from_tool_context(tool_context)
        creds = user_creds or GLOBAL_CONTEXT_CREDENTIALS
        _set_thread_credentials(creds)
        try:
            for trace_summary in traces[:trace_limit]:
                trace_id = trace_summary.get("trace_id")
                if trace_id:
                    full_trace = await run_in_threadpool(
                        _fetch_trace_sync, project_id, trace_id
                    )
                    if isinstance(full_trace, dict) and "spans" in full_trace:
                        full_traces.append(full_trace)
        finally:
            _clear_thread_credentials()

    # Build initial graph from traces
    graph = _build_graph_from_traces(full_traces)

    # Add asset relationships if requested
    if include_assets:
        assets_result = await run_in_threadpool(
            _search_assets_sync,
            "",  # empty query to get all assets
            [
                "compute.googleapis.com/Instance",
                "run.googleapis.com/Service",
                "container.googleapis.com/Cluster",
                "sqladmin.googleapis.com/Instance",
            ],
            f"projects/{project_id}",
            100,
            tool_context,
        )

        if isinstance(assets_result, dict) and "assets" in assets_result:
            graph = _merge_with_asset_relationships(
                graph, assets_result.get("assets", [])
            )

    # Add AppHub context if application specified
    if application_id:
        topology = await run_in_threadpool(
            _get_application_topology_sync,
            apphub_project_id,
            apphub_location,
            application_id,
            tool_context,
        )

        if isinstance(topology, dict) and "application" in topology:
            graph = _add_apphub_context(graph, topology)

    # Format output
    if output_format == "mermaid":
        result = {
            "format": "mermaid",
            "diagram": _render_mermaid(graph),
            "summary": graph["summary"],
        }
    elif output_format == "ascii":
        result = {
            "format": "ascii",
            "diagram": _render_ascii(graph),
            "summary": graph["summary"],
        }
    else:
        result = graph

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


@adk_tool
async def analyze_impact(
    service_name: str,
    project_id: str | None = None,
    trace_limit: int = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Analyze the impact of a service failure on dependent services.

    This tool builds a dependency graph and identifies all services
    that depend on the specified service, helping understand blast radius.

    Args:
        service_name: Name of the service to analyze.
        project_id: Project ID for queries.
        trace_limit: Number of traces to analyze.
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with impact analysis.

    Example:
        analyze_impact("payment-service")
    """
    from typing import cast

    # Build the dependency graph
    graph_response = cast(
        BaseToolResponse,
        await build_dependency_graph(
            project_id=project_id,
            trace_limit=trace_limit,
            output_format="json",
            tool_context=tool_context,
        ),
    )

    if graph_response.status != ToolStatus.SUCCESS:
        return graph_response

    graph = graph_response.result
    if graph is None or not isinstance(graph, dict):
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Failed to build dependency graph: no result returned.",
        )

    # Find the target service
    target_node = None
    for node in graph.get("nodes", []):
        if node["id"] == service_name or node["name"] == service_name:
            target_node = node
            break

    if not target_node:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Service '{service_name}' not found in dependency graph.",
        )

    # Find services that depend on this service (have edges TO this service)
    dependents: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if edge.get("target") == service_name:
            dependents.append(
                {
                    "service": edge["source"],
                    "call_count": edge.get("call_count", 0),
                    "avg_latency_ms": edge.get("avg_latency_ms", 0),
                }
            )

    # Find services this service depends on
    dependencies: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if edge.get("source") == service_name:
            dependencies.append(
                {
                    "service": edge["target"],
                    "call_count": edge.get("call_count", 0),
                    "avg_latency_ms": edge.get("avg_latency_ms", 0),
                }
            )

    # Calculate impact score (simplified)
    # Higher score = more critical service
    impact_score = len(dependents) * 10  # Base score from dependent count

    # Add weight for high-traffic dependencies
    for dep in dependents:
        if dep.get("call_count", 0) > 100:
            impact_score += 5

    result: dict[str, Any] = {
        "service": service_name,
        "impact_score": impact_score,
        "impact_level": (
            "CRITICAL"
            if impact_score >= 50
            else "HIGH"
            if impact_score >= 30
            else "MEDIUM"
            if impact_score >= 10
            else "LOW"
        ),
        "dependent_services": dependents,
        "dependent_count": len(dependents),
        "dependencies": dependencies,
        "dependency_count": len(dependencies),
        "analysis": {
            "message": (
                f"If '{service_name}' fails, {len(dependents)} service(s) will be affected."
            ),
            "recommendation": (
                "Consider implementing circuit breakers in dependent services."
                if len(dependents) > 3
                else "Monitor dependent services closely during incidents."
            ),
        },
    }

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


@adk_tool
async def find_root_cause_candidates(
    failing_service: str,
    project_id: str | None = None,
    trace_limit: int = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Find potential root cause candidates for a failing service.

    This tool analyzes the dependency graph to identify services
    that the failing service depends on, which could be the root cause.

    Args:
        failing_service: Name of the service experiencing issues.
        project_id: Project ID for queries.
        trace_limit: Number of traces to analyze.
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with root cause candidates.

    Example:
        find_root_cause_candidates("frontend-service")
    """
    from typing import cast

    # Build the dependency graph
    graph_response = cast(
        BaseToolResponse,
        await build_dependency_graph(
            project_id=project_id,
            trace_limit=trace_limit,
            output_format="json",
            tool_context=tool_context,
        ),
    )

    if graph_response.status != ToolStatus.SUCCESS:
        return graph_response

    graph = graph_response.result
    if graph is None or not isinstance(graph, dict):
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Failed to build dependency graph: no result returned.",
        )

    # Find the failing service node
    failing_node = None
    for node in graph.get("nodes", []):
        if node["id"] == failing_service or node["name"] == failing_service:
            failing_node = node
            break

    if not failing_node:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Service '{failing_service}' not found in dependency graph.",
        )

    # Find all dependencies (services this one calls)
    candidates: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if edge.get("source") == failing_service:
            target_name = edge["target"]

            # Find node info for the dependency
            dep_node = None
            for node in graph.get("nodes", []):
                if node["id"] == target_name:
                    dep_node = node
                    break

            candidate: dict[str, Any] = {
                "service": target_name,
                "call_count": edge.get("call_count", 0),
                "avg_latency_ms": edge.get("avg_latency_ms", 0),
                "suspicion_score": 0,
                "indicators": [],
            }

            # Calculate suspicion score
            if dep_node:
                # High error count is suspicious
                if dep_node.get("error_count", 0) > 0:
                    candidate["suspicion_score"] += 30
                    candidate["indicators"].append(
                        f"{dep_node['error_count']} errors detected"
                    )

                # High latency is suspicious
                avg_latency = dep_node.get("avg_latency_ms", 0)
                if avg_latency > 1000:
                    candidate["suspicion_score"] += 20
                    candidate["indicators"].append(f"High latency: {avg_latency:.0f}ms")
                elif avg_latency > 500:
                    candidate["suspicion_score"] += 10
                    candidate["indicators"].append(
                        f"Elevated latency: {avg_latency:.0f}ms"
                    )

            # High call count means high impact
            if edge.get("call_count", 0) > 50:
                candidate["suspicion_score"] += 10
                candidate["indicators"].append(
                    f"High call volume: {edge['call_count']}x"
                )

            candidates.append(candidate)

    # Sort by suspicion score
    candidates.sort(key=lambda x: x["suspicion_score"], reverse=True)

    result: dict[str, Any] = {
        "failing_service": failing_service,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "recommendation": (
            f"Investigate '{candidates[0]['service']}' first - highest suspicion score."
            if candidates and candidates[0]["suspicion_score"] > 0
            else "No obvious root cause candidates. Check service logs directly."
        ),
    }

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)
