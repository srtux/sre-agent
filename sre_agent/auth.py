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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import google.auth
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


def set_current_credentials(creds: Credentials) -> None:
    """Sets the credentials for the current context."""
    _credentials_context.set(creds)


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

    if os.getenv("STRICT_EUC_ENFORCEMENT", "false").lower() == "true":
        logger.info("Strict EUC enforcement enabled: no ADC fallback for credentials")
        raise PermissionError(
            "Authentication required: EUC not found and ADC fallback is disabled. "
            "Please ensure you are logged in."
        )

    return google.auth.default()


def get_current_credentials_or_none() -> Credentials | None:
    """Gets the explicitly set credentials or None."""
    return _credentials_context.get()


def get_current_project_id_or_none() -> str | None:
    """Gets the explicitly set project ID or None."""
    return _project_id_context.get()


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
        _, project_id = google.auth.default()
        return project_id
    except Exception:
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
            inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
                tool_context, "_invocation_context", None
            )
            session_state = getattr(inv_ctx, "session", None) if inv_ctx else None
            if session_state is not None:
                state_dict = getattr(session_state, "state", None)
                creds = get_credentials_from_session(state_dict)
                if creds:
                    logger.debug("Using credentials from session state")
                    return creds
        except Exception as e:
            logger.debug(f"Error getting credentials from tool_context: {e}")

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
            session_state = getattr(inv_ctx, "session", None) if inv_ctx else None
            if session_state is not None:
                state_dict = getattr(session_state, "state", None)
                project_id = get_project_id_from_session(state_dict)
                if project_id:
                    return project_id
        except Exception as e:
            logger.debug(f"Error getting project_id from tool_context: {e}")

    # 3. Fallback to discovery
    return get_current_project_id()


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


async def validate_access_token(access_token: str) -> TokenInfo:
    """Validate an OAuth 2.0 access token with Google's tokeninfo endpoint.

    This function makes an HTTP request to Google's tokeninfo endpoint to verify
    that the token is valid and retrieve associated metadata.

    Args:
        access_token: The OAuth 2.0 access token to validate.

    Returns:
        TokenInfo with validation results.

    Note:
        This adds latency (~50-100ms) to each request. Consider caching results
        or only validating on session creation.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
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
