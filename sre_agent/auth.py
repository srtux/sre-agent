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
import threading
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
SESSION_STATE_TRACE_ID_KEY = "_trace_id"
SESSION_STATE_SPAN_ID_KEY = "_span_id"
SESSION_STATE_TRACE_FLAGS_KEY = "_trace_flags"

_credentials_context: contextvars.ContextVar[Credentials | None] = (
    contextvars.ContextVar("credentials_context", default=None)
)

_project_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "project_id_context", default=None
)

_user_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id_context", default=None
)

_correlation_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id_context", default=None
)

_trace_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id_context", default=None
)

_span_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "span_id_context", default=None
)

_trace_flags_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_flags_context", default=None
)

_guest_mode_context: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "guest_mode_context", default=False
)

# Encryption key for securing tokens at rest
# In production, this should be loaded from a Secret Manager
ENCRYPTION_KEY = os.environ.get("SRE_AGENT_ENCRYPTION_KEY")
_cached_fernet = None
_fernet_lock = threading.Lock()


def _get_fernet() -> Any:
    """Gets a Fernet instance for encryption/decryption (thread-safe)."""
    global _cached_fernet
    if _cached_fernet is not None:
        return _cached_fernet

    with _fernet_lock:
        # Double-checked locking
        if _cached_fernet is not None:
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
    """Decrypts a token from storage.

    Returns:
        The decrypted token, or an empty string if decryption fails for a
        known Fernet-encrypted token (to prevent sending encrypted gibberish
        as an OAuth token to downstream services).
    """
    try:
        # If it doesn't look like a Fernet token, return as is (migration fallback)
        if not (encrypted_token.startswith("gAAAA") and len(encrypted_token) > 50):
            return encrypted_token

        f = _get_fernet()
        return cast(str, f.decrypt(encrypted_token.encode()).decode())
    except Exception as e:
        if encrypted_token.startswith("gAAAA"):
            logger.warning(
                f"🚨 Failed to decrypt Fernet token. This strongly indicates an "
                f"SRE_AGENT_ENCRYPTION_KEY mismatch between environment services. "
                f"The token will NOT be used to avoid sending encrypted gibberish "
                f"to downstream APIs. Error: {e}"
            )
            # Return empty string to signal no valid token - prevents sending
            # encrypted token as Bearer auth which causes 401 errors
            return ""
        else:
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


def set_auth_source(source: str) -> None:
    """Sets the authentication source (e.g. 'RemoteSession').

    This is used to track where credentials came from for debugging.
    Currently a stub to resolve test regressions.
    """
    # TODO: Implement full context tracking if needed.
    pass


def set_current_user_id(user_id: str | None) -> None:
    """Sets the user ID (email) for the current context."""
    _user_id_context.set(user_id)


def set_current_project_id(project_id: str | None) -> None:
    """Sets the project ID for the current context."""
    _project_id_context.set(project_id)


def set_correlation_id(correlation_id: str | None) -> None:
    """Sets the correlation ID for the current context."""
    _correlation_id_context.set(correlation_id)


def get_correlation_id() -> str | None:
    """Gets the correlation ID for the current context."""
    return _correlation_id_context.get()


def set_trace_id(trace_id: str | None) -> None:
    """Sets the trace ID for the current context."""
    _trace_id_context.set(trace_id)


def get_trace_id() -> str | None:
    """Gets the trace ID for the current context."""
    return _trace_id_context.get()


def set_guest_mode(enabled: bool) -> None:
    """Sets guest mode for the current request context."""
    _guest_mode_context.set(enabled)


def is_guest_mode() -> bool:
    """Returns True if the current request is in guest mode."""
    return _guest_mode_context.get()


def is_eval_mode() -> bool:
    """Returns True if the agent is running in evaluation mode."""
    return (
        os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
        or os.environ.get("ADK_ENV") == "test"
    )


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

    is_strict = os.getenv("STRICT_EUC_ENFORCEMENT", "false").lower() == "true"

    if is_strict:
        logger.info("Strict EUC enforcement enabled: no ADC fallback for credentials")
        raise PermissionError(
            "Authentication required: End-User Credentials (EUC) not found and ADC fallback is disabled. "
            "Please ensure you are logged in via the web UI."
        )

    is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
    if not is_eval:
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
) -> google.oauth2.credentials.Credentials | None:
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

    encrypted_token = session_state.get(SESSION_STATE_ACCESS_TOKEN_KEY)
    if not encrypted_token:
        return None

    # Decrypt token for use (handles unencrypted tokens via fallback)
    # Returns empty string if decryption fails for known Fernet tokens
    token = decrypt_token(encrypted_token)

    # If decryption failed (empty token), don't create invalid credentials
    if not token:
        logger.warning(
            "No valid token available after decryption - "
            "likely encryption key mismatch between services"
        )
        return None

    # Create Credentials from the access token
    from google.oauth2.credentials import Credentials

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
        self._adc_creds: google.auth.credentials.Credentials | None = None
        super().__init__()  # type: ignore[no-untyped-call]

    @property
    def adc_creds(self) -> google.auth.credentials.Credentials:
        """Lazily load Application Default Credentials."""
        if self._adc_creds is None:
            try:
                self._adc_creds, _ = google.auth.default()
            except Exception as e:
                logger.error(f"Failed to load ADC for context-aware fallback: {e}")
                # Create a dummy credentials object to avoid further errors if ADC is missing
                from google.auth.credentials import AnonymousCredentials

                self._adc_creds = AnonymousCredentials()  # type: ignore[no-untyped-call]
        return self._adc_creds

    @property
    def token(self) -> str | None:
        """Dynamically retrieve the token from the current context, or fall back to ADC."""
        creds = _credentials_context.get()
        user_id = get_current_user_id()
        trace_id = get_trace_id()

        identity_str = f"user={user_id or 'unknown'}, trace={trace_id or 'none'}"

        if creds:
            t = getattr(creds, "token", None)
            logger.debug(
                f"🔑 ContextAwareCredentials: Using token from context ({identity_str})"
            )
            return cast(str, t)

        if self._token:
            logger.debug(
                f"🔑 ContextAwareCredentials: Using explicitly set token ({identity_str})"
            )
            return self._token

        # Fallback to ADC token
        try:
            adc = self.adc_creds
            t = getattr(adc, "token", None)

            # Proactive refresh if token is missing or expired
            if not t or (hasattr(adc, "expired") and adc.expired):
                from google.auth.transport.requests import Request

                logger.info(
                    f"🔑 ContextAwareCredentials: ADC token missing or expired, refreshing... ({identity_str})"
                )
                from typing import Any

                cast(Any, adc).refresh(Request())
                t = getattr(adc, "token", None)

            logger.debug(
                f"🔑 ContextAwareCredentials: Using token from ADC ({identity_str}, type: {type(adc).__name__})"
            )
            return t
        except Exception as e:
            logger.warning(
                f"🔑 ContextAwareCredentials: Error getting/refreshing ADC token: {e}"
            )
            return None

    @token.setter
    def token(self, value: str | None) -> None:
        """Set the internal token."""
        self._token = value

    @property
    def expiry(self) -> Any | None:
        """Get the expiry of the current credentials."""
        creds = _credentials_context.get()
        if creds and hasattr(creds, "expiry"):
            return creds.expiry
        if self._token:
            return None
        adc = self.adc_creds
        return getattr(adc, "expiry", None)

    @expiry.setter
    def expiry(self, value: Any) -> None:
        """Setter for expiry to satisfy the base class requirement."""
        # This proxy generally delegates to context, but we allow setting for compatibility
        pass

    @property
    def valid(self) -> bool:
        """Check if the current context has valid credentials."""
        creds = _credentials_context.get()
        if creds:
            v = cast(bool, creds.valid)
            # logger.debug(f"🔑 ContextAwareCredentials: Context creds valid: {v}")
            return v

        if self._token:
            return True

        v = cast(bool, self.adc_creds.valid)
        # logger.debug(f"🔑 ContextAwareCredentials: ADC creds valid: {v}")
        return v

    @property
    def expired(self) -> bool:
        """Check if the current credentials have expired."""
        creds = _credentials_context.get()
        if creds:
            return cast(bool, creds.expired)
        if self._token:
            return False
        return cast(bool, self.adc_creds.expired)

    def apply(self, headers: dict[str, str], token: str | None = None) -> None:
        """Apply credentials to the request headers."""
        creds = _credentials_context.get()
        if creds:
            creds.apply(headers, token=token)  # type: ignore[no-untyped-call]
        else:
            # Fallback: do nothing or use default logic if no user identity
            t = self.token
            if t:
                headers["authorization"] = f"Bearer {t}"

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
                    logger.info(
                        "🔑 ContextAwareCredentials: Refreshing context credentials..."
                    )
                    creds.refresh(request)
                else:
                    logger.debug(
                        "🔑 ContextAwareCredentials: Context creds not refreshable"
                    )
            except Exception as e:
                logger.warning(
                    f"🔑 ContextAwareCredentials: Context refresh failed: {e}"
                )
        else:
            logger.info(
                "🔑 ContextAwareCredentials: No credentials in context. Falling back to ADC refresh."
            )
            try:
                self.adc_creds.refresh(request)  # type: ignore[no-untyped-call]
                logger.info(
                    f"🔑 ContextAwareCredentials: ADC refresh successful. Token exists: {self.adc_creds.token is not None}"
                )
            except Exception as e:
                logger.warning(f"🔑 ContextAwareCredentials: ADC refresh failed: {e}")

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
    _correlation_id_context.set(None)


# =============================================================================
# Zero-Trust Identity Propagation Logic
# =============================================================================


@dataclass
class AuthContext:
    """Consolidated authentication and trace context."""

    credentials: Credentials | None = None
    project_id: str | None = None
    user_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    trace_flags: str | None = None


def get_auth_context_from_tool_context(
    tool_context: "ToolContext | None",
) -> AuthContext:
    """Extracts a full AuthContext from the provided ToolContext or global vars."""
    # 1. Start with values from ContextVars (local)
    ctx = AuthContext(
        credentials=get_current_credentials_or_none(),
        project_id=get_current_project_id_or_none(),
        user_id=get_current_user_id(),
        trace_id=get_trace_id(),
        span_id=_span_id_context.get(),
        trace_flags=_trace_flags_context.get(),
    )

    # 2. Override with values from session state (Agent Engine)
    if tool_context is not None:
        inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
            tool_context, "_invocation_context", None
        )
        session_obj = getattr(inv_ctx, "session", None) if inv_ctx else None
        state = None
        if session_obj is not None:
            state = getattr(session_obj, "state", None)
            if state is None and isinstance(session_obj, dict):
                state = session_obj.get("state") or session_obj

        if state:
            # Credentials
            session_creds = get_credentials_from_session(state)
            if session_creds:
                ctx.credentials = session_creds

            # Project ID
            session_project = get_project_id_from_session(state)
            if session_project:
                ctx.project_id = session_project

            # User ID (usually not in session state, but we check anyway)
            session_user = state.get("_user_id")
            if session_user:
                ctx.user_id = session_user

            # Trace info
            if SESSION_STATE_TRACE_ID_KEY in state:
                ctx.trace_id = state[SESSION_STATE_TRACE_ID_KEY]
            if SESSION_STATE_SPAN_ID_KEY in state:
                ctx.span_id = state[SESSION_STATE_SPAN_ID_KEY]
            if SESSION_STATE_TRACE_FLAGS_KEY in state:
                ctx.trace_flags = state[SESSION_STATE_TRACE_FLAGS_KEY]

    return ctx


def set_auth_context(ctx: AuthContext) -> list[Any]:
    """Sets the authentication context and returns tokens for resetting."""
    tokens: list[Any] = []
    if ctx.credentials:
        tokens.append(_credentials_context.set(ctx.credentials))
    if ctx.project_id:
        tokens.append(_project_id_context.set(ctx.project_id))
    if ctx.user_id:
        tokens.append(_user_id_context.set(ctx.user_id))
    if ctx.trace_id:
        tokens.append(_trace_id_context.set(ctx.trace_id))
    if ctx.span_id:
        tokens.append(_span_id_context.set(ctx.span_id))
    if ctx.trace_flags:
        tokens.append(_trace_flags_context.set(ctx.trace_flags))

    # Attempt OTel rehydration if trace context is available
    otel_token = rehydrate_otel_context(ctx)
    if otel_token:
        tokens.append(("otel", otel_token))

    return tokens


def set_auth_context_from_tool_context(
    tool_context: "ToolContext | None",
) -> list[Any]:
    """Extracts and sets the auth context from tool context in one go."""
    ctx = get_auth_context_from_tool_context(tool_context)
    return set_auth_context(ctx)


def reset_auth_context(tokens: list[Any]) -> None:
    """Resets the authentication context using the provided tokens."""
    for token in reversed(tokens):
        if isinstance(token, tuple) and token[0] == "otel":
            from opentelemetry import context

            context.detach(token[1])
        else:
            token.var.reset(token)


def rehydrate_otel_context(ctx: AuthContext) -> Any | None:
    """Rehydrates the OpenTelemetry context from the provided AuthContext.

    This is useful in Agent Engine where the original OTel context is lost.
    Returns an OTel context token if rehydration occurred, None otherwise.
    """
    if not ctx.trace_id:
        return None

    try:
        from opentelemetry import context, trace
        from opentelemetry.trace import SpanContext, TraceFlags

        # Check if we already have a valid span context
        current_span = trace.get_current_span()
        if current_span and current_span.get_span_context().is_valid:
            # OPT-12: If we already have a valid span, we don't override it
            # to preserve local tracing hierarchy.
            return None

        # Create a new SpanContext from the IDs
        span_context = SpanContext(
            trace_id=int(ctx.trace_id, 16),
            span_id=int(ctx.span_id, 16) if ctx.span_id else 0,
            is_remote=True,
            trace_flags=TraceFlags(int(ctx.trace_flags, 16))  # type: ignore[arg-type]
            if ctx.trace_flags
            else TraceFlags.SAMPLED,
        )

        from opentelemetry.trace.span import NonRecordingSpan

        remote_span = NonRecordingSpan(span_context)

        # Make this span context active for the current task
        new_context = trace.set_span_in_context(remote_span)
        return context.attach(new_context)

    except Exception as e:
        logger.debug(f"Failed to rehydrate OTel context: {e}")
        return None


def get_auth_header(ctx: AuthContext | None = None) -> dict[str, str]:
    """Gets the Authorization header for the current or provided context.

    Useful for manual HTTP requests using httpx or requests.
    """
    if ctx is None:
        # Avoid circular dependency by using local imports if needed,
        # but here we are in the same module.
        creds = get_current_credentials_or_none()
        token = creds.token if creds else None
    else:
        token = ctx.credentials.token if ctx.credentials else None

    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}
