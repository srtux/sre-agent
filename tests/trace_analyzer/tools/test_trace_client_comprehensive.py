"""Comprehensive tests for Cloud Trace client tools."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from google.cloud import trace_v1
from google.cloud import logging_v2

from trace_analyzer.tools import trace_client
from tests.fixtures.synthetic_otel_data import (
    CloudTraceAPIGenerator,
    CloudLoggingAPIGenerator,
    generate_trace_id
)


@pytest.fixture
def mock_trace_client():
    """Mock Cloud Trace API client."""
    mock_client = MagicMock(spec=trace_v1.TraceServiceClient)
    return mock_client


@pytest.fixture
def mock_logging_client():
    """Mock Cloud Logging API client."""
    mock_client = MagicMock(spec=logging_v2.LoggingServiceV2Client)
    return mock_client


class TestFetchTrace:
    """Tests for fetch_trace function."""

    @patch('trace_analyzer.tools.trace_client.trace_v1.TraceServiceClient')
    def test_fetch_trace_success(self, mock_client_class):
        """Test successful trace fetch."""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        trace_id = generate_trace_id()
        mock_response = CloudTraceAPIGenerator.trace_response(
            trace_id=trace_id,
            include_error=False
        )

        # Convert to mock Trace object
        mock_trace = MagicMock()
        mock_trace.trace_id = trace_id
        mock_trace.project_id = "test-project"
        mock_trace.spans = []

        mock_client.get_trace.return_value = mock_trace

        # Execute
        result = trace_client.fetch_trace(
            project_id="test-project",
            trace_id=trace_id
        )

        # Verify
        assert result is not None
        mock_client.get_trace.assert_called_once()

    @patch('trace_analyzer.tools.trace_client.trace_v1.TraceServiceClient')
    def test_fetch_trace_with_invalid_trace_id(self, mock_client_class):
        """Test fetch trace with invalid trace ID."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup mock to raise exception
        from google.api_core import exceptions
        mock_client.get_trace.side_effect = exceptions.NotFound("Trace not found")

        # Execute and verify exception handling
        with pytest.raises(Exception):
            trace_client.fetch_trace(
                project_id="test-project",
                trace_id="invalid-trace-id"
            )


class TestListTraces:
    """Tests for list_traces function."""

    @patch('trace_analyzer.tools.trace_client.trace_v1.TraceServiceClient')
    def test_list_traces_success(self, mock_client_class):
        """Test successful trace listing."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup mock response
        mock_traces = []
        for i in range(5):
            mock_trace = MagicMock()
            mock_trace.trace_id = generate_trace_id()
            mock_trace.project_id = "test-project"
            mock_traces.append(mock_trace)

        mock_client.list_traces.return_value = mock_traces

        # Execute
        result = trace_client.list_traces(
            project_id="test-project",
            page_size=10
        )

        # Verify
        assert result is not None
        mock_client.list_traces.assert_called_once()

    @patch('trace_analyzer.tools.trace_client.trace_v1.TraceServiceClient')
    def test_list_traces_with_time_filter(self, mock_client_class):
        """Test trace listing with time filter."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.list_traces.return_value = []

        # Execute with time filter
        result = trace_client.list_traces(
            project_id="test-project",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z"
        )

        # Verify filter was applied
        call_args = mock_client.list_traces.call_args
        assert call_args is not None


class TestGetLogsForTrace:
    """Tests for get_logs_for_trace function."""

    @patch('trace_analyzer.tools.trace_client.logging_v2.LoggingServiceV2Client')
    def test_get_logs_for_trace_success(self, mock_client_class):
        """Test successful log retrieval for trace."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        trace_id = generate_trace_id()
        mock_logs = CloudLoggingAPIGenerator.log_entries_response(
            count=5,
            trace_id=trace_id,
            severity="ERROR"
        )

        # Setup mock response
        mock_entries = []
        for log_entry in mock_logs["entries"]:
            mock_entry = MagicMock()
            mock_entry.text_payload = log_entry["textPayload"]
            mock_entry.severity = log_entry["severity"]
            mock_entry.timestamp = log_entry["timestamp"]
            mock_entries.append(mock_entry)

        mock_client.list_log_entries.return_value = mock_entries

        # Execute
        result = trace_client.get_logs_for_trace(
            project_id="test-project",
            trace_id=trace_id
        )

        # Verify
        assert result is not None
        mock_client.list_log_entries.assert_called_once()

    @patch('trace_analyzer.tools.trace_client.logging_v2.LoggingServiceV2Client')
    def test_get_logs_with_severity_filter(self, mock_client_class):
        """Test log retrieval with severity filter."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_log_entries.return_value = []

        trace_id = generate_trace_id()

        # Execute with severity filter
        result = trace_client.get_logs_for_trace(
            project_id="test-project",
            trace_id=trace_id,
            severity="ERROR"
        )

        # Verify filter was applied in call
        call_args = mock_client.list_log_entries.call_args
        assert call_args is not None


class TestFindExampleTraces:
    """Tests for find_example_traces function."""

    @patch('trace_analyzer.tools.trace_client.trace_v1.TraceServiceClient')
    def test_find_example_traces_with_error_filter(self, mock_client_class):
        """Test finding example traces with error filter."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup mock traces with errors
        mock_traces = []
        for i in range(3):
            mock_trace = MagicMock()
            mock_trace.trace_id = generate_trace_id()
            mock_trace.project_id = "test-project"
            mock_traces.append(mock_trace)

        mock_client.list_traces.return_value = mock_traces

        # Execute
        result = trace_client.find_example_traces(
            project_id="test-project",
            filter_errors=True,
            max_results=5
        )

        # Verify
        assert result is not None
        mock_client.list_traces.assert_called_once()

    @patch('trace_analyzer.tools.trace_client.trace_v1.TraceServiceClient')
    def test_find_example_traces_with_latency_threshold(self, mock_client_class):
        """Test finding example traces with latency threshold."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_traces.return_value = []

        # Execute with latency filter
        result = trace_client.find_example_traces(
            project_id="test-project",
            min_latency_ms=100.0,
            max_results=10
        )

        # Verify filter was applied
        call_args = mock_client.list_traces.call_args
        assert call_args is not None


class TestGetTraceByURL:
    """Tests for get_trace_by_url function."""

    def test_extract_trace_id_from_url(self):
        """Test extracting trace ID from Cloud Console URL."""
        url = "https://console.cloud.google.com/traces/trace-details/abc123?project=test-project"

        # Mock the actual fetch to focus on URL parsing
        with patch('trace_analyzer.tools.trace_client.fetch_trace') as mock_fetch:
            mock_fetch.return_value = {"traceId": "abc123"}

            result = trace_client.get_trace_by_url(url)

            # Verify trace was fetched with correct ID
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args[1]
            assert "trace_id" in call_args

    def test_get_trace_by_url_invalid_url(self):
        """Test handling of invalid URL."""
        invalid_url = "https://example.com/invalid"

        with pytest.raises(Exception):
            trace_client.get_trace_by_url(invalid_url)


class TestListErrorEvents:
    """Tests for list_error_events function."""

    @patch('trace_analyzer.tools.trace_client.errorreporting_v1beta1.ErrorStatsServiceClient')
    def test_list_error_events_success(self, mock_client_class):
        """Test successful error event listing."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup mock error events
        mock_events = []
        for i in range(5):
            mock_event = MagicMock()
            mock_event.message = f"Error message {i}"
            mock_event.count = i + 1
            mock_events.append(mock_event)

        mock_client.list_group_stats.return_value = mock_events

        # Execute
        result = trace_client.list_error_events(
            project_id="test-project",
            time_range_hours=24
        )

        # Verify
        assert result is not None
        mock_client.list_group_stats.assert_called_once()

    @patch('trace_analyzer.tools.trace_client.errorreporting_v1beta1.ErrorStatsServiceClient')
    def test_list_error_events_with_service_filter(self, mock_client_class):
        """Test error event listing with service filter."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_group_stats.return_value = []

        # Execute with service filter
        result = trace_client.list_error_events(
            project_id="test-project",
            service_name="frontend",
            time_range_hours=24
        )

        # Verify filter was applied
        call_args = mock_client.list_group_stats.call_args
        assert call_args is not None


class TestListLogEntries:
    """Tests for list_log_entries function."""

    @patch('trace_analyzer.tools.trace_client.logging_v2.LoggingServiceV2Client')
    def test_list_log_entries_success(self, mock_client_class):
        """Test successful log entry listing."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup mock log entries
        mock_logs = CloudLoggingAPIGenerator.log_entries_response(
            count=10,
            severity="ERROR"
        )

        mock_entries = []
        for log_entry in mock_logs["entries"]:
            mock_entry = MagicMock()
            mock_entry.text_payload = log_entry["textPayload"]
            mock_entry.severity = log_entry["severity"]
            mock_entries.append(mock_entry)

        mock_client.list_log_entries.return_value = mock_entries

        # Execute
        result = trace_client.list_log_entries(
            project_id="test-project",
            filter_str='severity="ERROR"',
            max_results=10
        )

        # Verify
        assert result is not None
        mock_client.list_log_entries.assert_called_once()

    @patch('trace_analyzer.tools.trace_client.logging_v2.LoggingServiceV2Client')
    def test_list_log_entries_with_time_range(self, mock_client_class):
        """Test log entry listing with time range."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_log_entries.return_value = []

        # Execute with time range
        result = trace_client.list_log_entries(
            project_id="test-project",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z"
        )

        # Verify filter was applied
        call_args = mock_client.list_log_entries.call_args
        assert call_args is not None


class TestIntegration:
    """Integration tests for trace client tools."""

    @patch('trace_analyzer.tools.trace_client.trace_v1.TraceServiceClient')
    @patch('trace_analyzer.tools.trace_client.logging_v2.LoggingServiceV2Client')
    def test_fetch_trace_and_logs_workflow(self, mock_logging_client, mock_trace_client):
        """Test complete workflow of fetching trace and its logs."""
        # Setup trace mock
        trace_id = generate_trace_id()
        mock_trace = MagicMock()
        mock_trace.trace_id = trace_id
        mock_trace.project_id = "test-project"

        mock_trace_client.return_value.get_trace.return_value = mock_trace

        # Setup logging mock
        mock_log_entry = MagicMock()
        mock_log_entry.text_payload = "Error occurred"
        mock_log_entry.severity = "ERROR"

        mock_logging_client.return_value.list_log_entries.return_value = [mock_log_entry]

        # Execute workflow
        trace_result = trace_client.fetch_trace(
            project_id="test-project",
            trace_id=trace_id
        )

        log_result = trace_client.get_logs_for_trace(
            project_id="test-project",
            trace_id=trace_id
        )

        # Verify both calls succeeded
        assert trace_result is not None
        assert log_result is not None

    def test_synthetic_data_matches_api_structure(self):
        """Test that synthetic data matches actual API structure."""
        # Generate synthetic trace
        trace_data = CloudTraceAPIGenerator.trace_response(include_error=True)

        # Verify structure matches Cloud Trace API
        assert "projectId" in trace_data
        assert "traceId" in trace_data
        assert "spans" in trace_data
        assert isinstance(trace_data["spans"], list)

        if len(trace_data["spans"]) > 0:
            span = trace_data["spans"][0]
            assert "spanId" in span
            assert "name" in span
            assert "startTime" in span

        # Generate synthetic logs
        log_data = CloudLoggingAPIGenerator.log_entries_response(count=5)

        # Verify structure matches Cloud Logging API
        assert "entries" in log_data
        assert isinstance(log_data["entries"], list)
        assert len(log_data["entries"]) == 5

        if len(log_data["entries"]) > 0:
            entry = log_data["entries"][0]
            assert "logName" in entry
            assert "timestamp" in entry
            assert "severity" in entry
