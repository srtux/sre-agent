"""MCP-to-Direct-API fallback chain for graceful degradation.

When an MCP tool call fails (connection error, timeout, session error),
this module provides a mechanism to transparently fall back to the
equivalent direct API tool, ensuring the investigation can continue.

Usage:
    from sre_agent.tools.mcp.fallback import with_fallback

    result = await with_fallback(
        primary=lambda: mcp_list_log_entries(filter=f, tool_context=ctx),
        fallback=lambda: list_log_entries(filter=f, project_id=pid),
        tool_name="list_log_entries",
    )
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sre_agent.schema import BaseToolResponse

logger = logging.getLogger(__name__)

# Exceptions that indicate MCP infrastructure failure (not user error)
_MCP_RECOVERABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# Error message patterns that indicate MCP-specific failures
_MCP_ERROR_PATTERNS = (
    "session",
    "mcp",
    "connection refused",
    "connection reset",
    "timed out",
    "unavailable",
    "transport",
    "sse",
    "event stream",
)


def _is_mcp_failure(error: Exception | None = None, response: Any = None) -> bool:
    """Determine if a failure is MCP-infrastructure-related (vs. user error).

    MCP failures are connection issues, session errors, or transport problems.
    User errors (invalid filter, permission denied) should NOT trigger fallback.

    Args:
        error: An exception that was raised.
        response: A BaseToolResponse or dict that may contain error info.

    Returns:
        True if the failure is MCP-infrastructure-related.
    """
    if error is not None:
        if isinstance(error, _MCP_RECOVERABLE_ERRORS):
            return True
        error_lower = str(error).lower()
        return any(pattern in error_lower for pattern in _MCP_ERROR_PATTERNS)

    if response is not None:
        error_msg = ""
        if isinstance(response, BaseToolResponse) and response.error:
            error_msg = response.error.lower()
        elif isinstance(response, dict):
            error_msg = str(response.get("error", "")).lower()

        return any(pattern in error_msg for pattern in _MCP_ERROR_PATTERNS)

    return False


async def with_fallback(
    primary: Callable[[], Awaitable[Any]],
    fallback: Callable[[], Awaitable[Any]],
    tool_name: str,
) -> Any:
    """Execute a primary (MCP) tool call with fallback to direct API.

    Tries the primary callable first. If it fails with an MCP-infrastructure
    error, transparently retries using the fallback callable.

    User errors (invalid filter, permission denied) are returned as-is
    without triggering the fallback.

    Args:
        primary: Async callable for the MCP tool call.
        fallback: Async callable for the direct API equivalent.
        tool_name: Tool name for logging.

    Returns:
        Result from primary or fallback.

    Raises:
        Exception: If both primary and fallback fail.
    """
    try:
        result = await primary()

        # Check if the MCP call returned an error response
        if _is_mcp_failure(response=result):
            logger.warning(
                f"MCP tool '{tool_name}' returned infrastructure error. "
                "Falling back to direct API."
            )
            fallback_result = await fallback()
            if isinstance(fallback_result, BaseToolResponse):
                return fallback_result.model_copy(
                    update={
                        "metadata": {
                            **fallback_result.metadata,
                            "fallback_used": True,
                            "original_source": "mcp",
                        }
                    }
                )
            return fallback_result

        return result

    except _MCP_RECOVERABLE_ERRORS as e:
        logger.warning(
            f"MCP tool '{tool_name}' raised {type(e).__name__}: {e}. "
            "Falling back to direct API."
        )
        return await fallback()

    except Exception as e:
        if _is_mcp_failure(error=e):
            logger.warning(
                f"MCP tool '{tool_name}' failed with MCP error: {e}. "
                "Falling back to direct API."
            )
            return await fallback()
        # Not an MCP failure — re-raise the original error
        raise
