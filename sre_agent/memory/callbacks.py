"""Memory callbacks for automatic tool failure and API syntax learning.

These callbacks intercept tool results and errors to automatically persist
lessons learned into the Vertex AI Memory Bank, enabling cross-session
improvement.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Tool response keys that indicate failure
_ERROR_INDICATORS = {"error", "status"}

# Patterns in error messages worth remembering (API syntax, filter issues)
_LEARNABLE_ERROR_PATTERNS = [
    "invalid filter",
    "invalid argument",
    "unrecognized field",
    "parse error",
    "syntax error",
    "unknown metric",
    "resource.type",
    "resource.labels",
    "metric.type",
    "filter must",
    "could not parse",
    "malformed",
    "not a valid",
    "unsupported",
    "not supported",
    "400",
    "invalid_argument",
    "INVALID_ARGUMENT",
]


def _is_learnable_failure(tool_response: dict[str, Any]) -> bool:
    """Check if a tool response contains a learnable failure pattern.

    We focus on failures related to API syntax, filter language, and query
    construction - the kinds of mistakes that should be remembered to avoid
    repeating.
    """
    # Check for error status
    status = tool_response.get("status", "")
    if isinstance(status, str) and status.lower() == "error":
        error_msg = str(tool_response.get("error", ""))
        # Only learn from syntax/argument errors, not transient failures
        error_lower = error_msg.lower()
        return any(pattern in error_lower for pattern in _LEARNABLE_ERROR_PATTERNS)

    return False


def _extract_failure_lesson(
    tool_name: str,
    tool_args: dict[str, Any],
    tool_response: dict[str, Any],
) -> str:
    """Extract a concise lesson from a tool failure for memory storage."""
    error_msg = str(tool_response.get("error", "Unknown error"))

    # Build a structured lesson
    # Sanitize args to avoid storing sensitive data
    safe_args = {}
    for k, v in tool_args.items():
        if k in ("access_token", "credentials", "token"):
            continue
        if isinstance(v, str) and len(v) > 200:
            safe_args[k] = v[:200] + "..."
        else:
            safe_args[k] = v

    return (
        f"[TOOL FAILURE LESSON] Tool: {tool_name}\n"
        f"Args: {json.dumps(safe_args, default=str)}\n"
        f"Error: {error_msg}\n"
        f"Lesson: Avoid this parameter combination. "
        f"The error indicates incorrect syntax or invalid arguments."
    )


def _extract_error_lesson(
    tool_name: str,
    tool_args: dict[str, Any],
    error: Exception,
) -> str:
    """Extract a concise lesson from a tool exception for memory storage."""
    safe_args = {}
    for k, v in tool_args.items():
        if k in ("access_token", "credentials", "token"):
            continue
        if isinstance(v, str) and len(v) > 200:
            safe_args[k] = v[:200] + "..."
        else:
            safe_args[k] = v

    return (
        f"[TOOL ERROR LESSON] Tool: {tool_name}\n"
        f"Args: {json.dumps(safe_args, default=str)}\n"
        f"Exception: {type(error).__name__}: {error!s}\n"
        f"Lesson: This tool call raised an exception. "
        f"Adjust parameters or use an alternative tool."
    )


async def after_tool_memory_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """Record learnable tool failures to memory after each tool call.

    This callback fires after every tool call. It inspects the response
    for API syntax errors, invalid filter expressions, and other learnable
    failures, then persists the lesson to memory for future recall.

    Args:
        tool: The BaseTool instance that was called.
        args: The arguments passed to the tool.
        tool_context: The ToolContext for this invocation.
        tool_response: The dict response from the tool.

    Returns:
        None (does not modify the response).
    """
    tool_name = getattr(tool, "name", str(tool))

    try:
        if not isinstance(tool_response, dict):
            return None

        if not _is_learnable_failure(tool_response):
            return None

        lesson = _extract_failure_lesson(tool_name, args, tool_response)
        logger.info(f"Recording tool failure lesson for {tool_name}")

        # Store in memory via the MemoryManager
        from sre_agent.memory.factory import get_memory_manager

        manager = get_memory_manager()

        # Extract session context
        inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
            tool_context, "_invocation_context", None
        )
        session_id = None
        user_id = None
        if inv_ctx:
            session = getattr(inv_ctx, "session", None)
            session_id = getattr(session, "id", None) if session else None
            user_id = getattr(inv_ctx, "user_id", None)

        if not user_id:
            try:
                from sre_agent.auth import get_user_id_from_tool_context

                user_id = get_user_id_from_tool_context(tool_context)
            except Exception:
                user_id = "system"

        from sre_agent.schema import Confidence

        await manager.add_finding(
            description=lesson,
            source_tool=tool_name,
            confidence=Confidence.HIGH,
            session_id=session_id,
            user_id=user_id,
        )

    except Exception as e:
        # Never let memory recording break tool execution
        logger.debug(f"Failed to record tool failure lesson: {e}")

    return None


async def on_tool_error_memory_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
    error: Exception,
) -> dict[str, Any] | None:
    """Record tool exceptions to memory for future avoidance.

    This callback fires when a tool raises an exception. It persists
    the error pattern so the agent can avoid repeating the same mistake.

    Args:
        tool: The BaseTool instance that raised.
        args: The arguments passed to the tool.
        tool_context: The ToolContext for this invocation.
        error: The exception that was raised.

    Returns:
        None (does not modify error handling).
    """
    tool_name = getattr(tool, "name", str(tool))

    try:
        error_str = str(error).lower()
        # Only learn from syntax/argument errors, not transient issues
        is_learnable = any(
            pattern in error_str for pattern in _LEARNABLE_ERROR_PATTERNS
        )
        if not is_learnable:
            return None

        lesson = _extract_error_lesson(tool_name, args, error)
        logger.info(f"Recording tool error lesson for {tool_name}")

        from sre_agent.memory.factory import get_memory_manager

        manager = get_memory_manager()

        inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
            tool_context, "_invocation_context", None
        )
        session_id = None
        user_id = None
        if inv_ctx:
            session = getattr(inv_ctx, "session", None)
            session_id = getattr(session, "id", None) if session else None
            user_id = getattr(inv_ctx, "user_id", None)

        if not user_id:
            try:
                from sre_agent.auth import get_user_id_from_tool_context

                user_id = get_user_id_from_tool_context(tool_context)
            except Exception:
                user_id = "system"

        from sre_agent.schema import Confidence

        await manager.add_finding(
            description=lesson,
            source_tool=tool_name,
            confidence=Confidence.HIGH,
            session_id=session_id,
            user_id=user_id,
        )

    except Exception as e:
        # Never let memory recording break tool execution
        logger.debug(f"Failed to record tool error lesson: {e}")

    return None
