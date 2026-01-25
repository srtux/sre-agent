"""Tests for the Graph Service."""

import pytest

from sre_agent.core.graph_service import (
    BlastRadiusReport,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    EdgeType,
    GraphService,
    ServiceType,
    get_graph_service,
)


class TestDependencyNode:
    """Tests for DependencyNode dataclass."""

    def test_create_node(self) -> None:
        """Test creating a dependency node."""
        node = DependencyNode(
            service_name="checkout-service",
            service_type=ServiceType.COMPUTE,
            namespace="production",
            version="v1.2.3",
            metadata={"region": "us-central1"},
        )

        assert node.service_name == "checkout-service"
        assert node.service_type == ServiceType.COMPUTE
        assert node.namespace == "production"
        assert node.version == "v1.2.3"
        assert node.metadata["region"] == "us-central1"

    def test_node_with_metrics(self) -> None:
        """Test node with aggregated metrics."""
        node = DependencyNode(
            service_name="db-service",
            service_type=ServiceType.DATABASE,
            avg_latency_ms=50.5,
            error_rate=0.01,
            request_count=10000,
        )

        assert node.avg_latency_ms == 50.5
        assert node.error_rate == 0.01
        assert node.request_count == 10000


class TestDependencyEdge:
    """Tests for DependencyEdge dataclass."""

    def test_create_edge(self) -> None:
        """Test creating a dependency edge."""
        edge = DependencyEdge(
            source="frontend",
            target="backend",
            edge_type=EdgeType.CALLS,
        )

        assert edge.source == "frontend"
        assert edge.target == "backend"
        assert edge.edge_type == EdgeType.CALLS

    def test_edge_with_metrics(self) -> None:
        """Test edge with performance metrics."""
        edge = DependencyEdge(
            source="api-gateway",
            target="payment-service",
            edge_type=EdgeType.CALLS,
            latency_p50=25.0,
            latency_p99=150.0,
            error_rate=0.005,
            request_count=5000,
            protocol="gRPC",
            operation="ProcessPayment",
        )

        assert edge.latency_p50 == 25.0
        assert edge.latency_p99 == 150.0
        assert edge.error_rate == 0.005
        assert edge.protocol == "gRPC"
        assert edge.operation == "ProcessPayment"


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    @pytest.fixture
    def graph(self) -> DependencyGraph:
        """Create a dependency graph for testing."""
        g = DependencyGraph()

        # Add nodes
        g.add_node(DependencyNode("frontend", ServiceType.COMPUTE))
        g.add_node(DependencyNode("api-gateway", ServiceType.GATEWAY))
        g.add_node(DependencyNode("user-service", ServiceType.COMPUTE))
        g.add_node(DependencyNode("order-service", ServiceType.COMPUTE))
        g.add_node(DependencyNode("db-postgres", ServiceType.DATABASE))

        # Add edges
        g.add_edge(DependencyEdge("frontend", "api-gateway", EdgeType.CALLS))
        g.add_edge(DependencyEdge("api-gateway", "user-service", EdgeType.CALLS))
        g.add_edge(DependencyEdge("api-gateway", "order-service", EdgeType.CALLS))
        g.add_edge(DependencyEdge("user-service", "db-postgres", EdgeType.READS_FROM))
        g.add_edge(DependencyEdge("order-service", "db-postgres", EdgeType.WRITES_TO))

        return g

    def test_add_node(self, graph: DependencyGraph) -> None:
        """Test adding a node."""
        assert "frontend" in graph.nodes
        assert graph.nodes["frontend"].service_type == ServiceType.COMPUTE

    def test_add_edge(self, graph: DependencyGraph) -> None:
        """Test adding an edge."""
        assert len(graph.edges) == 5

    def test_get_downstream(self, graph: DependencyGraph) -> None:
        """Test getting downstream dependencies."""
        downstream = graph.get_downstream("api-gateway")

        assert "user-service" in downstream
        assert "order-service" in downstream
        assert "frontend" not in downstream

    def test_get_upstream(self, graph: DependencyGraph) -> None:
        """Test getting upstream dependents."""
        upstream = graph.get_upstream("db-postgres")

        assert "user-service" in upstream
        assert "order-service" in upstream
        assert "frontend" not in upstream

    def test_get_node(self, graph: DependencyGraph) -> None:
        """Test getting a node by name."""
        node = graph.get_node("user-service")

        assert node is not None
        assert node.service_name == "user-service"

    def test_get_nonexistent_node(self, graph: DependencyGraph) -> None:
        """Test getting a non-existent node."""
        node = graph.get_node("nonexistent")

        assert node is None

    def test_get_edges_from(self, graph: DependencyGraph) -> None:
        """Test getting edges from a service."""
        edges = graph.get_edges_from("api-gateway")

        assert len(edges) == 2
        assert all(e.source == "api-gateway" for e in edges)

    def test_get_edges_to(self, graph: DependencyGraph) -> None:
        """Test getting edges to a service."""
        edges = graph.get_edges_to("db-postgres")

        assert len(edges) == 2
        assert all(e.target == "db-postgres" for e in edges)

    def test_auto_create_nodes_on_edge(self) -> None:
        """Test that nodes are auto-created when adding edges."""
        g = DependencyGraph()
        g.add_edge(DependencyEdge("service-a", "service-b", EdgeType.CALLS))

        assert "service-a" in g.nodes
        assert "service-b" in g.nodes


class TestGraphService:
    """Tests for GraphService."""

    @pytest.fixture
    def service(self) -> GraphService:
        """Create a graph service for testing."""
        return GraphService()

    def test_get_or_create_graph(self, service: GraphService) -> None:
        """Test getting or creating a graph."""
        graph = service.get_or_create_graph("project-1")

        assert isinstance(graph, DependencyGraph)
        assert len(graph.nodes) == 0

        # Getting same project should return same graph
        graph2 = service.get_or_create_graph("project-1")
        assert graph is graph2

    def test_build_from_trace(self, service: GraphService) -> None:
        """Test building graph from trace data."""
        trace_data = {
            "spans": [
                {
                    "spanId": "span1",
                    "displayName": "frontend/GET",
                    "attributes": {"service.name": "frontend"},
                },
                {
                    "spanId": "span2",
                    "parentSpanId": "span1",
                    "displayName": "backend/process",
                    "attributes": {"service.name": "backend"},
                },
            ]
        }

        graph = service.build_from_trace("project-1", trace_data)

        assert "frontend" in graph.nodes
        assert "backend" in graph.nodes
        assert len(graph.edges) == 1
        assert graph.edges[0].source == "frontend"
        assert graph.edges[0].target == "backend"

    def test_build_from_traces(self, service: GraphService) -> None:
        """Test building graph from multiple traces."""
        traces = [
            {
                "spans": [
                    {"spanId": "1", "attributes": {"service.name": "svc-a"}},
                    {
                        "spanId": "2",
                        "parentSpanId": "1",
                        "attributes": {"service.name": "svc-b"},
                    },
                ]
            },
            {
                "spans": [
                    {"spanId": "3", "attributes": {"service.name": "svc-b"}},
                    {
                        "spanId": "4",
                        "parentSpanId": "3",
                        "attributes": {"service.name": "svc-c"},
                    },
                ]
            },
        ]

        graph = service.build_from_traces("project-1", traces)

        assert "svc-a" in graph.nodes
        assert "svc-b" in graph.nodes
        assert "svc-c" in graph.nodes

    def test_get_upstream(self, service: GraphService) -> None:
        """Test getting upstream services."""
        # Build a graph first
        trace_data = {
            "spans": [
                {"spanId": "1", "attributes": {"service.name": "frontend"}},
                {
                    "spanId": "2",
                    "parentSpanId": "1",
                    "attributes": {"service.name": "backend"},
                },
            ]
        }
        service.build_from_trace("project-1", trace_data)

        upstream = service.get_upstream("project-1", "backend")

        assert len(upstream) == 1
        assert upstream[0].service_name == "frontend"

    def test_get_downstream(self, service: GraphService) -> None:
        """Test getting downstream services."""
        trace_data = {
            "spans": [
                {"spanId": "1", "attributes": {"service.name": "frontend"}},
                {
                    "spanId": "2",
                    "parentSpanId": "1",
                    "attributes": {"service.name": "backend"},
                },
            ]
        }
        service.build_from_trace("project-1", trace_data)

        downstream = service.get_downstream("project-1", "frontend")

        assert len(downstream) == 1
        assert downstream[0].service_name == "backend"

    def test_get_blast_radius(self, service: GraphService) -> None:
        """Test calculating blast radius."""
        # Build a more complex graph
        traces = [
            {
                "spans": [
                    {"spanId": "1", "attributes": {"service.name": "frontend"}},
                    {
                        "spanId": "2",
                        "parentSpanId": "1",
                        "attributes": {"service.name": "api-gateway"},
                    },
                    {
                        "spanId": "3",
                        "parentSpanId": "2",
                        "attributes": {"service.name": "user-service"},
                    },
                    {
                        "spanId": "4",
                        "parentSpanId": "3",
                        "attributes": {"service.name": "db-service"},
                    },
                ]
            }
        ]
        service.build_from_traces("project-1", traces)

        report = service.get_blast_radius("project-1", "db-service")

        assert isinstance(report, BlastRadiusReport)
        assert report.source_service == "db-service"
        assert "user-service" in report.directly_affected
        assert report.total_affected > 0
        assert report.estimated_impact is not None

    def test_get_blast_radius_no_upstream(self, service: GraphService) -> None:
        """Test blast radius for service with no upstream."""
        trace_data = {
            "spans": [{"spanId": "1", "attributes": {"service.name": "standalone"}}]
        }
        service.build_from_trace("project-1", trace_data)

        report = service.get_blast_radius("project-1", "standalone")

        assert report.total_affected == 0
        assert "Minimal" in report.estimated_impact

    def test_extract_service_name_otel(self, service: GraphService) -> None:
        """Test extracting service name from OpenTelemetry format."""
        span = {"attributes": {"service.name": "my-service"}}

        name = service._extract_service_name(span)

        assert name == "my-service"

    def test_extract_service_name_k8s(self, service: GraphService) -> None:
        """Test extracting service name from Kubernetes format."""
        span = {"attributes": {"k8s.deployment.name": "my-deployment"}}

        name = service._extract_service_name(span)

        assert name == "my-deployment"

    def test_infer_service_type_database(self, service: GraphService) -> None:
        """Test inferring database service type."""
        span = {"displayName": "postgres/query"}

        svc_type = service._infer_service_type(span)

        assert svc_type == ServiceType.DATABASE

    def test_infer_service_type_cache(self, service: GraphService) -> None:
        """Test inferring cache service type."""
        span = {"displayName": "redis/GET"}

        svc_type = service._infer_service_type(span)

        assert svc_type == ServiceType.CACHE

    def test_infer_service_type_queue(self, service: GraphService) -> None:
        """Test inferring queue service type."""
        span = {"displayName": "pubsub/publish"}

        svc_type = service._infer_service_type(span)

        assert svc_type == ServiceType.QUEUE


class TestGraphServiceSingleton:
    """Tests for singleton access."""

    def test_get_graph_service_singleton(self) -> None:
        """Test that get_graph_service returns singleton."""
        service1 = get_graph_service()
        service2 = get_graph_service()

        assert service1 is service2


class TestBlastRadiusReport:
    """Tests for BlastRadiusReport model."""

    def test_blast_radius_report_creation(self) -> None:
        """Test creating a blast radius report."""
        report = BlastRadiusReport(
            source_service="db-service",
            directly_affected=["user-service", "order-service"],
            indirectly_affected=["frontend"],
            total_affected=3,
            critical_paths=[["frontend", "api", "db-service"]],
            estimated_impact="Medium - moderate cascade expected",
        )

        assert report.source_service == "db-service"
        assert len(report.directly_affected) == 2
        assert len(report.indirectly_affected) == 1
        assert report.total_affected == 3

    def test_blast_radius_report_immutable(self) -> None:
        """Test that blast radius report is immutable."""
        report = BlastRadiusReport(
            source_service="test",
            directly_affected=[],
            indirectly_affected=[],
            total_affected=0,
            critical_paths=[],
            estimated_impact="Minimal",
        )

        with pytest.raises(Exception):
            report.source_service = "other"  # type: ignore[misc]
