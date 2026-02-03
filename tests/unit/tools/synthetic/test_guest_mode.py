"""Tests for guest mode ContextVar and tool integration.

Validates that the guest mode ContextVar correctly controls
whether tools return synthetic vs real data.
"""

from __future__ import annotations

import contextvars

import pytest

from sre_agent.auth import is_guest_mode, set_guest_mode


class TestGuestModeContextVar:
    """Tests for the guest mode ContextVar."""

    def test_default_is_false(self) -> None:
        """Guest mode should be off by default."""
        ctx = contextvars.copy_context()
        assert ctx.run(is_guest_mode) is False

    def test_set_and_get(self) -> None:
        """Setting guest mode should be readable."""
        ctx = contextvars.copy_context()

        def _run() -> bool:
            set_guest_mode(True)
            return is_guest_mode()

        assert ctx.run(_run) is True

    def test_isolation_between_contexts(self) -> None:
        """Guest mode in one context should not leak to another."""
        ctx1 = contextvars.copy_context()
        ctx2 = contextvars.copy_context()

        def _enable() -> None:
            set_guest_mode(True)

        ctx1.run(_enable)
        # ctx2 should still be False
        assert ctx2.run(is_guest_mode) is False

    def test_can_disable_after_enable(self) -> None:
        """Guest mode should be disableable."""
        ctx = contextvars.copy_context()

        def _toggle() -> bool:
            set_guest_mode(True)
            assert is_guest_mode() is True
            set_guest_mode(False)
            return is_guest_mode()

        assert ctx.run(_toggle) is False


class TestGuestModeToolIntegration:
    """Tests that tools return synthetic data when guest mode is active."""

    @pytest.mark.asyncio
    async def test_fetch_trace_in_guest_mode(self) -> None:
        """fetch_trace should return synthetic data in guest mode."""
        from sre_agent.tools.clients.trace import fetch_trace
        from sre_agent.tools.synthetic.scenarios import TRACE_IDS

        ctx = contextvars.copy_context()

        async def _run() -> dict:
            set_guest_mode(True)
            result = await fetch_trace(TRACE_IDS["checkout_slow_1"])
            return result

        result = await ctx.run(_run)
        # Result is a BaseToolResponse (possibly dict after adk_tool normalization)
        if hasattr(result, "status"):
            assert result.status.value == "success" or str(result.status) == "success"
        elif isinstance(result, dict):
            assert result.get("status") == "success"

    @pytest.mark.asyncio
    async def test_list_alerts_in_guest_mode(self) -> None:
        """list_alerts should return synthetic alerts in guest mode."""
        from sre_agent.tools.clients.alerts import list_alerts

        ctx = contextvars.copy_context()

        async def _run() -> dict:
            set_guest_mode(True)
            return await list_alerts()

        result = await ctx.run(_run)
        if hasattr(result, "result"):
            alerts = result.result
        elif isinstance(result, dict):
            alerts = result.get("result", [])
        else:
            alerts = []
        assert isinstance(alerts, list)
        assert len(alerts) >= 3

    @pytest.mark.asyncio
    async def test_list_log_entries_in_guest_mode(self) -> None:
        """list_log_entries should return synthetic logs in guest mode."""
        from sre_agent.tools.clients.logging import list_log_entries

        ctx = contextvars.copy_context()

        async def _run() -> dict:
            set_guest_mode(True)
            return await list_log_entries(filter_str="severity>=ERROR")

        result = await ctx.run(_run)
        if hasattr(result, "result"):
            data = result.result
        elif isinstance(result, dict):
            data = result.get("result", {})
        else:
            data = {}
        assert "entries" in data
        assert len(data["entries"]) > 0
