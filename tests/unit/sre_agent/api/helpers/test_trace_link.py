"""Tests for Cloud Trace deep-link helpers."""

from __future__ import annotations

from unittest.mock import patch

from sre_agent.api.helpers import build_cloud_trace_url, get_current_trace_info


class TestBuildCloudTraceUrl:
    """Tests for build_cloud_trace_url."""

    def test_basic_url(self) -> None:
        url = build_cloud_trace_url("abc123def456", "my-project")
        assert url == (
            "https://console.cloud.google.com/traces/list"
            "?tid=abc123def456&project=my-project"
        )

    def test_full_length_trace_id(self) -> None:
        trace_id = "a" * 32
        url = build_cloud_trace_url(trace_id, "proj-1")
        assert f"tid={trace_id}" in url
        assert "project=proj-1" in url


class TestGetCurrentTraceInfo:
    """Tests for get_current_trace_info."""

    def test_returns_none_when_no_trace(self) -> None:
        """No OTel span and no manual trace ID -> None."""
        from opentelemetry import trace
        from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

        # Create an invalid span context (trace_id=0 is invalid)
        invalid_ctx = SpanContext(
            trace_id=0,
            span_id=0,
            is_remote=False,
            trace_flags=TraceFlags(0),
        )
        span = NonRecordingSpan(invalid_ctx)

        with (
            patch.object(trace, "get_current_span", return_value=span),
            patch("sre_agent.auth.get_trace_id", return_value=None),
        ):
            result = get_current_trace_info(project_id="proj")
            assert result is None

    def test_returns_payload_from_otel_span(self) -> None:
        """Valid OTel span -> trace_info payload with URL."""
        from opentelemetry import trace
        from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

        valid_ctx = SpanContext(
            trace_id=0xAABBCCDDEEFF00112233445566778899,
            span_id=0x1122334455667788,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        span = NonRecordingSpan(valid_ctx)

        with patch.object(trace, "get_current_span", return_value=span):
            result = get_current_trace_info(project_id="my-proj")

        assert result is not None
        assert result["type"] == "trace_info"
        assert result["trace_id"] == "aabbccddeeff00112233445566778899"
        assert result["project_id"] == "my-proj"
        assert "trace_url" in result
        assert "my-proj" in result["trace_url"]
        assert "aabbccddeeff00112233445566778899" in result["trace_url"]

    def test_returns_payload_without_url_when_no_project(self) -> None:
        """Trace ID available but no project -> payload without trace_url."""
        from opentelemetry import trace
        from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

        valid_ctx = SpanContext(
            trace_id=0xDEADBEEF00000000DEADBEEF00000000,
            span_id=0x1122334455667788,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        span = NonRecordingSpan(valid_ctx)

        with (
            patch.object(trace, "get_current_span", return_value=span),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = get_current_trace_info(project_id=None)

        assert result is not None
        assert result["type"] == "trace_info"
        assert "trace_url" not in result

    def test_fallback_to_manual_trace_id(self) -> None:
        """OTel span invalid, manual ContextVar set -> uses fallback."""
        from opentelemetry import trace
        from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

        invalid_ctx = SpanContext(
            trace_id=0,
            span_id=0,
            is_remote=False,
            trace_flags=TraceFlags(0),
        )
        span = NonRecordingSpan(invalid_ctx)

        manual_id = "abcd1234abcd1234abcd1234abcd1234"

        with (
            patch.object(trace, "get_current_span", return_value=span),
            patch("sre_agent.auth.get_trace_id", return_value=manual_id),
        ):
            result = get_current_trace_info(project_id="proj-2")

        assert result is not None
        assert result["trace_id"] == manual_id
        assert "proj-2" in result["trace_url"]
