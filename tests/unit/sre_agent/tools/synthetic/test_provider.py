"""Tests for the SyntheticDataProvider.

Validates that all synthetic data methods return valid BaseToolResponse
objects with correctly structured payloads matching the tool contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sre_agent.schema import ToolStatus
from sre_agent.tools.synthetic.provider import SyntheticDataProvider
from sre_agent.tools.synthetic.scenarios import DEMO_PROJECT_ID, TRACE_IDS


class TestFetchTrace:
    """Tests for SyntheticDataProvider.fetch_trace."""

    def test_known_trace_returns_success(self) -> None:
        trace_id = TRACE_IDS["checkout_slow_1"]
        result = SyntheticDataProvider.fetch_trace(trace_id)
        assert result.status == ToolStatus.SUCCESS
        assert result.result is not None
        assert result.result["trace_id"] == trace_id

    def test_known_trace_has_spans(self) -> None:
        trace_id = TRACE_IDS["checkout_slow_1"]
        result = SyntheticDataProvider.fetch_trace(trace_id)
        spans = result.result["spans"]
        assert len(spans) > 1
        # Verify span structure
        for span in spans:
            assert "span_id" in span
            assert "name" in span
            assert "start_time" in span
            assert "end_time" in span
            assert "labels" in span

    def test_error_trace_has_error_labels(self) -> None:
        trace_id = TRACE_IDS["checkout_error_1"]
        result = SyntheticDataProvider.fetch_trace(trace_id)
        spans = result.result["spans"]
        error_spans = [s for s in spans if s.get("labels", {}).get("error") == "true"]
        assert len(error_spans) > 0

    def test_unknown_trace_returns_generic(self) -> None:
        result = SyntheticDataProvider.fetch_trace("unknown_trace_id")
        assert result.status == ToolStatus.SUCCESS
        assert result.result["trace_id"] == "unknown_trace_id"

    def test_trace_has_parent_child_relationships(self) -> None:
        trace_id = TRACE_IDS["checkout_slow_1"]
        result = SyntheticDataProvider.fetch_trace(trace_id)
        spans = result.result["spans"]
        root_spans = [s for s in spans if s["parent_span_id"] is None]
        child_spans = [s for s in spans if s["parent_span_id"] is not None]
        assert len(root_spans) == 1
        assert len(child_spans) >= 1

    def test_trace_timestamps_are_recent(self) -> None:
        trace_id = TRACE_IDS["checkout_slow_1"]
        result = SyntheticDataProvider.fetch_trace(trace_id)
        root_span = result.result["spans"][0]
        start = datetime.fromisoformat(root_span["start_time"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        # Should be within last 2 hours
        delta = (now - start).total_seconds()
        assert 0 < delta < 7200


class TestListTraces:
    """Tests for SyntheticDataProvider.list_traces."""

    def test_returns_success(self) -> None:
        result = SyntheticDataProvider.list_traces()
        assert result.status == ToolStatus.SUCCESS
        assert isinstance(result.result, list)

    def test_respects_limit(self) -> None:
        result = SyntheticDataProvider.list_traces(limit=3)
        assert len(result.result) <= 3

    def test_trace_summaries_have_required_fields(self) -> None:
        result = SyntheticDataProvider.list_traces(limit=5)
        for trace in result.result:
            assert "trace_id" in trace
            assert "name" in trace
            assert "duration_ms" in trace
            assert "start_time" in trace

    def test_error_only_filter(self) -> None:
        result = SyntheticDataProvider.list_traces(error_only=True)
        assert result.status == ToolStatus.SUCCESS
        assert len(result.result) >= 1

    def test_min_latency_filter(self) -> None:
        result = SyntheticDataProvider.list_traces(min_latency_ms=1000)
        for trace in result.result:
            assert trace["duration_ms"] >= 1000


class TestFindExampleTraces:
    """Tests for SyntheticDataProvider.find_example_traces."""

    def test_returns_baseline_and_anomaly(self) -> None:
        result = SyntheticDataProvider.find_example_traces()
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert "baseline" in data
        assert "anomaly" in data
        assert "stats" in data
        assert "validation" in data

    def test_anomaly_has_higher_latency(self) -> None:
        result = SyntheticDataProvider.find_example_traces()
        data = result.result
        assert data["anomaly"]["duration_ms"] > data["baseline"]["duration_ms"]


class TestListLogEntries:
    """Tests for SyntheticDataProvider.list_log_entries."""

    def test_returns_success(self) -> None:
        result = SyntheticDataProvider.list_log_entries()
        assert result.status == ToolStatus.SUCCESS
        assert "entries" in result.result

    def test_entries_have_required_fields(self) -> None:
        result = SyntheticDataProvider.list_log_entries(limit=5)
        for entry in result.result["entries"]:
            assert "timestamp" in entry
            assert "severity" in entry
            assert "payload" in entry
            assert "resource" in entry
            assert "insert_id" in entry

    def test_error_filter_returns_errors(self) -> None:
        result = SyntheticDataProvider.list_log_entries(filter_str="severity>=ERROR")
        for entry in result.result["entries"]:
            assert entry["severity"] in ("ERROR", "CRITICAL")

    def test_checkout_filter(self) -> None:
        result = SyntheticDataProvider.list_log_entries(
            filter_str='resource.labels.container_name="checkout-service"'
        )
        assert len(result.result["entries"]) > 0

    def test_respects_limit(self) -> None:
        result = SyntheticDataProvider.list_log_entries(limit=3)
        assert len(result.result["entries"]) <= 3

    def test_entries_have_trace_correlation(self) -> None:
        result = SyntheticDataProvider.list_log_entries(limit=5)
        entries_with_trace = [
            e
            for e in result.result["entries"]
            if e.get("trace") and "traces/" in e["trace"]
        ]
        assert len(entries_with_trace) > 0


class TestListErrorEvents:
    """Tests for SyntheticDataProvider.list_error_events."""

    def test_returns_events(self) -> None:
        result = SyntheticDataProvider.list_error_events()
        assert result.status == ToolStatus.SUCCESS
        assert isinstance(result.result, list)
        assert len(result.result) > 0

    def test_event_structure(self) -> None:
        result = SyntheticDataProvider.list_error_events()
        for event in result.result:
            assert "event_time" in event
            assert "message" in event
            assert "service_context" in event
            assert "service" in event["service_context"]


class TestListTimeSeries:
    """Tests for SyntheticDataProvider.list_time_series."""

    def test_latency_metrics(self) -> None:
        result = SyntheticDataProvider.list_time_series(
            filter_str='metric.type="custom.googleapis.com/http/server/latency" AND checkout'
        )
        assert result.status == ToolStatus.SUCCESS
        assert isinstance(result.result, list)
        assert len(result.result) > 0

    def test_time_series_has_points(self) -> None:
        result = SyntheticDataProvider.list_time_series(
            filter_str='metric.type="custom.googleapis.com/http/server/latency"'
        )
        series = result.result[0]
        assert "metric" in series
        assert "resource" in series
        assert "points" in series
        assert len(series["points"]) > 0

    def test_points_have_timestamp_and_value(self) -> None:
        result = SyntheticDataProvider.list_time_series(filter_str="latency checkout")
        for point in result.result[0]["points"]:
            assert "timestamp" in point
            assert "value" in point

    def test_connection_pool_metrics(self) -> None:
        result = SyntheticDataProvider.list_time_series(
            filter_str="num_backends connection"
        )
        assert len(result.result) > 0
        assert "postgresql" in result.result[0]["metric"]["type"]


class TestListMetricDescriptors:
    """Tests for SyntheticDataProvider.list_metric_descriptors."""

    def test_returns_descriptors(self) -> None:
        result = SyntheticDataProvider.list_metric_descriptors()
        assert result.status == ToolStatus.SUCCESS
        assert isinstance(result.result, list)
        assert len(result.result) > 0

    def test_descriptor_structure(self) -> None:
        result = SyntheticDataProvider.list_metric_descriptors()
        for desc in result.result:
            assert "type" in desc
            assert "metric_kind" in desc
            assert "description" in desc

    def test_filter_works(self) -> None:
        result = SyntheticDataProvider.list_metric_descriptors(filter_str="latency")
        for desc in result.result:
            assert (
                "latency" in desc["type"].lower()
                or "latenc" in desc["description"].lower()
            )


class TestQueryPromql:
    """Tests for SyntheticDataProvider.query_promql."""

    def test_returns_matrix_format(self) -> None:
        result = SyntheticDataProvider.query_promql(
            query='http_server_request_duration_seconds{service="checkout-service"}'
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert data["status"] == "success"
        assert data["data"]["resultType"] == "matrix"

    def test_has_values(self) -> None:
        result = SyntheticDataProvider.query_promql(query="test")
        values = result.result["data"]["result"][0]["values"]
        assert len(values) > 0
        # Each value is [timestamp, string_value]
        assert len(values[0]) == 2


class TestListAlerts:
    """Tests for SyntheticDataProvider.list_alerts."""

    def test_returns_alerts(self) -> None:
        result = SyntheticDataProvider.list_alerts()
        assert result.status == ToolStatus.SUCCESS
        assert isinstance(result.result, list)
        assert len(result.result) >= 3

    def test_alert_structure(self) -> None:
        result = SyntheticDataProvider.list_alerts()
        for alert in result.result:
            assert "name" in alert
            assert "policy" in alert
            assert "state" in alert
            assert "severity" in alert
            assert "openTime" in alert
            assert "resource" in alert
            assert "metric" in alert

    def test_alerts_are_open(self) -> None:
        result = SyntheticDataProvider.list_alerts()
        for alert in result.result:
            assert alert["state"] == "OPEN"

    def test_alert_times_are_recent(self) -> None:
        result = SyntheticDataProvider.list_alerts()
        now = datetime.now(timezone.utc)
        for alert in result.result:
            open_time = datetime.fromisoformat(alert["openTime"].replace("Z", "+00:00"))
            delta = (now - open_time).total_seconds()
            # Should be within last 2 hours
            assert 0 < delta < 7200


class TestListAlertPolicies:
    """Tests for SyntheticDataProvider.list_alert_policies."""

    def test_returns_policies(self) -> None:
        result = SyntheticDataProvider.list_alert_policies()
        assert result.status == ToolStatus.SUCCESS
        assert isinstance(result.result, list)
        assert len(result.result) >= 3

    def test_policy_structure(self) -> None:
        result = SyntheticDataProvider.list_alert_policies()
        for policy in result.result:
            assert "name" in policy
            assert "display_name" in policy
            assert "conditions" in policy
            assert "enabled" in policy


class TestGetAlert:
    """Tests for SyntheticDataProvider.get_alert."""

    def test_known_alert(self) -> None:
        name = f"projects/{DEMO_PROJECT_ID}/alerts/alert-checkout-latency-001"
        result = SyntheticDataProvider.get_alert(name)
        assert result.status == ToolStatus.SUCCESS
        assert result.result["name"] == name

    def test_unknown_alert(self) -> None:
        result = SyntheticDataProvider.get_alert("projects/x/alerts/nonexistent")
        assert result.status == ToolStatus.ERROR
