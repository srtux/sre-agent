from google.oauth2.credentials import Credentials

from sre_agent.auth import (
    GLOBAL_CONTEXT_CREDENTIALS,
    clear_current_credentials,
    set_current_credentials,
)


def test_context_aware_credentials_delegation():
    """Verify that GLOBAL_CONTEXT_CREDENTIALS delegates to ContextVar."""
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
