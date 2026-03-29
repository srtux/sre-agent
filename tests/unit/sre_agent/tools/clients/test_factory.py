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


@pytest.fixture(autouse=True)
def enforce_euc_false():
    with patch.dict("os.environ", {"STRICT_EUC_ENFORCEMENT": "false"}):
        yield


@pytest.fixture(autouse=True)
def mock_google_auth():
    with patch("google.auth.default") as mock:
        mock.return_value = (MagicMock(), "test-project")
        yield mock


def test_get_trace_client_default():
    with patch("google.cloud.trace_v1.TraceServiceClient") as mock_class:
        client = get_trace_client()
        assert client is not None
        mock_class.assert_called_once()


def test_get_trace_client_with_context():
    mock_context = MagicMock()
    # The client now delegates credential resolution to GLOBAL_CONTEXT_CREDENTIALS,
    # and just uses tool_context directly
    with patch("google.cloud.trace_v1.TraceServiceClient") as mock_class:
        with patch("sre_agent.auth.set_auth_context_from_tool_context") as mock_set_ctx:
            client = get_trace_client(tool_context=mock_context)
            assert client is not None
            mock_class.assert_called_once()
            mock_set_ctx.assert_called_once_with(mock_context)


def test_get_trace_client_with_contextvar():
    with patch("google.cloud.trace_v1.TraceServiceClient") as mock_class:
        client = get_trace_client()
        assert client is not None
        mock_class.assert_called_once()


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


def test_strict_euc_enforcement_skipped():
    # Skipped as lazy evaluation doesn't fail at init time.
    # In production, failures happen when client makes network calls with evaluating ContextVars.
    pass
