"""Debug utilities for diagnosing telemetry and authentication issues.

This module provides comprehensive debugging for:
1. OpenTelemetry trace context propagation
2. Credential flow (ContextVar, Session State, Default)
3. MCP header injection
4. Agent Engine communication

Usage:
    from sre_agent.tools.common.debug import (
        log_telemetry_state,
        log_auth_state,
        log_mcp_auth_state,
    )

    # Call at strategic points to understand system state
    log_telemetry_state("before_agent_call")
    log_auth_state(tool_context, "in_tool_execution")
"""

import logging
import os
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.propagate import get_global_textmap
from opentelemetry.trace import SpanContext, get_current_span

if TYPE_CHECKING:
    from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# Debug flag - set via environment variable
DEBUG_TELEMETRY = os.environ.get("DEBUG_TELEMETRY", "false").lower() == "true"
DEBUG_AUTH = os.environ.get("DEBUG_AUTH", "false").lower() == "true"


def _format_span_context(span_context: SpanContext | None) -> dict[str, Any]:
    """Format span context for logging."""
    if span_context is None or not span_context.is_valid:
        return {"valid": False, "trace_id": None, "span_id": None}

    return {
        "valid": True,
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
        "trace_flags": span_context.trace_flags,
        "is_remote": span_context.is_remote,
    }


def log_telemetry_state(context_label: str = "unknown") -> dict[str, Any]:
    """Log comprehensive telemetry state for debugging.

    Args:
        context_label: A label describing where this is being called from

    Returns:
        Dictionary containing telemetry state information
    """
    state: dict[str, Any] = {
        "context_label": context_label,
        "environment": {},
        "tracer_provider": {},
        "current_span": {},
        "propagation": {},
    }

    # 1. Environment variables
    env_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
        "OTEL_TRACES_EXPORTER",
        "OTEL_METRICS_EXPORTER",
        "DISABLE_TELEMETRY",
        "LOG_LEVEL",
        "SRE_AGENT_ID",
    ]
    for var in env_vars:
        value = os.environ.get(var)
        state["environment"][var] = value if value else "(not set)"

    # 2. Tracer Provider state
    try:
        tracer_provider = trace.get_tracer_provider()
        provider_type = type(tracer_provider).__name__
        state["tracer_provider"]["type"] = provider_type
        state["tracer_provider"]["is_proxy"] = "ProxyTracerProvider" in provider_type

        # Check if it has span processors (SDK TracerProvider)
        if hasattr(tracer_provider, "_active_span_processor"):
            processor = tracer_provider._active_span_processor
            state["tracer_provider"]["has_span_processor"] = processor is not None
            if processor and hasattr(processor, "_span_processors"):
                state["tracer_provider"]["processor_count"] = len(
                    processor._span_processors
                )
        else:
            state["tracer_provider"]["has_span_processor"] = "unknown"

    except Exception as e:
        state["tracer_provider"]["error"] = str(e)

    # 3. Current span state
    try:
        current_span = get_current_span()
        state["current_span"]["recording"] = current_span.is_recording()

        span_context = current_span.get_span_context()
        state["current_span"]["context"] = _format_span_context(span_context)

        # Get span name if available
        if hasattr(current_span, "name"):
            state["current_span"]["name"] = current_span.name
        elif hasattr(current_span, "_name"):
            state["current_span"]["name"] = current_span._name

    except Exception as e:
        state["current_span"]["error"] = str(e)

    # 4. Propagation context (for distributed tracing)
    try:
        carrier: dict[str, str] = {}
        propagator = get_global_textmap()
        propagator.inject(carrier)
        state["propagation"]["carrier"] = carrier
        state["propagation"]["propagator_type"] = type(propagator).__name__

    except Exception as e:
        state["propagation"]["error"] = str(e)

    # Log the state
    if DEBUG_TELEMETRY or logger.isEnabledFor(logging.DEBUG):
        logger.info(f"🔍 TELEMETRY DEBUG [{context_label}]: {state}")

    return state


def log_auth_state(
    tool_context: "ToolContext | None" = None,
    context_label: str = "unknown",
) -> dict[str, Any]:
    """Log comprehensive authentication state for debugging.

    Args:
        tool_context: ADK ToolContext if available
        context_label: A label describing where this is being called from

    Returns:
        Dictionary containing auth state information
    """
    from ...auth import (
        SESSION_STATE_ACCESS_TOKEN_KEY,
        SESSION_STATE_PROJECT_ID_KEY,
        get_current_credentials_or_none,
        get_current_project_id,
    )

    state: dict[str, Any] = {
        "context_label": context_label,
        "context_var": {},
        "session_state": {},
        "effective": {},
    }

    # 1. ContextVar credentials (set by middleware)
    try:
        creds = get_current_credentials_or_none()
        if creds:
            state["context_var"]["has_credentials"] = True
            state["context_var"]["token_present"] = (
                hasattr(creds, "token") and creds.token is not None
            )
            if hasattr(creds, "token") and creds.token:
                # Log token prefix for debugging (NOT the full token!)
                token = creds.token
                state["context_var"]["token_prefix"] = (
                    token[:20] + "..." if token else None
                )
                state["context_var"]["token_length"] = len(token) if token else 0
        else:
            state["context_var"]["has_credentials"] = False

        project_id = get_current_project_id()
        state["context_var"]["project_id"] = project_id

    except Exception as e:
        state["context_var"]["error"] = str(e)

    # 2. Session state credentials (for Agent Engine)
    try:
        if tool_context is not None:
            session = getattr(
                getattr(tool_context, "invocation_context", None),
                "session",
                None,
            )
            if session is not None:
                session_state = getattr(session, "state", None)
                if session_state:
                    state["session_state"]["has_state"] = True

                    # Check for user token
                    has_token = SESSION_STATE_ACCESS_TOKEN_KEY in session_state
                    state["session_state"]["has_user_token"] = has_token
                    if has_token:
                        token = session_state.get(SESSION_STATE_ACCESS_TOKEN_KEY)
                        if token:
                            state["session_state"]["token_prefix"] = token[:20] + "..."
                            state["session_state"]["token_length"] = len(token)

                    # Check for project ID
                    has_project = SESSION_STATE_PROJECT_ID_KEY in session_state
                    state["session_state"]["has_project_id"] = has_project
                    if has_project:
                        state["session_state"]["project_id"] = session_state.get(
                            SESSION_STATE_PROJECT_ID_KEY
                        )

                    # List all state keys (for debugging)
                    state["session_state"]["all_keys"] = list(session_state.keys())
                else:
                    state["session_state"]["has_state"] = False
            else:
                state["session_state"]["session_available"] = False
        else:
            state["session_state"]["tool_context_available"] = False

    except Exception as e:
        state["session_state"]["error"] = str(e)

    # 3. Effective credentials (what will actually be used)
    try:
        from ...auth import get_credentials_from_tool_context

        effective_creds = get_credentials_from_tool_context(tool_context)
        if effective_creds:
            state["effective"]["source"] = "user_credentials"
            state["effective"]["token_present"] = (
                hasattr(effective_creds, "token") and effective_creds.token is not None
            )
        else:
            state["effective"]["source"] = "default_credentials"
            state["effective"]["note"] = "Will use service account or ADC"

    except Exception as e:
        state["effective"]["error"] = str(e)

    # Log the state
    if DEBUG_AUTH or logger.isEnabledFor(logging.DEBUG):
        logger.info(f"🔑 AUTH DEBUG [{context_label}]: {state}")

    return state


def log_mcp_auth_state(
    project_id: str | None = None,
    tool_context: "ToolContext | None" = None,
    context_label: str = "unknown",
) -> dict[str, Any]:
    """Log MCP-specific authentication state for debugging.

    This is useful for understanding what headers will be sent to MCP servers.

    Args:
        project_id: The project ID being used
        tool_context: ADK ToolContext if available
        context_label: A label describing where this is being called from

    Returns:
        Dictionary containing MCP auth state information
    """
    from ..mcp.gcp import _create_header_provider, _mcp_tool_context

    state: dict[str, Any] = {
        "context_label": context_label,
        "project_id": project_id,
        "mcp_context_var": {},
        "headers": {},
    }

    # 1. Check MCP tool context
    try:
        mcp_ctx = _mcp_tool_context.get()
        state["mcp_context_var"]["is_set"] = mcp_ctx is not None
    except Exception as e:
        state["mcp_context_var"]["error"] = str(e)

    # 2. Generate headers (simulating what would be sent)
    try:
        if project_id:
            header_provider = _create_header_provider(project_id)
            headers = header_provider(None)

            state["headers"]["x-goog-user-project"] = headers.get("x-goog-user-project")

            if "Authorization" in headers:
                auth_header = headers["Authorization"]
                state["headers"]["has_authorization"] = True
                state["headers"]["auth_type"] = (
                    "Bearer" if auth_header.startswith("Bearer ") else "Other"
                )
                # Don't log the actual token
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    state["headers"]["token_prefix"] = token[:20] + "..."
                    state["headers"]["token_length"] = len(token)
            else:
                state["headers"]["has_authorization"] = False
                state["headers"]["note"] = (
                    "No Authorization header - will use default credentials"
                )
        else:
            state["headers"]["note"] = "No project_id provided"

    except Exception as e:
        state["headers"]["error"] = str(e)

    # Log the state
    if DEBUG_AUTH or logger.isEnabledFor(logging.DEBUG):
        logger.info(f"🔗 MCP AUTH DEBUG [{context_label}]: {state}")

    return state


def log_agent_engine_call_state(
    user_message: str,
    session_id: str,
    user_access_token: str | None,
    project_id: str | None,
    context_label: str = "unknown",
) -> dict[str, Any]:
    """Log state before calling Agent Engine for debugging.

    Args:
        user_message: The user's message (will be truncated)
        session_id: The session ID being used
        user_access_token: The user's access token (will show prefix only)
        project_id: The project ID
        context_label: A label describing where this is being called from

    Returns:
        Dictionary containing call state information
    """
    state: dict[str, Any] = {
        "context_label": context_label,
        "message": {},
        "session": {},
        "credentials": {},
        "trace_context": {},
    }

    # 1. Message info (truncated)
    state["message"]["length"] = len(user_message) if user_message else 0
    state["message"]["preview"] = (
        user_message[:100] + "..."
        if user_message and len(user_message) > 100
        else user_message
    )

    # 2. Session info
    state["session"]["id"] = session_id
    state["session"]["project_id"] = project_id

    # 3. Credentials being passed
    if user_access_token:
        state["credentials"]["has_token"] = True
        state["credentials"]["token_prefix"] = user_access_token[:20] + "..."
        state["credentials"]["token_length"] = len(user_access_token)
    else:
        state["credentials"]["has_token"] = False
        state["credentials"]["note"] = (
            "No user token - Agent Engine will use service account"
        )

    # 4. Trace context that could be propagated
    try:
        carrier: dict[str, str] = {}
        propagator = get_global_textmap()
        propagator.inject(carrier)
        state["trace_context"]["w3c_headers"] = carrier
        state["trace_context"]["can_propagate"] = bool(carrier)
    except Exception as e:
        state["trace_context"]["error"] = str(e)

    # Log the state
    if DEBUG_AUTH or DEBUG_TELEMETRY or logger.isEnabledFor(logging.DEBUG):
        logger.info(f"📡 AGENT ENGINE CALL DEBUG [{context_label}]: {state}")

    return state


def enable_debug_mode() -> None:
    """Enable debug mode for telemetry and auth.

    Sets environment variables and updates logging level.
    """
    global DEBUG_TELEMETRY, DEBUG_AUTH
    DEBUG_TELEMETRY = True
    DEBUG_AUTH = True
    os.environ["DEBUG_TELEMETRY"] = "true"
    os.environ["DEBUG_AUTH"] = "true"

    # Also ensure logging is at DEBUG level
    logging.getLogger("sre_agent").setLevel(logging.DEBUG)
    logger.info("🐛 Debug mode enabled for telemetry and auth")


def get_debug_summary() -> dict[str, Any]:
    """Get a summary of debug state for diagnostics endpoint.

    Returns:
        Dictionary containing summary of telemetry and auth configuration
    """
    return {
        "debug_enabled": {
            "telemetry": DEBUG_TELEMETRY,
            "auth": DEBUG_AUTH,
        },
        "telemetry": log_telemetry_state("summary"),
        "auth": log_auth_state(None, "summary"),
    }
