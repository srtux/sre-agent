"""Authentication utilities for propagating End User Credentials (EUC).

This module implements OAuth 2.0 credential propagation for the SRE Agent,
enabling multi-tenant access where each user accesses their own GCP projects.

## Architecture Overview

The EUC (End User Credentials) flow works as follows:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flutter Web    │     │  FastAPI        │     │  ADK Agent      │
│  (Cloud Run)    │     │  (Cloud Run)    │     │  (Local/Engine) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ 1. Google Sign-In     │                       │
         │    (OAuth 2.0)        │                       │
         │    Scopes:            │                       │
         │    - email            │                       │
         │    - cloud-platform   │                       │
         │                       │                       │
         │ 2. Send Request       │                       │
         │    Headers:           │                       │
         │    - Authorization:   │                       │
         │      Bearer <token>   │                       │
         │    - X-GCP-Project-ID │                       │
         ├──────────────────────>│                       │
         │                       │ 3. Middleware         │
         │                       │    - Extract token    │
         │                       │    - Validate (opt)   │
         │                       │    - Set ContextVar   │
         │                       │                       │
         │                       │ 4a. Local Execution   │
         │                       ├──────────────────────>│
         │                       │    ContextVar creds   │
         │                       │                       │
         │                       │ 4b. Agent Engine      │
         │                       ├──────────────────────>│
         │                       │    Session State:     │
         │                       │    _user_access_token │
         │                       │    _user_project_id   │
         │                       │                       │
         │                       │ 5. Tool Execution     │
         │                       │    get_credentials_   │
         │                       │    from_tool_context()│
         │                       │<──────────────────────┤
         │                       │                       │
         │ 6. Response           │                       │
         │<──────────────────────┤                       │
         │                       │                       │
```

## Execution Contexts

1. **ContextVar-based**: For local execution where Cloud Run middleware sets
   credentials in context variables that tools can access.

2. **Session State-based**: For remote Agent Engine execution where credentials
   are passed via session state (since ContextVars don't cross process boundaries).

## Credential Resolution Order

1. ContextVar (set by middleware in local mode)
2. Session state (for Agent Engine remote execution)
3. Default credentials (service account fallback)

## Security Considerations

- Access tokens are short-lived (typically 1 hour)
- Token refresh is handled by the frontend (Google Sign-In)
- Backend can optionally validate tokens via Google's tokeninfo endpoint
- Credentials are NOT persisted to disk; only held in memory during request
"""

import contextvars
import logging
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import google.auth
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials

if TYPE_CHECKING:
    from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# Session state keys for credential propagation to Agent Engine
# These keys are used to pass user credentials through session state
# when calling remote agents where ContextVars aren't available.
SESSION_STATE_ACCESS_TOKEN_KEY = "_user_access_token"
SESSION_STATE_PROJECT_ID_KEY = "_user_project_id"

_credentials_context: contextvars.ContextVar[Credentials | None] = (
    contextvars.ContextVar("credentials_context", default=None)
)

_project_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "project_id_context", default=None
)

_user_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id_context", default=None
)

# Encryption key for securing tokens at rest
# In production, this should be loaded from a Secret Manager
ENCRYPTION_KEY = os.environ.get("SRE_AGENT_ENCRYPTION_KEY")
_cached_fernet = None


def _get_fernet() -> Any:
    """Gets a Fernet instance for encryption/decryption."""
    global _cached_fernet
    if _cached_fernet:
        return _cached_fernet

    from cryptography.fernet import Fernet

    key = ENCRYPTION_KEY
    if not key:
        # Fallback for local development (NOT for production)
        # Use a consistent key within the same process
        key = Fernet.generate_key().decode()
        logger.warning(
            "⚠️ SRE_AGENT_ENCRYPTION_KEY not set. Using a transient key. Tokens will not be decryptable after restart."
        )

    _cached_fernet = Fernet(key.encode())
    return _cached_fernet


def encrypt_token(token: str) -> str:
    """Encrypts a token for storage."""
    try:
        f = _get_fernet()
        return cast(str, f.encrypt(token.encode()).decode())
    except Exception as e:
        logger.error(f"Failed to encrypt token: {e}")
        return token


def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a token from storage."""
    try:
        # If it doesn't look like a Fernet token, return as is (migration fallback)
        if not (encrypted_token.startswith("gAAAA") and len(encrypted_token) > 50):
            return encrypted_token

        f = _get_fernet()
        return cast(str, f.decrypt(encrypted_token.encode()).decode())
    except Exception as e:
        logger.debug(f"Decryption failed (might be unencrypted): {e}")
        return encrypted_token


# Token Validation Cache (TTL: 10 minutes)
_token_cache: dict[str, tuple[float, "TokenInfo"]] = {}
TOKEN_CACHE_TTL = 600  # 10 minutes


def _get_cached_token_info(token: str) -> "TokenInfo | None":
    """Retrieves token info from cache if not expired."""
    if token in _token_cache:
        expiry, info = _token_cache[token]
        if time.time() < expiry:
            return info
        del _token_cache[token]
    return None


def _cache_token_info(token: str, info: "TokenInfo") -> None:
    """Caches token info if valid."""
    if info.valid:
        _token_cache[token] = (time.time() + TOKEN_CACHE_TTL, info)


def set_current_credentials(creds: Credentials) -> None:
    """Sets the credentials for the current context."""
    _credentials_context.set(creds)


def set_current_user_id(user_id: str | None) -> None:
    """Sets the user ID (email) for the current context."""
    _user_id_context.set(user_id)


def set_current_project_id(project_id: str | None) -> None:
    """Sets the project ID for the current context."""
    _project_id_context.set(project_id)


def get_current_credentials() -> tuple[google.auth.credentials.Credentials, str | None]:
    """Gets the credentials for the current context, falling back to default.

    Returns:
        A tuple of (credentials, project_id).
    """
    creds = _credentials_context.get()
    if creds:
        return creds, None

    # Fallback to default if no user credentials (e.g. running locally or background tasks)
    # UNLESS strict EUC enforcement is enabled.
    import os

    is_strict = os.getenv("STRICT_EUC_ENFORCEMENT", "false").lower() == "true"

    if is_strict:
        logger.info("Strict EUC enforcement enabled: no ADC fallback for credentials")
        raise PermissionError(
            "Authentication required: End-User Credentials (EUC) not found and ADC fallback is disabled. "
            "Please ensure you are logged in via the web UI."
        )

    logger.warning(
        "⚠️ No user credentials (EUC) found in context. Falling back to Application Default Credentials (ADC). "
        "This is expected for background tasks but may indicate an auth failure in interactive sessions."
    )
    try:
        return google.auth.default()
    except Exception as e:
        logger.error(f"Failed to load Application Default Credentials: {e}")
        raise PermissionError(
            f"Authentication failed: No user credentials found and ADC fallback failed: {e}. "
            "If you are running locally, please run 'gcloud auth application-default login'."
        ) from e


def get_current_credentials_or_none() -> Credentials | None:
    """Gets the explicitly set credentials or None."""
    return _credentials_context.get()


def get_current_project_id_or_none() -> str | None:
    """Gets the explicitly set project ID or None."""
    return _project_id_context.get()


def get_current_user_id() -> str | None:
    """Gets the explicitly set user ID (email) or None."""
    return _user_id_context.get()


def get_current_project_id() -> str | None:
    """Gets the project ID for the current context, falling back to discovery.

    Checks:
    1. ContextVar (set by middleware)
    2. Environment variables (GOOGLE_CLOUD_PROJECT, GCP_PROJECT_ID)
    3. Application Default Credentials
    """
    # 1. Check ContextVar
    project_id = _project_id_context.get()
    if project_id:
        return project_id

    # 2. Check Environment
    import os

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
        "GCP_PROJECT_ID"
    )
    if project_id:
        return project_id

    # 3. Check Credentials
    # UNLESS strict EUC enforcement is enabled and we have no user credentials.
    if os.getenv("STRICT_EUC_ENFORCEMENT", "false").lower() == "true":
        logger.debug(
            "Strict EUC enforcement enabled: skipping ADC fallback for project ID"
        )
        return None

    try:
        logger.debug("Falling back to ADC for project ID discovery")
        _, project_id = google.auth.default()
        return project_id
    except Exception as e:
        logger.debug(f"ADC project discovery failed: {e}")
        pass

    return None


def get_credentials_from_session(
    session_state: dict[str, Any] | None,
) -> Credentials | None:
    """Extract user credentials from session state.

    This is used when running in Agent Engine where ContextVars aren't available.
    The Cloud Run proxy stores the user's access token in session state before
    calling the remote agent.

    Args:
        session_state: The session state dictionary (from session.state)

    Returns:
        Credentials object if token found in session state, None otherwise.
    """
    if not session_state:
        return None

    token = session_state.get(SESSION_STATE_ACCESS_TOKEN_KEY)
    if not token:
        return None

    # Create Credentials from the access token
    return Credentials(token=token)  # type: ignore[no-untyped-call]


def get_project_id_from_session(session_state: dict[str, Any] | None) -> str | None:
    """Extract project ID from session state.

    Args:
        session_state: The session state dictionary (from session.state)

    Returns:
        Project ID if found in session state, None otherwise.
    """
    if not session_state:
        return None

    return session_state.get(SESSION_STATE_PROJECT_ID_KEY)


def get_credentials_from_tool_context(
    tool_context: "ToolContext | None",
) -> Credentials | None:
    """Get user credentials from tool context, checking both ContextVar and session.

    This is the primary function tools should use to get user credentials.
    It checks multiple sources in order of preference:
    1. ContextVar (for local execution)
    2. Session state (for Agent Engine execution)

    Args:
        tool_context: The ADK ToolContext (can be None for standalone tool calls)

    Returns:
        Credentials object if found, None otherwise (will fall back to default).
    """
    # First, check ContextVar (works in local execution)
    creds = get_current_credentials_or_none()
    if creds and hasattr(creds, "token") and creds.token:
        logger.debug("Using credentials from ContextVar")
        return creds

    # Second, check session state (for Agent Engine)
    if tool_context is not None:
        try:
            logger.debug(
                f"Extracting credentials from tool_context type={type(tool_context)}"
            )
            inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
                tool_context, "_invocation_context", None
            )

            if inv_ctx is None:
                logger.debug(
                    f"Invocation context not found in tool_context. Available attrs: {dir(tool_context)}"
                )

            session_obj = getattr(inv_ctx, "session", None) if inv_ctx else None
            if session_obj is not None:
                # Handle both object with .state and dictionary (for different ADK versions/mocks)
                state_dict = getattr(session_obj, "state", None)
                if state_dict is None and isinstance(session_obj, dict):
                    state_dict = session_obj.get("state") or session_obj

                logger.debug(
                    f"Found session state keys: {list(state_dict.keys()) if state_dict else 'None'}"
                )
                creds = get_credentials_from_session(state_dict)
                if creds:
                    logger.debug("Using credentials from session state")

                    # If user ID not set in context, try to set it from session
                    # This helps in Agent Engine mode
                    user_id = get_current_user_id()
                    if not user_id and state_dict:
                        user_email = state_dict.get("user_email")
                        if user_email:
                            set_current_user_id(user_email)
                            logger.info(
                                f"Auto-set user ID to {user_email} from session state"
                            )

                    return creds
                else:
                    logger.debug(
                        f"No token found in session state with key {SESSION_STATE_ACCESS_TOKEN_KEY}"
                    )
            else:
                logger.debug("No session found in invocation_context")
        except Exception as e:
            logger.debug(f"Error getting credentials from tool_context: {e}")

    logger.debug("No user credentials found in ContextVar or session")
    return None


def get_project_id_from_tool_context(tool_context: "ToolContext | None") -> str | None:
    """Get project ID from tool context, checking both ContextVar and session.

    Priority order:
    1. ContextVar (explicitly set via middleware)
    2. Session state (for Agent Engine execution)
    3. Discovery (env vars or ADC)

    Args:
        tool_context: The ADK ToolContext (can be None for standalone tool calls)

    Returns:
        Project ID if found, None otherwise.
    """
    # 1. Check ContextVar
    project_id = get_current_project_id_or_none()
    if project_id:
        return project_id

    # 2. Check session state
    if tool_context is not None:
        try:
            inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
                tool_context, "_invocation_context", None
            )
            session_obj = getattr(inv_ctx, "session", None) if inv_ctx else None
            if session_obj is not None:
                # Handle both object with .state and dictionary
                state_dict = getattr(session_obj, "state", None)
                if state_dict is None and isinstance(session_obj, dict):
                    state_dict = session_obj.get("state") or session_obj

                project_id = get_project_id_from_session(state_dict)
                if project_id:
                    return project_id
        except Exception as e:
            logger.debug(f"Error getting project_id from tool_context: {e}")

    # 3. Fallback to discovery
    return get_current_project_id()


def get_user_id_from_tool_context(tool_context: "ToolContext | None") -> str | None:
    """Get user ID (email) from tool context, checking both ContextVar and session.

    Args:
        tool_context: The ADK ToolContext.

    Returns:
        User email if found, None otherwise.
    """
    # 1. Check ContextVar
    user_id = get_current_user_id()
    if user_id:
        return user_id

    # 2. Check session state (assuming we store it there in future)
    # For now, we only support ContextVar based propagation for user identity
    # TODO: Add session state propagation for user ID in Agent Engine mode
    return None


# =============================================================================
# Token Validation
# =============================================================================


@dataclass
class TokenInfo:
    """Information about a validated OAuth token.

    Attributes:
        valid: Whether the token is valid and not expired.
        email: The email address associated with the token.
        expires_in: Seconds until token expiration (0 if expired).
        scopes: List of OAuth scopes granted to the token.
        audience: The client ID the token was issued for.
        error: Error message if validation failed.
    """

    valid: bool
    email: str | None = None
    expires_in: int = 0
    scopes: list[str] | None = None
    audience: str | None = None
    error: str | None = None


class ContextAwareCredentials(google.auth.credentials.Credentials):
    """Credentials that dynamically delegate to the current execution context.

    This class bridges the gap between long-lived service clients (like gRPC)
    and per-request user identity. It satisfies the google-auth interface
    while pulling the actual token from ContextVars at the moment of the request.
    """

    def __init__(self) -> None:
        """Initialize context-aware credentials."""
        self._token: str | None = None
        super().__init__()  # type: ignore[no-untyped-call]

    @property
    def token(self) -> str | None:
        """Dynamically retrieve the token from the current context."""
        creds = _credentials_context.get()
        if creds:
            t = getattr(creds, "token", None)
            # logger.debug(f"🔑 ContextAwareCredentials: Found token in ContextVar")
            return cast(str, t)

        if self._token:
            # logger.debug(f"🔑 ContextAwareCredentials: Using fallback token")
            return self._token

        return None

    @token.setter
    def token(self, value: str | None) -> None:
        """Set the internal token."""
        self._token = value

    @property
    def valid(self) -> bool:
        """Check if the current context has valid credentials."""
        creds = _credentials_context.get()
        if creds:
            return cast(bool, creds.valid)
        return False

    def apply(self, headers: dict[str, str], token: str | None = None) -> None:
        """Apply credentials to the request headers."""
        creds = _credentials_context.get()
        if creds:
            creds.apply(headers, token=token)  # type: ignore[no-untyped-call]
        else:
            # Fallback: do nothing or use default logic if no user identity
            if self.token:
                headers["authorization"] = f"Bearer {self.token}"

    def before_request(
        self, request: Any, method: str, url: str, headers: dict[str, str]
    ) -> None:
        """Called before a request is made to inject credentials."""
        creds = _credentials_context.get()
        if creds:
            creds.before_request(request, method, url, headers)  # type: ignore[no-untyped-call]
        else:
            # If no user context, we don't inject anything here.
            # This allows the client to fall back to its internal behavior
            # or default auth if configured elsewhere.
            self.apply(headers)

    def refresh(self, request: Any) -> None:
        """Delegates refresh to the current credentials."""
        creds = _credentials_context.get()
        if creds:
            try:
                # Only call refresh if the credentials support it (have a refresh token)
                if hasattr(creds, "refresh_token") and creds.refresh_token:
                    logger.debug(
                        "🔑 ContextAwareCredentials: Refreshing credentials..."
                    )
                    creds.refresh(request)
                else:
                    logger.debug(
                        "🔑 ContextAwareCredentials: Creds in context not refreshable (no refresh token)"
                    )
            except Exception as e:
                logger.warning(f"🔑 ContextAwareCredentials: Refresh failed: {e}")
        else:
            logger.debug(
                "🔑 ContextAwareCredentials: No credentials in context to refresh"
            )

    def __deepcopy__(self, memo: Any) -> "ContextAwareCredentials":
        """Dunder method to support deepcopy and pickling during deployment.

        Since we are a proxy to global ContextVars, sharing the same instance
        during deepcopy is acceptable and avoids pickling issues with locks.
        """
        if id(self) in memo:
            return cast("ContextAwareCredentials", memo[id(self)])
        return self


# Singleton instance of context-aware credentials for global use
# Inject this into clients that need to pick up request identity dynamically.
GLOBAL_CONTEXT_CREDENTIALS = ContextAwareCredentials()


async def validate_access_token(access_token: str) -> TokenInfo:
    """Validate an OAuth 2.0 access token with Google's tokeninfo endpoint.

    This function is cached to prevent high-latency network calls on every request.
    """
    # 1. Check cache first
    cached = _get_cached_token_info(access_token)
    if cached:
        return cached

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
            )

            if response.status_code == 200:
                data = response.json()
                info = TokenInfo(
                    valid=True,
                    email=data.get("email"),
                    expires_in=int(data.get("expires_in", 0)),
                    scopes=data.get("scope", "").split(" ")
                    if data.get("scope")
                    else [],
                    audience=data.get("aud"),
                )
                _cache_token_info(access_token, info)
                return info
            elif response.status_code == 400:
                # Token is invalid or expired
                error_data = response.json()
                return TokenInfo(
                    valid=False,
                    error=error_data.get("error_description", "Invalid token"),
                )
            else:
                return TokenInfo(
                    valid=False,
                    error=f"Token validation failed with status {response.status_code}",
                )

    except httpx.TimeoutException:
        logger.warning("Token validation timed out")
        return TokenInfo(valid=False, error="Token validation timed out")
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return TokenInfo(valid=False, error=str(e))


async def validate_id_token(id_token_str: str) -> TokenInfo:
    """Validates an OIDC ID Token locally using Google's public keys.

    This is much faster than validate_access_token as it doesn't always
    require a network call (public keys are cached by the library).
    """
    # Check cache first
    cached = _get_cached_token_info(id_token_str)
    if cached:
        return cached

    from google.auth.transport import requests

    try:
        # Request object is used for fetching/caching Google's public keys
        request = requests.Request()

        # Local signature verification and claim extraction
        # SECURITY: Specifying audience (GOOGLE_CLIENT_ID) prevents ID token substitution attacks
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        idinfo = id_token.verify_oauth2_token(id_token_str, request, audience=client_id)  # type: ignore[no-untyped-call]

        info = TokenInfo(
            valid=True,
            email=idinfo.get("email"),
            expires_in=int(idinfo.get("exp", 0)) - int(time.time()),
            scopes=["openid", "email", "profile"],
            audience=idinfo.get("aud"),
        )
        _cache_token_info(id_token_str, info)
        return info
    except ValueError as e:
        # Invalid token
        return TokenInfo(valid=False, error=str(e))
    except Exception as e:
        logger.error(f"ID Token validation error: {e}")
        return TokenInfo(valid=False, error=str(e))


def validate_access_token_sync(access_token: str) -> TokenInfo:
    """Synchronous version of validate_access_token.

    Uses httpx synchronous client for environments where async is not available.

    Args:
        access_token: The OAuth 2.0 access token to validate.

    Returns:
        TokenInfo with validation results.
    """
    import httpx

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
            )

            if response.status_code == 200:
                data = response.json()
                return TokenInfo(
                    valid=True,
                    email=data.get("email"),
                    expires_in=int(data.get("expires_in", 0)),
                    scopes=data.get("scope", "").split(" ")
                    if data.get("scope")
                    else [],
                    audience=data.get("aud"),
                )
            elif response.status_code == 400:
                error_data = response.json()
                return TokenInfo(
                    valid=False,
                    error=error_data.get("error_description", "Invalid token"),
                )
            else:
                return TokenInfo(
                    valid=False,
                    error=f"Token validation failed with status {response.status_code}",
                )

    except httpx.TimeoutException:
        logger.warning("Token validation timed out")
        return TokenInfo(valid=False, error="Token validation timed out")
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return TokenInfo(valid=False, error=str(e))


def has_required_scopes(token_info: TokenInfo, required_scopes: list[str]) -> bool:
    """Check if a token has all required OAuth scopes.

    Args:
        token_info: TokenInfo from validate_access_token.
        required_scopes: List of required scope strings.

    Returns:
        True if token has all required scopes, False otherwise.
    """
    if not token_info.valid or not token_info.scopes:
        return False

    return all(scope in token_info.scopes for scope in required_scopes)


# Required scopes for SRE Agent operations
REQUIRED_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]


def clear_current_credentials() -> None:
    """Clear credentials from the current context.

    Call this after request processing to prevent credential leakage.
    """
    _credentials_context.set(None)
    _project_id_context.set(None)
    _user_id_context.set(None)
