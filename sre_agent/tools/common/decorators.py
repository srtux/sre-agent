"""Decorators for SRE Agent tools with OpenTelemetry instrumentation and resilience."""

import functools
import inspect
import json
import logging
import os
import time
from collections.abc import Callable
from typing import Any

from .serialization import normalize_obj

logger = logging.getLogger(__name__)

# Optional dashboard queue integration.
# The import is conditional so tools work even when the API layer is absent
# (e.g. during ``adk run``, tests, or standalone scripts).
try:
    from sre_agent.api.helpers.dashboard_queue import (
        queue_tool_result as _queue_tool_result,
    )

    _HAS_DASHBOARD_QUEUE = True
except Exception:  # pragma: no cover - import may fail in minimal envs
    _HAS_DASHBOARD_QUEUE = False

    def _queue_tool_result(tool_name: str, result: Any) -> None:
        """No-op fallback when dashboard queue is unavailable."""


# Tools that interact with external GCP APIs and should be circuit-protected.
# Pure analysis tools (no I/O) are excluded to avoid unnecessary overhead.
_CIRCUIT_BREAKER_TOOL_PREFIXES: frozenset[str] = frozenset(
    {
        "fetch_trace",
        "list_traces",
        "find_example_traces",
        "get_trace_by_url",
        "list_log_entries",
        "get_logs_for_trace",
        "list_error_events",
        "list_time_series",
        "query_promql",
        "list_alerts",
        "get_alert",
        "list_alert_policies",
        "list_metric_descriptors",
        "list_slos",
        "get_slo_status",
        "get_gke_cluster_health",
        "analyze_node_conditions",
        "get_pod_restart_events",
        "analyze_hpa_events",
        "get_container_oom_events",
        "get_workload_health_summary",
        "list_gcp_projects",
        "mcp_execute_sql",
        "mcp_list_log_entries",
        "mcp_list_timeseries",
        "mcp_query_range",
        "mcp_list_dataset_ids",
        "mcp_list_table_ids",
        "mcp_get_table_info",
    }
)


def _is_circuit_breaker_enabled() -> bool:
    """Check if circuit breaker integration is enabled."""
    return os.environ.get("SRE_AGENT_CIRCUIT_BREAKER", "true").lower() != "false"


def _should_use_circuit_breaker(tool_name: str) -> bool:
    """Determine if a tool should use circuit breaker protection."""
    return _is_circuit_breaker_enabled() and tool_name in _CIRCUIT_BREAKER_TOOL_PREFIXES


def _is_tool_failure(result: Any) -> bool:
    """Check if a tool result indicates a failure.

    Examines the result in multiple formats:
    - JSON string with "error" key
    - Dict with "error" key
    - BaseToolResponse with status="error" or non-None error field

    Args:
        result: The tool's return value.

    Returns:
        True if the result indicates a logical failure.
    """
    if isinstance(result, str) and '"error":' in result:
        try:
            data = json.loads(result)
            if isinstance(data, dict) and data.get("error"):
                return True
        except (json.JSONDecodeError, ValueError):
            pass
    elif isinstance(result, dict) and result.get("error"):
        return True
    elif hasattr(result, "status") and str(getattr(result, "status", "")) == "error":
        return True
    elif hasattr(result, "error") and getattr(result, "error", None):
        return True
    return False


def adk_tool(
    func: Callable[..., Any] | None = None,
    *,
    skip_summarization: bool = False,
) -> Callable[..., Any]:
    """Decorator to mark a function as an ADK tool.

    This decorator provides:
    - OTel Spans for every execution
    - OTel Metrics (count and duration)
    - Standardized Logging of args and results/errors
    - Error handling (ensures errors are logged before raising/returning)
    - Circuit breaker integration for external API tools
    - Tool result validation (BaseToolResponse normalization)
    - Optional skip_summarization flag (OPT-8)

    Args:
        func: The function to decorate (when used without parentheses).
        skip_summarization: If True, marks the tool to skip LLM summarization
            of its output. Use for tools returning structured data intended for
            agent consumption rather than user display. The flag is stored as
            ``_skip_summarization`` on the wrapper and consumed by
            ``prepare_tools()`` when building agent tool lists.

    Example:
        @adk_tool
        async def fetch_trace(trace_id: str) -> dict:
            ...

        @adk_tool(skip_summarization=True)
        async def list_time_series(filter_str: str) -> dict:
            ...
    """

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _build_adk_tool_wrapper(fn, skip_summarization=skip_summarization)

    # Support both @adk_tool and @adk_tool(skip_summarization=True)
    if func is not None:
        # Called as @adk_tool without parentheses
        return _build_adk_tool_wrapper(func, skip_summarization=False)
    # Called as @adk_tool(...) with parentheses
    return _decorator


def _build_adk_tool_wrapper(
    func: Callable[..., Any], *, skip_summarization: bool = False
) -> Callable[..., Any]:
    """Internal: build the actual wrapper for @adk_tool."""

    def should_skip_logging() -> bool:
        """Check if we should skip logging due to native instrumentation."""
        return (
            os.environ.get(
                "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", ""
            ).lower()
            == "true"
        )

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        start_time = time.time()

        # Log calling
        try:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_str = ", ".join(
                f"{k}={repr(v)[:200]}" for k, v in bound.arguments.items()
            )

            # Full args for debug
            full_arg_str = ", ".join(f"{k}={v!r}" for k, v in bound.arguments.items())
            logger.debug(f"Tool '{tool_name}' FULL ARGS: {full_arg_str}")
        except Exception:
            arg_str = f"args={args}, kwargs={kwargs}"

        if not should_skip_logging():
            logger.info(f"🛠️  Tool Call: '{tool_name}' | Args: {arg_str}")

        # Circuit breaker pre-call check
        use_cb = _should_use_circuit_breaker(tool_name)
        registry = None
        if use_cb:
            try:
                from sre_agent.core.circuit_breaker import (
                    CircuitBreakerOpenError,
                    get_circuit_breaker_registry,
                )

                registry = get_circuit_breaker_registry()
                registry.pre_call(tool_name)
            except CircuitBreakerOpenError as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(
                    f"⚡ Circuit OPEN for '{tool_name}' | "
                    f"Retry after {e.retry_after_seconds:.1f}s | "
                    f"Duration: {duration_ms:.2f}ms"
                )
                from sre_agent.schema import BaseToolResponse, ToolStatus

                return BaseToolResponse(
                    status=ToolStatus.ERROR,
                    error=(
                        f"Circuit breaker OPEN for '{tool_name}'. "
                        f"The service appears degraded. "
                        f"Retry after {e.retry_after_seconds:.0f}s. "
                        "DO NOT retry immediately — use an alternative tool or wait."
                    ),
                    metadata={
                        "circuit_breaker": True,
                        "retry_after_seconds": e.retry_after_seconds,
                        "non_retryable": True,
                    },
                )
            except Exception as cb_err:
                # Circuit breaker itself should never block tool execution
                logger.debug(
                    f"Circuit breaker check failed for '{tool_name}': {cb_err}"
                )

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Check if the result indicates a tool-level error
            is_failed = _is_tool_failure(result)

            if is_failed:
                logger.error(
                    f"❌ Tool Failed (Logical): '{tool_name}' | Result contains error | Duration: {duration_ms:.2f}ms"
                )
                # Record failure in circuit breaker
                if use_cb and registry:
                    registry.record_failure(tool_name)
            else:
                if not should_skip_logging():
                    logger.info(
                        f"✅ Tool Success: '{tool_name}' | Duration: {duration_ms:.2f}ms"
                    )
                # Record success in circuit breaker
                if use_cb and registry:
                    registry.record_success(tool_name)

            # Do NOT normalize BaseToolResponse objects, legacy to keep for others
            from sre_agent.schema import BaseToolResponse

            if isinstance(result, BaseToolResponse):
                # Normalize the internal result and metadata of the BaseToolResponse
                # This ensures that even when returned in an envelope, GCP types are cleaned
                normalized_result = normalize_obj(result.result)
                normalized_metadata = normalize_obj(result.metadata)

                # BaseToolResponse is frozen, so we use model_copy
                final_result = result.model_copy(
                    update={
                        "result": normalized_result,
                        "metadata": normalized_metadata,
                    }
                )
                # Queue for dashboard event creation (captures sub-agent tool calls)
                if not is_failed:
                    _queue_tool_result(tool_name, final_result)
                return final_result

            # Normalize result (convert GCP types to native Python types)
            final_result = normalize_obj(result)
            # Queue for dashboard event creation (captures sub-agent tool calls)
            if not is_failed:
                _queue_tool_result(tool_name, final_result)
            return final_result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"❌ Tool Failed: '{tool_name}' | Duration: {duration_ms:.2f}ms | Error: {e}",
                exc_info=True,
            )
            # Record exception in circuit breaker
            if use_cb and registry:
                registry.record_failure(tool_name)
            raise e

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        start_time = time.time()

        # Log calling
        try:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_str = ", ".join(
                f"{k}={repr(v)[:200]}" for k, v in bound.arguments.items()
            )

            # Full args for debug
            full_arg_str = ", ".join(f"{k}={v!r}" for k, v in bound.arguments.items())
            logger.debug(f"Tool '{tool_name}' FULL ARGS: {full_arg_str}")
        except Exception:
            arg_str = f"args={args}, kwargs={kwargs}"

        if not should_skip_logging():
            logger.info(f"🛠️  Tool Call: '{tool_name}' | Args: {arg_str}")

        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Check if the result indicates a tool-level error
            is_failed = _is_tool_failure(result)

            if is_failed:
                logger.error(
                    f"❌ Tool Failed (Logical): '{tool_name}' | Result contains error | Duration: {duration_ms:.2f}ms"
                )
            elif not should_skip_logging():
                logger.info(
                    f"✅ Tool Success: '{tool_name}' | Duration: {duration_ms:.2f}ms"
                )

            # Do NOT normalize BaseToolResponse objects
            from sre_agent.schema import BaseToolResponse

            if isinstance(result, BaseToolResponse):
                # Normalize the internal result and metadata of the BaseToolResponse
                normalized_result = normalize_obj(result.result)
                normalized_metadata = normalize_obj(result.metadata)

                # BaseToolResponse is frozen, so we use model_copy
                final_result = result.model_copy(
                    update={
                        "result": normalized_result,
                        "metadata": normalized_metadata,
                    }
                )
                if not is_failed:
                    _queue_tool_result(tool_name, final_result)
                return final_result

            final_result = normalize_obj(result)
            if not is_failed:
                _queue_tool_result(tool_name, final_result)
            return final_result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"❌ Tool Failed: '{tool_name}' | Duration: {duration_ms:.2f}ms | Error: {e}",
                exc_info=True,
            )
            raise e

    if inspect.iscoroutinefunction(func):
        async_wrapper._skip_summarization = skip_summarization  # type: ignore[attr-defined]
        return async_wrapper
    else:
        sync_wrapper._skip_summarization = skip_summarization  # type: ignore[attr-defined]
        return sync_wrapper


def prepare_tools(tools: list[Any]) -> list[Any]:
    """Convert tool functions to FunctionTool objects, respecting skip_summarization.

    Tools decorated with ``@adk_tool(skip_summarization=True)`` will be wrapped
    in ``google.adk.tools.FunctionTool`` with ``skip_summarization=True``, which
    tells ADK to pass the tool output directly to the agent without an
    intermediate LLM summarization call.

    Tools without the flag are returned as-is (ADK auto-wraps them).

    Args:
        tools: List of tool functions (decorated with @adk_tool).

    Returns:
        List of tools, with skip_summarization tools wrapped in FunctionTool.
    """
    try:
        from google.adk.tools import FunctionTool  # type: ignore[attr-defined]
    except ImportError:
        # ADK not available — return tools as-is (tests, standalone scripts)
        return tools

    result: list[Any] = []
    for tool in tools:
        if getattr(tool, "_skip_summarization", False):
            result.append(FunctionTool(func=tool))
        else:
            result.append(tool)
    return result
