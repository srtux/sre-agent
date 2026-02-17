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
    mock_get.side_effect = lambda k, d=None: (
        test_key if k == "SRE_AGENT_ENCRYPTION_KEY" else d
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


def test_decryption_key_mismatch_returns_empty():
    """Test that decryption with wrong key returns empty string for Fernet tokens.

    This prevents sending encrypted gibberish to downstream APIs when there's
    an encryption key mismatch between services (Cloud Run vs Agent Engine).
    """
    # Create a token that looks like a valid Fernet token (>50 chars, starts with gAAAA)
    # but with invalid/corrupted data that can't be decrypted
    invalid_fernet = (
        "gAAAAABpddLuv-invalid-fernet-token-with-enough-characters-to-look-real-"
        "and-trigger-the-decryption-path-in-our-code-0123456789"
    )
    assert len(invalid_fernet) > 50
    assert invalid_fernet.startswith("gAAAA")

    decrypted = decrypt_token(invalid_fernet)
    # Should return empty string, NOT the encrypted gibberish
    assert decrypted == ""


def test_get_credentials_from_session_key_mismatch_returns_none():
    """Test that session credentials return None when decryption fails.

    When there's an encryption key mismatch, get_credentials_from_session
    should return None rather than invalid Credentials with gibberish token.
    """
    # Create a token that looks like a valid Fernet token but can't be decrypted
    invalid_fernet = (
        "gAAAAABpddLuv-invalid-fernet-token-with-enough-characters-to-look-real-"
        "and-trigger-the-decryption-path-in-our-code-0123456789"
    )

    session_state = {SESSION_STATE_ACCESS_TOKEN_KEY: invalid_fernet}
    creds = get_credentials_from_session(session_state)

    # Should return None instead of Credentials with invalid token
    assert creds is None
