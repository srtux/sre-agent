"""Lazy initialization for GCP service clients to optimize resource usage.

This module provides factory functions for GCP service clients that support
End User Identity Credentials (EIC) propagation:

1. ContextVar-based credentials (set by middleware for local execution)
2. Session state credentials (for Agent Engine execution)

The credential resolution order is:
1. Explicit tool_context (if provided via get_*_client_with_context)
2. ContextVar (set by middleware)
3. Default credentials (service account)
"""

import logging
import threading
from typing import TYPE_CHECKING, Any, TypeVar, cast

from google.cloud import monitoring_v3, trace_v1
from google.cloud.logging_v2.services.logging_service_v2 import LoggingServiceV2Client

from ...auth import get_credentials_from_tool_context, get_current_credentials_or_none

if TYPE_CHECKING:
    from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

T = TypeVar("T")

_clients: dict[str, Any] = {}
_lock = threading.Lock()


def _get_client(
    name: str,
    client_class: type[T],
    tool_context: "ToolContext | None" = None,
) -> T:
    """Helper for thread-safe lazy initialization of clients.

    Supports End User Identity Credential (EIC) propagation by checking
    both ContextVar and session state for user credentials.

    Args:
        name: Unique name/key for the client instance.
        client_class: The client class to instantiate.
        tool_context: Optional ADK ToolContext for session-based credentials.

    Returns:
        The initialized client instance.
    """
    if name not in _clients:
        with _lock:
            if name not in _clients:
                _clients[name] = client_class()

    # First, check for user credentials from tool_context (session state)
    # This is the EIC path for Agent Engine execution
    if tool_context is not None:
        user_creds = get_credentials_from_tool_context(tool_context)
        if user_creds:
            logger.debug(f"Using user credentials from tool_context for {name} client")
            return client_class(credentials=user_creds)  # type: ignore[call-arg]

    # Second, check for user-specific credentials from ContextVar (local execution)
    user_creds = get_current_credentials_or_none()
    if user_creds:
        logger.debug(f"Using user credentials from ContextVar for {name} client")
        # Create a new client with these credentials
        # We don't cache these in the global cache to avoid mixing user sessions.
        return client_class(credentials=user_creds)  # type: ignore[call-arg]

    return cast(T, _clients[name])


def get_trace_client(
    tool_context: "ToolContext | None" = None,
) -> trace_v1.TraceServiceClient:
    """Returns a Cloud Trace client, using user credentials if available.

    Args:
        tool_context: Optional ADK ToolContext for session-based credentials.
    """
    return _get_client("trace", trace_v1.TraceServiceClient, tool_context)


def get_logging_client(
    tool_context: "ToolContext | None" = None,
) -> LoggingServiceV2Client:
    """Returns a Cloud Logging client, using user credentials if available.

    Args:
        tool_context: Optional ADK ToolContext for session-based credentials.
    """
    return _get_client("logging", LoggingServiceV2Client, tool_context)


def get_monitoring_client(
    tool_context: "ToolContext | None" = None,
) -> monitoring_v3.MetricServiceClient:
    """Returns a Cloud Monitoring client, using user credentials if available.

    Args:
        tool_context: Optional ADK ToolContext for session-based credentials.
    """
    return _get_client("monitoring", monitoring_v3.MetricServiceClient, tool_context)


def get_alert_policy_client(
    tool_context: "ToolContext | None" = None,
) -> monitoring_v3.AlertPolicyServiceClient:
    """Returns a Cloud Monitoring Alert Policy client, using user credentials if available.

    Args:
        tool_context: Optional ADK ToolContext for session-based credentials.
    """
    return _get_client(
        "alert_policies", monitoring_v3.AlertPolicyServiceClient, tool_context
    )
