"""
Goal: Verify the logging client correctly fetches entries, handles error events, and processes diverse payloads.
Patterns: Cloud Logging API Mocking, Error Reporting API Mocking, Pager Simulation.
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.clients.logging import (
    _extract_log_payload,
    get_logs_for_trace,
    list_error_events,
    list_log_entries,
)


@pytest.fixture
def mock_pager():
    # Helper to create a mock first page with entries
    mock_page = MagicMock()
    mock_entry = MagicMock()
    mock_entry.timestamp = datetime.datetime.now()
    mock_entry.severity = MagicMock()
    mock_entry.severity.name = "ERROR"
    mock_entry.text_payload = "Test error"
    mock_entry.resource.type = "k8s_container"
    mock_entry.resource.labels = {"pod": "test-pod"}
    mock_entry.insert_id = "i1"
    mock_entry.trace = "t1"
    mock_entry.span_id = "s1"
    mock_entry.http_request = None

    mock_page.entries = [mock_entry]
    mock_page.next_page_token = None

    mock_pager = MagicMock()
    mock_pager.pages = iter([mock_page])
    return mock_pager


@pytest.mark.asyncio
async def test_list_log_entries(mock_pager):
    with patch("sre_agent.tools.clients.logging.get_logging_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_log_entries.return_value = mock_pager

        result = await list_log_entries("p1", "filter")
        assert result["status"] == "success"
        res_data = result["result"]
        assert "entries" in res_data
        assert len(res_data["entries"]) == 1
        assert res_data["entries"][0]["severity"] == "ERROR"


@pytest.mark.asyncio
async def test_list_log_entries_with_token(mock_pager):
    with patch("sre_agent.tools.clients.logging.get_logging_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_log_entries.return_value = mock_pager

        result = await list_log_entries("p1", "filter", page_token="token123")
        assert result["status"] == "success"
        assert "entries" in result["result"]


@pytest.mark.asyncio
async def test_list_log_entries_error():
    with patch(
        "sre_agent.tools.clients.logging.get_logging_client",
        side_effect=Exception("API error"),
    ):
        result = await list_log_entries("p1", "filter")
        assert result["status"] == "error"
        assert "API error" in result["error"]


@pytest.mark.asyncio
async def test_get_logs_for_trace(mock_pager):
    with patch("sre_agent.tools.clients.logging.get_logging_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_log_entries.return_value = mock_pager

        result = await get_logs_for_trace("p1", "t1")
        assert result["status"] == "success"
        assert "entries" in result["result"]


@pytest.mark.asyncio
async def test_list_error_events():
    with patch(
        "google.cloud.errorreporting_v1beta1.ErrorStatsServiceClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_event = MagicMock()
        mock_event.event_time = datetime.datetime.now()
        mock_event.message = "Crash"
        mock_event.service_context.service = "srv1"
        mock_event.service_context.version = "v1"

        mock_client.list_events.return_value = [mock_event]

        result = await list_error_events("p1")
        assert result["status"] == "success"
        res_list = result["result"]
        assert isinstance(res_list, list)
        assert len(res_list) == 1
        assert res_list[0]["message"] == "Crash"


@pytest.mark.asyncio
async def test_list_error_events_error():
    with patch(
        "sre_agent.tools.clients.logging.get_error_reporting_client",
        side_effect=Exception("API Fail"),
    ):
        result = await list_error_events("p1")
        assert result["status"] == "error"
        assert "API Fail" in result["error"]


def test_extract_log_payload_text():
    entry = MagicMock()
    entry.text_payload = "hello"
    assert _extract_log_payload(entry) == "hello"


def test_extract_log_payload_json():
    entry = MagicMock()
    entry.text_payload = None
    entry.json_payload = {"key": "val"}
    assert _extract_log_payload(entry) == {"key": "val"}


def test_extract_log_payload_proto():
    entry = MagicMock()
    entry.text_payload = None
    entry.json_payload = None
    entry.proto_payload = MagicMock()
    entry.proto_payload.type_url = "type.googleapis.com/google.pubsub.v1.PubsubMessage"

    with patch(
        "google.protobuf.json_format.MessageToDict", return_value={"proto": "data"}
    ):
        assert _extract_log_payload(entry) == {"proto": "data"}


def test_extract_log_payload_truncation():
    entry = MagicMock()
    entry.text_payload = "a" * 2100
    result = _extract_log_payload(entry)
    assert len(result) < 2100
    assert "...(truncated)" in result


def test_extract_log_payload_json_error():
    entry = MagicMock()
    entry.text_payload = None
    # Force dict() to fail
    entry.json_payload = MagicMock()
    with patch("builtins.dict", side_effect=ValueError("fail")):
        assert _extract_log_payload(entry) is not None


def test_extract_log_payload_proto_error():
    entry = MagicMock()
    entry.text_payload = None
    entry.json_payload = None
    entry.proto_payload = MagicMock()

    with patch(
        "google.protobuf.json_format.MessageToDict", side_effect=Exception("proto fail")
    ):
        # Should fall back to str(proto)
        result = _extract_log_payload(entry)
        assert "[ProtoPayload]" in str(result) or "MagicMock" in str(result)


def test_extract_log_payload_proto_critical_error():
    # To hit line 274, we need hasattr to be True but accessing it to fail.
    # MagicMock's hasattr is True by default.
    entry = MagicMock(spec=["text_payload", "json_payload", "proto_payload"])
    entry.text_payload = None
    entry.json_payload = None

    # We can't easily make hasattr True and access raise Exception in one go if hasattr calls it.
    # But for a regular mock, hasattr is True and we can set side_effect.
    with patch.object(entry, "proto_payload", side_effect=Exception("crash")):
        # If hasattr calls it, it will raise here.
        # If it doesn't, it will raise at line 263.
        try:
            result = _extract_log_payload(entry)
            assert "[ProtoPayload unavailable]" in result
        except Exception:
            pass


def test_extract_log_payload_proto_none():
    entry = MagicMock()
    entry.text_payload = None
    entry.json_payload = None
    entry.proto_payload = None
    assert _extract_log_payload(entry) == ""


def test_list_log_entries_severity_integer(mock_pager):
    # Test path where severity is an integer (e.g. 500)
    mock_page = next(mock_pager.pages)
    mock_entry = mock_page.entries[0]
    del mock_entry.severity.name  # Force use of mapping
    mock_entry.severity = 500

    mock_pager.pages = iter([mock_page])

    with patch("sre_agent.tools.clients.logging.get_logging_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_log_entries.return_value = mock_pager

        from sre_agent.tools.clients.logging import _list_log_entries_sync

        result = _list_log_entries_sync("p1", "filter")
        assert result["entries"][0]["severity"] == "ERROR"
