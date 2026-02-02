"""Tests for the Change Correlation tool.

Validates the ability to find and rank recent changes that may have
caused an incident.
"""

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.correlation.change_correlation import (
    _build_audit_log_filter,
    _calculate_temporal_correlation,
    _classify_change,
    correlate_changes_with_incident,
)


class TestClassifyChange:
    """Tests for change classification logic."""

    def test_deployment_method(self) -> None:
        result = _classify_change(
            "google.cloud.run.v2.Services.UpdateService"
        )
        assert result["category"] == "deployment"
        assert result["risk"] == "high"

    def test_kubernetes_deployment(self) -> None:
        result = _classify_change("io.k8s.apps.v1.deployments.create")
        assert result["category"] == "deployment"

    def test_networking_change(self) -> None:
        result = _classify_change("google.compute.firewalls.insert")
        assert result["category"] == "networking"
        assert result["risk"] == "high"

    def test_unknown_create_method(self) -> None:
        result = _classify_change("some.api.CreateResource")
        assert result["category"] == "deployment"
        assert result["indicator"] == "unknown"

    def test_unknown_update_method(self) -> None:
        result = _classify_change("some.api.UpdateConfig")
        assert result["category"] == "configuration"

    def test_unknown_delete_method(self) -> None:
        result = _classify_change("some.api.DeleteResource")
        assert result["category"] == "infrastructure"
        assert result["risk"] == "high"

    def test_completely_unknown_method(self) -> None:
        result = _classify_change("some.api.DoSomething")
        assert result["category"] == "other"
        assert result["risk"] == "low"


class TestTemporalCorrelation:
    """Tests for temporal correlation scoring."""

    def test_very_strong_correlation(self) -> None:
        """Change 5 minutes before incident should score ~0.95."""
        result = _calculate_temporal_correlation(
            "2024-06-15T13:55:00Z",
            "2024-06-15T14:00:00Z",
            6.0,
        )
        assert result["correlation_score"] == 0.95
        assert result["minutes_before_incident"] == pytest.approx(5.0)

    def test_strong_correlation(self) -> None:
        """Change 30 minutes before incident should score ~0.8."""
        result = _calculate_temporal_correlation(
            "2024-06-15T13:30:00Z",
            "2024-06-15T14:00:00Z",
            6.0,
        )
        assert result["correlation_score"] == 0.8

    def test_moderate_correlation(self) -> None:
        """Change 3 hours before incident should score ~0.5."""
        result = _calculate_temporal_correlation(
            "2024-06-15T11:00:00Z",
            "2024-06-15T14:00:00Z",
            6.0,
        )
        assert result["correlation_score"] == 0.5

    def test_weak_correlation(self) -> None:
        """Change at edge of lookback should score low."""
        result = _calculate_temporal_correlation(
            "2024-06-15T08:00:00Z",
            "2024-06-15T14:00:00Z",
            6.0,
        )
        assert 0.0 < result["correlation_score"] < 0.5

    def test_change_after_incident(self) -> None:
        """Change after incident start should score very low."""
        result = _calculate_temporal_correlation(
            "2024-06-15T14:30:00Z",
            "2024-06-15T14:00:00Z",
            6.0,
        )
        assert result["correlation_score"] == 0.1
        assert "after incident" in result["assessment"].lower()

    def test_invalid_timestamps(self) -> None:
        """Invalid timestamps should return zero score."""
        result = _calculate_temporal_correlation("invalid", "also-invalid", 6.0)
        assert result["correlation_score"] == 0.0


class TestBuildAuditLogFilter:
    """Tests for audit log filter construction."""

    def test_basic_filter(self) -> None:
        filter_str = _build_audit_log_filter(
            "my-project",
            "2024-06-15T08:00:00Z",
            "2024-06-15T15:00:00Z",
        )
        assert "my-project" in filter_str
        assert "cloudaudit" in filter_str
        assert "2024-06-15T08:00:00Z" in filter_str

    def test_filter_with_service(self) -> None:
        filter_str = _build_audit_log_filter(
            "my-project",
            "2024-06-15T08:00:00Z",
            "2024-06-15T15:00:00Z",
            service_name="checkout-service",
        )
        assert "checkout-service" in filter_str


class TestCorrelateChangesWithIncident:
    """Tests for the main correlate_changes_with_incident tool."""

    @pytest.mark.asyncio
    async def test_returns_guidance_when_no_data(self) -> None:
        """Should return guidance when audit logs aren't available."""
        result = await correlate_changes_with_incident(
            project_id="test-project",
            incident_start="2024-06-15T14:00:00Z",
            lookback_hours=6.0,
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert data["changes_found"] == 0
        assert "guidance" in data
        assert "manual_checks" in data["guidance"]
        assert "gcloud_command" in data["guidance"]

    @pytest.mark.asyncio
    async def test_service_filter_passed(self) -> None:
        """Service filter should be included in results."""
        result = await correlate_changes_with_incident(
            project_id="test-project",
            incident_start="2024-06-15T14:00:00Z",
            service_name="my-service",
        )
        data = result.result
        assert data["service_filter"] == "my-service"

    @pytest.mark.asyncio
    async def test_metadata_includes_category(self) -> None:
        """Metadata should include tool category."""
        result = await correlate_changes_with_incident(
            project_id="test-project",
            incident_start="2024-06-15T14:00:00Z",
        )
        assert result.metadata.get("tool_category") == "change_correlation"
