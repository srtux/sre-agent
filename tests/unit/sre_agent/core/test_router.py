"""Tests for the SRE Agent Router tool.

Validates that the route_request @adk_tool correctly classifies queries
into the 3-tier routing system and returns proper BaseToolResponse with
actionable guidance.
"""

import pytest

from sre_agent.core.router import route_request


class TestRouteRequestDirect:
    """Tests for DIRECT tier routing via the tool."""

    @pytest.mark.asyncio
    async def test_direct_tier_for_log_retrieval(self) -> None:
        """Log retrieval queries should return DIRECT tier."""
        result = await route_request(query="show me the logs for checkout-service")
        assert result.status.value == "success"
        assert result.result["decision"] == "direct"
        assert "suggested_tools" in result.result
        assert len(result.result["suggested_tools"]) > 0

    @pytest.mark.asyncio
    async def test_direct_tier_for_alert_listing(self) -> None:
        """Alert listing queries should return DIRECT tier."""
        result = await route_request(query="list all alerts")
        assert result.status.value == "success"
        assert result.result["decision"] == "direct"
        assert "list_alerts" in result.result["suggested_tools"]

    @pytest.mark.asyncio
    async def test_direct_tier_for_trace_fetch(self) -> None:
        """Trace fetch queries should return DIRECT tier."""
        result = await route_request(query="get the traces for the API")
        assert result.status.value == "success"
        assert result.result["decision"] == "direct"

    @pytest.mark.asyncio
    async def test_direct_includes_guidance(self) -> None:
        """DIRECT tier should include actionable guidance."""
        result = await route_request(query="show me the metrics for CPU")
        assert result.status.value == "success"
        assert "guidance" in result.result
        assert "Do NOT delegate" in result.result["guidance"]


class TestRouteRequestSubAgent:
    """Tests for SUB_AGENT tier routing via the tool."""

    @pytest.mark.asyncio
    async def test_sub_agent_tier_for_analysis(self) -> None:
        """Analysis queries should return SUB_AGENT tier."""
        result = await route_request(query="analyze the trace for latency bottlenecks")
        assert result.status.value == "success"
        assert result.result["decision"] == "sub_agent"
        assert "suggested_agent" in result.result
        assert result.result["suggested_agent"] != ""

    @pytest.mark.asyncio
    async def test_sub_agent_tier_for_anomaly_detection(self) -> None:
        """Anomaly detection queries should return SUB_AGENT tier."""
        result = await route_request(query="detect anomalies in the CPU metrics")
        assert result.status.value == "success"
        assert result.result["decision"] == "sub_agent"

    @pytest.mark.asyncio
    async def test_sub_agent_includes_guidance(self) -> None:
        """SUB_AGENT tier should include agent delegation guidance."""
        result = await route_request(query="analyze this trace for bottlenecks")
        assert result.status.value == "success"
        assert "guidance" in result.result
        assert "Delegate" in result.result["guidance"]


class TestRouteRequestCouncil:
    """Tests for COUNCIL tier routing via the tool."""

    @pytest.mark.asyncio
    async def test_council_tier_for_root_cause(self) -> None:
        """Root cause analysis should return COUNCIL tier."""
        result = await route_request(query="find the root cause of the latency spike")
        assert result.status.value == "success"
        assert result.result["decision"] == "council"
        assert "investigation_mode" in result.result

    @pytest.mark.asyncio
    async def test_council_tier_for_incident(self) -> None:
        """Incident investigation should return COUNCIL tier."""
        result = await route_request(
            query="P0 incident: payment service is down"
        )
        assert result.status.value == "success"
        assert result.result["decision"] == "council"

    @pytest.mark.asyncio
    async def test_council_includes_guidance(self) -> None:
        """COUNCIL tier should include investigation guidance."""
        result = await route_request(query="root cause of the outage")
        assert result.status.value == "success"
        assert "guidance" in result.result
        assert "council investigation" in result.result["guidance"].lower() or "run_council_investigation" in result.result["guidance"]


class TestRouteRequestMetadata:
    """Tests for router tool metadata and response structure."""

    @pytest.mark.asyncio
    async def test_includes_signal_type(self) -> None:
        """All responses should include a signal_type."""
        result = await route_request(query="show me the alerts")
        assert "signal_type" in result.result
        assert result.result["signal_type"] in ("trace", "metrics", "logs", "alerts")

    @pytest.mark.asyncio
    async def test_includes_original_query(self) -> None:
        """All responses should include the original query."""
        query = "list the log entries"
        result = await route_request(query=query)
        assert result.result["query"] == query

    @pytest.mark.asyncio
    async def test_includes_description(self) -> None:
        """All responses should include a tier description."""
        result = await route_request(query="analyze the metrics")
        assert "description" in result.result
        assert isinstance(result.result["description"], str)

    @pytest.mark.asyncio
    async def test_metadata_contains_router_type(self) -> None:
        """Metadata should indicate the router type."""
        result = await route_request(query="test query")
        assert result.metadata["router"] == "rule_based"

    @pytest.mark.asyncio
    async def test_metadata_contains_tier(self) -> None:
        """Metadata should include the routing tier."""
        result = await route_request(query="show me the logs")
        assert "tier" in result.metadata
        assert result.metadata["tier"] in ("direct", "sub_agent", "council")
