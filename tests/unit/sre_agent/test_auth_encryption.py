from unittest.mock import patch

from google.oauth2.credentials import Credentials

from sre_agent.auth import (
    SESSION_STATE_ACCESS_TOKEN_KEY,
    decrypt_token,
    encrypt_token,
    get_credentials_from_session,
)


def test_encryption_decryption_cycle():
    """Test that a token can be encrypted and then decrypted correctly."""
    token = "ya29.A0ARrdaM8-TEST-TOKEN"
    encrypted = encrypt_token(token)

    assert encrypted != token
    assert encrypted.startswith("gAAAA")

    decrypted = decrypt_token(encrypted)
    assert decrypted == token


def test_decryption_fallback():
    """Test that non-encrypted tokens are returned as-is."""
    plain_token = "plain-text-token"
    assert decrypt_token(plain_token) == plain_token

    short_fernet_like = "gAAAA123"  # too short
    assert decrypt_token(short_fernet_like) == short_fernet_like


def test_get_credentials_from_session_decryption():
    """Test that get_credentials_from_session automatically decrypts the token."""
    token = "secret-session-token"
    encrypted = encrypt_token(token)

    session_state = {SESSION_STATE_ACCESS_TOKEN_KEY: encrypted}
    creds = get_credentials_from_session(session_state)

    assert creds is not None
    assert creds.token == token
    assert isinstance(creds, Credentials)


@patch("os.environ.get")
def test_consistent_key_from_env(mock_get):
    """Test that the same ENCRYPTION_KEY produces decryptable tokens."""
    # Use a fixed valid Fernet key
    test_key = (
        "52E77h0CL_ZEwMxY0z7iXct98Fr50Savh5Jq4qX6weM="  # pragma: allowlist secret
    )
    mock_get.side_effect = (
        lambda k, d=None: test_key if k == "SRE_AGENT_ENCRYPTION_KEY" else d
    )

    # Reset the cached Fernet instance to pick up the mocked env
    with patch("sre_agent.auth._cached_fernet", None):
        token = "stable-token"
        encrypted = encrypt_token(token)
        decrypted = decrypt_token(encrypted)
        assert decrypted == token


def test_transient_key_fallback():
    """Test encryption works even without SRE_AGENT_ENCRYPTION_KEY (transient key)."""
    with patch("os.environ.get", return_value=None):
        with patch("sre_agent.auth._cached_fernet", None):
            token = "transient-token"
            encrypted = encrypt_token(token)
            decrypted = decrypt_token(encrypted)
            assert decrypted == token
