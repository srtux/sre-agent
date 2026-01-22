from unittest.mock import MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials

from sre_agent.auth import (
    SESSION_STATE_ACCESS_TOKEN_KEY,
    SESSION_STATE_PROJECT_ID_KEY,
    _credentials_context,
    _project_id_context,
    get_credentials_from_session,
    get_credentials_from_tool_context,
    get_current_credentials,
    get_current_credentials_or_none,
    get_current_project_id,
    get_project_id_from_session,
    get_project_id_from_tool_context,
    set_current_credentials,
    set_current_project_id,
)


@pytest.fixture(autouse=True)
def reset_contexts():
    """Reset ContextVars before each test."""
    _credentials_context.set(None)
    _project_id_context.set(None)
    yield
    _credentials_context.set(None)
    _project_id_context.set(None)


def test_credentials_context():
    creds = Credentials(token="test-token")
    set_current_credentials(creds)
    assert get_current_credentials_or_none() == creds

    # get_current_credentials returns (creds, None) when context is set
    ctx_creds, project_id = get_current_credentials()
    assert ctx_creds == creds
    assert project_id is None


def test_project_id_context():
    project_id = "test-project"
    set_current_project_id(project_id)
    assert get_current_project_id() == project_id


def test_get_current_credentials_fallback():
    mock_default_creds = MagicMock()
    with patch(
        "google.auth.default", return_value=(mock_default_creds, "default-project")
    ):
        creds, project_id = get_current_credentials()
        assert creds == mock_default_creds
        assert project_id == "default-project"


def test_get_credentials_from_session():
    session_state = {SESSION_STATE_ACCESS_TOKEN_KEY: "session-token"}
    creds = get_credentials_from_session(session_state)
    assert creds.token == "session-token"

    assert get_credentials_from_session({}) is None
    assert get_credentials_from_session(None) is None


def test_get_project_id_from_session():
    session_state = {SESSION_STATE_PROJECT_ID_KEY: "session-project"}
    assert get_project_id_from_session(session_state) == "session-project"
    assert get_project_id_from_session({}) is None


def test_get_credentials_from_tool_context_priority():
    # 1. Priority: ContextVar
    creds_ctx = Credentials(token="ctx-token")
    set_current_credentials(creds_ctx)

    mock_tool_context = MagicMock()
    # Even if session has a token, ContextVar should win
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: "session-token"
    }

    resolved = get_credentials_from_tool_context(mock_tool_context)
    assert resolved == creds_ctx
    assert resolved.token == "ctx-token"


def test_get_credentials_from_tool_context_session_fallback():
    # ContextVar is empty
    _credentials_context.set(None)

    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: "session-token"
    }

    resolved = get_credentials_from_tool_context(mock_tool_context)
    assert resolved.token == "session-token"


def test_get_project_id_from_tool_context_priority():
    # 1. Priority: ContextVar
    set_current_project_id("ctx-project")

    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_PROJECT_ID_KEY: "session-project"
    }

    assert get_project_id_from_tool_context(mock_tool_context) == "ctx-project"


def test_get_project_id_from_tool_context_session_fallback():
    _project_id_context.set(None)

    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_PROJECT_ID_KEY: "session-project"
    }

    assert get_project_id_from_tool_context(mock_tool_context) == "session-project"
