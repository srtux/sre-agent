from google.oauth2.credentials import Credentials

from sre_agent.auth import (
    GLOBAL_CONTEXT_CREDENTIALS,
    clear_current_credentials,
    set_current_credentials,
)


def test_context_aware_credentials_delegation():
    """Verify that GLOBAL_CONTEXT_CREDENTIALS delegates to ContextVar."""
    from unittest.mock import MagicMock, patch

    # Mock google.auth.default to return no token
    # This prevents the test from picking up real ADC tokens in the environment
    mock_adc = MagicMock()
    mock_adc.token = None
    mock_adc.valid = False

    # Reset the singleton's cached ADC credentials to force re-evaluation
    # This ensures the mock below is actually used
    GLOBAL_CONTEXT_CREDENTIALS._adc_creds = None

    with patch("google.auth.default", return_value=(mock_adc, "test-project")):
        clear_current_credentials()

        # 1. No credentials in context
        assert GLOBAL_CONTEXT_CREDENTIALS.token is None

    # 2. Set user credentials
    user_token = "fake-user-token"
    user_creds = Credentials(token=user_token)
    set_current_credentials(user_creds)

    assert GLOBAL_CONTEXT_CREDENTIALS.token == user_token

    # 3. Apply to headers
    headers = {}
    GLOBAL_CONTEXT_CREDENTIALS.apply(headers)
    assert headers["authorization"] == f"Bearer {user_token}"

    clear_current_credentials()
    assert GLOBAL_CONTEXT_CREDENTIALS.token is None
