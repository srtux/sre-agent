"""Tests for council tool registry.

Validates that panel tool sets are correctly defined, non-empty,
and contain callable tool functions.
"""

from sre_agent.council.tool_registry import (
    ALERTS_PANEL_TOOLS,
    LOGS_PANEL_TOOLS,
    METRICS_PANEL_TOOLS,
    TRACE_PANEL_TOOLS,
)


class TestTracePanelTools:
    """Tests for trace panel tool set."""

    def test_non_empty(self) -> None:
        """Trace panel should have tools assigned."""
        assert len(TRACE_PANEL_TOOLS) > 0

    def test_all_callable(self) -> None:
        """All trace panel tools should be callable."""
        for tool in TRACE_PANEL_TOOLS:
            assert callable(tool), f"Tool {tool} is not callable"

    def test_expected_tool_count(self) -> None:
        """Trace panel should have the expected number of tools."""
        # Trace panel has ~23 tools (trace analysis + aggregate + state)
        assert len(TRACE_PANEL_TOOLS) >= 15
        assert len(TRACE_PANEL_TOOLS) <= 30

    def test_contains_primary_tools(self) -> None:
        """Trace panel should contain its primary analysis tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in TRACE_PANEL_TOOLS}
        assert "analyze_trace_comprehensive" in tool_names
        assert "fetch_trace" in tool_names
        assert "analyze_critical_path" in tool_names


class TestMetricsPanelTools:
    """Tests for metrics panel tool set."""

    def test_non_empty(self) -> None:
        """Metrics panel should have tools assigned."""
        assert len(METRICS_PANEL_TOOLS) > 0

    def test_all_callable(self) -> None:
        """All metrics panel tools should be callable."""
        for tool in METRICS_PANEL_TOOLS:
            assert callable(tool), f"Tool {tool} is not callable"

    def test_expected_tool_count(self) -> None:
        """Metrics panel should have the expected number of tools."""
        # Metrics panel has ~14 tools
        assert len(METRICS_PANEL_TOOLS) >= 10
        assert len(METRICS_PANEL_TOOLS) <= 20

    def test_contains_primary_tools(self) -> None:
        """Metrics panel should contain its primary analysis tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in METRICS_PANEL_TOOLS}
        assert "query_promql" in tool_names
        assert "list_time_series" in tool_names
        assert "detect_metric_anomalies" in tool_names


class TestLogsPanelTools:
    """Tests for logs panel tool set."""

    def test_non_empty(self) -> None:
        """Logs panel should have tools assigned."""
        assert len(LOGS_PANEL_TOOLS) > 0

    def test_all_callable(self) -> None:
        """All logs panel tools should be callable."""
        for tool in LOGS_PANEL_TOOLS:
            assert callable(tool), f"Tool {tool} is not callable"

    def test_expected_tool_count(self) -> None:
        """Logs panel should have the expected number of tools."""
        assert len(LOGS_PANEL_TOOLS) >= 5
        assert len(LOGS_PANEL_TOOLS) <= 15

    def test_contains_primary_tools(self) -> None:
        """Logs panel should contain its primary analysis tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in LOGS_PANEL_TOOLS}
        assert "list_log_entries" in tool_names
        assert "analyze_bigquery_log_patterns" in tool_names
        assert "extract_log_patterns" in tool_names

    def test_no_alert_tools(self) -> None:
        """Logs panel should NOT contain alert-specific tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in LOGS_PANEL_TOOLS}
        assert "list_alerts" not in tool_names
        assert "get_alert" not in tool_names


class TestAlertsPanelTools:
    """Tests for alerts panel tool set."""

    def test_non_empty(self) -> None:
        """Alerts panel should have tools assigned."""
        assert len(ALERTS_PANEL_TOOLS) > 0

    def test_all_callable(self) -> None:
        """All alerts panel tools should be callable."""
        for tool in ALERTS_PANEL_TOOLS:
            assert callable(tool), f"Tool {tool} is not callable"

    def test_expected_tool_count(self) -> None:
        """Alerts panel should have the expected number of tools."""
        assert len(ALERTS_PANEL_TOOLS) >= 5
        assert len(ALERTS_PANEL_TOOLS) <= 15

    def test_contains_primary_tools(self) -> None:
        """Alerts panel should contain its primary analysis tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in ALERTS_PANEL_TOOLS}
        assert "list_alerts" in tool_names
        assert "list_alert_policies" in tool_names
        assert "get_alert" in tool_names

    def test_no_log_analysis_tools(self) -> None:
        """Alerts panel should NOT contain log-analysis-specific tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in ALERTS_PANEL_TOOLS}
        assert "analyze_bigquery_log_patterns" not in tool_names
        assert "extract_log_patterns" not in tool_names


class TestToolSetUniqueness:
    """Tests for tool set organization."""

    def test_no_duplicate_tools_in_panels(self) -> None:
        """Each panel should not have duplicate tools within itself."""
        for panel_name, tools in [
            ("trace", TRACE_PANEL_TOOLS),
            ("metrics", METRICS_PANEL_TOOLS),
            ("logs", LOGS_PANEL_TOOLS),
            ("alerts", ALERTS_PANEL_TOOLS),
        ]:
            tool_ids = [id(t) for t in tools]
            assert len(tool_ids) == len(set(tool_ids)), (
                f"Panel '{panel_name}' has duplicate tools"
            )
