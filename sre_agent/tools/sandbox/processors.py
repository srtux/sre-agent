"""Data processing tools using Agent Engine Code Execution sandbox.

This module provides tools that leverage sandboxes to process large volumes of data
returned by other tools (e.g., list_metric_descriptors, list_time_series, list_logs),
summarizing and aggregating the results to avoid exceeding LLM context windows.

These tools should be used when:
- A tool returns more than ~100 items
- You need statistical analysis of large datasets
- You want to filter and rank results before presenting to user

Example:
    # Instead of sending 1000+ metric descriptors to the LLM:
    raw_result = await list_metric_descriptors(filter_str="compute")
    summary = await summarize_metric_descriptors_in_sandbox(raw_result.result)
    # summary contains aggregations and top items, not full dataset
"""

import json
import logging
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool

from .executor import (
    DATA_PROCESSING_TEMPLATES,
    SandboxExecutor,
    is_sandbox_enabled,
    process_data_in_sandbox,
)
from .schemas import DataProcessingResult

logger = logging.getLogger(__name__)

# Thresholds for when to use sandbox processing
SANDBOX_THRESHOLD_ITEMS = 50  # Use sandbox if more than this many items
SANDBOX_THRESHOLD_BYTES = 50_000  # Use sandbox if data exceeds ~50KB


def _should_use_sandbox(data: Any) -> bool:
    """Determine if sandbox processing should be used based on data size.

    Args:
        data: Data to check.

    Returns:
        True if sandbox processing is recommended.
    """
    if not is_sandbox_enabled():
        return False

    if isinstance(data, list):
        if len(data) > SANDBOX_THRESHOLD_ITEMS:
            return True
        # Also check serialized size
        try:
            size = len(json.dumps(data, default=str))
            return size > SANDBOX_THRESHOLD_BYTES
        except (TypeError, ValueError):
            return len(data) > SANDBOX_THRESHOLD_ITEMS

    if isinstance(data, dict):
        # Check if it's a collection-like dict
        try:
            size = len(json.dumps(data, default=str))
            return size > SANDBOX_THRESHOLD_BYTES
        except (TypeError, ValueError):
            return False

    return False


def _fallback_summarize(
    data: list[dict[str, Any]], data_type: str
) -> DataProcessingResult:
    """Fallback summarization when sandbox is not available.

    Provides basic summarization without sandbox execution.

    Args:
        data: Data to summarize.
        data_type: Type of data being summarized.

    Returns:
        DataProcessingResult with basic summary.
    """
    count = len(data)
    truncated = count > 20

    top_items = data[:20] if truncated else data

    summary = f"Found {count} {data_type}."
    if truncated:
        summary += " Showing first 20 items. Use sandbox for full analysis."

    return DataProcessingResult(
        summary=summary,
        statistics={"total": count},
        top_items=top_items,
        total_count=count,
        truncated=truncated,
        processing_metadata={"method": "fallback", "sandbox_enabled": False},
    )


@adk_tool
async def summarize_metric_descriptors_in_sandbox(
    descriptors: list[dict[str, Any]],
    filter_pattern: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Summarize a large list of metric descriptors using sandbox execution.

    Use this tool when list_metric_descriptors returns too many results
    to fit in context. The sandbox analyzes the data and returns:
    - Total count and breakdown by metric kind
    - Top metrics matching any filter pattern
    - Statistical distribution of metric types

    Args:
        descriptors: List of metric descriptors from list_metric_descriptors.
        filter_pattern: Optional pattern to filter metrics by type/name.
        tool_context: Context object for tool execution.

    Returns:
        BaseToolResponse with summarized metrics information.

    Example:
        # Get raw descriptors
        result = await list_metric_descriptors()
        # Summarize if too many
        if len(result.result) > 50:
            summary = await summarize_metric_descriptors_in_sandbox(result.result)
    """
    if not descriptors:
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=DataProcessingResult(
                summary="No metric descriptors to analyze.",
                statistics={},
                top_items=[],
                total_count=0,
                truncated=False,
                processing_metadata={},
            ).model_dump(),
        )

    # Filter if pattern provided
    if filter_pattern:
        pattern_lower = filter_pattern.lower()
        descriptors = [
            d
            for d in descriptors
            if pattern_lower in d.get("type", "").lower()
            or pattern_lower in d.get("display_name", "").lower()
        ]

    # Use sandbox if enabled and data is large
    if _should_use_sandbox(descriptors):
        try:
            logger.info(
                f"Using sandbox to summarize {len(descriptors)} metric descriptors"
            )
            result = await process_data_in_sandbox(
                data=descriptors, template_name="summarize_metrics"
            )
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={"processed_in_sandbox": True, "input_count": len(descriptors)},
            )
        except Exception as e:
            logger.warning(
                f"Sandbox processing failed, using fallback: {e}", exc_info=True
            )

    # Fallback to basic summarization
    fallback_result = _fallback_summarize(descriptors, "metric descriptors")
    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result=fallback_result.model_dump(),
        metadata={"processed_in_sandbox": False, "input_count": len(descriptors)},
    )


@adk_tool
async def summarize_time_series_in_sandbox(
    time_series: list[dict[str, Any]],
    include_stats: bool = True,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Summarize a large list of time series using sandbox execution.

    Use this tool when list_time_series returns many series to avoid
    exceeding context. The sandbox calculates:
    - Total series count by metric and resource type
    - Statistical summary (min/max/avg) for each series
    - Top series by data point count

    Args:
        time_series: List of time series from list_time_series.
        include_stats: Whether to calculate per-series statistics.
        tool_context: Context object for tool execution.

    Returns:
        BaseToolResponse with summarized time series information.
    """
    if not time_series:
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=DataProcessingResult(
                summary="No time series to analyze.",
                statistics={},
                top_items=[],
                total_count=0,
                truncated=False,
                processing_metadata={},
            ).model_dump(),
        )

    # Use sandbox if enabled and data is large
    if _should_use_sandbox(time_series):
        try:
            logger.info(f"Using sandbox to summarize {len(time_series)} time series")
            result = await process_data_in_sandbox(
                data=time_series, template_name="summarize_timeseries"
            )
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={"processed_in_sandbox": True, "input_count": len(time_series)},
            )
        except Exception as e:
            logger.warning(
                f"Sandbox processing failed, using fallback: {e}", exc_info=True
            )

    # Fallback
    fallback_result = _fallback_summarize(time_series, "time series")
    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result=fallback_result.model_dump(),
        metadata={"processed_in_sandbox": False, "input_count": len(time_series)},
    )


@adk_tool
async def summarize_log_entries_in_sandbox(
    log_entries: list[dict[str, Any]],
    extract_errors: bool = True,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Summarize a large list of log entries using sandbox execution.

    Use this tool when list_log_entries returns too many entries.
    The sandbox provides:
    - Count breakdown by severity level
    - Count breakdown by resource type
    - Top error messages
    - Time range of logs
    - Sample entries from each severity

    Args:
        log_entries: List of log entries from list_log_entries.
        extract_errors: Whether to extract and rank error messages.
        tool_context: Context object for tool execution.

    Returns:
        BaseToolResponse with summarized log information.
    """
    if not log_entries:
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=DataProcessingResult(
                summary="No log entries to analyze.",
                statistics={},
                top_items=[],
                total_count=0,
                truncated=False,
                processing_metadata={},
            ).model_dump(),
        )

    # Use sandbox if enabled and data is large
    if _should_use_sandbox(log_entries):
        try:
            logger.info(f"Using sandbox to summarize {len(log_entries)} log entries")
            result = await process_data_in_sandbox(
                data=log_entries, template_name="summarize_logs"
            )
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={"processed_in_sandbox": True, "input_count": len(log_entries)},
            )
        except Exception as e:
            logger.warning(
                f"Sandbox processing failed, using fallback: {e}", exc_info=True
            )

    # Fallback
    fallback_result = _fallback_summarize(log_entries, "log entries")
    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result=fallback_result.model_dump(),
        metadata={"processed_in_sandbox": False, "input_count": len(log_entries)},
    )


@adk_tool
async def summarize_traces_in_sandbox(
    traces: list[dict[str, Any]],
    slow_threshold_ms: int = 1000,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Summarize a large list of traces using sandbox execution.

    Use this tool when list_traces returns many traces. The sandbox provides:
    - Count breakdown by service
    - Error vs success counts
    - Latency statistics (min/max/avg)
    - Lists of error and slow traces

    Args:
        traces: List of traces with spans.
        slow_threshold_ms: Threshold in ms to consider a trace slow.
        tool_context: Context object for tool execution.

    Returns:
        BaseToolResponse with summarized trace information.
    """
    if not traces:
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=DataProcessingResult(
                summary="No traces to analyze.",
                statistics={},
                top_items=[],
                total_count=0,
                truncated=False,
                processing_metadata={},
            ).model_dump(),
        )

    # Use sandbox if enabled and data is large
    if _should_use_sandbox(traces):
        try:
            logger.info(f"Using sandbox to summarize {len(traces)} traces")
            result = await process_data_in_sandbox(
                data=traces, template_name="summarize_traces"
            )
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={
                    "processed_in_sandbox": True,
                    "input_count": len(traces),
                    "slow_threshold_ms": slow_threshold_ms,
                },
            )
        except Exception as e:
            logger.warning(
                f"Sandbox processing failed, using fallback: {e}", exc_info=True
            )

    # Fallback
    fallback_result = _fallback_summarize(traces, "traces")
    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result=fallback_result.model_dump(),
        metadata={"processed_in_sandbox": False, "input_count": len(traces)},
    )


@adk_tool
async def execute_custom_analysis_in_sandbox(
    data: list[dict[str, Any]] | dict[str, Any],
    analysis_code: str,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Execute custom Python analysis code in a sandbox.

    This tool allows the agent to write and execute custom analysis code
    in an isolated sandbox environment. The data is loaded as a variable
    named `data` in the sandbox.

    SECURITY: Only use this for trusted analysis tasks. The sandbox
    provides process-level isolation.

    Args:
        data: Data to analyze (will be available as `data` variable).
        analysis_code: Python code to execute. Must print results or
            write to output.json file.
        tool_context: Context object for tool execution.

    Returns:
        BaseToolResponse with analysis results.

    Example code:
        '''
        import json
        result = {"count": len(data), "first_item": data[0] if data else None}
        print(json.dumps(result))
        '''
    """
    if not analysis_code or not analysis_code.strip():
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Analysis code is required",
        )

    # Validate basic safety (this is defense in depth, sandbox provides isolation)
    dangerous_patterns = ["import os", "import subprocess", "__import__", "eval(", "exec("]
    for pattern in dangerous_patterns:
        if pattern in analysis_code:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"Analysis code contains potentially unsafe pattern: {pattern}",
            )

    if not is_sandbox_enabled():
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=(
                "Sandbox execution is not enabled. "
                "Set SRE_AGENT_SANDBOX_ENABLED=true to enable custom code execution."
            ),
        )

    try:
        logger.info("Executing custom analysis in sandbox")
        async with await SandboxExecutor.create() as executor:
            output = await executor.execute_data_processing(
                data=data, processing_code=analysis_code
            )

        if output.execution_error:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"Sandbox execution failed: {output.execution_error}",
                metadata={"stderr": output.stderr},
            )

        # Try to parse output as JSON
        try:
            result = json.loads(output.stdout) if output.stdout else {}
        except json.JSONDecodeError:
            # Return raw output if not JSON
            result = {"raw_output": output.stdout}

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={
                "processed_in_sandbox": True,
                "stderr": output.stderr if output.stderr else None,
            },
        )

    except Exception as e:
        logger.error(f"Custom sandbox analysis failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Sandbox analysis failed: {e}",
        )


@adk_tool
async def get_sandbox_status(
    tool_context: Any = None,
) -> BaseToolResponse:
    """Check the status and availability of sandbox execution.

    Returns information about whether sandbox execution is enabled
    and configured, along with any configuration details.

    Args:
        tool_context: Context object for tool execution.

    Returns:
        BaseToolResponse with sandbox status information.
    """
    from .executor import (
        get_agent_engine_resource_name,
        get_sandbox_resource_name,
        is_sandbox_enabled,
    )

    enabled = is_sandbox_enabled()
    sandbox_name = get_sandbox_resource_name()
    agent_engine_name = get_agent_engine_resource_name()

    result = {
        "enabled": enabled,
        "sandbox_resource_name": sandbox_name,
        "agent_engine_resource_name": agent_engine_name,
        "available_templates": list(DATA_PROCESSING_TEMPLATES.keys()),
        "thresholds": {
            "items": SANDBOX_THRESHOLD_ITEMS,
            "bytes": SANDBOX_THRESHOLD_BYTES,
        },
    }

    if not enabled:
        result["message"] = (
            "Sandbox execution is disabled. "
            "Set SRE_AGENT_SANDBOX_ENABLED=true to enable."
        )
    elif not sandbox_name and not agent_engine_name:
        result["message"] = (
            "Sandbox will be created on-demand. "
            "Set SRE_AGENT_SANDBOX_RESOURCE_NAME to use a persistent sandbox."
        )
    else:
        result["message"] = "Sandbox execution is configured and ready."

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result=result,
    )
