"""
Goal: Verify debug utilities provide comprehensive diagnostic information about auth and telemetry state.
Patterns: Environment Patching, Mock Tool Context Simulation.
"""

import os
from unittest.mock import MagicMock, patch

from sre_agent.tools.common.debug import (
    enable_debug_mode,
    get_debug_summary,
    log_agent_engine_call_state,
    log_auth_state,
    log_mcp_auth_state,
    log_telemetry_state,
)


def test_log_telemetry_state():
    result = log_telemetry_state("test")
    assert result["context_label"] == "test"
    assert "environment" in result
    assert "current_span" in result


def test_log_auth_state():
    with patch("sre_agent.auth.get_current_credentials_or_none", return_value=None):
        result = log_auth_state(None, "test")
        assert result["context_label"] == "test"
        assert result["context_var"]["has_credentials"] is False


def test_log_auth_state_with_session():
    mock_session = MagicMock()
    mock_session.state = {"_user_access_token": "secret"}
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session = mock_session

    result = log_auth_state(mock_tool_context, "test")
    assert result["session_state"]["has_user_token"] is True
    assert result["session_state"]["token_prefix"] == "secret"[:20] + "..."


def test_log_mcp_auth_state():
    with patch(
        "sre_agent.tools.mcp.gcp._create_header_provider"
    ) as mock_provider_factory:
        mock_provider = MagicMock()
        mock_provider.return_value = {"Authorization": "Bearer token"}
        mock_provider_factory.return_value = mock_provider

        result = log_mcp_auth_state("p1", None, "test")
        assert result["project_id"] == "p1"
        assert result["headers"]["has_authorization"] is True


def test_log_agent_engine_call_state():
    result = log_agent_engine_call_state("hello", "s1", "token", "p1", "test")
    assert result["session"]["id"] == "s1"
    assert result["credentials"]["has_token"] is True
    assert "hello" in result["message"]["preview"]


def test_enable_debug_mode():
    enable_debug_mode()
    assert os.environ["DEBUG_TELEMETRY"] == "true"
    assert os.environ["DEBUG_AUTH"] == "true"


def test_get_debug_summary():
    result = get_debug_summary()
    assert "debug_enabled" in result
    assert "telemetry" in result
    assert "auth" in result
