"""Dashboard event queue for propagating sub-agent tool results.

When tools are called by sub-agents (e.g., council panels inside AgentTool),
their function_response events don't flow through the router's event stream.
This module provides a ContextVar-based queue so that @adk_tool-decorated
functions can enqueue dashboard-relevant results, and the router can drain
them when it next yields control.

Usage:
    # Router (event_generator): initialise at start of request
    init_dashboard_queue()

    # @adk_tool decorator: after successful execution
    queue_tool_result(tool_name, result)

    # Router: after processing each ADK event batch
    for tool_name, result in drain_dashboard_queue():
        ...
"""

from __future__ import annotations

import contextvars
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Per-request queue of (tool_name, raw_result) pairs.
# None means the queue has not been initialised for this context.
_dashboard_queue: contextvars.ContextVar[list[tuple[str, Any]] | None] = (
    contextvars.ContextVar("_dashboard_queue", default=None)
)


def init_dashboard_queue() -> None:
    """Initialise an empty dashboard queue for the current async context.

    Call this once at the start of each request handler (event_generator).
    """
    _dashboard_queue.set([])


def queue_tool_result(tool_name: str, result: Any) -> None:
    """Enqueue a tool result for later dashboard event creation.

    Safe to call even when no queue has been initialised (e.g. in tests
    or CLI mode) -- the call is silently ignored.

    Args:
        tool_name: Name of the tool that produced the result.
        result: The raw tool result (may be BaseToolResponse, dict, str, etc.).
    """
    q = _dashboard_queue.get(None)
    if q is None:
        return
    q.append((tool_name, result))


def drain_dashboard_queue() -> list[tuple[str, Any]]:
    """Drain all queued tool results and return them.

    Returns an empty list if the queue was never initialised or is empty.
    """
    q = _dashboard_queue.get(None)
    if not q:
        return []
    items = list(q)
    q.clear()
    return items
