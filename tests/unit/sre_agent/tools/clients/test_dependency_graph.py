"""Unit tests for dependency graph module."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.clients.dependency_graph import (
    _build_graph_from_traces,
    _extract_service_from_span,
    _merge_with_asset_relationships,
    _render_ascii,
    _render_mermaid,
    analyze_impact,
    build_dependency_graph,
    find_root_cause_candidates,
)


class TestServiceExtraction:
    """Tests for service extraction from spans."""

    def test_extract_from_gae_label(self):
        """Test extracting service from GAE label."""
        span = {"labels": {"g.co/gae/app/module": "my-service"}}
        assert _extract_service_from_span(span) == "my-service"

    def test_extract_from_service_name_label(self):
        """Test extracting from service.name label."""
        span = {"labels": {"service.name": "backend"}}
        assert _extract_service_from_span(span) == "backend"

    def test_extract_from_http_host(self):
        """Test extracting from HTTP host label."""
        span = {"labels": {"/http/host": "api.example.com"}}
        assert _extract_service_from_span(span) == "api.example.com"

    def test_extract_from_span_name(self):
        """Test extracting from span name pattern."""
        span = {"labels": {}, "name": "PaymentService/ProcessPayment"}
        assert _extract_service_from_span(span) == "PaymentService"

    def test_extract_none_for_http_url(self):
        """Test that HTTP URLs don't extract as service names."""
        span = {"labels": {}, "name": "http://example.com/api"}
        result = _extract_service_from_span(span)
        assert result is None or result != "http:"

    def test_extract_none_for_empty_span(self):
        """Test extracting from empty span."""
        span = {"labels": {}, "name": ""}
        assert _extract_service_from_span(span) is None


class TestGraphBuilding:
    """Tests for building dependency graphs from traces."""

    def test_build_graph_from_empty_traces(self):
        """Test building graph from empty trace list."""
        graph = _build_graph_from_traces([])

        assert graph["nodes"] == []
        assert graph["edges"] == []
        assert graph["summary"]["trace_count"] == 0

    def test_build_graph_single_service(self):
        """Test building graph with single service."""
        traces = [
            {
                "spans": [
                    {
                        "span_id": "span-1",
                        "name": "MyService/Operation",
                        "labels": {"service.name": "MyService"},
                        "parent_span_id": None,
                        "start_time_unix": 1000,
                        "end_time_unix": 1001,
                    }
                ]
            }
        ]

        graph = _build_graph_from_traces(traces)

        assert len(graph["nodes"]) == 1
        assert graph["nodes"][0]["name"] == "MyService"
        assert graph["edges"] == []

    def test_build_graph_with_dependencies(self):
        """Test building graph with service dependencies."""
        traces = [
            {
                "spans": [
                    {
                        "span_id": "span-1",
                        "name": "Frontend/GetPage",
                        "labels": {"service.name": "Frontend"},
                        "parent_span_id": None,
                        "start_time_unix": 1000,
                        "end_time_unix": 1002,
                    },
                    {
                        "span_id": "span-2",
                        "name": "Backend/FetchData",
                        "labels": {"service.name": "Backend"},
                        "parent_span_id": "span-1",
                        "start_time_unix": 1000.5,
                        "end_time_unix": 1001.5,
                    },
                ]
            }
        ]

        graph = _build_graph_from_traces(traces)

        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1
        assert graph["edges"][0]["source"] == "Frontend"
        assert graph["edges"][0]["target"] == "Backend"

    def test_build_graph_counts_errors(self):
        """Test that graph tracks error counts."""
        traces = [
            {
                "spans": [
                    {
                        "span_id": "span-1",
                        "name": "Service/Op",
                        "labels": {
                            "service.name": "ErrorService",
                            "/http/status_code": "500",
                        },
                        "parent_span_id": None,
                        "start_time_unix": 1000,
                        "end_time_unix": 1001,
                    }
                ]
            }
        ]

        graph = _build_graph_from_traces(traces)

        assert graph["nodes"][0]["error_count"] == 1


class TestAssetMerging:
    """Tests for merging asset relationships into graph."""

    def test_merge_with_network_dependency(self):
        """Test merging network dependencies from assets."""
        graph = {
            "nodes": [{"id": "my-vm", "name": "my-vm"}],
            "edges": [],
            "summary": {"node_count": 1, "edge_count": 0},
        }

        assets = [
            {
                "name": "//compute.googleapis.com/projects/test/instances/my-vm",
                "asset_type": "compute.googleapis.com/Instance",
                "resource": {
                    "data": {
                        "network": "//compute.googleapis.com/projects/test/networks/my-network"
                    }
                },
            }
        ]

        merged = _merge_with_asset_relationships(graph, assets)

        # Should add network node and edge
        assert len(merged["nodes"]) >= 2
        assert any(e["relationship"] == "uses_network" for e in merged["edges"])


class TestGraphRendering:
    """Tests for graph rendering functions."""

    def test_render_mermaid(self):
        """Test Mermaid diagram rendering."""
        graph = {
            "nodes": [
                {"id": "ServiceA", "name": "Service A"},
                {"id": "ServiceB", "name": "Service B", "error_count": 1},
            ],
            "edges": [{"source": "ServiceA", "target": "ServiceB", "call_count": 10}],
            "summary": {"node_count": 2, "edge_count": 1},
        }

        mermaid = _render_mermaid(graph)

        assert "graph LR" in mermaid
        assert "ServiceA" in mermaid
        assert "ServiceB" in mermaid
        assert "-->" in mermaid

    def test_render_ascii(self):
        """Test ASCII diagram rendering."""
        graph = {
            "nodes": [
                {"id": "A", "name": "Service A", "avg_latency_ms": 100},
                {"id": "B", "name": "Service B", "error_count": 2},
            ],
            "edges": [{"source": "A", "target": "B", "call_count": 5}],
            "summary": {"node_count": 2, "edge_count": 1},
        }

        ascii_output = _render_ascii(graph)

        assert "DEPENDENCY GRAPH" in ascii_output
        assert "Service A" in ascii_output
        assert "Service B" in ascii_output
        assert "→" in ascii_output


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph function."""

    @pytest.mark.asyncio
    async def test_build_graph_no_project(self):
        """Test building graph without project ID."""
        with patch(
            "sre_agent.tools.clients.dependency_graph.get_current_project_id",
            return_value=None,
        ):
            result = await build_dependency_graph()
            assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_build_graph_success(self):
        """Test successful graph building."""
        mock_traces = [{"trace_id": "trace-1", "duration_ms": 100}]

        mock_full_trace = {
            "trace_id": "trace-1",
            "spans": [
                {
                    "span_id": "span-1",
                    "name": "Test/Op",
                    "labels": {"service.name": "TestService"},
                    "parent_span_id": None,
                    "start_time_unix": 1000,
                    "end_time_unix": 1001,
                }
            ],
        }

        mock_assets = {"assets": []}

        with patch(
            "sre_agent.tools.clients.trace._list_traces_sync",
            return_value=mock_traces,
        ):
            with patch(
                "sre_agent.tools.clients.trace._fetch_trace_sync",
                return_value=mock_full_trace,
            ):
                with patch(
                    "sre_agent.tools.clients.asset_inventory._search_assets_sync",
                    return_value=mock_assets,
                ):
                    with patch("sre_agent.tools.clients.trace._set_thread_credentials"):
                        with patch(
                            "sre_agent.tools.clients.trace._clear_thread_credentials"
                        ):
                            result = await build_dependency_graph(
                                project_id="test-project",
                                output_format="json",
                            )

                            assert result.status == ToolStatus.SUCCESS
                            assert "nodes" in result.result
                            assert "edges" in result.result


class TestAnalyzeImpact:
    """Tests for analyze_impact function."""

    @pytest.mark.asyncio
    async def test_analyze_impact_success(self):
        """Test successful impact analysis."""
        mock_graph = {
            "nodes": [
                {"id": "payment-service", "name": "payment-service"},
                {"id": "checkout", "name": "checkout"},
                {"id": "orders", "name": "orders"},
            ],
            "edges": [
                {"source": "checkout", "target": "payment-service", "call_count": 100},
                {"source": "orders", "target": "payment-service", "call_count": 50},
            ],
            "summary": {"node_count": 3, "edge_count": 2},
        }

        with patch(
            "sre_agent.tools.clients.dependency_graph.build_dependency_graph"
        ) as mock_build:
            mock_build.return_value = MagicMock(
                status=ToolStatus.SUCCESS,
                result=mock_graph,
            )

            result = await analyze_impact(
                service_name="payment-service",
                project_id="test-project",
            )

            assert result.status == ToolStatus.SUCCESS
            assert result.result["dependent_count"] == 2
            assert result.result["impact_level"] in [
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
            ]

    @pytest.mark.asyncio
    async def test_analyze_impact_service_not_found(self):
        """Test impact analysis when service not found."""
        mock_graph = {
            "nodes": [{"id": "other-service", "name": "other-service"}],
            "edges": [],
            "summary": {"node_count": 1, "edge_count": 0},
        }

        with patch(
            "sre_agent.tools.clients.dependency_graph.build_dependency_graph"
        ) as mock_build:
            mock_build.return_value = MagicMock(
                status=ToolStatus.SUCCESS,
                result=mock_graph,
            )

            result = await analyze_impact(
                service_name="nonexistent-service",
                project_id="test-project",
            )

            assert result.status == ToolStatus.ERROR
            assert "not found" in result.error.lower()


class TestFindRootCauseCandidates:
    """Tests for find_root_cause_candidates function."""

    @pytest.mark.asyncio
    async def test_find_candidates_success(self):
        """Test successful root cause candidate finding."""
        mock_graph = {
            "nodes": [
                {"id": "frontend", "name": "frontend"},
                {
                    "id": "backend",
                    "name": "backend",
                    "error_count": 5,
                    "avg_latency_ms": 2000,
                },
                {"id": "database", "name": "database"},
            ],
            "edges": [
                {"source": "frontend", "target": "backend", "call_count": 100},
                {"source": "frontend", "target": "database", "call_count": 10},
            ],
            "summary": {"node_count": 3, "edge_count": 2},
        }

        with patch(
            "sre_agent.tools.clients.dependency_graph.build_dependency_graph"
        ) as mock_build:
            mock_build.return_value = MagicMock(
                status=ToolStatus.SUCCESS,
                result=mock_graph,
            )

            result = await find_root_cause_candidates(
                failing_service="frontend",
                project_id="test-project",
            )

            assert result.status == ToolStatus.SUCCESS
            assert result.result["candidate_count"] == 2
            # Backend should be first due to errors and high latency
            assert result.result["candidates"][0]["service"] == "backend"
            assert result.result["candidates"][0]["suspicion_score"] > 0
