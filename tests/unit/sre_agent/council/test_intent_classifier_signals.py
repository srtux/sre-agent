"""Tests for the signal-type-aware intent classifier.

Validates that:
- classify_intent_with_signal returns ClassificationResult
- FAST mode queries route to the correct signal type panel
- classify_intent backward compatibility is preserved
- Signal type detection works for each domain
"""

import pytest

from sre_agent.council.intent_classifier import (
    ClassificationResult,
    SignalType,
    _detect_signal_type,
    classify_intent,
    classify_intent_with_signal,
)
from sre_agent.council.schemas import InvestigationMode


class TestClassifyIntentWithSignal:
    """Tests for the extended classifier returning ClassificationResult."""

    def test_returns_classification_result(self) -> None:
        """Should return ClassificationResult dataclass."""
        result = classify_intent_with_signal("check the health of my service")
        assert isinstance(result, ClassificationResult)
        assert hasattr(result, "mode")
        assert hasattr(result, "signal_type")

    def test_debate_mode_defaults_to_trace_signal(self) -> None:
        """DEBATE mode should default signal_type to TRACE."""
        result = classify_intent_with_signal("root cause of the outage")
        assert result.mode == InvestigationMode.DEBATE
        assert result.signal_type == SignalType.TRACE

    def test_standard_mode_defaults_to_trace_signal(self) -> None:
        """STANDARD mode should default signal_type to TRACE."""
        result = classify_intent_with_signal(
            "analyze the error rates across services"
        )
        assert result.mode == InvestigationMode.STANDARD
        assert result.signal_type == SignalType.TRACE

    def test_fast_mode_detects_trace_signal(self) -> None:
        """FAST mode with trace keywords should use TRACE signal."""
        result = classify_intent_with_signal("check the latency of api service")
        assert result.mode == InvestigationMode.FAST
        assert result.signal_type == SignalType.TRACE

    def test_fast_mode_detects_metrics_signal(self) -> None:
        """FAST mode with metrics keywords should use METRICS signal."""
        result = classify_intent_with_signal("check cpu utilization now")
        assert result.mode == InvestigationMode.FAST
        assert result.signal_type == SignalType.METRICS

    def test_fast_mode_detects_logs_signal(self) -> None:
        """FAST mode with logs keywords should use LOGS signal."""
        result = classify_intent_with_signal("check log entries for errors")
        assert result.mode == InvestigationMode.FAST
        assert result.signal_type == SignalType.LOGS

    def test_fast_mode_detects_alerts_signal(self) -> None:
        """FAST mode with alert keywords should use ALERTS signal."""
        result = classify_intent_with_signal("check if alerts are firing")
        assert result.mode == InvestigationMode.FAST
        assert result.signal_type == SignalType.ALERTS

    def test_fast_mode_no_signal_defaults_to_trace(self) -> None:
        """FAST mode with no specific signal should default to TRACE."""
        result = classify_intent_with_signal("quick health check")
        assert result.mode == InvestigationMode.FAST
        assert result.signal_type == SignalType.TRACE


class TestClassifyIntentBackwardCompatibility:
    """Ensure the original classify_intent function still works."""

    def test_returns_investigation_mode(self) -> None:
        """Should still return InvestigationMode enum."""
        result = classify_intent("check the status")
        assert isinstance(result, InvestigationMode)

    def test_fast_mode(self) -> None:
        """FAST mode should still work."""
        assert classify_intent("quick status check") == InvestigationMode.FAST

    def test_debate_mode(self) -> None:
        """DEBATE mode should still work."""
        assert classify_intent("root cause analysis") == InvestigationMode.DEBATE

    def test_standard_mode(self) -> None:
        """STANDARD mode should still work."""
        assert (
            classify_intent("show me the error rates")
            == InvestigationMode.STANDARD
        )


class TestSignalTypeDetection:
    """Tests for the _detect_signal_type helper function."""

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("show me the trace waterfall", SignalType.TRACE),
            ("latency on the api endpoint", SignalType.TRACE),
            ("spans for the grpc call", SignalType.TRACE),
            ("timeout on http requests", SignalType.TRACE),
        ],
    )
    def test_trace_keywords(self, query: str, expected: SignalType) -> None:
        """Trace-related queries should return TRACE signal."""
        assert _detect_signal_type(query.lower()) == expected

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("cpu utilization is high", SignalType.METRICS),
            ("memory usage on the cluster", SignalType.METRICS),
            ("slo error budget burn rate", SignalType.METRICS),
            ("p99 percentile is degraded", SignalType.METRICS),
            ("run a promql query for throughput", SignalType.METRICS),
        ],
    )
    def test_metrics_keywords(self, query: str, expected: SignalType) -> None:
        """Metrics-related queries should return METRICS signal."""
        assert _detect_signal_type(query.lower()) == expected

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("check the error log entries", SignalType.LOGS),
            ("exception in the application logs", SignalType.LOGS),
            ("oom killed events in stderr", SignalType.LOGS),
            ("stack trace from the crash", SignalType.LOGS),
        ],
    )
    def test_logs_keywords(self, query: str, expected: SignalType) -> None:
        """Logs-related queries should return LOGS signal."""
        assert _detect_signal_type(query.lower()) == expected

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("any alerts firing right now", SignalType.ALERTS),
            ("check the alerting policies", SignalType.ALERTS),
            ("notification from the pager", SignalType.ALERTS),
            ("triggered threshold alarms", SignalType.ALERTS),
        ],
    )
    def test_alerts_keywords(self, query: str, expected: SignalType) -> None:
        """Alerts-related queries should return ALERTS signal."""
        assert _detect_signal_type(query.lower()) == expected

    def test_no_keywords_defaults_to_trace(self) -> None:
        """Queries with no signal keywords should default to TRACE."""
        assert _detect_signal_type("some random words") == SignalType.TRACE

    def test_empty_string_defaults_to_trace(self) -> None:
        """Empty string should default to TRACE."""
        assert _detect_signal_type("") == SignalType.TRACE

    def test_mixed_signals_picks_dominant(self) -> None:
        """When multiple signal types match, should pick the one with most hits."""
        # This query has more metrics keywords than trace keywords
        query = "check cpu memory disk utilization metrics and rate"
        result = _detect_signal_type(query.lower())
        assert result == SignalType.METRICS


class TestClassificationResultImmutability:
    """Tests for ClassificationResult frozen dataclass."""

    def test_is_frozen(self) -> None:
        """ClassificationResult should be immutable."""
        result = ClassificationResult(mode=InvestigationMode.FAST)
        with pytest.raises(AttributeError):
            result.mode = InvestigationMode.DEBATE  # type: ignore[misc]

    def test_default_signal_type(self) -> None:
        """Default signal_type should be TRACE."""
        result = ClassificationResult(mode=InvestigationMode.STANDARD)
        assert result.signal_type == SignalType.TRACE

    def test_equality(self) -> None:
        """Two identical results should be equal."""
        r1 = ClassificationResult(
            mode=InvestigationMode.FAST, signal_type=SignalType.LOGS
        )
        r2 = ClassificationResult(
            mode=InvestigationMode.FAST, signal_type=SignalType.LOGS
        )
        assert r1 == r2


class TestSignalTypeEnum:
    """Tests for SignalType enum values."""

    def test_values(self) -> None:
        """SignalType should have trace, metrics, logs, alerts."""
        assert SignalType.TRACE.value == "trace"
        assert SignalType.METRICS.value == "metrics"
        assert SignalType.LOGS.value == "logs"
        assert SignalType.ALERTS.value == "alerts"

    def test_is_str_enum(self) -> None:
        """SignalType should be a string enum."""
        assert isinstance(SignalType.TRACE, str)
        assert SignalType.TRACE == "trace"
