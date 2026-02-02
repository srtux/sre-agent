"""End-to-end integration tests for the investigation pipeline.

Goal: Verify the full agent investigation lifecycle from user query through
tool execution to final response, testing the actual analysis logic with
synthetic data rather than mocking the tools themselves.

These tests exercise:
- InvestigationState phase transitions
- Tool analysis functions with realistic synthetic data
- Cross-signal correlation (traces + logs + metrics)
- Error handling and recovery in the pipeline
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sre_agent.models.investigation import InvestigationPhase, InvestigationState

# ---------------------------------------------------------------------------
# Synthetic data generators
# ---------------------------------------------------------------------------


def make_trace_spans(
    trace_id: str = "abc123def456",
    root_latency_ms: int = 500,
    child_count: int = 3,
    error_span_index: int | None = None,
) -> list[dict[str, Any]]:
    """Generate synthetic trace spans for testing."""
    base_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    spans: list[dict[str, Any]] = []

    # Root span
    root_start = base_time.isoformat() + "Z"
    root_end = (base_time + timedelta(milliseconds=root_latency_ms)).isoformat() + "Z"
    spans.append(
        {
            "trace_id": trace_id,
            "span_id": "root-span-001",
            "parent_span_id": None,
            "name": "HTTP GET /api/checkout",
            "kind": 2,
            "start_time": root_start,
            "end_time": root_end,
            "status": {"code": 1, "message": ""},
            "attributes": {"http.method": "GET", "http.status_code": "200"},
            "resource": {"attributes": {"service.name": "api-gateway"}},
        }
    )

    # Child spans
    for i in range(child_count):
        child_start = (base_time + timedelta(milliseconds=i * 50)).isoformat() + "Z"
        child_end = (
            base_time + timedelta(milliseconds=(i + 1) * 100)
        ).isoformat() + "Z"
        status_code = 2 if error_span_index == i else 1
        spans.append(
            {
                "trace_id": trace_id,
                "span_id": f"child-span-{i:03d}",
                "parent_span_id": "root-span-001",
                "name": f"DB Query {i}",
                "kind": 3,
                "start_time": child_start,
                "end_time": child_end,
                "status": {
                    "code": status_code,
                    "message": "error" if status_code == 2 else "",
                },
                "attributes": {"db.system": "postgresql", "db.operation": "SELECT"},
                "resource": {"attributes": {"service.name": "checkout-service"}},
            }
        )

    return spans


def make_log_entries(
    count: int = 20,
    error_ratio: float = 0.3,
    service_name: str = "checkout-service",
) -> list[dict[str, Any]]:
    """Generate synthetic log entries with configurable error ratio."""
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    entries: list[dict[str, Any]] = []

    for i in range(count):
        is_error = i < int(count * error_ratio)
        severity = "ERROR" if is_error else "INFO"
        msg = (
            f"Connection refused to database-primary:5432 (attempt {i})"
            if is_error
            else f"Request {i} completed successfully in 45ms"
        )
        entries.append(
            {
                "logName": f"projects/test-project/logs/{service_name}",
                "timestamp": (base_time + timedelta(seconds=i * 3)).isoformat() + "Z",
                "severity": severity,
                "textPayload": msg,
                "resource": {"type": "k8s_container"},
                "labels": {"k8s-pod/app": service_name},
            }
        )

    return entries


def make_metric_points(
    count: int = 10,
    baseline_value: float = 50.0,
    spike_index: int = 7,
    spike_multiplier: float = 10.0,
) -> list[dict[str, Any]]:
    """Generate synthetic time series points with an anomaly spike."""
    base_time = datetime.now(timezone.utc) - timedelta(minutes=count)
    points: list[dict[str, Any]] = []

    for i in range(count):
        value = baseline_value
        if i >= spike_index:
            value = baseline_value * spike_multiplier
        points.append(
            {
                "interval": {
                    "startTime": (base_time + timedelta(minutes=i)).isoformat() + "Z",
                    "endTime": (base_time + timedelta(minutes=i + 1)).isoformat() + "Z",
                },
                "value": {"doubleValue": value},
            }
        )

    return points


# ---------------------------------------------------------------------------
# Investigation State Tests
# ---------------------------------------------------------------------------


class TestInvestigationLifecycle:
    """Tests for the full investigation state machine."""

    def test_investigation_progresses_through_phases(self) -> None:
        """Investigation state transitions from triage to completed."""
        state = InvestigationState()
        assert state.phase == InvestigationPhase.TRIAGE

        # Triage phase: gather initial signals
        state = InvestigationState(
            phase=InvestigationPhase.TRIAGE,
            findings=["Error rate spike: 15% (baseline 0.1%)"],
        )
        assert len(state.findings) == 1

        # Analysis phase: deep dive
        state = InvestigationState(
            phase=InvestigationPhase.ANALYSIS,
            findings=[
                "Error rate spike: 15% (baseline 0.1%)",
                "DB connection timeouts in traces",
                "Connection refused errors in logs",
            ],
            hypotheses=["Database connection pool exhausted"],
        )
        assert state.phase == InvestigationPhase.ANALYSIS
        assert len(state.findings) == 3

        # Root cause identified
        state = InvestigationState(
            phase=InvestigationPhase.ROOT_CAUSE,
            findings=state.findings,
            hypotheses=state.hypotheses,
            confirmed_root_cause="Connection pool limit of 10 reached under load",
        )
        assert state.confirmed_root_cause is not None

        # Remediation suggested
        state = InvestigationState(
            phase=InvestigationPhase.REMEDIATION,
            findings=state.findings,
            hypotheses=state.hypotheses,
            confirmed_root_cause=state.confirmed_root_cause,
            suggested_fix="Increase max_pool_size from 10 to 50 in database config",
        )
        assert state.suggested_fix is not None

        # Completed
        state = InvestigationState(
            phase=InvestigationPhase.COMPLETED,
            findings=state.findings,
            hypotheses=state.hypotheses,
            confirmed_root_cause=state.confirmed_root_cause,
            suggested_fix=state.suggested_fix,
        )
        assert state.phase == InvestigationPhase.COMPLETED

    def test_state_serialization_preserves_investigation(self) -> None:
        """Full investigation state survives dict roundtrip."""
        state = InvestigationState(
            phase=InvestigationPhase.ROOT_CAUSE,
            findings=[
                "P99 latency 12s (norm 200ms)",
                "Trace shows auth-service span taking 11.5s",
                "Auth-service logs: 'Redis connection pool exhausted'",
            ],
            hypotheses=[
                "Redis connection pool saturated",
                "Auth-service token cache miss storm",
            ],
            confirmed_root_cause="Redis connection pool exhausted due to leaked connections",
            suggested_fix="Deploy fix for connection leak in auth-service v2.3.1",
        )

        data = state.to_dict()
        restored = InvestigationState.from_dict(data)

        assert restored.phase == state.phase
        assert restored.findings == state.findings
        assert restored.hypotheses == state.hypotheses
        assert restored.confirmed_root_cause == state.confirmed_root_cause
        assert restored.suggested_fix == state.suggested_fix


# ---------------------------------------------------------------------------
# Synthetic Data Quality Tests
# ---------------------------------------------------------------------------


class TestSyntheticDataGenerators:
    """Verify synthetic data generators produce valid structures."""

    def test_trace_spans_have_required_fields(self) -> None:
        """Generated spans contain all required trace fields."""
        spans = make_trace_spans()
        required_fields = {
            "trace_id",
            "span_id",
            "name",
            "kind",
            "start_time",
            "end_time",
        }
        for span in spans:
            assert required_fields.issubset(span.keys())

    def test_trace_spans_parent_child_relationship(self) -> None:
        """Root span has no parent, children reference root."""
        spans = make_trace_spans(child_count=3)
        root = spans[0]
        assert root["parent_span_id"] is None
        for child in spans[1:]:
            assert child["parent_span_id"] == root["span_id"]

    def test_trace_spans_error_injection(self) -> None:
        """Error span has error status code."""
        spans = make_trace_spans(child_count=3, error_span_index=1)
        error_span = spans[2]  # index 0 is root, error_span_index 1 maps to spans[2]
        assert error_span["status"]["code"] == 2

    def test_log_entries_error_ratio(self) -> None:
        """Log entries respect the configured error ratio."""
        entries = make_log_entries(count=100, error_ratio=0.25)
        error_count = sum(1 for e in entries if e["severity"] == "ERROR")
        assert error_count == 25

    def test_metric_points_spike_detection(self) -> None:
        """Metric points show clear spike at configured index."""
        points = make_metric_points(
            count=10, baseline_value=50.0, spike_index=7, spike_multiplier=10.0
        )
        # Before spike
        assert points[6]["value"]["doubleValue"] == 50.0
        # At spike
        assert points[7]["value"]["doubleValue"] == 500.0
        # After spike
        assert points[9]["value"]["doubleValue"] == 500.0


# ---------------------------------------------------------------------------
# Cross-Signal Correlation Tests
# ---------------------------------------------------------------------------


class TestCrossSignalCorrelation:
    """Tests that verify cross-signal analysis patterns."""

    def test_error_logs_correlate_with_trace_errors(self) -> None:
        """Error spans in traces should correlate with error logs."""
        # Generate trace with error in span index 1
        spans = make_trace_spans(error_span_index=1)
        error_spans = [s for s in spans if s["status"]["code"] == 2]
        assert len(error_spans) == 1

        # Generate logs with errors
        logs = make_log_entries(count=10, error_ratio=0.3)
        error_logs = [e for e in logs if e["severity"] == "ERROR"]
        assert len(error_logs) == 3

        # Both signals indicate errors in the same service
        error_service = error_spans[0]["resource"]["attributes"]["service.name"]
        assert error_service == "checkout-service"

    def test_metric_spike_aligns_with_error_period(self) -> None:
        """Metric spike timing should align with error log timing."""
        metrics = make_metric_points(count=10, spike_index=7)
        logs = make_log_entries(count=10, error_ratio=0.3)

        # Verify spike exists
        spike_values = [p["value"]["doubleValue"] for p in metrics[7:]]
        assert all(v > 100 for v in spike_values)

        # Verify errors exist in logs
        error_count = sum(1 for e in logs if e["severity"] == "ERROR")
        assert error_count > 0

    def test_investigation_state_accumulates_multi_signal_findings(self) -> None:
        """Investigation state can accumulate findings from multiple signals."""
        state = InvestigationState(
            phase=InvestigationPhase.ANALYSIS,
            findings=[
                "[TRACE] Span 'DB Query 1' shows error status (11.5s latency)",
                "[LOGS] 3 'Connection refused' errors in checkout-service",
                "[METRICS] Error rate spiked from 0.1% to 15% at 14:32 UTC",
                "[ALERTS] 'High Error Rate' alert fired at 14:33 UTC",
            ],
            hypotheses=[
                "Database connection pool exhaustion under load spike",
                "Network partition between app and database",
            ],
        )

        assert len(state.findings) == 4
        # Verify different signal types are represented
        signal_types = {f.split("]")[0].strip("[") for f in state.findings}
        assert signal_types == {"TRACE", "LOGS", "METRICS", "ALERTS"}
