"""Tests for the dashboard_queue module.

Covers the ContextVar-based queue lifecycle: init, enqueue, drain, and
edge cases (uninitialised queue, empty queue, double drain, re-init).
"""

from __future__ import annotations

import contextvars

from sre_agent.api.helpers.dashboard_queue import (
    drain_dashboard_queue,
    init_dashboard_queue,
    queue_tool_result,
)


class TestDrainDashboardQueue:
    """Tests for drain_dashboard_queue."""

    def test_drain_returns_empty_list_when_queue_not_initialized(self) -> None:
        """Draining before init_dashboard_queue returns an empty list."""
        # Run in a fresh context so the ContextVar has its default (None).
        # Without this, earlier tests in the same thread may have already
        # called init_dashboard_queue, leaving the var set.
        ctx = contextvars.copy_context()
        result = ctx.run(drain_dashboard_queue)
        assert result == []

    def test_drain_returns_empty_list_when_queue_empty(self) -> None:
        """Draining an initialised but empty queue returns an empty list."""
        init_dashboard_queue()
        result = drain_dashboard_queue()
        assert result == []

    def test_drain_clears_queue_second_drain_returns_empty(self) -> None:
        """After draining, a second drain returns an empty list."""
        init_dashboard_queue()
        queue_tool_result("tool_a", {"key": "value"})

        first = drain_dashboard_queue()
        assert len(first) == 1

        second = drain_dashboard_queue()
        assert second == []


class TestQueueToolResult:
    """Tests for queue_tool_result."""

    def test_queue_is_noop_when_not_initialized(self) -> None:
        """Enqueuing without init_dashboard_queue does nothing (no error)."""

        def _run_in_fresh_context() -> list:
            # In a truly empty context the ContextVar has its default (None).
            # queue_tool_result should silently no-op.
            queue_tool_result("ignored_tool", {"data": 123})
            return drain_dashboard_queue()

        # contextvars.Context() creates a truly empty context (unlike
        # copy_context() which inherits existing values from the thread).
        ctx = contextvars.Context()
        result = ctx.run(_run_in_fresh_context)
        assert result == []

    def test_queue_and_drain_returns_correct_items(self) -> None:
        """Items enqueued are returned by drain in FIFO order."""
        init_dashboard_queue()
        queue_tool_result("fetch_trace", {"trace_id": "abc"})
        queue_tool_result("list_logs", {"filter": "severity>=ERROR"})

        items = drain_dashboard_queue()
        assert len(items) == 2
        assert items[0] == ("fetch_trace", {"trace_id": "abc"})
        assert items[1] == ("list_logs", {"filter": "severity>=ERROR"})

    def test_multiple_items_can_be_queued(self) -> None:
        """Multiple items are accumulated in insertion order."""
        init_dashboard_queue()
        for i in range(5):
            queue_tool_result(f"tool_{i}", {"index": i})

        items = drain_dashboard_queue()
        assert len(items) == 5
        for i, (name, result) in enumerate(items):
            assert name == f"tool_{i}"
            assert result == {"index": i}

    def test_queue_accepts_various_result_types(self) -> None:
        """Results can be dicts, strings, ints, or None."""
        init_dashboard_queue()
        queue_tool_result("dict_tool", {"key": "value"})
        queue_tool_result("str_tool", "plain string")
        queue_tool_result("int_tool", 42)
        queue_tool_result("none_tool", None)

        items = drain_dashboard_queue()
        assert len(items) == 4
        assert items[0] == ("dict_tool", {"key": "value"})
        assert items[1] == ("str_tool", "plain string")
        assert items[2] == ("int_tool", 42)
        assert items[3] == ("none_tool", None)


class TestInitDashboardQueue:
    """Tests for init_dashboard_queue."""

    def test_init_resets_queue(self) -> None:
        """Calling init_dashboard_queue discards any previously queued items."""
        init_dashboard_queue()
        queue_tool_result("old_tool", {"old": True})

        # Re-initialise: should start a fresh empty queue
        init_dashboard_queue()

        items = drain_dashboard_queue()
        assert items == []

    def test_init_allows_subsequent_enqueue(self) -> None:
        """After init, enqueuing and draining works normally."""
        init_dashboard_queue()
        queue_tool_result("my_tool", "result")

        items = drain_dashboard_queue()
        assert items == [("my_tool", "result")]

    def test_double_init_does_not_raise(self) -> None:
        """Calling init_dashboard_queue twice in a row does not raise."""
        init_dashboard_queue()
        init_dashboard_queue()
        # Should simply work
        queue_tool_result("tool", "val")
        items = drain_dashboard_queue()
        assert items == [("tool", "val")]
