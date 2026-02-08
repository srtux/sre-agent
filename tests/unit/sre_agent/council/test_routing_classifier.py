"""Tests for the 3-tier routing classification in the intent classifier.

Validates that queries are correctly routed to the appropriate tier:
- DIRECT: Simple data retrieval (logs, metrics, traces, alerts)
- SUB_AGENT: Focused analysis (anomaly detection, pattern analysis)
- COUNCIL: Complex multi-signal investigation (root cause, incidents)
"""

import pytest

from sre_agent.council.intent_classifier import (
    SignalType,
    classify_routing,
)
from sre_agent.council.schemas import InvestigationMode, RoutingDecision


class TestDirectRouting:
    """Tests for DIRECT tier routing (simple data retrieval)."""

    @pytest.mark.parametrize(
        "query",
        [
            "show me the logs for payment-service",
            "list all alerts",
            "get trace abc123def456",
            "fetch the metrics for checkout-service",
            "display the traces from the last hour",
            "show me the log entries for namespace default",
            "list the alert policies",
            "view the metrics for CPU usage",
            "pull logs from the auth service",
        ],
    )
    def test_direct_retrieval_queries(self, query: str) -> None:
        """Simple retrieval queries should route to DIRECT tier."""
        result = classify_routing(query)
        assert result.decision == RoutingDecision.DIRECT

    def test_direct_returns_suggested_tools(self) -> None:
        """DIRECT routing should include suggested tool names."""
        result = classify_routing("show me the logs for payment-service")
        assert result.decision == RoutingDecision.DIRECT
        assert len(result.suggested_tools) > 0

    def test_direct_logs_suggests_log_tools(self) -> None:
        """Log retrieval queries should suggest log-related tools."""
        result = classify_routing("show me the log entries for checkout-service")
        assert result.decision == RoutingDecision.DIRECT
        assert result.signal_type == SignalType.LOGS
        assert "list_log_entries" in result.suggested_tools

    def test_direct_traces_suggests_trace_tools(self) -> None:
        """Trace retrieval queries should suggest trace-related tools."""
        result = classify_routing("get the traces for the API gateway")
        assert result.decision == RoutingDecision.DIRECT
        assert result.signal_type == SignalType.TRACE
        assert (
            "fetch_trace" in result.suggested_tools
            or "list_traces" in result.suggested_tools
        )

    def test_direct_metrics_suggests_metric_tools(self) -> None:
        """Metric retrieval queries should suggest metric-related tools."""
        result = classify_routing("list the time series for CPU utilization")
        assert result.decision == RoutingDecision.DIRECT
        assert result.signal_type == SignalType.METRICS
        assert (
            "list_time_series" in result.suggested_tools
            or "query_promql" in result.suggested_tools
        )

    def test_direct_alerts_suggests_alert_tools(self) -> None:
        """Alert retrieval queries should suggest alert-related tools."""
        result = classify_routing("show me the alerts that are firing")
        assert result.decision == RoutingDecision.DIRECT
        assert result.signal_type == SignalType.ALERTS
        assert "list_alerts" in result.suggested_tools


class TestSubAgentRouting:
    """Tests for SUB_AGENT tier routing (focused analysis)."""

    @pytest.mark.parametrize(
        "query",
        [
            "analyze this trace for bottlenecks",
            "detect anomalies in the metrics",
            "find patterns in the error logs",
            "compare the log patterns before and after deployment",
            "correlate traces with metrics",
            "diagnose the latency issue",
            "identify the trend in error rates",
            "debug the connection timeout issue",
            "troubleshoot the pod restart loop",
        ],
    )
    def test_analysis_queries(self, query: str) -> None:
        """Analysis queries should route to SUB_AGENT tier."""
        result = classify_routing(query)
        assert result.decision == RoutingDecision.SUB_AGENT

    def test_sub_agent_returns_suggested_agent(self) -> None:
        """SUB_AGENT routing should include a suggested agent name."""
        result = classify_routing("analyze this trace for latency bottlenecks")
        assert result.decision == RoutingDecision.SUB_AGENT
        assert result.suggested_agent != ""

    def test_trace_analysis_suggests_trace_analyst(self) -> None:
        """Trace analysis queries should suggest the trace_analyst."""
        result = classify_routing("analyze the trace latency and spans")
        assert result.decision == RoutingDecision.SUB_AGENT
        assert result.suggested_agent == "trace_analyst"

    def test_log_analysis_suggests_log_analyst(self) -> None:
        """Log analysis queries should suggest the log_analyst."""
        result = classify_routing("analyze the log patterns for errors")
        assert result.decision == RoutingDecision.SUB_AGENT
        assert result.suggested_agent == "log_analyst"

    def test_metric_analysis_suggests_metrics_analyzer(self) -> None:
        """Metric analysis queries should suggest the metrics_analyzer."""
        result = classify_routing("detect anomalies in CPU metrics")
        assert result.decision == RoutingDecision.SUB_AGENT
        assert result.suggested_agent == "metrics_analyzer"

    def test_alert_analysis_suggests_alert_analyst(self) -> None:
        """Alert analysis queries should suggest the alert_analyst."""
        result = classify_routing("analyze the alert policies for issues")
        assert result.decision == RoutingDecision.SUB_AGENT
        assert result.suggested_agent == "alert_analyst"


class TestCouncilRouting:
    """Tests for COUNCIL tier routing (complex multi-signal investigation)."""

    @pytest.mark.parametrize(
        "query",
        [
            "find the root cause of the latency spike",
            "deep dive into the checkout failure",
            "we have a production incident on payment-service",
            "this is a P0 - payments are failing",
            "sev1 alert on the API gateway",
            "what caused the outage at 2pm?",
            "why is the service failing?",
            "investigate the error rate spike",
            "comprehensive analysis of the system",
            "emergency - database connections exhausted",
            "blast radius of the auth-service failure",
            "thorough analysis of the latency",
            "we need a postmortem on yesterday's incident",
        ],
    )
    def test_council_investigation_queries(self, query: str) -> None:
        """Complex investigation queries should route to COUNCIL tier."""
        result = classify_routing(query)
        assert result.decision == RoutingDecision.COUNCIL

    def test_council_returns_investigation_mode(self) -> None:
        """COUNCIL routing should include an investigation mode."""
        result = classify_routing("find the root cause of the latency spike")
        assert result.decision == RoutingDecision.COUNCIL
        assert result.investigation_mode in (
            InvestigationMode.FAST,
            InvestigationMode.STANDARD,
            InvestigationMode.DEBATE,
        )

    def test_council_debate_mode_for_incidents(self) -> None:
        """P0/P1 incident queries should use DEBATE investigation mode."""
        result = classify_routing("P0 incident: payments are down")
        assert result.decision == RoutingDecision.COUNCIL
        assert result.investigation_mode == InvestigationMode.DEBATE


class TestRoutingPriority:
    """Tests for routing priority order."""

    def test_council_takes_priority_over_analysis(self) -> None:
        """Council keywords should win over analysis keywords."""
        query = "analyze the root cause of the incident"
        result = classify_routing(query)
        assert result.decision == RoutingDecision.COUNCIL

    def test_council_takes_priority_over_direct(self) -> None:
        """Council keywords should win over direct keywords."""
        query = "show me the root cause of the outage"
        result = classify_routing(query)
        assert result.decision == RoutingDecision.COUNCIL

    def test_analysis_takes_priority_over_direct(self) -> None:
        """Analysis keywords should win over direct keywords."""
        query = "analyze the logs for patterns"
        result = classify_routing(query)
        assert result.decision == RoutingDecision.SUB_AGENT


class TestRoutingEdgeCases:
    """Tests for edge cases in routing classification."""

    def test_empty_query_defaults_to_sub_agent(self) -> None:
        """Empty query should default to SUB_AGENT."""
        result = classify_routing("")
        assert result.decision == RoutingDecision.SUB_AGENT

    def test_generic_question_defaults_to_sub_agent(self) -> None:
        """Generic questions should default to SUB_AGENT."""
        result = classify_routing("how are the services performing today?")
        assert result.decision == RoutingDecision.SUB_AGENT

    def test_routing_result_is_frozen(self) -> None:
        """RoutingResult should be a frozen dataclass."""
        result = classify_routing("show me the logs")
        with pytest.raises(AttributeError):
            result.decision = RoutingDecision.COUNCIL  # type: ignore[misc]

    def test_routing_result_has_signal_type(self) -> None:
        """All routing results should include a signal_type."""
        result = classify_routing("show me the alerts")
        assert isinstance(result.signal_type, SignalType)

    def test_direct_query_with_trace_id_pattern(self) -> None:
        """Query with trace ID should route to DIRECT."""
        result = classify_routing("trace 1234abcd5678ef90")
        assert result.decision == RoutingDecision.DIRECT
        assert result.signal_type == SignalType.TRACE
