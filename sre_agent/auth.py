"""Authentication utilities for propagating user credentials.

This module provides utilities for managing user credentials across different
execution contexts:

1. **ContextVar-based**: For local execution where Cloud Run middleware sets
   credentials in context variables that tools can access.

2. **Session State-based**: For remote Agent Engine execution where credentials
   are passed via session state (since ContextVars don't cross process boundaries).

The credential resolution order is:
1. ContextVar (set by middleware in local mode)
2. Session state (for Agent Engine remote execution)
3. Default credentials (service account fallback)
"""

import contextvars
import logging
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
    return google.auth.default()


def get_current_credentials_or_none() -> Credentials | None:
    """Gets the explicitly set credentials or None."""
    return _credentials_context.get()


def get_current_project_id() -> str | None:
    """Gets the project ID for the current context."""
    return _project_id_context.get()


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
            session_state = getattr(
                getattr(tool_context, "invocation_context", None),
                "session",
                None,
            )
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

    Args:
        tool_context: The ADK ToolContext (can be None for standalone tool calls)

    Returns:
        Project ID if found, None otherwise.
    """
    # First, check ContextVar
    project_id = get_current_project_id()
    if project_id:
        return project_id

    # Second, check session state
    if tool_context is not None:
        try:
            session_state = getattr(
                getattr(tool_context, "invocation_context", None),
                "session",
                None,
            )
            if session_state is not None:
                state_dict = getattr(session_state, "state", None)
                project_id = get_project_id_from_session(state_dict)
                if project_id:
                    return project_id
        except Exception as e:
            logger.debug(f"Error getting project_id from tool_context: {e}")

    return None
