"""Tests for the Cymbal Shops demo data generator.

Validates session/trace generation, topology aggregation, Sankey diagrams,
dashboard KPIs, and deterministic reproducibility.
"""

from __future__ import annotations

import pytest

from sre_agent.tools.synthetic.cymbal_assistant import DEMO_USERS
from sre_agent.tools.synthetic.demo_data_generator import DemoDataGenerator


@pytest.fixture()
def generator() -> DemoDataGenerator:
    """Return a fresh deterministic generator."""
    return DemoDataGenerator(seed=42)


# ---------------------------------------------------------------------------
# Session Generation
# ---------------------------------------------------------------------------


class TestSessionGeneration:
    """Validate generated session data."""

    def test_generates_expected_session_count(
        self, generator: DemoDataGenerator
    ) -> None:
        sessions = generator.get_sessions()
        assert 70 <= len(sessions) <= 90

    def test_sessions_span_seven_days(self, generator: DemoDataGenerator) -> None:
        sessions = generator.get_sessions()
        timestamps = [s["timestamp"] for s in sessions]
        span_hours = (max(timestamps) - min(timestamps)).total_seconds() / 3600
        assert span_hours >= 144

    def test_sessions_have_required_fields(self, generator: DemoDataGenerator) -> None:
        required = {"session_id", "user_id", "timestamp", "journey_type", "turns"}
        assert required.issubset(generator.get_sessions()[0].keys())

    def test_sessions_use_known_users(self, generator: DemoDataGenerator) -> None:
        valid = {u.user_id for u in DEMO_USERS}
        for s in generator.get_sessions():
            assert s["user_id"] in valid


# ---------------------------------------------------------------------------
# Trace Generation
# ---------------------------------------------------------------------------


class TestTraceGeneration:
    """Validate generated trace data."""

    def test_generates_expected_trace_count(self, generator: DemoDataGenerator) -> None:
        assert 350 <= len(generator.get_all_traces()) <= 450

    def test_trace_has_otel_fields(self, generator: DemoDataGenerator) -> None:
        t = generator.get_all_traces()[0]
        assert "trace_id" in t and "spans" in t
        assert len(t["spans"]) >= 5

    def test_span_has_genai_attributes(self, generator: DemoDataGenerator) -> None:
        span = generator.get_all_traces()[0]["spans"][0]
        assert "gen_ai.operation.name" in span.get("attributes", {})

    def test_resource_has_agent_engine_platform(
        self, generator: DemoDataGenerator
    ) -> None:
        span = generator.get_all_traces()[0]["spans"][0]
        assert span["resource"]["attributes"]["cloud.platform"] == "gcp.agent_engine"

    def test_degraded_traces_have_more_spans(
        self, generator: DemoDataGenerator
    ) -> None:
        traces = generator.get_all_traces()
        normal = [t for t in traces if not t["is_degraded"]]
        degraded = [t for t in traces if t["is_degraded"]]
        if normal and degraded:
            avg_normal = sum(len(t["spans"]) for t in normal) / len(normal)
            avg_degraded = sum(len(t["spans"]) for t in degraded) / len(degraded)
            assert avg_degraded > avg_normal

    def test_degraded_traces_have_errors(self, generator: DemoDataGenerator) -> None:
        degraded = [t for t in generator.get_all_traces() if t["is_degraded"]]
        assert any(
            any(s.get("status", {}).get("code") == 2 for s in t["spans"])
            for t in degraded
        )

    def test_trace_id_format(self, generator: DemoDataGenerator) -> None:
        """All trace_ids must be 32 hex characters."""
        for t in generator.get_all_traces():
            assert len(t["trace_id"]) == 32
            int(t["trace_id"], 16)  # must not raise

    def test_span_id_format(self, generator: DemoDataGenerator) -> None:
        """All span_ids must be 16 hex characters."""
        for t in generator.get_all_traces():
            for s in t["spans"]:
                assert len(s["span_id"]) == 16
                int(s["span_id"], 16)  # must not raise

    def test_root_span_has_no_parent(self, generator: DemoDataGenerator) -> None:
        """First span in each trace is the root and has no parent."""
        for t in generator.get_all_traces():
            assert t["spans"][0]["parent_span_id"] is None

    def test_spans_have_timestamps_in_window(
        self, generator: DemoDataGenerator
    ) -> None:
        """All span timestamps are within the 7-day window."""
        for t in generator.get_all_traces():
            for s in t["spans"]:
                assert s["start_time"].endswith("Z")
                assert s["end_time"].endswith("Z")


# ---------------------------------------------------------------------------
# Topology Aggregation
# ---------------------------------------------------------------------------


class TestTopologyAggregation:
    """Validate topology graph output format."""

    def test_topology_has_nodes_and_edges(self, generator: DemoDataGenerator) -> None:
        topo = generator.get_topology(hours=168)
        assert len(topo["nodes"]) >= 10
        assert len(topo["edges"]) >= 15

    def test_topology_node_format(self, generator: DemoDataGenerator) -> None:
        node = generator.get_topology(hours=168)["nodes"][0]
        assert all(k in node for k in ["id", "type", "data"])
        assert "label" in node["data"]

    def test_topology_edge_format(self, generator: DemoDataGenerator) -> None:
        edge = generator.get_topology(hours=168)["edges"][0]
        assert all(k in edge for k in ["source", "target", "data"])

    def test_topology_node_data_fields(self, generator: DemoDataGenerator) -> None:
        node = generator.get_topology(hours=168)["nodes"][0]
        required_data = {
            "label",
            "nodeType",
            "executionCount",
            "totalTokens",
            "errorCount",
            "avgDurationMs",
        }
        assert required_data.issubset(node["data"].keys())

    def test_topology_edge_data_fields(self, generator: DemoDataGenerator) -> None:
        edge = generator.get_topology(hours=168)["edges"][0]
        required_data = {"callCount", "avgDurationMs", "errorCount", "totalTokens"}
        assert required_data.issubset(edge["data"].keys())

    def test_topology_node_has_position(self, generator: DemoDataGenerator) -> None:
        node = generator.get_topology(hours=168)["nodes"][0]
        assert "position" in node
        assert "x" in node["position"] and "y" in node["position"]


# ---------------------------------------------------------------------------
# Sankey Aggregation
# ---------------------------------------------------------------------------


class TestSankeyAggregation:
    """Validate Sankey/trajectory output format."""

    def test_sankey_has_nodes_and_links(self, generator: DemoDataGenerator) -> None:
        s = generator.get_trajectories(hours=168)
        assert len(s["nodes"]) >= 8
        assert len(s["links"]) >= 10

    def test_sankey_link_format(self, generator: DemoDataGenerator) -> None:
        link = generator.get_trajectories(hours=168)["links"][0]
        assert all(k in link for k in ["source", "target", "value"])

    def test_sankey_node_has_color(self, generator: DemoDataGenerator) -> None:
        node = generator.get_trajectories(hours=168)["nodes"][0]
        assert "nodeColor" in node
        assert node["nodeColor"].startswith("#")

    def test_sankey_has_loop_traces(self, generator: DemoDataGenerator) -> None:
        s = generator.get_trajectories(hours=168)
        assert "loopTraces" in s


# ---------------------------------------------------------------------------
# Dashboard KPIs
# ---------------------------------------------------------------------------


class TestDashboardKPIs:
    """Validate KPI response format."""

    def test_kpis_have_required_fields(self, generator: DemoDataGenerator) -> None:
        kpis = generator.get_dashboard_kpis(hours=168)["kpis"]
        required = {
            "totalSessions",
            "avgTurns",
            "rootInvocations",
            "errorRate",
            "totalSessionsTrend",
            "avgTurnsTrend",
            "rootInvocationsTrend",
            "errorRateTrend",
        }
        assert required.issubset(kpis.keys())

    def test_kpis_have_positive_counts(self, generator: DemoDataGenerator) -> None:
        kpis = generator.get_dashboard_kpis(hours=168)["kpis"]
        assert kpis["totalSessions"] > 0
        assert kpis["rootInvocations"] > 0
        assert kpis["avgTurns"] > 0

    def test_kpis_error_rate_is_fraction(self, generator: DemoDataGenerator) -> None:
        kpis = generator.get_dashboard_kpis(hours=168)["kpis"]
        assert 0.0 <= kpis["errorRate"] <= 1.0


# ---------------------------------------------------------------------------
# Dashboard Timeseries
# ---------------------------------------------------------------------------


class TestDashboardTimeseries:
    """Validate timeseries response format."""

    def test_timeseries_has_all_series(self, generator: DemoDataGenerator) -> None:
        ts = generator.get_dashboard_timeseries(hours=168)
        assert "latency" in ts
        assert "qps" in ts
        assert "tokens" in ts

    def test_latency_series_format(self, generator: DemoDataGenerator) -> None:
        ts = generator.get_dashboard_timeseries(hours=168)
        entry = ts["latency"][0]
        assert all(k in entry for k in ["timestamp", "p50", "p95"])

    def test_qps_series_format(self, generator: DemoDataGenerator) -> None:
        ts = generator.get_dashboard_timeseries(hours=168)
        entry = ts["qps"][0]
        assert all(k in entry for k in ["timestamp", "qps", "errorRate"])

    def test_token_series_format(self, generator: DemoDataGenerator) -> None:
        ts = generator.get_dashboard_timeseries(hours=168)
        entry = ts["tokens"][0]
        assert all(k in entry for k in ["timestamp", "input", "output"])


# ---------------------------------------------------------------------------
# Dashboard Models & Tools
# ---------------------------------------------------------------------------


class TestDashboardModels:
    """Validate model call statistics format."""

    def test_model_calls_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_dashboard_models(hours=168)
        assert "modelCalls" in result
        entry = result["modelCalls"][0]
        required = {
            "modelName",
            "totalCalls",
            "p95Duration",
            "errorRate",
            "quotaExits",
            "tokensUsed",
        }
        assert required.issubset(entry.keys())

    def test_model_calls_have_known_models(self, generator: DemoDataGenerator) -> None:
        result = generator.get_dashboard_models(hours=168)
        model_names = {e["modelName"] for e in result["modelCalls"]}
        assert "gemini-2.5-flash" in model_names


class TestDashboardTools:
    """Validate tool call statistics format."""

    def test_tool_calls_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_dashboard_tools(hours=168)
        assert "toolCalls" in result
        entry = result["toolCalls"][0]
        required = {"toolName", "totalCalls", "p95Duration", "errorRate"}
        assert required.issubset(entry.keys())


# ---------------------------------------------------------------------------
# Dashboard Logs, Sessions, Traces
# ---------------------------------------------------------------------------


class TestDashboardLogs:
    """Validate agent logs format."""

    def test_logs_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_dashboard_logs(hours=168, limit=10)
        assert "agentLogs" in result
        entry = result["agentLogs"][0]
        required = {
            "timestamp",
            "agentId",
            "severity",
            "message",
            "traceId",
            "spanId",
            "agentName",
            "resourceId",
        }
        assert required.issubset(entry.keys())

    def test_logs_limit(self, generator: DemoDataGenerator) -> None:
        result = generator.get_dashboard_logs(hours=168, limit=5)
        assert len(result["agentLogs"]) <= 5


class TestDashboardSessions:
    """Validate session list format."""

    def test_sessions_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_dashboard_sessions(hours=168, limit=10)
        assert "agentSessions" in result
        entry = result["agentSessions"][0]
        required = {
            "timestamp",
            "sessionId",
            "turns",
            "latestTraceId",
            "totalTokens",
            "errorCount",
            "avgLatencyMs",
            "p95LatencyMs",
            "agentName",
            "resourceId",
            "spanCount",
            "llmCallCount",
            "toolCallCount",
            "toolErrorCount",
            "llmErrorCount",
        }
        assert required.issubset(entry.keys())


class TestDashboardTraces:
    """Validate trace list format."""

    def test_traces_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_dashboard_traces(hours=168, limit=10)
        assert "agentTraces" in result
        entry = result["agentTraces"][0]
        required = {
            "timestamp",
            "traceId",
            "sessionId",
            "totalTokens",
            "errorCount",
            "latencyMs",
            "agentName",
            "resourceId",
            "spanCount",
            "llmCallCount",
            "toolCallCount",
            "toolErrorCount",
            "llmErrorCount",
        }
        assert required.issubset(entry.keys())


# ---------------------------------------------------------------------------
# Registry Endpoints
# ---------------------------------------------------------------------------


class TestRegistryAgents:
    """Validate agent registry format."""

    def test_registry_agents_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_registry_agents(hours=168)
        assert "agents" in result
        entry = result["agents"][0]
        required = {
            "serviceName",
            "agentId",
            "agentName",
            "totalSessions",
            "totalTurns",
            "inputTokens",
            "outputTokens",
            "errorCount",
            "errorRate",
            "p50DurationMs",
            "p95DurationMs",
        }
        assert required.issubset(entry.keys())

    def test_registry_has_root_agent(self, generator: DemoDataGenerator) -> None:
        result = generator.get_registry_agents(hours=168)
        names = {a["agentName"] for a in result["agents"]}
        assert "cymbal-assistant" in names


class TestRegistryTools:
    """Validate tool registry format."""

    def test_registry_tools_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_registry_tools(hours=168)
        assert "tools" in result
        entry = result["tools"][0]
        required = {
            "serviceName",
            "toolId",
            "toolName",
            "executionCount",
            "errorCount",
            "errorRate",
            "avgDurationMs",
            "p95DurationMs",
        }
        assert required.issubset(entry.keys())


# ---------------------------------------------------------------------------
# Detail Endpoints
# ---------------------------------------------------------------------------


class TestSpanDetails:
    """Validate span detail format."""

    def test_span_details_format(self, generator: DemoDataGenerator) -> None:
        trace = generator.get_all_traces()[0]
        span = trace["spans"][0]
        result = generator.get_span_details(trace["trace_id"], span["span_id"])
        required = {
            "traceId",
            "spanId",
            "statusCode",
            "statusMessage",
            "exceptions",
            "attributes",
        }
        assert required.issubset(result.keys())

    def test_span_details_not_found(self, generator: DemoDataGenerator) -> None:
        result = generator.get_span_details("nonexistent", "nonexistent")
        assert result["statusMessage"] == "span not found"


class TestTraceLogs:
    """Validate trace log format."""

    def test_trace_logs_format(self, generator: DemoDataGenerator) -> None:
        trace = generator.get_all_traces()[0]
        result = generator.get_trace_logs(trace["trace_id"])
        assert "traceId" in result
        assert "logs" in result
        assert len(result["logs"]) > 0
        entry = result["logs"][0]
        assert all(k in entry for k in ["timestamp", "severity", "payload"])

    def test_trace_logs_not_found(self, generator: DemoDataGenerator) -> None:
        result = generator.get_trace_logs("nonexistent_trace")
        assert result["logs"] == []


# ---------------------------------------------------------------------------
# Node & Edge Detail
# ---------------------------------------------------------------------------


class TestNodeDetail:
    """Validate node detail format."""

    def test_node_detail_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_node_detail("cymbal-assistant", hours=168)
        required = {
            "nodeId",
            "nodeType",
            "label",
            "totalInvocations",
            "errorRate",
            "errorCount",
            "inputTokens",
            "outputTokens",
            "estimatedCost",
            "latency",
            "topErrors",
            "recentPayloads",
        }
        assert required.issubset(result.keys())
        assert "p50" in result["latency"]
        assert "p95" in result["latency"]
        assert "p99" in result["latency"]

    def test_node_detail_recent_payloads(self, generator: DemoDataGenerator) -> None:
        result = generator.get_node_detail("cymbal-assistant", hours=168)
        assert len(result["recentPayloads"]) > 0
        payload = result["recentPayloads"][0]
        required = {
            "traceId",
            "spanId",
            "timestamp",
            "nodeType",
            "prompt",
            "completion",
            "toolInput",
            "toolOutput",
        }
        assert required.issubset(payload.keys())


class TestEdgeDetail:
    """Validate edge detail format."""

    def test_edge_detail_format(self, generator: DemoDataGenerator) -> None:
        result = generator.get_edge_detail(
            "cymbal-assistant", "product-discovery", hours=168
        )
        required = {
            "sourceId",
            "targetId",
            "callCount",
            "errorCount",
            "errorRate",
            "avgDurationMs",
            "p95DurationMs",
            "p99DurationMs",
            "totalTokens",
            "inputTokens",
            "outputTokens",
        }
        assert required.issubset(result.keys())


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Verify that two generators with the same seed produce identical data."""

    def test_same_data_each_time(self) -> None:
        g1, g2 = DemoDataGenerator(), DemoDataGenerator()
        assert g1.get_sessions()[0]["session_id"] == g2.get_sessions()[0]["session_id"]
        assert g1.get_all_traces()[0]["trace_id"] == g2.get_all_traces()[0]["trace_id"]

    def test_different_seed_different_data(self) -> None:
        g1 = DemoDataGenerator(seed=42)
        g2 = DemoDataGenerator(seed=99)
        assert g1.get_sessions()[0]["session_id"] != g2.get_sessions()[0]["session_id"]
