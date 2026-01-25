"""Tests for the Event Summarizer."""

import json

import pytest

from sre_agent.core.summarizer import EventSummary, Summarizer, get_summarizer


class TestSummarizer:
    """Tests for Summarizer."""

    @pytest.fixture
    def summarizer(self) -> Summarizer:
        """Create a summarizer for testing."""
        return Summarizer(use_llm=False)

    def test_summarize_user_message_event(self, summarizer: Summarizer) -> None:
        """Test summarizing a user message event."""
        event = {
            "type": "user_message",
            "content": "What's causing the latency spike in checkout service?",
            "timestamp": "2026-01-25T10:00:00Z",
        }

        summary = summarizer.summarize_event(event)

        assert "User:" in summary
        assert "latency" in summary.lower()

    def test_summarize_model_thought_event(self, summarizer: Summarizer) -> None:
        """Test summarizing a model thought event."""
        event = {
            "type": "model_thought",
            "content": "I should start by analyzing the aggregate metrics to understand the scope of the issue.",
            "timestamp": "2026-01-25T10:00:01Z",
        }

        summary = summarizer.summarize_event(event)

        assert "Agent thought:" in summary

    def test_summarize_tool_call_event(self, summarizer: Summarizer) -> None:
        """Test summarizing a tool call event."""
        event = {
            "type": "tool_call",
            "tool_name": "fetch_trace",
            "content": '{"trace_id": "abc123"}',
            "timestamp": "2026-01-25T10:00:02Z",
        }

        summary = summarizer.summarize_event(event)

        assert "Called tool: fetch_trace" in summary

    def test_summarize_trace_tool_output(self, summarizer: Summarizer) -> None:
        """Test summarizing fetch_trace output."""
        output = {
            "status": "success",
            "result": {
                "span_count": 15,
                "total_duration_ms": 1234.5,
                "error_count": 2,
            },
        }

        event = {
            "type": "tool_output",
            "tool_name": "fetch_trace",
            "content": json.dumps(output),
            "timestamp": "2026-01-25T10:00:03Z",
        }

        summary = summarizer.summarize_event(event)

        assert "15 spans" in summary
        assert "1235" in summary or "1234" in summary  # Duration
        assert "2 errors" in summary

    def test_summarize_log_entries_output(self, summarizer: Summarizer) -> None:
        """Test summarizing list_log_entries output."""
        output = {
            "status": "success",
            "result": [{"log": "entry1"}, {"log": "entry2"}, {"log": "entry3"}],
        }

        event = {
            "type": "tool_output",
            "tool_name": "list_log_entries",
            "content": json.dumps(output),
            "timestamp": "2026-01-25T10:00:04Z",
        }

        summary = summarizer.summarize_event(event)

        assert "3 log entries" in summary

    def test_summarize_error_output(self, summarizer: Summarizer) -> None:
        """Test summarizing error output."""
        output = {
            "status": "error",
            "error": "Connection timeout after 30 seconds",
        }

        event = {
            "type": "tool_output",
            "tool_name": "analyze_critical_path",  # Use a tool without specific summarizer
            "content": json.dumps(output),
            "timestamp": "2026-01-25T10:00:05Z",
        }

        summary = summarizer.summarize_event(event)

        assert "failed" in summary.lower()
        assert "timeout" in summary.lower()

    def test_summarize_events_list(self, summarizer: Summarizer) -> None:
        """Test summarizing a list of events."""
        events = [
            {
                "type": "user_message",
                "content": "Investigate the checkout service",
                "timestamp": "2026-01-25T10:00:00Z",
            },
            {
                "type": "tool_call",
                "tool_name": "fetch_trace",
                "content": "{}",
                "timestamp": "2026-01-25T10:00:01Z",
            },
            {
                "type": "tool_output",
                "tool_name": "fetch_trace",
                "content": json.dumps(
                    {"status": "success", "result": {"span_count": 10}}
                ),
                "timestamp": "2026-01-25T10:00:02Z",
            },
        ]

        result = summarizer.summarize_events(events)

        assert isinstance(result, EventSummary)
        assert result.events_summarized == 3
        assert "fetch_trace" in result.tools_used
        assert result.token_estimate > 0

    def test_summarize_empty_events(self, summarizer: Summarizer) -> None:
        """Test summarizing empty event list."""
        result = summarizer.summarize_events([])

        assert result.events_summarized == 0
        assert "No events" in result.summary_text

    def test_extract_finding_with_root_cause(self, summarizer: Summarizer) -> None:
        """Test extracting finding with root cause."""
        event = {
            "type": "tool_output",
            "content": json.dumps(
                {
                    "status": "success",
                    "result": {"root_cause": "Database connection pool exhausted"},
                }
            ),
        }

        # Test private method
        finding = summarizer._extract_finding(event)

        assert finding is not None
        assert "Root cause:" in finding
        assert "connection pool" in finding.lower()

    def test_extract_finding_with_bottleneck(self, summarizer: Summarizer) -> None:
        """Test extracting finding with bottleneck."""
        event = {
            "type": "tool_output",
            "content": json.dumps(
                {
                    "status": "success",
                    "result": {"bottleneck": "payment-service taking 2s per request"},
                }
            ),
        }

        finding = summarizer._extract_finding(event)

        assert finding is not None
        assert "Bottleneck:" in finding

    def test_extract_finding_with_anomalies(self, summarizer: Summarizer) -> None:
        """Test extracting finding with anomalies."""
        event = {
            "type": "tool_output",
            "content": json.dumps(
                {
                    "status": "success",
                    "result": {
                        "anomalies": [{"name": "a1"}, {"name": "a2"}, {"name": "a3"}]
                    },
                }
            ),
        }

        finding = summarizer._extract_finding(event)

        assert finding is not None
        assert "3 anomalies" in finding

    def test_truncate_long_content(self, summarizer: Summarizer) -> None:
        """Test that long content is truncated."""
        long_content = "A" * 1000

        event = {
            "type": "user_message",
            "content": long_content,
            "timestamp": "2026-01-25T10:00:00Z",
        }

        summary = summarizer.summarize_event(event)

        assert len(summary) < len(long_content)
        assert "..." in summary

    def test_summarize_promql_output(self, summarizer: Summarizer) -> None:
        """Test summarizing PromQL query output."""
        output = {
            "status": "success",
            "result": {
                "data": {
                    "resultType": "vector",
                    "result": [{"metric": {}}, {"metric": {}}, {"metric": {}}],
                }
            },
        }

        event = {
            "type": "tool_output",
            "tool_name": "query_promql",
            "content": json.dumps(output),
            "timestamp": "2026-01-25T10:00:06Z",
        }

        summary = summarizer.summarize_event(event)

        assert "PromQL" in summary
        assert "3" in summary
        assert "vector" in summary

    def test_summarize_pattern_output(self, summarizer: Summarizer) -> None:
        """Test summarizing log pattern extraction output."""
        output = {
            "status": "success",
            "result": {
                "patterns": [{"pattern": "p1"}, {"pattern": "p2"}, {"pattern": "p3"}]
            },
        }

        event = {
            "type": "tool_output",
            "tool_name": "extract_log_patterns",
            "content": json.dumps(output),
            "timestamp": "2026-01-25T10:00:07Z",
        }

        summary = summarizer.summarize_event(event)

        assert "3 log patterns" in summary

    def test_error_count_tracking(self, summarizer: Summarizer) -> None:
        """Test that error events are counted."""
        events = [
            {
                "type": "tool_output",
                "content": json.dumps({"status": "error", "error": "Error 1"}),
            },
            {
                "type": "tool_output",
                "content": json.dumps({"status": "success", "result": {}}),
            },
            {
                "type": "tool_output",
                "content": json.dumps({"status": "error", "error": "Error 2"}),
            },
        ]

        result = summarizer.summarize_events(events)

        assert result.error_count == 2


class TestSummarizerSingleton:
    """Tests for singleton access."""

    def test_get_summarizer_singleton(self) -> None:
        """Test that get_summarizer returns singleton."""
        summarizer1 = get_summarizer()
        summarizer2 = get_summarizer()

        assert summarizer1 is summarizer2


class TestEventSummary:
    """Tests for EventSummary dataclass."""

    def test_event_summary_creation(self) -> None:
        """Test creating an event summary."""
        summary = EventSummary(
            summary_text="User investigated checkout service",
            key_findings=["Found bottleneck in db-service"],
            tools_used=["fetch_trace", "list_log_entries"],
            error_count=1,
            events_summarized=10,
            token_estimate=500,
        )

        assert summary.summary_text == "User investigated checkout service"
        assert len(summary.key_findings) == 1
        assert len(summary.tools_used) == 2
        assert summary.error_count == 1
        assert summary.events_summarized == 10
        assert summary.token_estimate == 500
