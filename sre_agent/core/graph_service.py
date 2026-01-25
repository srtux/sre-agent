"""Service Dependency Graph.

Implements the Knowledge Graph for mapping service dependencies,
enabling blast radius analysis and causal inference.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ServiceType(str, Enum):
    """Type of service in the dependency graph."""

    COMPUTE = "compute"  # App servers, functions
    DATABASE = "database"  # SQL, NoSQL databases
    CACHE = "cache"  # Redis, Memcache
    QUEUE = "queue"  # Pub/Sub, Kafka
    EXTERNAL = "external"  # Third-party APIs
    GATEWAY = "gateway"  # API gateways, load balancers
    STORAGE = "storage"  # GCS, S3
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    """Type of dependency edge."""

    CALLS = "calls"  # Synchronous call
    READS_FROM = "reads_from"  # Data read
    WRITES_TO = "writes_to"  # Data write
    SUBSCRIBES = "subscribes"  # Async subscription
    PUBLISHES = "publishes"  # Async publish
    DEPENDS_ON = "depends_on"  # Generic dependency


@dataclass
class DependencyNode:
    """A node in the service dependency graph."""

    service_name: str
    service_type: ServiceType = ServiceType.UNKNOWN
    namespace: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Aggregated metrics
    avg_latency_ms: float | None = None
    error_rate: float | None = None
    request_count: int = 0


@dataclass
class DependencyEdge:
    """An edge representing a dependency between services."""

    source: str  # Service that initiates
    target: str  # Service that responds
    edge_type: EdgeType = EdgeType.CALLS

    # Edge metrics
    latency_p50: float | None = None
    latency_p99: float | None = None
    error_rate: float | None = None
    request_count: int = 0

    # Metadata
    protocol: str | None = None  # HTTP, gRPC, etc.
    operation: str | None = None  # Specific operation/method


class BlastRadiusReport(BaseModel):
    """Report of blast radius analysis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_service: str = Field(description="Service that failed")
    directly_affected: list[str] = Field(
        default_factory=list, description="Services directly calling this service"
    )
    indirectly_affected: list[str] = Field(
        default_factory=list, description="Services affected through cascade"
    )
    total_affected: int = Field(description="Total count of affected services")
    critical_paths: list[list[str]] = Field(
        default_factory=list, description="Critical paths through the failed service"
    )
    estimated_impact: str = Field(description="Estimated user impact")


@dataclass
class DependencyGraph:
    """Service dependency graph structure."""

    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    edges: list[DependencyEdge] = field(default_factory=list)

    # Adjacency lists for efficient traversal
    _outgoing: dict[str, list[str]] = field(default_factory=dict)
    _incoming: dict[str, list[str]] = field(default_factory=dict)

    def add_node(self, node: DependencyNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.service_name] = node
        if node.service_name not in self._outgoing:
            self._outgoing[node.service_name] = []
        if node.service_name not in self._incoming:
            self._incoming[node.service_name] = []

    def add_edge(self, edge: DependencyEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

        # Ensure nodes exist
        if edge.source not in self.nodes:
            self.add_node(DependencyNode(service_name=edge.source))
        if edge.target not in self.nodes:
            self.add_node(DependencyNode(service_name=edge.target))

        # Update adjacency lists
        if edge.target not in self._outgoing.get(edge.source, []):
            self._outgoing.setdefault(edge.source, []).append(edge.target)
        if edge.source not in self._incoming.get(edge.target, []):
            self._incoming.setdefault(edge.target, []).append(edge.source)

    def get_downstream(self, service: str) -> list[str]:
        """Get services that this service calls (downstream dependencies)."""
        return self._outgoing.get(service, [])

    def get_upstream(self, service: str) -> list[str]:
        """Get services that call this service (upstream dependents)."""
        return self._incoming.get(service, [])

    def get_node(self, service: str) -> DependencyNode | None:
        """Get a node by service name."""
        return self.nodes.get(service)

    def get_edges_from(self, service: str) -> list[DependencyEdge]:
        """Get all edges originating from a service."""
        return [e for e in self.edges if e.source == service]

    def get_edges_to(self, service: str) -> list[DependencyEdge]:
        """Get all edges targeting a service."""
        return [e for e in self.edges if e.target == service]


class GraphService:
    """Manages the service dependency knowledge graph.

    Builds and queries the graph for:
    - Dependency mapping from traces
    - Blast radius calculation
    - Critical path identification
    """

    def __init__(self) -> None:
        """Initialize the graph service."""
        self._graphs: dict[str, DependencyGraph] = {}

    def get_or_create_graph(self, project_id: str) -> DependencyGraph:
        """Get or create a dependency graph for a project."""
        if project_id not in self._graphs:
            self._graphs[project_id] = DependencyGraph()
        return self._graphs[project_id]

    def build_from_trace(
        self, project_id: str, trace_data: dict[str, Any]
    ) -> DependencyGraph:
        """Build dependency graph from trace data.

        Args:
            project_id: GCP project ID
            trace_data: Trace data with spans

        Returns:
            Updated dependency graph
        """
        graph = self.get_or_create_graph(project_id)

        spans = trace_data.get("spans", [])
        if not spans:
            return graph

        # Build span lookup
        span_by_id: dict[str, dict[str, Any]] = {}
        for span in spans:
            span_id = span.get("spanId", span.get("span_id", ""))
            span_by_id[span_id] = span

        # Extract service information and build graph
        for span in spans:
            service_name = self._extract_service_name(span)
            if not service_name:
                continue

            # Create or update node
            if service_name not in graph.nodes:
                service_type = self._infer_service_type(span)
                node = DependencyNode(
                    service_name=service_name,
                    service_type=service_type,
                )
                graph.add_node(node)

            # Find parent and create edge
            parent_id = span.get("parentSpanId", span.get("parent_span_id"))
            if parent_id and parent_id in span_by_id:
                parent_span = span_by_id[parent_id]
                parent_service = self._extract_service_name(parent_span)

                if parent_service and parent_service != service_name:
                    # Create edge from parent to child
                    edge = DependencyEdge(
                        source=parent_service,
                        target=service_name,
                        edge_type=EdgeType.CALLS,
                        operation=span.get("displayName", span.get("name")),
                    )

                    # Extract latency
                    duration = self._extract_duration(span)
                    if duration is not None:
                        edge.latency_p50 = duration

                    graph.add_edge(edge)

        return graph

    def build_from_traces(
        self, project_id: str, traces: list[dict[str, Any]]
    ) -> DependencyGraph:
        """Build dependency graph from multiple traces.

        Args:
            project_id: GCP project ID
            traces: List of trace data

        Returns:
            Combined dependency graph
        """
        graph = self.get_or_create_graph(project_id)

        for trace_data in traces:
            self.build_from_trace(project_id, trace_data)

        return graph

    def get_upstream(self, project_id: str, service: str) -> list[DependencyNode]:
        """Get all services that call this service.

        Args:
            project_id: GCP project ID
            service: Service name

        Returns:
            List of upstream service nodes
        """
        graph = self.get_or_create_graph(project_id)
        upstream_names = graph.get_upstream(service)
        return [graph.nodes[name] for name in upstream_names if name in graph.nodes]

    def get_downstream(self, project_id: str, service: str) -> list[DependencyNode]:
        """Get all services this service depends on.

        Args:
            project_id: GCP project ID
            service: Service name

        Returns:
            List of downstream service nodes
        """
        graph = self.get_or_create_graph(project_id)
        downstream_names = graph.get_downstream(service)
        return [graph.nodes[name] for name in downstream_names if name in graph.nodes]

    def get_blast_radius(self, project_id: str, service: str) -> BlastRadiusReport:
        """Calculate the impact if a service fails.

        Args:
            project_id: GCP project ID
            service: Failed service name

        Returns:
            Blast radius report
        """
        graph = self.get_or_create_graph(project_id)

        # BFS to find all affected services
        directly_affected = set(graph.get_upstream(service))
        indirectly_affected: set[str] = set()

        visited = {service}
        queue = list(directly_affected)

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Find upstream of upstream
            upstream = graph.get_upstream(current)
            for upstream_svc in upstream:
                if (
                    upstream_svc not in visited
                    and upstream_svc not in directly_affected
                ):
                    indirectly_affected.add(upstream_svc)
                    queue.append(upstream_svc)

        # Find critical paths
        critical_paths = self._find_critical_paths(graph, service)

        # Estimate impact
        total = len(directly_affected) + len(indirectly_affected)
        if total == 0:
            impact = "Minimal - no upstream dependencies detected"
        elif total < 3:
            impact = "Low - few services affected"
        elif total < 10:
            impact = "Medium - moderate cascade expected"
        else:
            impact = "High - widespread cascade expected"

        return BlastRadiusReport(
            source_service=service,
            directly_affected=sorted(directly_affected),
            indirectly_affected=sorted(indirectly_affected),
            total_affected=total,
            critical_paths=critical_paths,
            estimated_impact=impact,
        )

    def _find_critical_paths(
        self, graph: DependencyGraph, service: str, max_depth: int = 5
    ) -> list[list[str]]:
        """Find critical paths through a service.

        Args:
            graph: Dependency graph
            service: Service to find paths through
            max_depth: Maximum path depth

        Returns:
            List of critical paths
        """
        paths: list[list[str]] = []

        # Find entry points (services with no incoming edges)
        entry_points = [
            name for name, node in graph.nodes.items() if not graph.get_upstream(name)
        ]

        for entry in entry_points:
            path = self._find_path(graph, entry, service, max_depth)
            if path:
                paths.append(path)

        return paths[:5]  # Return top 5 paths

    def _find_path(
        self,
        graph: DependencyGraph,
        start: str,
        end: str,
        max_depth: int,
        current_path: list[str] | None = None,
    ) -> list[str] | None:
        """Find a path between two services using DFS.

        Args:
            graph: Dependency graph
            start: Starting service
            end: Target service
            max_depth: Maximum depth
            current_path: Current path being explored

        Returns:
            Path if found, None otherwise
        """
        if current_path is None:
            current_path = []

        if len(current_path) > max_depth:
            return None

        current_path = [*current_path, start]

        if start == end:
            return current_path

        for neighbor in graph.get_downstream(start):
            if neighbor not in current_path:
                result = self._find_path(graph, neighbor, end, max_depth, current_path)
                if result:
                    return result

        return None

    def _extract_service_name(self, span: dict[str, Any]) -> str | None:
        """Extract service name from span data."""
        # Try common attribute locations
        labels = span.get("attributes", span.get("labels", {}))

        # OpenTelemetry convention
        if "service.name" in labels:
            return str(labels["service.name"])

        # Cloud Trace convention
        if "g.co/r/generic_task/job" in labels:
            return str(labels["g.co/r/generic_task/job"])

        # Kubernetes convention
        if "k8s.deployment.name" in labels:
            return str(labels["k8s.deployment.name"])

        # Fallback to display name parsing
        display_name = span.get("displayName", span.get("name", ""))
        if "/" in display_name:
            parts = display_name.split("/")
            if len(parts) >= 2:
                return str(parts[0])

        return None

    def _extract_duration(self, span: dict[str, Any]) -> float | None:
        """Extract duration in milliseconds from span."""
        # Try direct duration
        if "duration" in span:
            duration = span["duration"]
            if isinstance(duration, int | float):
                return float(duration)
            # Parse duration string (e.g., "1.234s")
            if isinstance(duration, str):
                try:
                    if duration.endswith("s"):
                        return float(duration[:-1]) * 1000
                    elif duration.endswith("ms"):
                        return float(duration[:-2])
                except ValueError:
                    pass

        # Calculate from timestamps
        start_time = span.get("startTime", span.get("start_time"))
        end_time = span.get("endTime", span.get("end_time"))

        if start_time and end_time:
            try:
                from datetime import datetime

                start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                return (end - start).total_seconds() * 1000
            except (ValueError, TypeError):
                pass

        return None

    def _infer_service_type(self, span: dict[str, Any]) -> ServiceType:
        """Infer service type from span attributes."""
        labels = span.get("attributes", span.get("labels", {}))
        name = span.get("displayName", span.get("name", "")).lower()

        # Database indicators
        if any(
            db in name
            for db in ["sql", "postgres", "mysql", "mongodb", "spanner", "firestore"]
        ):
            return ServiceType.DATABASE

        if "db.system" in labels:
            return ServiceType.DATABASE

        # Cache indicators
        if any(cache in name for cache in ["redis", "memcache", "cache"]):
            return ServiceType.CACHE

        # Queue indicators
        if any(queue in name for queue in ["pubsub", "kafka", "queue", "sqs"]):
            return ServiceType.QUEUE

        # Storage indicators
        if any(storage in name for storage in ["gcs", "s3", "storage", "blob"]):
            return ServiceType.STORAGE

        # Gateway indicators
        if any(gw in name for gw in ["gateway", "ingress", "loadbalancer", "proxy"]):
            return ServiceType.GATEWAY

        # External indicators
        if "http.url" in labels:
            url = labels.get("http.url", "")
            if not any(
                internal in url
                for internal in ["localhost", "internal", "cluster.local"]
            ):
                return ServiceType.EXTERNAL

        return ServiceType.COMPUTE


# Singleton instance
_graph_service: GraphService | None = None


def get_graph_service() -> GraphService:
    """Get the singleton graph service instance."""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
