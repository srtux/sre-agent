"""Tests for explore_project_health tool."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.exploration.explore_health import (
    _compute_health_summary,
    _safe_result,
    explore_project_health,
)
from sre_agent.tools.synthetic.provider import SyntheticDataProvider

# ---------------------------------------------------------------------------
# Synthetic / Guest-mode tests
# ---------------------------------------------------------------------------


class TestSyntheticExploreProjectHealth:
    """Tests for the synthetic (guest mode) code path."""

    def test_returns_success(self) -> None:
        result = SyntheticDataProvider.explore_project_health()
        assert result.status == ToolStatus.SUCCESS
        assert result.result is not None

    def test_result_has_all_signal_keys(self) -> None:
        result = SyntheticDataProvider.explore_project_health()
        data = result.result
        assert isinstance(data, dict)
        for key in ("alerts", "logs", "traces", "metrics", "summary"):
            assert key in data, f"Missing key: {key}"

    def test_result_has_project_id(self) -> None:
        result = SyntheticDataProvider.explore_project_health(project_id="my-proj")
        assert result.result["project_id"] == "my-proj"

    def test_summary_structure(self) -> None:
        result = SyntheticDataProvider.explore_project_health()
        summary = result.result["summary"]
        for field in (
            "total_alerts",
            "open_alerts",
            "error_log_count",
            "warning_log_count",
            "trace_count",
            "has_issues",
            "health_status",
        ):
            assert field in summary, f"Missing summary field: {field}"

    def test_health_status_is_valid(self) -> None:
        result = SyntheticDataProvider.explore_project_health()
        assert result.result["summary"]["health_status"] in (
            "healthy",
            "degraded",
            "critical",
        )

    def test_alerts_is_list(self) -> None:
        result = SyntheticDataProvider.explore_project_health()
        assert isinstance(result.result["alerts"], list)

    def test_traces_is_list(self) -> None:
        result = SyntheticDataProvider.explore_project_health()
        assert isinstance(result.result["traces"], list)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestComputeHealthSummary:
    """Tests for _compute_health_summary."""

    def _make_resp(
        self,
        status: ToolStatus = ToolStatus.SUCCESS,
        result: Any = None,
    ) -> BaseToolResponse:
        return BaseToolResponse(status=status, result=result)

    def test_all_empty_is_healthy(self) -> None:
        summary = _compute_health_summary(
            alerts_result=self._make_resp(result=[]),
            logs_result=self._make_resp(result={"entries": []}),
            traces_result=self._make_resp(result=[]),
            metrics_result=self._make_resp(result=[]),
        )
        assert summary["health_status"] == "healthy"
        assert summary["has_issues"] is False
        assert summary["total_alerts"] == 0

    def test_open_alerts_cause_degraded(self) -> None:
        alerts = [{"name": "a1", "state": "OPEN"}]
        summary = _compute_health_summary(
            alerts_result=self._make_resp(result=alerts),
            logs_result=self._make_resp(result={"entries": []}),
            traces_result=self._make_resp(result=[]),
            metrics_result=self._make_resp(result=[]),
        )
        assert summary["health_status"] == "degraded"
        assert summary["has_issues"] is True
        assert summary["open_alerts"] == 1

    def test_many_open_alerts_cause_critical(self) -> None:
        alerts = [{"name": f"a{i}", "state": "OPEN"} for i in range(5)]
        summary = _compute_health_summary(
            alerts_result=self._make_resp(result=alerts),
            logs_result=self._make_resp(result={"entries": []}),
            traces_result=self._make_resp(result=[]),
            metrics_result=self._make_resp(result=[]),
        )
        assert summary["health_status"] == "critical"

    def test_error_logs_counted(self) -> None:
        entries = [
            {"severity": "ERROR", "payload": "e1"},
            {"severity": "WARNING", "payload": "w1"},
            {"severity": "CRITICAL", "payload": "c1"},
        ]
        summary = _compute_health_summary(
            alerts_result=self._make_resp(result=[]),
            logs_result=self._make_resp(result={"entries": entries}),
            traces_result=self._make_resp(result=[]),
            metrics_result=self._make_resp(result=[]),
        )
        assert summary["error_log_count"] == 2  # ERROR + CRITICAL
        assert summary["warning_log_count"] == 1

    def test_many_error_logs_cause_critical(self) -> None:
        entries = [{"severity": "ERROR", "payload": f"e{i}"} for i in range(12)]
        summary = _compute_health_summary(
            alerts_result=self._make_resp(result=[]),
            logs_result=self._make_resp(result={"entries": entries}),
            traces_result=self._make_resp(result=[]),
            metrics_result=self._make_resp(result=[]),
        )
        assert summary["health_status"] == "critical"

    def test_trace_count(self) -> None:
        traces = [{"trace_id": f"t{i}"} for i in range(5)]
        summary = _compute_health_summary(
            alerts_result=self._make_resp(result=[]),
            logs_result=self._make_resp(result={"entries": []}),
            traces_result=self._make_resp(result=traces),
            metrics_result=self._make_resp(result=[]),
        )
        assert summary["trace_count"] == 5

    def test_error_result_treated_as_empty(self) -> None:
        summary = _compute_health_summary(
            alerts_result=self._make_resp(status=ToolStatus.ERROR, result=None),
            logs_result=self._make_resp(status=ToolStatus.ERROR, result=None),
            traces_result=self._make_resp(status=ToolStatus.ERROR, result=None),
            metrics_result=self._make_resp(status=ToolStatus.ERROR, result=None),
        )
        assert summary["health_status"] == "healthy"
        assert summary["total_alerts"] == 0


class TestSafeResult:
    """Tests for _safe_result."""

    def test_passes_through_response(self) -> None:
        resp = BaseToolResponse(status=ToolStatus.SUCCESS, result={"x": 1})
        assert _safe_result(resp) is resp

    def test_converts_exception_to_error(self) -> None:
        exc = RuntimeError("boom")
        resp = _safe_result(exc)
        assert resp.status == ToolStatus.ERROR
        assert "boom" in (resp.error or "")


# ---------------------------------------------------------------------------
# Tool function tests (guest mode integration)
# ---------------------------------------------------------------------------


class TestExploreProjectHealthTool:
    """Tests for the @adk_tool decorated function."""

    @pytest.mark.asyncio
    @patch("sre_agent.auth.is_guest_mode", return_value=True)
    async def test_guest_mode_returns_success(self, _mock_guest: Any) -> None:
        result = await explore_project_health(project_id="test-proj")
        assert result.status == ToolStatus.SUCCESS
        assert "summary" in result.result

    @pytest.mark.asyncio
    @patch("sre_agent.auth.is_guest_mode", return_value=False)
    @patch(
        "sre_agent.auth.get_current_project_id",
        return_value=None,
    )
    async def test_missing_project_id_returns_error(
        self, _mock_pid: Any, _mock_guest: Any
    ) -> None:
        result = await explore_project_health(project_id=None)
        assert result.status == ToolStatus.ERROR
        assert "Project ID" in (result.error or "")

    @pytest.mark.asyncio
    @patch("sre_agent.auth.is_guest_mode", return_value=False)
    @patch(
        "sre_agent.auth.get_current_project_id",
        return_value="my-project",
    )
    async def test_partial_failure_still_succeeds(
        self, _mock_pid: Any, _mock_guest: Any
    ) -> None:
        """One sub-query raising an exception should not fail the whole scan."""
        ok_resp = BaseToolResponse(status=ToolStatus.SUCCESS, result=[])

        with (
            patch(
                "sre_agent.tools.clients.alerts.list_alerts",
                new_callable=AsyncMock,
                side_effect=RuntimeError("alerts down"),
            ),
            patch(
                "sre_agent.tools.clients.logging.list_log_entries",
                new_callable=AsyncMock,
                return_value=ok_resp,
            ),
            patch(
                "sre_agent.tools.clients.trace.list_traces",
                new_callable=AsyncMock,
                return_value=ok_resp,
            ),
            patch(
                "sre_agent.tools.clients.monitoring.list_time_series",
                new_callable=AsyncMock,
                return_value=ok_resp,
            ),
        ):
            result = await explore_project_health(project_id="my-project")
            assert result.status == ToolStatus.SUCCESS
            assert result.result["summary"]["health_status"] == "healthy"

    @pytest.mark.asyncio
    @patch("sre_agent.auth.is_guest_mode", return_value=False)
    @patch(
        "sre_agent.auth.get_current_project_id",
        return_value="my-project",
    )
    async def test_happy_path_with_data(self, _mock_pid: Any, _mock_guest: Any) -> None:
        alerts_resp = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=[{"name": "a1", "state": "OPEN"}],
        )
        logs_resp = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"entries": [{"severity": "ERROR", "payload": "bad"}]},
        )
        traces_resp = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=[{"trace_id": "t1"}],
        )
        metrics_resp = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=[{"metric": "m1"}],
        )

        with (
            patch(
                "sre_agent.tools.clients.alerts.list_alerts",
                new_callable=AsyncMock,
                return_value=alerts_resp,
            ),
            patch(
                "sre_agent.tools.clients.logging.list_log_entries",
                new_callable=AsyncMock,
                return_value=logs_resp,
            ),
            patch(
                "sre_agent.tools.clients.trace.list_traces",
                new_callable=AsyncMock,
                return_value=traces_resp,
            ),
            patch(
                "sre_agent.tools.clients.monitoring.list_time_series",
                new_callable=AsyncMock,
                return_value=metrics_resp,
            ),
        ):
            result = await explore_project_health(project_id="my-project")
            assert result.status == ToolStatus.SUCCESS
            data = result.result
            assert data["project_id"] == "my-project"
            assert data["summary"]["open_alerts"] == 1
            assert data["summary"]["error_log_count"] == 1
            assert data["summary"]["trace_count"] == 1
            assert data["summary"]["health_status"] == "degraded"
