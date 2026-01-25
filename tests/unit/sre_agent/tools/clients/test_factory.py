"""Unit tests for the GCP client factory."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.clients.factory import (
    get_alert_policy_client,
    get_logging_client,
    get_monitoring_client,
    get_trace_client,
)


@pytest.fixture(autouse=True)
def clear_clients_cache():
    import sre_agent.tools.clients.factory as factory

    with factory._lock:
        factory._clients.clear()


def test_get_trace_client_default():
    with patch("google.cloud.trace_v1.TraceServiceClient") as mock_class:
        client = get_trace_client()
        assert client is not None
        mock_class.assert_called_once()


def test_get_trace_client_with_context():
    mock_context = MagicMock()
    mock_creds = MagicMock()
    with patch(
        "sre_agent.tools.clients.factory.get_credentials_from_tool_context",
        return_value=mock_creds,
    ):
        with patch("google.cloud.trace_v1.TraceServiceClient") as mock_class:
            client = get_trace_client(tool_context=mock_context)
            assert client is not None
            mock_class.assert_called_with(credentials=mock_creds)


def test_get_trace_client_with_contextvar():
    mock_creds = MagicMock()
    with patch(
        "sre_agent.tools.clients.factory.get_current_credentials_or_none",
        return_value=mock_creds,
    ):
        with patch("google.cloud.trace_v1.TraceServiceClient") as mock_class:
            client = get_trace_client()
            assert client is not None
            mock_class.assert_called_with(credentials=mock_creds)


def test_get_logging_client():
    with patch("sre_agent.tools.clients.factory.LoggingServiceV2Client") as mock_class:
        client = get_logging_client()
        assert client is not None
        mock_class.assert_called_once()


def test_get_monitoring_client():
    with patch("google.cloud.monitoring_v3.MetricServiceClient") as mock_class:
        client = get_monitoring_client()
        assert client is not None
        mock_class.assert_called_once()


def test_get_alert_policy_client():
    with patch("google.cloud.monitoring_v3.AlertPolicyServiceClient") as mock_class:
        client = get_alert_policy_client()
        assert client is not None
        mock_class.assert_called_once()


def test_strict_euc_enforcement():
    with patch.dict("os.environ", {"STRICT_EUC_ENFORCEMENT": "true"}):
        with patch(
            "sre_agent.tools.clients.factory.get_current_credentials_or_none",
            return_value=None,
        ):
            with pytest.raises(PermissionError) as excinfo:
                get_trace_client()
            assert "Authentication failed" in str(excinfo.value)
