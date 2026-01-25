from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sre_agent.api import create_app
from sre_agent.auth import (
    SESSION_STATE_ACCESS_TOKEN_KEY,
    encrypt_token,
)
from sre_agent.services import get_session_service

app = create_app()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_session_cookie_decryption_integration(client):
    """
    Integration test for the core auth flow:
    1. Create a session with an ENCRYPTED token.
    2. Send a request with the session cookie.
    3. Verify the middleware retrieves, DECRYPTS, and sets context correctly.
    """
    session_manager = get_session_service()

    # 1. Prepare an encrypted token as it would be stored by /api/auth/login
    raw_token = "secret-access-token-999"
    encrypted_token = encrypt_token(raw_token)

    # 2. Mock a valid session stored in the database
    # In a real integration test, we'd use the actual SQLite, but mocking the manager
    # here allows us to focus on the Middleware <-> Auth interaction.
    mock_session = MagicMock()
    mock_session.id = "integ-session-id"
    mock_session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: encrypted_token,
        "user_email": "integ-user@google.com",
    }

    # Setup the mock validation to return success for our token
    from sre_agent.auth import TokenInfo

    mock_info = TokenInfo(valid=True, email="integ-user@google.com", expires_in=3600)

    with patch("sre_agent.services.get_session_service", return_value=session_manager):
        # We mock the low-level session lookup in the manager to return our pre-baked session
        session_manager.get_session = AsyncMock(return_value=mock_session)

        with patch("sre_agent.auth.validate_access_token", return_value=mock_info):
            with patch("sre_agent.auth.set_current_credentials") as mock_set_creds:
                # 3. Simulate a request from a browser with the session cookie
                client.cookies.set("sre_session_id", "integ-session-id")

                # Use a simple health check or any endpoint
                response = client.get("/health")

                assert response.status_code == 200

                # 4. CRITICAL VERIFICATION:
                # Middleware must have:
                # a) Retrieved the session
                # b) Decrypted the token
                # c) Set credentials with the DECRYPTED token
                mock_set_creds.assert_called_once()
                creds = mock_set_creds.call_args[0][0]
                assert creds.token == raw_token
                assert creds.token != encrypted_token

                print(
                    "\n✅ Integration Check Passed: Encrypted token in session was correctly decrypted by middleware."
                )


@pytest.mark.asyncio
async def test_audience_verification_integration(client):
    """
    Verify that validate_id_token correctly uses GOOGLE_CLIENT_ID for audience verification.
    """
    from sre_agent.auth import validate_id_token

    id_token_str = "valid.but.wrong.audience.jwt"
    client_id = "our-real-client-id"

    with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": client_id}):
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            # Simulate library rejection due to audience mismatch
            mock_verify.side_effect = ValueError("Invalid audience")

            info = await validate_id_token(id_token_str)

            assert info.valid is False
            assert "Invalid audience" in info.error
            # Verify the call included our audience
            mock_verify.assert_called_once()
            _args, kwargs = mock_verify.call_args
            assert kwargs["audience"] == client_id

            print(
                "\n✅ Integration Check Passed: Audience verification is enforced in ID tokens."
            )
