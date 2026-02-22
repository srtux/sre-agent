"""MCP (Model Context Protocol) integration for GCP services.

This module provides lazy-loaded MCP toolsets for GCP observability services:
- BigQuery: SQL-based data analysis
- Cloud Logging: Log queries and analysis
- Cloud Monitoring: Metrics and time series queries

MCP toolsets are created lazily in async context to avoid session lifecycle issues.
Creating at module import time causes "Attempted to exit cancel scope in a
different task" errors because anyio cancel scopes cannot cross task boundaries.
"""

import asyncio
import contextvars
import logging
import os
import sys
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import httpx
from google.adk.tools.api_registry import ApiRegistry

from ...auth import (
    get_credentials_from_tool_context,
    get_current_credentials,
)
from ...schema import BaseToolResponse, ToolStatus
from ..common import adk_tool
from ..common.debug import log_auth_state, log_mcp_auth_state
from ..config import get_tool_config_manager
from .mock_mcp import MockMcpToolset

# Compatibility for ExceptionGroup/BaseExceptionGroup in Python < 3.11
_BaseExceptionGroup: Any
_ExceptionGroup: Any

if sys.version_info >= (3, 11):
    _BaseExceptionGroup = BaseExceptionGroup  # type: ignore # noqa: F821
    _ExceptionGroup = ExceptionGroup  # type: ignore # noqa: F821
else:
    try:
        from anyio import (
            BaseExceptionGroup as _AnyioBaseExceptionGroup,
        )
        from anyio import (
            ExceptionGroup as _AnyioExceptionGroup,
        )

        _BaseExceptionGroup = _AnyioBaseExceptionGroup
        _ExceptionGroup = _AnyioExceptionGroup
    except ImportError:
        # Fallback if anyio not available
        class _FallbackExceptionGroup(Exception):
            pass

        _BaseExceptionGroup = _FallbackExceptionGroup
        _ExceptionGroup = _FallbackExceptionGroup

logger = logging.getLogger(__name__)

# Context variable for tool context during MCP calls
# This allows the header provider to access tool_context for session state
_mcp_tool_context: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "mcp_tool_context", default=None
)


def set_mcp_tool_context(tool_context: Any) -> None:
    """Set the tool context for MCP header provider to access session state."""
    _mcp_tool_context.set(tool_context)


def clear_mcp_tool_context() -> None:
    """Clear the tool context after MCP call."""
    _mcp_tool_context.set(None)


def _create_header_provider(project_id: str) -> Callable[[Any], dict[str, str]]:
    """Creates a header provider that injects the user token if available.

    The provider checks multiple sources for credentials:
    1. ContextVar (for local execution via middleware)
    2. Session state (for Agent Engine execution via session state propagation)
    """

    def header_provider(_: Any) -> dict[str, str]:
        headers = {"x-goog-user-project": project_id}

        # Use unified credential resolution (ContextVar + Session State + Decryption)
        ctx = _mcp_tool_context.get()
        user_creds = get_credentials_from_tool_context(ctx)

        if user_creds and hasattr(user_creds, "token") and user_creds.token:
            logger.debug("MCP: Using resolved user/session credentials")
            headers["Authorization"] = f"Bearer {user_creds.token}"
            return headers

        # Fallback for Local Development / Service Account mode
        # If no user credentials, try to get a token from ADC
        try:
            logger.debug(
                "MCP: No user credentials found, attempting ADC fallback for token"
            )
            adc_creds, _ = get_current_credentials()
            if not adc_creds.token:
                # Force a refresh to get the token
                import google.auth.transport.requests

                cast(Any, adc_creds).refresh(google.auth.transport.requests.Request())

            if adc_creds.token:
                logger.debug("MCP: Using token from Application Default Credentials")
                headers["Authorization"] = f"Bearer {adc_creds.token}"
        except Exception as e:
            logger.debug(f"MCP: Failed to resolve ADC token: {e}")

        return headers

    return header_provider


def get_project_id_with_fallback() -> str | None:
    """Get project ID from environment or default credentials.

    Checks in the following order:
    1. Tool context / Session state (if available)
    2. Default credentials
    3. Environment variables
    """
    # 1. Check Tool Context (if set via set_mcp_tool_context)
    ctx = _mcp_tool_context.get()
    if ctx is not None:
        try:
            from ...auth import get_project_id_from_tool_context

            project_id = get_project_id_from_tool_context(ctx)
            if project_id:
                logger.debug(f"Resolved project ID from tool context: {project_id}")
                return project_id
        except Exception as e:
            logger.debug(f"Error resolving project ID from tool context: {e}")

    # 2. Existing logic (Default credentials / Environment)
    project_id = None
    try:
        _, project_id = get_current_credentials()
        project_id = (
            project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCP_PROJECT_ID")
        )
    except Exception:
        pass
    return project_id


def create_bigquery_mcp_toolset(project_id: str | None = None) -> Any:
    """Creates a new instance of the BigQuery MCP toolset.

    NOTE: This function should be called in an async context (within an async
    function) to ensure proper MCP session lifecycle management.

    Tools exposed:
        - list_dataset_ids: List available datasets
        - list_table_ids: List tables in a dataset
        - get_table_info: Get table schema and metadata

    Environment variable override:
        BIGQUERY_MCP_SERVER: Override the default MCP server

    Args:
        project_id: GCP project ID. If not provided, uses default credentials.

    Returns:
        MCP toolset or None if unavailable.
    """
    if not project_id:
        project_id = get_project_id_with_fallback()

    if not project_id:
        logger.warning(
            "No Project ID detected; BigQuery MCP toolset will not be available"
        )
        return None

    # Check for test environment or evaluation mode
    is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
    if (
        os.environ.get("USE_MOCK_MCP") == "true"
        or os.environ.get("ADK_ENV") == "test"
        or is_eval
    ):
        logger.info(
            f"Using Mock BigQuery MCP toolset (Env: {'eval' if is_eval else 'test'})"
        )
        return MockMcpToolset()

    logger.info(f"Creating BigQuery MCP toolset for project: {project_id}")

    default_server = "google-bigquery.googleapis.com-mcp"
    mcp_server = os.environ.get("BIGQUERY_MCP_SERVER", default_server)
    mcp_server_name = f"projects/{project_id}/locations/global/mcpServers/{mcp_server}"

    api_registry = ApiRegistry(
        project_id, header_provider=_create_header_provider(project_id)
    )

    # Dynamic Tool Filtering: Filter MCP tools based on configuration
    manager = get_tool_config_manager()
    default_tools = [
        "list_dataset_ids",
        "list_table_ids",
        "get_table_info",
    ]
    # Check both raw name and ADK wrapper name (prefixed with mcp_)
    applied_filter = [
        t
        for t in default_tools
        if manager.is_enabled(t) or manager.is_enabled(f"mcp_{t}")
    ]

    mcp_toolset = api_registry.get_toolset(
        mcp_server_name=mcp_server_name,
        tool_filter=applied_filter,
    )

    return mcp_toolset


def create_logging_mcp_toolset(project_id: str | None = None) -> Any:
    """Creates a Cloud Logging MCP toolset with generic logging capabilities.

    Tools exposed:
        - list_log_entries: Search and retrieve log entries

    Environment variable override:
        LOGGING_MCP_SERVER: Override the default MCP server

    Args:
        project_id: GCP project ID. If not provided, uses default credentials.

    Returns:
        MCP toolset or None if unavailable.
    """
    if not project_id:
        project_id = get_project_id_with_fallback()

    if not project_id:
        logger.warning(
            "No Project ID detected; Cloud Logging MCP toolset will not be available"
        )
        return None

    # Check for test environment or evaluation mode
    is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
    if (
        os.environ.get("USE_MOCK_MCP") == "true"
        or os.environ.get("ADK_ENV") == "test"
        or is_eval
    ):
        logger.info(
            f"Using Mock Cloud Logging MCP toolset (Env: {'eval' if is_eval else 'test'})"
        )
        return MockMcpToolset()

    logger.info(f"Creating Cloud Logging MCP toolset for project: {project_id}")

    default_server = "google-logging.googleapis.com-mcp"
    mcp_server = os.environ.get("LOGGING_MCP_SERVER", default_server)
    mcp_server_name = f"projects/{project_id}/locations/global/mcpServers/{mcp_server}"

    api_registry = ApiRegistry(
        project_id, header_provider=_create_header_provider(project_id)
    )

    # Dynamic Tool Filtering: Filter MCP tools based on configuration
    manager = get_tool_config_manager()
    default_tools = ["list_log_entries"]
    applied_filter = [
        t
        for t in default_tools
        if manager.is_enabled(t) or manager.is_enabled(f"mcp_{t}")
    ]

    mcp_toolset = api_registry.get_toolset(
        mcp_server_name=mcp_server_name,
        tool_filter=applied_filter,
    )

    return mcp_toolset


def create_monitoring_mcp_toolset(project_id: str | None = None) -> Any:
    """Creates a Cloud Monitoring MCP toolset with generic metrics capabilities.

    Tools exposed:
        - list_timeseries: Query time series metrics data
        - query_range: Evaluate PromQL queries over a time range

    Environment variable override:
        MONITORING_MCP_SERVER: Override the default MCP server

    Args:
        project_id: GCP project ID. If not provided, uses default credentials.

    Returns:
        MCP toolset or None if unavailable.
    """
    if not project_id:
        project_id = get_project_id_with_fallback()

    if not project_id:
        logger.warning(
            "No Project ID detected; Cloud Monitoring MCP toolset will not be available"
        )
        return None

    # Check for test environment or evaluation mode
    is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
    if (
        os.environ.get("USE_MOCK_MCP") == "true"
        or os.environ.get("ADK_ENV") == "test"
        or is_eval
    ):
        logger.info(
            f"Using Mock Cloud Monitoring MCP toolset (Env: {'eval' if is_eval else 'test'})"
        )
        return MockMcpToolset()

    logger.info(f"Creating Cloud Monitoring MCP toolset for project: {project_id}")

    default_server = "google-monitoring.googleapis.com-mcp"
    mcp_server = os.environ.get("MONITORING_MCP_SERVER", default_server)
    mcp_server_name = f"projects/{project_id}/locations/global/mcpServers/{mcp_server}"

    api_registry = ApiRegistry(
        project_id, header_provider=_create_header_provider(project_id)
    )

    # Dynamic Tool Filtering: Filter MCP tools based on configuration
    manager = get_tool_config_manager()
    default_tools = ["list_timeseries", "query_range"]
    applied_filter = [
        t
        for t in default_tools
        if manager.is_enabled(t) or manager.is_enabled(f"mcp_{t}")
    ]

    mcp_toolset = api_registry.get_toolset(
        mcp_server_name=mcp_server_name,
        tool_filter=applied_filter,
    )

    return mcp_toolset


async def call_mcp_tool_with_retry(
    create_toolset_fn: Callable[[str | None], Any],
    tool_name: str,
    args: dict[str, Any],
    tool_context: Any | None,
    project_id: str | None = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> dict[str, Any]:
    """Generic helper to call an MCP tool with retry logic for session errors.

    Args:
        create_toolset_fn: Function to create the MCP toolset.
        tool_name: Name of the MCP tool to call.
        args: Arguments to pass to the tool.
        tool_context: ADK tool context.
        project_id: Optional project ID override.
        max_retries: Max retry attempts for session errors.
        base_delay: Base delay for exponential backoff.

    Returns:
        Tool result or error dict.
    """
    # Set tool context for header provider to access session state
    # This enables EIC (End User Identity Credential) propagation in Agent Engine
    set_mcp_tool_context(tool_context)

    if not project_id:
        project_id = get_project_id_with_fallback()

    if not project_id:
        return {
            "status": ToolStatus.ERROR,
            "error": (
                "No project ID available. HINT: If you are using the Agent Engine playground, "
                "please ensure you have selected a project or passed the project ID in your request "
                "(e.g., 'Analyze logs in project my-project-id'). Local users should set the "
                "GOOGLE_CLOUD_PROJECT environment variable."
            ),
        }

    # DEBUG: Log auth state and MCP headers before making the call
    log_auth_state(tool_context, f"mcp_call_{tool_name}")
    log_mcp_auth_state(project_id, tool_context, f"mcp_call_{tool_name}")

    for attempt in range(max_retries):
        mcp_toolset = None
        try:
            logger.debug(
                f"DEBUG: Calling create_toolset_fn for {tool_name} (project_id={project_id})"
            )
            # Create toolset directly in the current event loop. It only does HTTP
            # calls or builds objects, so it doesn't need to be offloaded.
            try:
                mcp_toolset = create_toolset_fn(project_id)
            except ValueError as e:
                # Catch "MCP server ... not found" error from api_registry.get_toolset
                logger.error(f"MCP server configuration error for {tool_name}: {e}")
                clear_mcp_tool_context()
                return {
                    "status": ToolStatus.ERROR,
                    "error": (
                        f"MCP server unavailable for '{tool_name}'. verify the MCP server configuration. "
                        "Use direct API alternatives instead: list_log_entries for logs, fetch_trace for traces, "
                        "query_promql for metrics."
                    ),
                    "non_retryable": True,
                    "error_type": "MCP_CONFIG_ERROR",
                }
            except asyncio.TimeoutError:
                logger.error(f"Timeout creating MCP toolset for {tool_name}")
                clear_mcp_tool_context()
                return {
                    "status": ToolStatus.ERROR,
                    "error": (
                        f"Failed to create MCP toolset for '{tool_name}': Connection timed out after 60 seconds. "
                        "The MCP server may be unavailable or overloaded. DO NOT retry this tool. "
                        "Use direct API alternatives instead: list_log_entries for logs, fetch_trace for traces, "
                        "query_promql for metrics."
                    ),
                    "non_retryable": True,
                    "error_type": "MCP_CONNECTION_TIMEOUT",
                }

            logger.debug(f"DEBUG: create_toolset_fn returned for {tool_name}")

            if not mcp_toolset:
                clear_mcp_tool_context()
                return {
                    "status": ToolStatus.ERROR,
                    "error": (
                        f"MCP toolset unavailable for '{tool_name}'. The MCP server could not be initialized. "
                        "This is typically a configuration or authentication issue. DO NOT retry this tool. "
                        "Use direct API alternatives instead: list_log_entries for logs, fetch_trace for traces, "
                        "query_promql or list_time_series for metrics."
                    ),
                    "non_retryable": True,
                    "error_type": "MCP_UNAVAILABLE",
                }

            tools = await mcp_toolset.get_tools()

            for tool in tools:
                if tool.name == tool_name:
                    # Enforce timeout on tool execution
                    try:
                        logger.info(
                            f"🔗 MCP Call: '{tool_name}' (Project: {project_id}) | Args: {args}"
                        )
                        result = await asyncio.wait_for(
                            tool.run_async(args=args, tool_context=tool_context),
                            timeout=180.0,  # 180s timeout for tool execution
                        )
                        logger.info(f"✨ MCP Success: '{tool_name}'")
                        clear_mcp_tool_context()
                        return {
                            "status": ToolStatus.SUCCESS,
                            "result": result,
                            "metadata": {"source": "mcp"},
                        }
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout executing MCP tool {tool_name}")
                        clear_mcp_tool_context()
                        return {
                            "status": ToolStatus.ERROR,
                            "error": (
                                f"Tool '{tool_name}' timed out after 180 seconds. This is typically caused by "
                                "slow network conditions or high server load. DO NOT retry immediately. "
                                "Consider using direct API alternatives (list_log_entries, fetch_trace, query_promql) "
                                "which may be more reliable, or wait and try again later."
                            ),
                            "non_retryable": True,
                            "error_type": "TIMEOUT",
                        }

            clear_mcp_tool_context()
            return {
                "status": ToolStatus.ERROR,
                "error": (
                    f"Tool '{tool_name}' not found in MCP toolset. This is a configuration error - "
                    "the tool may not be available in the current MCP server. DO NOT retry. "
                    "Use direct API alternatives instead."
                ),
                "non_retryable": True,
                "error_type": "TOOL_NOT_FOUND",
            }

        except asyncio.CancelledError:
            logger.warning(f"MCP Tool execution cancelled: {tool_name}")
            clear_mcp_tool_context()
            return {
                "status": ToolStatus.ERROR,
                "error": (
                    f"Tool '{tool_name}' execution was cancelled by the system. "
                    "DO NOT retry this operation immediately. "
                    "Use an alternative approach or smaller data scope if this was due to a timeout."
                ),
                "non_retryable": True,
                "error_type": "SYSTEM_CANCELLATION",
            }

        except (httpx.HTTPStatusError, Exception) as e:
            # Unwrap ExceptionGroup from AnyIO TaskGroup (e.g., from streamable_http_client)
            actual_error = e
            if isinstance(e, _BaseExceptionGroup) and hasattr(e, "exceptions"):
                for sub_err in e.exceptions:
                    if isinstance(
                        sub_err, httpx.HTTPStatusError
                    ) or "Session terminated" in str(sub_err):
                        actual_error = sub_err
                        break

            logger.error(
                f"MCP Tool execution failed: {tool_name} error={actual_error!s}",
                exc_info=True,
            )

            error_str = str(actual_error)
            is_session_error = "Session terminated" in error_str or (
                "session" in error_str.lower() and "error" in error_str.lower()
            )

            if is_session_error and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"MCP session error during {tool_name} attempt {attempt + 1}/{max_retries}: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            elif is_session_error and attempt >= max_retries - 1:
                # Session errors exhausted all retries - mark as non-retryable
                logger.error(
                    f"{tool_name} failed after {max_retries} attempts due to session errors: {e}"
                )
                clear_mcp_tool_context()
                return {
                    "status": ToolStatus.ERROR,
                    "error": (
                        f"Tool '{tool_name}' failed after {max_retries} retry attempts due to persistent session errors. "
                        "The MCP connection is unstable. DO NOT retry this tool. "
                        "Switch to direct API alternatives: list_log_entries, fetch_trace, query_promql, list_time_series."
                    ),
                    "non_retryable": True,
                    "error_type": "MAX_RETRIES_EXHAUSTED",
                }
            else:
                # Non-session error - determine if retryable based on error content
                error_str_lower = str(e).lower()
                is_auth_error = any(
                    kw in error_str_lower
                    for kw in ["permission", "unauthorized", "forbidden", "403", "401"]
                )
                is_not_found = any(
                    kw in error_str_lower
                    for kw in ["not found", "404", "does not exist"]
                )
                is_non_retryable = is_auth_error or is_not_found

                clear_mcp_tool_context()
                return {
                    "status": ToolStatus.ERROR,
                    "error": (
                        f"Tool '{tool_name}' execution failed: {e!s}. "
                        + (
                            "This appears to be a permission or resource issue - DO NOT retry. "
                            "Check authentication and resource availability."
                            if is_non_retryable
                            else "This may be a transient error. If the issue persists after one retry, "
                            "try using direct API alternatives instead."
                        )
                    ),
                    "non_retryable": is_non_retryable,
                    "error_type": "AUTH_ERROR"
                    if is_auth_error
                    else "NOT_FOUND"
                    if is_not_found
                    else "EXECUTION_ERROR",
                }
        finally:
            if mcp_toolset and hasattr(mcp_toolset, "close"):
                try:
                    await mcp_toolset.close()
                except asyncio.CancelledError:
                    # Ignore cancellation errors during cleanup to ensure result is returned
                    logger.debug(
                        "MCP toolset close interrupted by cancellation (ignored)"
                    )
                except RuntimeError as e:
                    # Ignore "Attempted to exit cancel scope..." errors from anyio/mcp cleanup
                    # These occur due to task scoping issues in the underlying library during forced cleanup
                    logger.debug(f"RuntimeError during MCP cleanup (ignored): {e}")
                except Exception as e:
                    logger.warning(f"Error closing MCP toolset: {e}")

    # Clear tool context on function exit (all retry attempts exhausted)
    clear_mcp_tool_context()

    return {
        "status": ToolStatus.ERROR,
        "error": (
            f"Tool '{tool_name}' failed after {max_retries} retry attempts due to persistent session errors. "
            "The MCP connection is unstable. DO NOT retry this tool. "
            "Switch to direct API alternatives: list_log_entries, fetch_trace, query_promql, list_time_series."
        ),
        "non_retryable": True,
        "error_type": "MAX_RETRIES_EXHAUSTED",
    }


# =============================================================================
# Generic GCP MCP Tools
# =============================================================================


@adk_tool
async def mcp_list_log_entries(
    filter: str,
    project_id: str | None = None,
    page_size: int = 100,
    order_by: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Search and retrieve log entries from Google Cloud Logging via MCP.

    This is the primary tool for querying Cloud Logging. Use it for debugging
    application behavior, finding specific error messages, auditing events,
    or any log analysis task.

    Args:
        filter: Cloud Logging filter expression. Powerful syntax for selecting logs
            by severity, resource type, text content, labels, and more.
        project_id: GCP project ID. If not provided, uses default credentials.
        page_size: Maximum number of log entries to return (default 100).
        order_by: Optional field to sort by (e.g., "timestamp desc").
        tool_context: ADK tool context (required).

    Returns:
        Log entries matching the filter criteria.

    Example filters:
        - 'severity>=ERROR' - All errors and above
        - 'resource.type="k8s_container"' - Kubernetes container logs
        - 'resource.type="gce_instance"' - Compute Engine logs
        - 'textPayload:"OutOfMemory"' - Logs containing specific text
        - 'jsonPayload.level="error"' - Structured logs by field
        - 'trace="projects/PROJECT/traces/TRACE_ID"' - Logs for a trace
        - 'timestamp>="2024-01-01T00:00:00Z"' - Time-bounded queries
        - 'labels.env="production" AND severity>=WARNING' - Combined filters
    """
    args = {
        "filter": filter,
        "page_size": page_size,
    }
    if order_by:
        args["order_by"] = order_by

    # Add resource_names if project_id is available
    pid = project_id or get_project_id_with_fallback()
    if pid:
        args["resource_names"] = [f"projects/{pid}"]

    res = await call_mcp_tool_with_retry(
        create_logging_mcp_toolset,
        "list_log_entries",
        args,
        tool_context,
        project_id=project_id,
    )
    return BaseToolResponse(
        status=res.get("status", ToolStatus.SUCCESS),
        result=res.get("result"),
        error=res.get("error"),
    )


@adk_tool
async def mcp_list_timeseries(
    filter: str,
    project_id: str | None = None,
    interval_start_time: str | None = None,
    interval_end_time: str | None = None,
    minutes_ago: int = 60,
    aggregation_json: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Query time series metrics data from Google Cloud Monitoring via MCP.

    Use this tool to retrieve metric values over time for monitoring, alerting,
    capacity planning, performance analysis, or any metrics-based task.

    Args:
        filter: Monitoring filter string for selecting metrics and resources.
        project_id: GCP project ID. If not provided, uses default credentials.
        interval_start_time: Start of time interval (ISO format). If not provided,
            calculated from minutes_ago.
        interval_end_time: End of time interval (ISO format). If not provided,
            uses current time.
        minutes_ago: Minutes back from now for start time (default 60). Only used
            if interval_start_time is not provided.
        aggregation_json: Optional aggregation settings as JSON string (e.g., '{"alignmentPeriod": "60s", ...}').
        tool_context: ADK tool context (required).

    Returns:
        Time series data with metric values, labels, and timestamps.

    Example filters:
        - 'metric.type="compute.googleapis.com/instance/cpu/utilization"' - CPU usage
        - 'metric.type="loadbalancing.googleapis.com/https/request_count"' - LB requests
        - 'metric.type="cloudsql.googleapis.com/database/cpu/utilization"' - Cloud SQL CPU
        - 'resource.labels.instance_id="12345"' - Filter by instance
        - 'metric.labels.response_code="500"' - Filter by metric label
    """
    import json

    pid = project_id or get_project_id_with_fallback()

    # Build time interval
    if interval_end_time:
        end_str = interval_end_time
    else:
        end_str = datetime.now(timezone.utc).isoformat()

    if interval_start_time:
        start_str = interval_start_time
    else:
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        start_dt = end_dt - timedelta(minutes=minutes_ago)
        start_str = start_dt.isoformat()

    args = {
        "name": f"projects/{pid}" if pid else "",
        "filter": filter,
        "interval": {
            "end_time": end_str,
            "start_time": start_str,
        },
    }

    if aggregation_json:
        if isinstance(aggregation_json, dict):
            args["aggregation"] = aggregation_json
        elif isinstance(aggregation_json, str):
            try:
                args["aggregation"] = json.loads(aggregation_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse aggregation_json: {e}")
                pass

    res = await call_mcp_tool_with_retry(
        create_monitoring_mcp_toolset,
        "list_timeseries",
        args,
        tool_context,
        project_id=project_id,
    )
    return BaseToolResponse(
        status=res.get("status", ToolStatus.SUCCESS),
        result=res.get("result"),
        error=res.get("error"),
    )


@adk_tool
async def mcp_query_range(
    query: str,
    project_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    minutes_ago: int = 60,
    step: str = "60s",
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Evaluate a PromQL query over a time range via Cloud Monitoring MCP.

    Use this for complex metric aggregations, calculations, and analysis using
    PromQL syntax. Ideal for rate calculations, histogram analysis, and
    multi-metric correlations.

    Args:
        query: PromQL query expression.
        project_id: GCP project ID. If not provided, uses default credentials.
        start_time: Start of query range (ISO format or RFC3339).
        end_time: End of query range (ISO format or RFC3339).
        minutes_ago: Minutes back from now for start time (default 60).
        step: Query resolution step (default "60s").
        tool_context: ADK tool context (required).

    Returns:
        Query results with time series data.

    Example queries:
        - 'rate(http_requests_total[5m])' - Request rate over 5 minutes
        - 'sum by (status_code)(http_requests_total)' - Requests grouped by status
        - 'histogram_quantile(0.95, http_request_duration_bucket)' - P95 latency
        - 'increase(errors_total[1h])' - Error count increase over 1 hour
    """
    import time as time_module

    # Build time range
    if end_time:
        end_str = end_time
    else:
        end_str = datetime.now(timezone.utc).isoformat()

    if start_time:
        start_str = start_time
    else:
        start_ts = time_module.time() - (minutes_ago * 60)
        start_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()

    args = {
        "query": query,
        "start": start_str,
        "end": end_str,
        "step": step,
    }

    res = await call_mcp_tool_with_retry(
        create_monitoring_mcp_toolset,
        "query_range",
        args,
        tool_context,
        project_id=project_id,
    )
    return BaseToolResponse(
        status=res.get("status", ToolStatus.SUCCESS),
        result=res.get("result"),
        error=res.get("error"),
    )


@adk_tool
async def gcp_execute_sql(
    sql_query: str,
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Execute a SQL query against BigQuery directly.

    Use this tool to run analytical queries against trace and log data
    exported to BigQuery. This is essential for Stage 0 (Aggregate Analysis).

    Args:
        sql_query: The SQL query to execute.
        project_id: GCP project ID. If not provided, uses default credentials.
        tool_context: ADK tool context (required).

    Returns:
        Query results or error.
    """
    try:
        from sre_agent.tools.bigquery.client import BigQueryClient

        client = BigQueryClient(project_id=project_id, tool_context=tool_context)
        rows = await client.execute_query(sql_query)
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=rows,
        )
    except Exception as e:
        logger.exception("Failed to execute SQL query")
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=str(e),
        )


@adk_tool
async def mcp_list_dataset_ids(
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """List available BigQuery datasets via MCP.

    Use this to explore available data sources for analytical queries.

    Args:
        project_id: GCP project ID. If not provided, uses default credentials.
        tool_context: ADK tool context (required).

    Returns:
        List of dataset IDs.
    """
    pid = project_id or get_project_id_with_fallback()
    args = {"projectId": pid}

    res = await call_mcp_tool_with_retry(
        create_bigquery_mcp_toolset,
        "list_dataset_ids",
        args,
        tool_context,
        project_id=project_id,
    )
    return BaseToolResponse(
        status=res.get("status", ToolStatus.SUCCESS),
        result=res.get("result"),
        error=res.get("error"),
    )


@adk_tool
async def mcp_list_table_ids(
    dataset_id: str,
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """List tables in a specific BigQuery dataset via MCP.

    Args:
        dataset_id: The ID of the dataset to list tables from.
        project_id: GCP project ID. If not provided, uses default credentials.
        tool_context: ADK tool context (required).

    Returns:
        List of table IDs.
    """
    pid = project_id or get_project_id_with_fallback()
    args = {"datasetId": dataset_id, "projectId": pid}

    res = await call_mcp_tool_with_retry(
        create_bigquery_mcp_toolset,
        "list_table_ids",
        args,
        tool_context,
        project_id=project_id,
    )
    return BaseToolResponse(
        status=res.get("status", ToolStatus.SUCCESS),
        result=res.get("result"),
        error=res.get("error"),
    )


@adk_tool
async def mcp_get_table_info(
    dataset_id: str,
    table_id: str,
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Get BigQuery table schema and metadata via MCP.

    Args:
        dataset_id: The ID of the dataset.
        table_id: The ID of the table.
        project_id: GCP project ID. If not provided, uses default credentials.
        tool_context: ADK tool context (required).

    Returns:
        Table information including schema.
    """
    pid = project_id or get_project_id_with_fallback()
    args = {
        "datasetId": dataset_id,
        "tableId": table_id,
        "projectId": pid,
    }

    res = await call_mcp_tool_with_retry(
        create_bigquery_mcp_toolset,
        "get_table_info",
        args,
        tool_context,
        project_id=project_id,
    )
    return BaseToolResponse(
        status=res.get("status", ToolStatus.SUCCESS),
        result=res.get("result"),
        error=res.get("error"),
    )
