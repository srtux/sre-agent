"""Tests for the Multi-Window SLO Burn Rate Analyzer.

Validates Google's multi-window, multi-burn-rate alerting strategy:
- Correct burn rate calculation
- Error budget status computation
- Multi-window alert triggering
- Both per-window and single-rate modes
"""

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.slo.burn_rate import (
    _calculate_burn_rate,
    _calculate_error_budget_status,
    analyze_multi_window_burn_rate,
)


class TestBurnRateCalculation:
    """Tests for the burn rate formula."""

    def test_zero_errors_zero_burn(self) -> None:
        """Zero errors should produce zero burn rate."""
        rate = _calculate_burn_rate(0, 1000, 0.999)
        assert rate == 0.0

    def test_at_slo_limit(self) -> None:
        """Error rate exactly at SLO limit should give burn rate of 1.0."""
        # SLO = 99.9%, so max error rate = 0.1%
        # 1 error in 1000 requests = 0.1% error rate = burn rate 1.0
        rate = _calculate_burn_rate(1, 1000, 0.999)
        assert rate == pytest.approx(1.0)

    def test_double_slo_limit(self) -> None:
        """Double the SLO error rate should give burn rate of 2.0."""
        rate = _calculate_burn_rate(2, 1000, 0.999)
        assert rate == pytest.approx(2.0)

    def test_fast_burn_rate(self) -> None:
        """14.4x burn rate (Google's page threshold for 1h window)."""
        # 14.4 errors per 1000 with SLO 99.9%
        rate = _calculate_burn_rate(144, 10000, 0.999)
        assert rate == pytest.approx(14.4)

    def test_zero_total_count(self) -> None:
        """Zero total count should return 0 burn rate."""
        rate = _calculate_burn_rate(0, 0, 0.999)
        assert rate == 0.0

    def test_perfect_slo_target(self) -> None:
        """SLO target of 1.0 (100%) with errors should return infinity."""
        rate = _calculate_burn_rate(1, 1000, 1.0)
        assert rate == float("inf")


class TestErrorBudgetStatus:
    """Tests for error budget status computation."""

    def test_healthy_status(self) -> None:
        """Low burn rate should produce HEALTHY status."""
        status = _calculate_error_budget_status(0.5, 0.999, 30)
        assert status["status"] == "HEALTHY"
        assert status["projected_exhaustion_hours"] is not None

    def test_critical_status(self) -> None:
        """Very high burn rate should produce CRITICAL status."""
        status = _calculate_error_budget_status(100.0, 0.999, 30)
        assert status["status"] == "CRITICAL"

    def test_warning_status(self) -> None:
        """Moderate burn rate should produce WARNING status."""
        # burn_rate = 15 -> 30*24/15 = 48 hours to exhaustion -> WARNING
        status = _calculate_error_budget_status(15.0, 0.999, 30)
        assert status["status"] == "WARNING"

    def test_zero_burn_rate(self) -> None:
        """Zero burn rate should be HEALTHY with no exhaustion projection."""
        status = _calculate_error_budget_status(0.0, 0.999, 30)
        assert status["status"] == "HEALTHY"
        assert status["projected_exhaustion_hours"] is None

    def test_budget_total_minutes(self) -> None:
        """Error budget total should be calculated correctly."""
        # 30 days * 24h * 60m * (1 - 0.999) = 43.2 minutes
        status = _calculate_error_budget_status(1.0, 0.999, 30)
        assert status["budget_total_minutes"] == pytest.approx(43.2)


class TestAnalyzeMultiWindowBurnRate:
    """Tests for the main analyze_multi_window_burn_rate tool."""

    @pytest.mark.asyncio
    async def test_single_error_rate_mode(self) -> None:
        """Tool should work with a single error rate."""
        result = await analyze_multi_window_burn_rate(
            slo_target=0.999,
            current_error_rate=0.001,
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.result is not None
        data = result.result
        assert data["slo_target"] == 0.999
        assert data["overall_severity"] in ("OK", "WARNING", "CRITICAL")
        assert "window_analysis" in data
        assert "error_budget" in data

    @pytest.mark.asyncio
    async def test_high_error_rate_triggers_page(self) -> None:
        """Very high error rate should trigger PAGE alerts."""
        # burn rate = 0.02 / 0.001 = 20x (exceeds 14.4x page threshold)
        result = await analyze_multi_window_burn_rate(
            slo_target=0.999,
            current_error_rate=0.02,
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert data["overall_severity"] == "CRITICAL"
        assert data["overall_action"] == "PAGE"
        assert len(data["alerts_triggered"]) > 0

    @pytest.mark.asyncio
    async def test_low_error_rate_no_alerts(self) -> None:
        """Low error rate should not trigger any alerts."""
        # burn rate = 0.0001 / 0.001 = 0.1x (well below any threshold)
        result = await analyze_multi_window_burn_rate(
            slo_target=0.999,
            current_error_rate=0.0001,
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert data["overall_severity"] == "OK"
        assert data["overall_action"] == "NONE"
        assert len(data["alerts_triggered"]) == 0

    @pytest.mark.asyncio
    async def test_per_window_mode(self) -> None:
        """Tool should work with per-window error counts."""
        result = await analyze_multi_window_burn_rate(
            slo_target=0.999,
            error_counts_by_window={
                "1h": 10,
                "6h": 50,
                "24h": 100,
                "72h": 200,
                "5m": 2,
                "30m": 5,
                "2h": 15,
            },
            total_counts_by_window={
                "1h": 100000,
                "6h": 600000,
                "24h": 2400000,
                "72h": 7200000,
                "5m": 8000,
                "30m": 50000,
                "2h": 200000,
            },
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert "window_analysis" in data
        assert len(data["window_analysis"]) == 4  # 4 windows

    @pytest.mark.asyncio
    async def test_invalid_slo_target(self) -> None:
        """Invalid SLO target should return error."""
        result = await analyze_multi_window_burn_rate(
            slo_target=1.5,
            current_error_rate=0.001,
        )
        assert result.status == ToolStatus.ERROR
        assert "Invalid SLO target" in str(result.error)

    @pytest.mark.asyncio
    async def test_no_data_provided(self) -> None:
        """No error data should return error."""
        result = await analyze_multi_window_burn_rate(
            slo_target=0.999,
        )
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_metadata_includes_category(self) -> None:
        """Metadata should include tool category."""
        result = await analyze_multi_window_burn_rate(
            slo_target=0.999,
            current_error_rate=0.001,
        )
        assert result.metadata.get("tool_category") == "slo_analysis"

    @pytest.mark.asyncio
    async def test_summary_text_present(self) -> None:
        """Result should include a human-readable summary."""
        result = await analyze_multi_window_burn_rate(
            slo_target=0.999,
            current_error_rate=0.001,
        )
        assert "summary" in result.result
