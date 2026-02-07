"""Large Payload Handler — Automatic sandbox processing for oversized tool outputs.

Intercepts tool results that exceed token-safe thresholds and processes them
through the sandbox (local or cloud) before they reach the LLM, preventing
context window overflow while preserving data insights.

Problem:
    Tools like ``list_log_entries`` or ``list_metric_descriptors`` can return
    hundreds of thousands of items.  Previously these were either:

    1. Sent raw to the LLM (exceeding context limits), or
    2. Bluntly truncated at 200 k chars (losing valuable data).

Solution:
    This module sits in the ``after_tool_callback`` chain *before* the old
    truncation guard.  When a result exceeds configurable thresholds it is:

    * **Auto-summarised** — if the originating tool maps to a known sandbox
      template (metrics, logs, traces, time series), the data is processed
      in-process via :class:`LocalCodeExecutor` / :class:`SandboxExecutor`.

    * **Code-generation-ready** - for unknown data shapes the handler returns
      a compact sample of the data together with a structured prompt that
      tells the LLM to generate analysis code.  The LLM can then call
      ``execute_custom_analysis_in_sandbox`` with that code to obtain the
      full summary, keeping the raw payload out of the context window.

Architecture::

    Tool execution
         │
         ▼
    @adk_tool decorator
         │
         ▼
    composite_after_tool_callback()
      ├→ **large_payload_handler()**   ← THIS MODULE
      │     ├→ detect payload size
      │     ├→ select template (or build code-gen prompt)
      │     ├→ execute in sandbox
      │     └→ replace result with summary + metadata
      ├→ truncate_tool_output_callback()   (safety net)
      └→ after_tool_memory_callback()      (learning)

Environment variables:
    SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS:
        List-item count above which sandbox processing triggers (default 50).
    SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS:
        Serialised-JSON character count above which processing triggers
        (default 100 000, approx 25-40 k tokens).
    SRE_AGENT_LARGE_PAYLOAD_ENABLED:
        Explicitly enable/disable the handler (default ``"true"``).
        Set to ``"false"`` to bypass sandbox processing entirely.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_THRESHOLD_ITEMS_ENV = "SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS"
_THRESHOLD_CHARS_ENV = "SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS"
_ENABLED_ENV = "SRE_AGENT_LARGE_PAYLOAD_ENABLED"

DEFAULT_THRESHOLD_ITEMS: int = 50
DEFAULT_THRESHOLD_CHARS: int = 100_000  # ~25-40k tokens depending on content

# Maximum size for the data sample included in a code-generation prompt
_CODE_GEN_SAMPLE_ITEMS: int = 3
_CODE_GEN_SAMPLE_CHARS: int = 2_000

# ---------------------------------------------------------------------------
# Tool → sandbox template mapping
# ---------------------------------------------------------------------------

#: Maps tool names to the pre-built sandbox template that best summarises
#: their output.  Only tools whose results are known to be large collections
#: are listed.  For everything else the handler falls back to generic
#: summarisation or code-generation prompting.
TOOL_TEMPLATE_MAP: dict[str, str] = {
    # Metric tools
    "list_metric_descriptors": "summarize_metrics",
    "list_monitored_resource_descriptors": "summarize_metrics",
    # Time-series tools
    "list_time_series": "summarize_timeseries",
    "query_promql": "summarize_timeseries",
    "get_metric_time_series": "summarize_timeseries",
    # Log tools
    "list_log_entries": "summarize_logs",
    "search_logs": "summarize_logs",
    "tail_log_entries": "summarize_logs",
    # Trace tools
    "list_traces": "summarize_traces",
    "list_trace_spans": "summarize_traces",
    "batch_list_traces": "summarize_traces",
}

# ---------------------------------------------------------------------------
# Generic summarisation template (for large data without a specific template)
# ---------------------------------------------------------------------------

GENERIC_SUMMARY_TEMPLATE: str = """
import json
from collections import defaultdict

result = {
    "total_count": 0,
    "data_type": "unknown",
    "field_distribution": {},
    "sample_items": [],
    "summary": "",
}

if isinstance(data, list):
    result["total_count"] = len(data)
    result["data_type"] = "list"

    # Discover common top-level keys
    key_counts = defaultdict(int)
    for item in data:
        if isinstance(item, dict):
            for k in item:
                key_counts[k] += 1
    result["field_distribution"] = {
        k: v for k, v in sorted(key_counts.items(), key=lambda x: -x[1])[:20]
    }

    # Collect a representative sample (first 5 items, truncated)
    for item in data[:5]:
        item_str = json.dumps(item, default=str)
        if len(item_str) > 500:
            item_str = item_str[:500] + "..."
        result["sample_items"].append(json.loads(item_str) if item_str.endswith("}") else item_str)

    result["summary"] = (
        f"Collection of {result['total_count']} items. "
        f"Top keys: {list(result['field_distribution'].keys())[:10]}."
    )

elif isinstance(data, dict):
    result["total_count"] = len(data)
    result["data_type"] = "dict"

    # Classify value types without using type() (not in sandbox builtins)
    def _classify(v):
        if isinstance(v, str):
            return "str"
        if isinstance(v, bool):
            return "bool"
        if isinstance(v, int):
            return "int"
        if isinstance(v, float):
            return "float"
        if isinstance(v, list):
            return "list"
        if isinstance(v, dict):
            return "dict"
        if v is None:
            return "NoneType"
        return "other"

    result["field_distribution"] = {
        k: _classify(v) for k, v in list(data.items())[:20]
    }
    result["summary"] = (
        f"Dictionary with {len(data)} top-level keys: "
        f"{list(data.keys())[:10]}."
    )

with open("output.json", "w") as f:
    json.dump(result, f, default=str)

print(json.dumps(result, default=str))
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def is_large_payload_handling_enabled() -> bool:
    """Check whether automatic large-payload handling is enabled.

    Returns ``True`` by default; set ``SRE_AGENT_LARGE_PAYLOAD_ENABLED=false``
    to disable.
    """
    return os.environ.get(_ENABLED_ENV, "true").lower() != "false"


def get_threshold_items() -> int:
    """Return the item-count threshold from env or default."""
    try:
        return int(os.environ.get(_THRESHOLD_ITEMS_ENV, str(DEFAULT_THRESHOLD_ITEMS)))
    except (ValueError, TypeError):
        return DEFAULT_THRESHOLD_ITEMS


def get_threshold_chars() -> int:
    """Return the character-count threshold from env or default."""
    try:
        return int(os.environ.get(_THRESHOLD_CHARS_ENV, str(DEFAULT_THRESHOLD_CHARS)))
    except (ValueError, TypeError):
        return DEFAULT_THRESHOLD_CHARS


# ---------------------------------------------------------------------------
# Payload analysis
# ---------------------------------------------------------------------------


def estimate_payload_size(result: Any) -> tuple[int, int]:
    """Estimate the size of a tool result.

    Args:
        result: The ``result`` field from a tool response dict.

    Returns:
        ``(item_count, char_count)`` where *item_count* is the number of
        top-level items (for lists) or keys (for dicts), and *char_count*
        is the serialised JSON length.
    """
    if result is None:
        return 0, 0

    item_count = 0
    char_count = 0

    if isinstance(result, list):
        item_count = len(result)
    elif isinstance(result, dict):
        item_count = len(result)

    try:
        char_count = len(json.dumps(result, default=str))
    except (TypeError, ValueError, OverflowError):
        # Fallback: str() representation length
        char_count = len(str(result))

    return item_count, char_count


def is_payload_large(result: Any) -> bool:
    """Decide whether a tool result qualifies as "large".

    Args:
        result: The ``result`` field from a tool response dict.

    Returns:
        ``True`` if the result exceeds either the item-count or the
        character-count threshold.
    """
    if result is None:
        return False

    items, chars = estimate_payload_size(result)
    return items > get_threshold_items() or chars > get_threshold_chars()


# ---------------------------------------------------------------------------
# Template selection
# ---------------------------------------------------------------------------


def get_template_for_tool(tool_name: str) -> str | None:
    """Return the sandbox template name for a known-large-output tool.

    Args:
        tool_name: Name of the originating tool.

    Returns:
        Template name such as ``"summarize_logs"`` or ``None`` if no
        dedicated template exists for the tool.
    """
    return TOOL_TEMPLATE_MAP.get(tool_name)


# ---------------------------------------------------------------------------
# Code-generation prompt builder
# ---------------------------------------------------------------------------


def build_code_generation_prompt(
    tool_name: str,
    result: Any,
) -> dict[str, Any]:
    """Build a structured response asking the LLM to generate sandbox code.

    When no pre-built template matches the tool, the handler cannot
    automatically summarise the data.  Instead it returns a compact sample
    of the data together with a natural-language prompt that instructs the
    LLM to produce analysis code.  The LLM can then invoke
    ``execute_custom_analysis_in_sandbox`` with that code.

    Args:
        tool_name: Name of the tool that produced the result.
        result: The raw tool result (list or dict).

    Returns:
        A dictionary suitable for use as the ``result`` field in the
        tool response — it contains a ``data_sample``, ``schema_hint``,
        ``total_count``, and a ``code_generation_prompt`` string.
    """
    sample: Any
    schema_hint: dict[str, str] = {}

    if isinstance(result, list):
        total_count = len(result)
        sample_items = result[:_CODE_GEN_SAMPLE_ITEMS]
        # Build schema hint from first item
        if sample_items and isinstance(sample_items[0], dict):
            schema_hint = {k: type(v).__name__ for k, v in sample_items[0].items()}
        # Truncate each sample item's string repr
        sample = []
        for item in sample_items:
            item_str = json.dumps(item, default=str)
            if len(item_str) > _CODE_GEN_SAMPLE_CHARS:
                item_str = item_str[:_CODE_GEN_SAMPLE_CHARS] + "..."
            try:
                sample.append(
                    json.loads(item_str) if not item_str.endswith("...") else item_str
                )
            except json.JSONDecodeError:
                sample.append(item_str)
    elif isinstance(result, dict):
        total_count = len(result)
        schema_hint = {k: type(v).__name__ for k, v in list(result.items())[:10]}
        sample_str = json.dumps(
            {k: result[k] for k in list(result.keys())[:_CODE_GEN_SAMPLE_ITEMS]},
            default=str,
        )
        if len(sample_str) > _CODE_GEN_SAMPLE_CHARS:
            sample_str = sample_str[:_CODE_GEN_SAMPLE_CHARS] + "..."
        sample = sample_str
    else:
        total_count = 1
        sample = str(result)[:_CODE_GEN_SAMPLE_CHARS]

    prompt = (
        f"The tool '{tool_name}' returned {total_count} items — too large to "
        f"fit in the LLM context window.  A small sample and schema are "
        f"provided below.\n\n"
        f"To analyse the full dataset, write Python code that:\n"
        f"1. Reads the data from the variable `data` (already loaded).\n"
        f"2. Computes relevant statistics, aggregations, or filters.\n"
        f"3. Prints a JSON summary via `print(json.dumps(result))`.\n\n"
        f"Then call `execute_custom_analysis_in_sandbox` with the full "
        f"dataset and your code."
    )

    return {
        "large_payload_handled": True,
        "handling_mode": "code_generation_prompt",
        "tool_name": tool_name,
        "total_count": total_count,
        "data_sample": sample,
        "schema_hint": schema_hint,
        "code_generation_prompt": prompt,
    }


# ---------------------------------------------------------------------------
# Sandbox processing
# ---------------------------------------------------------------------------


async def _process_with_template(
    tool_name: str,
    result: Any,
    template_name: str,
) -> dict[str, Any]:
    """Process large data through a known sandbox template.

    Args:
        tool_name: Originating tool name (for logging).
        result: Raw tool result data.
        template_name: Sandbox template to apply.

    Returns:
        A dictionary containing the processed summary.

    Raises:
        RuntimeError: If sandbox execution fails.
    """
    from sre_agent.tools.sandbox.executor import process_data_in_sandbox

    item_count = len(result) if isinstance(result, list) else 1
    logger.info(
        "Large payload handler: processing %d items from '%s' with template '%s'",
        item_count,
        tool_name,
        template_name,
    )

    return await process_data_in_sandbox(data=result, template_name=template_name)


async def _process_with_generic_template(
    tool_name: str,
    result: Any,
) -> dict[str, Any]:
    """Process large data with the generic summarisation template.

    Used when no tool-specific template is available but the sandbox is
    enabled.

    Args:
        tool_name: Originating tool name.
        result: Raw tool result data.

    Returns:
        A dictionary with the generic summary.
    """
    from sre_agent.tools.sandbox.executor import get_code_executor, is_sandbox_enabled

    if not is_sandbox_enabled():
        # Sandbox not available — fall back to code-gen prompt
        return build_code_generation_prompt(tool_name, result)

    item_count = (
        len(result)
        if isinstance(result, list)
        else len(result)
        if isinstance(result, dict)
        else 1
    )
    logger.info(
        "Large payload handler: generic processing of %d items from '%s'",
        item_count,
        tool_name,
    )

    executor = await get_code_executor()
    async with executor:
        output = await executor.execute_data_processing(
            data=result,
            processing_code=GENERIC_SUMMARY_TEMPLATE,
        )

    if output.execution_error:
        logger.warning(
            "Generic sandbox processing failed for '%s': %s",
            tool_name,
            output.execution_error,
        )
        # Fall back to code-gen prompt
        return build_code_generation_prompt(tool_name, result)

    import json as _json

    try:
        parsed = _json.loads(output.stdout)
        parsed["large_payload_handled"] = True
        parsed["handling_mode"] = "generic_sandbox"
        parsed["tool_name"] = tool_name
        return parsed  # type: ignore[no-any-return]
    except _json.JSONDecodeError:
        # Try output file
        for f in output.output_files:
            if f.name == "output.json":
                parsed = _json.loads(f.content.decode("utf-8"))
                parsed["large_payload_handled"] = True
                parsed["handling_mode"] = "generic_sandbox"
                parsed["tool_name"] = tool_name
                return parsed  # type: ignore[no-any-return]

        logger.warning("Could not parse generic sandbox output for '%s'", tool_name)
        return build_code_generation_prompt(tool_name, result)


# ---------------------------------------------------------------------------
# Main entry point (after_tool_callback compatible)
# ---------------------------------------------------------------------------


async def handle_large_payload(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """Intercept large tool results and process them via sandbox.

    This function follows the ADK ``after_tool_callback`` signature and
    should be invoked *before* :func:`truncate_tool_output_callback` in the
    composite callback chain.

    Decision flow:

    1. If the handler is disabled → return ``None`` (no-op).
    2. If the result is not large → return ``None``.
    3. If a tool-specific template exists → process in sandbox.
    4. If the sandbox is enabled → process with the generic template.
    5. Otherwise → return a code-generation prompt for the LLM.

    Args:
        tool: The tool instance (has ``.name`` attribute).
        args: Arguments that were passed to the tool.
        tool_context: ADK tool execution context.
        tool_response: The tool response dictionary (mutable).

    Returns:
        The modified ``tool_response`` when processing occurred, or
        ``None`` if no modification was needed.
    """
    if not is_large_payload_handling_enabled():
        return None

    if not isinstance(tool_response, dict):
        return None

    result = tool_response.get("result")
    if result is None:
        return None

    # Skip results that are already handled (e.g. BaseToolResponse error)
    if isinstance(result, dict) and result.get("large_payload_handled"):
        return None

    # Quick size check
    if not is_payload_large(result):
        return None

    tool_name = getattr(tool, "name", str(tool))
    items, chars = estimate_payload_size(result)

    logger.info(
        "Large payload detected from '%s': %d items, %s chars — "
        "routing through sandbox handler",
        tool_name,
        items,
        f"{chars:,}",
    )

    start = time.time()

    try:
        # 1. Try tool-specific template
        template = get_template_for_tool(tool_name)
        if template:
            from sre_agent.tools.sandbox.executor import is_sandbox_enabled

            if is_sandbox_enabled():
                processed = await _process_with_template(tool_name, result, template)
                processed["large_payload_handled"] = True
                processed["handling_mode"] = "template_sandbox"
                processed["original_item_count"] = items
                processed["original_char_count"] = chars
                processed["tool_name"] = tool_name

                tool_response["result"] = processed
                tool_response["metadata"] = {
                    **tool_response.get("metadata", {}),
                    "large_payload_handled": True,
                    "handling_mode": "template_sandbox",
                    "template_used": template,
                    "original_items": items,
                    "original_chars": chars,
                    "processing_ms": round((time.time() - start) * 1000, 1),
                }

                logger.info(
                    "Large payload from '%s' processed via template '%s' "
                    "in %.1f ms (reduced from %s chars)",
                    tool_name,
                    template,
                    (time.time() - start) * 1000,
                    f"{chars:,}",
                )
                return tool_response

        # 2. Try generic sandbox processing
        from sre_agent.tools.sandbox.executor import is_sandbox_enabled

        if is_sandbox_enabled():
            processed = await _process_with_generic_template(tool_name, result)
            tool_response["result"] = processed
            tool_response["metadata"] = {
                **tool_response.get("metadata", {}),
                "large_payload_handled": True,
                "handling_mode": processed.get("handling_mode", "generic_sandbox"),
                "original_items": items,
                "original_chars": chars,
                "processing_ms": round((time.time() - start) * 1000, 1),
            }
            logger.info(
                "Large payload from '%s' processed via generic sandbox in %.1f ms",
                tool_name,
                (time.time() - start) * 1000,
            )
            return tool_response

        # 3. Sandbox not available — build code-generation prompt
        prompt_result = build_code_generation_prompt(tool_name, result)
        tool_response["result"] = prompt_result
        tool_response["metadata"] = {
            **tool_response.get("metadata", {}),
            "large_payload_handled": True,
            "handling_mode": "code_generation_prompt",
            "original_items": items,
            "original_chars": chars,
        }
        logger.info(
            "Large payload from '%s': sandbox unavailable, returning "
            "code-generation prompt",
            tool_name,
        )
        return tool_response

    except Exception:
        logger.exception(
            "Large payload handler failed for '%s' — passing through "
            "to truncation guard",
            tool_name,
        )
        # Don't modify the response — the downstream truncation guard
        # will handle it.
        return None
