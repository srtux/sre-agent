"""Memory callbacks for automatic learning from tool successes and failures.

These callbacks intercept tool results and errors to automatically persist
lessons learned into the Vertex AI Memory Bank, enabling cross-session
improvement.

Key Features:
- before_tool_memory_callback: Records tool calls for investigation pattern tracking
- after_tool_memory_callback: Records learnable failures (API syntax errors)
- after_tool_success_callback: Records significant successful findings
- on_tool_error_memory_callback: Records tool exceptions
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

# Tools whose successful results should be recorded to memory
_SIGNIFICANT_FINDING_TOOLS = {
    "analyze_critical_path": "Identified critical path bottleneck",
    "find_bottleneck_services": "Discovered service bottleneck",
    "detect_metric_anomalies": "Found metric anomaly",
    "detect_latency_anomalies": "Detected latency anomaly",
    "detect_cascading_timeout": "Identified cascading timeout pattern",
    "detect_retry_storm": "Discovered retry storm",
    "detect_connection_pool_issues": "Found connection pool problem",
    "detect_circular_dependencies": "Detected circular dependency",
    "analyze_log_anomalies": "Found log anomaly pattern",
    "extract_log_patterns": "Extracted error patterns from logs",
    "perform_causal_analysis": "Completed causal analysis",
    "correlate_changes_with_incident": "Correlated incident with change",
    "find_similar_past_incidents": "Found similar historical incident",
    "generate_remediation_suggestions": "Generated remediation plan",
    "analyze_error_budget_burn": "Analyzed error budget consumption",
    "detect_all_sre_patterns": "Detected SRE anti-patterns",
}


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


def _is_significant_success(tool_name: str, tool_response: dict[str, Any]) -> bool:
    """Check if a tool response contains significant successful findings.

    Returns True if the tool is in the significant findings list and
    the response indicates success with meaningful data.
    """
    if tool_name not in _SIGNIFICANT_FINDING_TOOLS:
        return False

    status = tool_response.get("status", "")
    if isinstance(status, str) and status.lower() == "success":
        # Check if there's meaningful result data
        result = tool_response.get("result")
        if result:
            # Only record if there are actual findings
            if isinstance(result, dict):
                # Check for common indicators of meaningful findings
                has_findings = (
                    result.get("bottlenecks")
                    or result.get("anomalies")
                    or result.get("patterns")
                    or result.get("root_cause")
                    or result.get("recommendations")
                    or result.get("issues")
                    or result.get("correlations")
                    or result.get("severity")
                )
                if has_findings:
                    return True
            elif isinstance(result, list) and len(result) > 0:
                return True
            elif isinstance(result, str) and len(result) > 50:
                return True
    return False


def _extract_success_finding(
    tool_name: str,
    tool_args: dict[str, Any],
    tool_response: dict[str, Any],
) -> str:
    """Extract a structured finding from a successful tool response."""
    finding_type = _SIGNIFICANT_FINDING_TOOLS.get(tool_name, "Investigation finding")
    result = tool_response.get("result", {})

    # Sanitize args
    safe_args = {}
    for k, v in tool_args.items():
        if k in ("access_token", "credentials", "token"):
            continue
        if isinstance(v, str) and len(v) > 100:
            safe_args[k] = v[:100] + "..."
        else:
            safe_args[k] = v

    # Extract key findings
    finding_summary = ""
    if isinstance(result, dict):
        # Prioritize common finding fields
        for key in [
            "summary",
            "root_cause",
            "conclusion",
            "recommendations",
            "bottlenecks",
            "anomalies",
            "patterns",
        ]:
            if result.get(key):
                finding_summary = str(result[key])[:500]
                break
        if not finding_summary:
            finding_summary = str(result)[:500]
    else:
        finding_summary = str(result)[:500]

    return (
        f"[SUCCESSFUL FINDING] Type: {finding_type}\n"
        f"Tool: {tool_name}\n"
        f"Context: {json.dumps(safe_args, default=str)}\n"
        f"Finding: {finding_summary}\n"
        f"Use this pattern when investigating similar symptoms."
    )


async def before_tool_memory_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
) -> dict[str, Any] | None:
    """Record tool calls to track investigation patterns.

    This callback fires BEFORE every tool call to track the sequence
    of tools used during an investigation. This enables learning
    which tool sequences successfully resolve different symptom types.

    Args:
        tool: The BaseTool instance about to be called.
        args: The arguments passed to the tool.
        tool_context: The ToolContext for this invocation.

    Returns:
        None (does not modify the call).
    """
    tool_name = getattr(tool, "name", str(tool))

    try:
        from sre_agent.memory.factory import get_memory_manager

        manager = get_memory_manager()

        # Record the tool call for pattern tracking
        manager.record_tool_call(tool_name)
        logger.debug(f"Recorded tool call: {tool_name}")

    except Exception as e:
        # Never let memory recording break tool execution
        logger.debug(f"Failed to record tool call: {e}")

    return None


async def after_tool_memory_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """Record learnable tool failures AND significant successes to memory.

    This callback fires after every tool call. It inspects the response for:
    1. API syntax errors, invalid filter expressions (learnable failures)
    2. Significant successful findings (bottlenecks, anomalies, root causes)

    Both types are persisted to memory for future recall.

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

        # Helper to get context once
        def get_context() -> tuple[Any, str | None, str | None]:
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

            return inv_ctx, session_id, user_id

        # Check for learnable failure
        if _is_learnable_failure(tool_response):
            lesson = _extract_failure_lesson(tool_name, args, tool_response)
            logger.info(f"Recording tool failure lesson for {tool_name}")

            from sre_agent.memory.factory import get_memory_manager

            manager = get_memory_manager()
            _, session_id, user_id = get_context()

            from sre_agent.schema import Confidence

            await manager.add_finding(
                description=lesson,
                source_tool=tool_name,
                confidence=Confidence.HIGH,
                session_id=session_id,
                user_id=user_id,
            )
            return None

        # Check for significant success
        if _is_significant_success(tool_name, tool_response):
            finding = _extract_success_finding(tool_name, args, tool_response)
            logger.info(f"Recording successful finding from {tool_name}")

            from sre_agent.memory.factory import get_memory_manager

            manager = get_memory_manager()
            _, session_id, user_id = get_context()

            from sre_agent.schema import Confidence

            await manager.add_finding(
                description=finding,
                source_tool=tool_name,
                confidence=Confidence.HIGH,
                session_id=session_id,
                user_id=user_id,
            )

    except Exception as e:
        # Never let memory recording break tool execution
        logger.debug(f"Failed to record tool memory: {e}")

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
