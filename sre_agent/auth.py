import contextvars

import google.auth
from google.oauth2.credentials import Credentials

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
