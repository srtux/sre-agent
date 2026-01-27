"""Tests for metrics sub-agent."""

from sre_agent.sub_agents.metrics import get_metrics_analyzer


def test_metrics_analyzer_initialization():
    agent = get_metrics_analyzer()
    assert agent.name == "metrics_analyzer"
    assert "metrics" in agent.description


def test_metrics_analyzer_tools():
    agent = get_metrics_analyzer()
    tool_names = [getattr(t, "name", t.__name__) for t in agent.tools]
    assert "list_time_series" in tool_names
    assert "query_promql" in tool_names
    assert "detect_metric_anomalies" in tool_names
    assert "compare_metric_windows" in tool_names
    assert "calculate_series_stats" in tool_names
