from unittest.mock import MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials

from sre_agent.auth import (
    REQUIRED_SCOPES,
    SESSION_STATE_ACCESS_TOKEN_KEY,
    SESSION_STATE_PROJECT_ID_KEY,
    TokenInfo,
    _credentials_context,
    _project_id_context,
    clear_current_credentials,
    get_credentials_from_session,
    get_credentials_from_tool_context,
    get_current_credentials,
    get_current_credentials_or_none,
    get_current_project_id,
    get_current_project_id_or_none,
    get_project_id_from_session,
    get_project_id_from_tool_context,
    get_trace_id,
    has_required_scopes,
    set_current_credentials,
    set_current_project_id,
    set_trace_id,
    validate_access_token,
    validate_access_token_sync,
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


def test_trace_id_context():
    trace_id = "test-trace-id"
    set_trace_id(trace_id)
    assert get_trace_id() == trace_id


def test_get_current_credentials_fallback():
    mock_default_creds = MagicMock()
    # Test with strict enforcement OFF
    with patch(
        "os.getenv",
        side_effect=lambda k, d=None: "false" if k == "STRICT_EUC_ENFORCEMENT" else d,
    ):
        with patch(
            "google.auth.default", return_value=(mock_default_creds, "default-project")
        ):
            creds, project_id = get_current_credentials()
            assert creds == mock_default_creds
            assert project_id == "default-project"


def test_get_current_credentials_strict_enforcement():
    # Test with strict enforcement ON
    with patch(
        "os.getenv",
        side_effect=lambda k, d=None: "true" if k == "STRICT_EUC_ENFORCEMENT" else d,
    ):
        with pytest.raises(PermissionError) as excinfo:
            get_current_credentials()
        assert "Authentication required" in str(excinfo.value)


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


# =============================================================================
# Token Validation Tests
# =============================================================================


def test_token_info_dataclass():
    """Test TokenInfo dataclass initialization."""
    # Valid token info
    info = TokenInfo(
        valid=True,
        email="user@example.com",
        expires_in=3600,
        scopes=["email", "https://www.googleapis.com/auth/cloud-platform"],
        audience="client-id",
    )
    assert info.valid is True
    assert info.email == "user@example.com"
    assert info.expires_in == 3600
    assert len(info.scopes) == 2
    assert info.error is None

    # Invalid token info
    invalid_info = TokenInfo(valid=False, error="Token expired")
    assert invalid_info.valid is False
    assert invalid_info.error == "Token expired"


def test_has_required_scopes():
    """Test has_required_scopes function."""
    # Token with all required scopes
    full_scopes = TokenInfo(
        valid=True,
        scopes=[
            "email",
            "https://www.googleapis.com/auth/cloud-platform",
            "openid",
        ],
    )
    assert has_required_scopes(full_scopes, REQUIRED_SCOPES) is True

    # Token missing cloud-platform scope
    missing_scope = TokenInfo(valid=True, scopes=["email", "openid"])
    assert has_required_scopes(missing_scope, REQUIRED_SCOPES) is False

    # Invalid token
    invalid_token = TokenInfo(valid=False, scopes=[])
    assert has_required_scopes(invalid_token, REQUIRED_SCOPES) is False

    # Token with no scopes
    no_scopes = TokenInfo(valid=True, scopes=None)
    assert has_required_scopes(no_scopes, REQUIRED_SCOPES) is False


def test_clear_current_credentials():
    """Test clear_current_credentials function."""
    # Set credentials
    creds = Credentials(token="test-token")
    set_current_credentials(creds)
    set_current_project_id("test-project")

    # Verify they're set
    assert get_current_credentials_or_none() is not None
    assert get_current_project_id() == "test-project"

    # Clear them
    clear_current_credentials()

    # Verify they're cleared
    assert get_current_credentials_or_none() is None
    assert get_current_project_id_or_none() is None


@pytest.mark.anyio
async def test_validate_access_token_success():
    """Test validate_access_token with a valid token response."""
    from unittest.mock import AsyncMock

    import httpx

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "email": "user@example.com",
        "expires_in": "3600",
        "scope": "email https://www.googleapis.com/auth/cloud-platform",
        "aud": "client-id.apps.googleusercontent.com",
    }

    # Create mock async client
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    # Create async context manager
    mock_ctx_manager = MagicMock()
    mock_ctx_manager.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx_manager.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_ctx_manager):
        result = await validate_access_token("valid-token")

    assert result.valid is True
    assert result.email == "user@example.com"
    assert result.expires_in == 3600
    assert "email" in result.scopes
    assert result.error is None


@pytest.mark.anyio
async def test_validate_access_token_invalid():
    """Test validate_access_token with an invalid token."""
    from unittest.mock import AsyncMock

    import httpx

    # Create mock response for invalid token
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error_description": "Invalid Value",
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    mock_ctx_manager = MagicMock()
    mock_ctx_manager.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx_manager.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_ctx_manager):
        result = await validate_access_token("invalid-token")

    assert result.valid is False
    assert result.error == "Invalid Value"


@pytest.mark.anyio
async def test_validate_access_token_timeout():
    """Test validate_access_token handles timeout."""
    from unittest.mock import AsyncMock

    import httpx

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")

    mock_ctx_manager = MagicMock()
    mock_ctx_manager.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx_manager.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_ctx_manager):
        result = await validate_access_token("some-token")

    assert result.valid is False
    assert "timed out" in result.error.lower()


def test_validate_access_token_sync_success():
    """Test synchronous token validation."""
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "user@example.com",
            "expires_in": "3600",
            "scope": "email cloud-platform",
            "aud": "client-id",
        }
        mock_client.get.return_value = mock_response

        result = validate_access_token_sync("valid-token")

        assert result.valid is True
        assert result.email == "user@example.com"


def test_get_credentials_from_tool_context_session_no_fallback_to_adc():
    """Ensure we correctly retrieve session credentials without triggering ADC.

    This verifies that when a valid token exists in the session state, we use it
    directly and do NOT call google.auth.default() (ADC).
    """
    # 1. Setup: Clean context and prepare tool_context with a session token
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: "session-token-123"
    }

    # 2. Mock google.auth.default to FAIL if called.
    # We want to prove it is NEVER called when session token is present.
    with patch(
        "google.auth.default", side_effect=RuntimeError("ADC SHOULD NOT BE CALLED")
    ):
        # 3. Action
        creds = get_credentials_from_tool_context(mock_tool_context)

        # 4. Assertions
        assert creds is not None
        assert creds.token == "session-token-123"

        # Additional verification: The credentials object should be a simple Credentials wrapping the token
        assert isinstance(creds, Credentials)


def test_get_credentials_from_tool_context_no_context_returns_none():
    """Ensure get_credentials_from_tool_context returns None if no creds found.

    It should NOT fallback to ADC internally. Fallback is the caller's responsibility.
    """

    with patch("google.auth.default") as mock_adc:
        creds = get_credentials_from_tool_context(None)

        assert creds is None
        mock_adc.assert_not_called()
