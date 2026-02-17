from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sre_agent.api import create_app
from sre_agent.auth import (
    SESSION_STATE_ACCESS_TOKEN_KEY,
    SESSION_STATE_PROJECT_ID_KEY,
    decrypt_token,
)

app = create_app()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_session_manager():
    with patch("sre_agent.api.routers.system.get_session_service") as mock_get_service:
        mock_manager = MagicMock()
        mock_get_service.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def mock_session_manager_middleware():
    with patch("sre_agent.services.get_session_service") as mock_get_service:
        mock_manager = MagicMock()
        mock_get_service.return_value = mock_manager
        yield mock_manager


@pytest.mark.asyncio
async def test_login_endpoint(client, mock_session_manager):
    # Setup mock token validation
    mock_token_info = MagicMock()
    mock_token_info.valid = True
    mock_token_info.email = "test@example.com"

    # Setup mock session creation
    mock_session = MagicMock()
    mock_session.id = "test-session-id"
    # Use AsyncMock for create_session since it's awaited
    mock_session_manager.create_session = AsyncMock(return_value=mock_session)

    with patch(
        "sre_agent.api.routers.system.validate_access_token",
        return_value=mock_token_info,
    ):
        response = client.post(
            "/api/auth/login",
            json={"access_token": "valid-token", "project_id": "test-project"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["session_id"] == "test-session-id"

    # Check cookie
    assert "sre_session_id" in response.cookies
    assert response.cookies["sre_session_id"] == "test-session-id"

    # Verify session was created with correct state
    mock_session_manager.create_session.assert_called_once()
    _args, kwargs = mock_session_manager.create_session.call_args
    assert kwargs["user_id"] == "test@example.com"
    stored_token = kwargs["initial_state"][SESSION_STATE_ACCESS_TOKEN_KEY]
    assert decrypt_token(stored_token) == "valid-token"
    assert kwargs["initial_state"]["user_email"] == "test@example.com"
    assert kwargs["initial_state"][SESSION_STATE_PROJECT_ID_KEY] == "test-project"


@pytest.mark.asyncio
async def test_auth_middleware_with_cookie_and_header(
    client, mock_session_manager_middleware
):
    # Setup mock session
    mock_session = MagicMock()
    mock_session.id = "test-session-id"
    from sre_agent.auth import encrypt_token

    mock_session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: encrypt_token("cached-token"),
        "user_email": "test@example.com",
    }
    # Mock lookup with specific user_id
    mock_session_manager_middleware.get_session = AsyncMock(
        side_effect=lambda sid, user_id: (
            mock_session if user_id == "test@example.com" else None
        )
    )

    with patch("sre_agent.auth.set_current_credentials") as mock_set_creds:
        with patch("sre_agent.auth.set_current_user_id") as mock_set_user:
            with patch("sre_agent.auth.validate_access_token") as mock_validate:
                mock_validate.return_value = MagicMock(
                    valid=True, email="test@example.com"
                )

                # Set cookies on the client instance to avoid DeprecationWarning
                client.cookies.set("sre_session_id", "test-session-id")

                # Make a request with the X-User-ID header
                response = client.get(
                    "/health", headers={"X-User-ID": "test@example.com"}
                )

                assert response.status_code == 200

                # Verify middleware retrieved session with correct user_id
                mock_session_manager_middleware.get_session.assert_called_with(
                    "test-session-id", user_id="test@example.com"
                )
                mock_set_creds.assert_called_once()
                mock_set_user.assert_called_with("test@example.com")


@pytest.mark.asyncio
async def test_auth_middleware_with_expired_token(
    client, mock_session_manager_middleware
):
    # Setup mock session with an expired token
    mock_session = MagicMock()
    mock_session.id = "test-session-id"
    from sre_agent.auth import encrypt_token

    mock_session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: encrypt_token("expired-token"),
        "user_email": "test@example.com",
    }
    mock_session_manager_middleware.get_session = AsyncMock(return_value=mock_session)

    with patch("sre_agent.auth.set_current_credentials") as mock_set_creds:
        with patch("sre_agent.auth.validate_access_token") as mock_validate:
            # Token is invalid
            mock_validate.return_value = MagicMock(valid=False, error="Token expired")

            # Set cookies on the client instance to avoid DeprecationWarning
            client.cookies.set("sre_session_id", "test-session-id")
            response = client.get("/health")

            assert response.status_code == 200

            # Verify context was NOT set
            mock_set_creds.assert_not_called()


@pytest.mark.asyncio
async def test_auth_middleware_user_id_fallback(
    client, mock_session_manager_middleware
):
    # Setup mock session
    mock_session = MagicMock()
    mock_session.id = "test-session-id"
    mock_session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: "token",
        "user_email": "test@example.com",
    }

    # Mock lookup failing for empty user_id but succeeding for 'default'
    def get_session_mock(sid, user_id):
        if user_id == "default":
            return mock_session
        return None

    mock_session_manager_middleware.get_session = AsyncMock(
        side_effect=get_session_mock
    )

    with patch("sre_agent.auth.set_current_credentials") as mock_set_creds:
        with patch("sre_agent.auth.validate_access_token") as mock_validate:
            mock_validate.return_value = MagicMock(valid=True, email="test@example.com")

            # Set cookies on the client instance to avoid DeprecationWarning
            client.cookies.set("sre_session_id", "test-session-id")
            response = client.get("/health")

            assert response.status_code == 200

            # Verify it tried 'default' fallback
            assert mock_session_manager_middleware.get_session.call_count == 2
            mock_session_manager_middleware.get_session.assert_any_call(
                "test-session-id", user_id=""
            )
            mock_session_manager_middleware.get_session.assert_any_call(
                "test-session-id", user_id="default"
            )
            mock_set_creds.assert_called_once()


def test_logout_endpoint(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Cookie should be deleted (max_age=0 or expires in past)
    # httpx (used by TestClient) handles cookie deletion by setting it to empty with expired date
    assert response.cookies.get("sre_session_id") is None
