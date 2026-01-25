import time
from unittest.mock import patch

import pytest

from sre_agent.auth import (
    TokenInfo,
    _cache_token_info,
    _get_cached_token_info,
    decrypt_token,
    encrypt_token,
    validate_id_token,
)


def test_token_encryption_roundtrip():
    """Verify that a token can be encrypted and decrypted correctly."""
    token = "ya29.test-token-123"
    encrypted = encrypt_token(token)
    assert encrypted != token
    assert "gAAAA" in encrypted  # Fernet prefix

    decrypted = decrypt_token(encrypted)
    assert decrypted == token


def test_decryption_failure_graceful():
    """Verify that decryption failure doesn't crash the system."""
    # Invalid fernet token
    invalid_token = "gAAAAABpddLuv-this-is-garbage-data"
    decrypted = decrypt_token(invalid_token)
    # Should return original if decryption fails (as a migration fallback)
    assert decrypted == invalid_token


def test_token_cache_logic():
    """Verify the TTL cache logic."""
    token = "test-token-cache"
    info = TokenInfo(valid=True, email="user@example.com")

    # 1. Initially empty
    assert _get_cached_token_info(token) is None

    # 2. Store in cache
    _cache_token_info(token, info)
    assert _get_cached_token_info(token) == info

    # 3. Verify expiry (mocking time)
    with patch("time.time", return_value=time.time() + 1000):
        assert _get_cached_token_info(token) is None


@pytest.mark.asyncio
async def test_id_token_validation_failure():
    """Verify that invalid ID tokens are rejected."""
    invalid_id_token = "this.is.not.a.jwt"

    # Mocking the library to avoid network calls for public keys
    with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.side_effect = ValueError("Invalid token")

        info = await validate_id_token(invalid_id_token)
        assert info.valid is False
        assert "Invalid token" in info.error


@pytest.mark.asyncio
async def test_id_token_claim_extraction():
    """Verify that claims are correctly extracted from a valid ID token."""
    valid_id_token = "valid.jwt.id_token"
    mock_claims = {
        "email": "verified@google.com",
        "aud": "client-123",
        "exp": time.time() + 3600,
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_claims):
        with patch("google.auth.transport.requests.Request"):
            info = await validate_id_token(valid_id_token)
            assert info.valid is True
            assert info.email == "verified@google.com"
            assert info.audience == "client-123"
            assert info.expires_in > 0
