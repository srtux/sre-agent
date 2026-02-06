"""Tool callbacks for result safety and truncation.

Prevents massive tool outputs from blowing up the LLM context window.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maximum size for a single tool result in characters (~50k tokens)
MAX_RESULT_CHARS = 200_000


async def truncate_tool_output_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """Truncates massive tool outputs to prevent token limit exceedance.

    This callback inspects the tool response and truncates 'result' if it
    exceeds a safe character limit. This is a safety guard against
    tools that might return MBs of data (e.g., unfiltered logs).

    Args:
        tool: The tool instance.
        args: Arguments passed to the tool.
        tool_context: Tool execution context.
        tool_response: The response from the tool.

    Returns:
        The (potentially modified) tool response.
    |
    """
    if not isinstance(tool_response, dict):
        return None

    result = tool_response.get("result")
    if result is None:
        return None

    tool_name = getattr(tool, "name", str(tool))
    original_size = 0
    is_truncated = False

    if isinstance(result, str):
        original_size = len(result)
        if original_size > MAX_RESULT_CHARS:
            tool_response["result"] = (
                result[:MAX_RESULT_CHARS]
                + "\n\n... [TRUNCATED BY SRE AGENT SAFETY GUARD: Result too large for LLM context] ..."
            )
            is_truncated = True

    elif isinstance(result, list):
        # Estimate size of list
        try:
            # We don't want to re-serialize if possible, but it's the safest way to know size
            # For lists, we can just check length
            if len(result) > 500:  # Heuristic: more than 500 items is likely too big
                tool_response["result"] = result[:500]
                tool_response["metadata"] = tool_response.get("metadata", {})
                tool_response["metadata"]["truncated_count"] = len(result) - 500
                is_truncated = True
        except Exception:
            pass

    elif isinstance(result, dict):
        # For dicts, we serialize to check size
        res_str = json.dumps(result, default=str)
        original_size = len(res_str)
        if original_size > MAX_RESULT_CHARS:
            # Hard truncation of the string representation if it's too complex to slice
            tool_response["result"] = {
                "error": "Result too large",
                "message": f"Tool output ({original_size:,} chars) exceeded safety limit. Try a more specific filter.",
                "truncated_preview": res_str[: MAX_RESULT_CHARS // 2] + "...",
            }
            is_truncated = True

    if is_truncated:
        logger.warning(
            f"⚠️ Truncated massive result from tool '{tool_name}' "
            f"({original_size:,} -> {len(str(tool_response['result'])):,} chars)"
        )

    return tool_response
