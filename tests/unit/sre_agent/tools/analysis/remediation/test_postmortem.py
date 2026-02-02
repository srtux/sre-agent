"""Tests for the Automated Postmortem Generator.

Validates structured blameless postmortem generation:
- Severity assessment
- Duration calculation
- Action item generation
- Timeline handling
- Edge cases
"""

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.remediation.postmortem import (
    _assess_severity,
    _calculate_incident_duration,
    _format_duration,
    _generate_action_items,
    generate_postmortem,
)


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_seconds(self) -> None:
        assert _format_duration(0.5) == "30 seconds"

    def test_minutes(self) -> None:
        assert _format_duration(45) == "45 minutes"

    def test_hours_and_minutes(self) -> None:
        assert _format_duration(90) == "1h 30m"

    def test_days_and_hours(self) -> None:
        assert _format_duration(1500) == "1d 1h"


class TestCalculateIncidentDuration:
    """Tests for incident duration calculation."""

    def test_known_start_and_end(self) -> None:
        result = _calculate_incident_duration(
            "2024-06-15T14:00:00Z", "2024-06-15T14:45:00Z"
        )
        assert result["duration_minutes"] == 45.0
        assert result["is_ongoing"] is False

    def test_ongoing_incident(self) -> None:
        result = _calculate_incident_duration("2024-06-15T14:00:00Z", None)
        assert result["is_ongoing"] is True
        assert result["duration_minutes"] > 0

    def test_invalid_timestamps(self) -> None:
        result = _calculate_incident_duration("invalid", "also-invalid")
        assert result["duration_minutes"] == 0
        assert result["duration_human"] == "Unknown"


class TestAssessSeverity:
    """Tests for severity assessment logic."""

    def test_critical_revenue_impact(self) -> None:
        result = _assess_severity(revenue_impact=True)
        assert result["severity"] == "critical"
        assert any("Revenue" in f for f in result["factors"])

    def test_critical_high_user_impact(self) -> None:
        result = _assess_severity(user_impact_percent=80)
        assert result["severity"] == "critical"

    def test_high_moderate_user_impact(self) -> None:
        result = _assess_severity(user_impact_percent=25)
        assert result["severity"] == "high"

    def test_medium_low_user_impact(self) -> None:
        result = _assess_severity(user_impact_percent=5)
        assert result["severity"] == "medium"

    def test_critical_budget_consumption(self) -> None:
        result = _assess_severity(error_budget_consumed_percent=60)
        assert result["severity"] == "critical"

    def test_no_factors(self) -> None:
        result = _assess_severity()
        assert result["severity"] == "low"
        assert len(result["factors"]) > 0

    def test_combined_factors(self) -> None:
        result = _assess_severity(
            user_impact_percent=50,
            error_budget_consumed_percent=30,
            duration_minutes=300,
        )
        assert result["severity"] == "critical"
        assert len(result["factors"]) >= 2


class TestGenerateActionItems:
    """Tests for action item generation."""

    def test_always_includes_detection_improvement(self) -> None:
        items = _generate_action_items("unknown cause", [], "unknown")
        detection_items = [i for i in items if i["type"] == "detection"]
        assert len(detection_items) >= 1

    def test_always_includes_root_cause_fix(self) -> None:
        items = _generate_action_items("database overload", [], "unknown")
        fix_items = [i for i in items if i["type"] == "fix"]
        assert len(fix_items) >= 1

    def test_deployment_root_cause_adds_canary(self) -> None:
        items = _generate_action_items("Bad deployment caused outage", [], "deployment")
        process_items = [i for i in items if "canary" in i["action"].lower()]
        assert len(process_items) >= 1

    def test_capacity_root_cause_adds_load_testing(self) -> None:
        items = _generate_action_items(
            "OOM killed due to capacity", [], "infrastructure"
        )
        infra_items = [i for i in items if "capacity" in i["action"].lower()]
        assert len(infra_items) >= 1

    def test_always_includes_runbook_update(self) -> None:
        items = _generate_action_items("any cause", [], "unknown")
        doc_items = [i for i in items if i["type"] == "documentation"]
        assert len(doc_items) >= 1

    def test_contributing_factors_create_items(self) -> None:
        items = _generate_action_items(
            "root cause",
            ["factor 1", "factor 2"],
            "unknown",
        )
        improvement_items = [i for i in items if i["type"] == "improvement"]
        assert len(improvement_items) == 2


class TestGeneratePostmortem:
    """Tests for the main generate_postmortem tool."""

    @pytest.mark.asyncio
    async def test_basic_postmortem(self) -> None:
        """Should generate a complete postmortem with minimal inputs."""
        result = await generate_postmortem(
            title="Checkout latency spike",
            incident_start="2024-06-15T14:00:00Z",
            root_cause="Connection pool exhaustion",
            summary="Users experienced 5x latency for 45 minutes",
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert data["title"] == "Checkout latency spike"
        assert data["summary"] == "Users experienced 5x latency for 45 minutes"
        assert "action_items" in data
        assert len(data["action_items"]) > 0

    @pytest.mark.asyncio
    async def test_full_postmortem(self) -> None:
        """Should generate a complete postmortem with all inputs."""
        result = await generate_postmortem(
            title="Payment service outage",
            incident_start="2024-06-15T14:00:00Z",
            incident_end="2024-06-15T14:45:00Z",
            root_cause="Database migration broke schema compatibility",
            summary="Payment processing failed for 45 minutes",
            affected_services=["payment", "checkout", "order"],
            detection_method="Alert: payment_error_rate > 5%",
            detection_time="2024-06-15T14:05:00Z",
            mitigation_time="2024-06-15T14:30:00Z",
            user_impact_percent=30,
            error_budget_consumed_percent=8,
            revenue_impact=True,
            contributing_factors=[
                "No staging validation for schema changes",
                "Insufficient rollback testing",
            ],
            timeline_events=[
                {"time": "14:00", "event": "Deployment started"},
                {"time": "14:03", "event": "Error rate increased"},
                {"time": "14:05", "event": "Alert fired"},
            ],
            findings=[
                "Database connection errors in payment service",
                "Schema incompatibility with column rename",
            ],
            category="deployment",
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert data["severity"]["severity"] == "critical"
        assert data["incident_details"]["affected_services"] == [
            "payment",
            "checkout",
            "order",
        ]
        assert data["metrics"]["time_to_detect_minutes"] == 5.0
        assert data["metrics"]["time_to_mitigate_minutes"] == 25.0
        assert len(data["action_items"]) >= 4

    @pytest.mark.asyncio
    async def test_ongoing_incident_postmortem(self) -> None:
        """Should handle ongoing incidents without end time."""
        result = await generate_postmortem(
            title="Ongoing outage",
            incident_start="2024-06-15T14:00:00Z",
            root_cause="Under investigation",
            summary="Service is currently down",
        )
        assert result.status == ToolStatus.SUCCESS
        data = result.result
        assert data["status"] == "DRAFT"
        assert data["incident_details"]["duration"]["is_ongoing"] is True

    @pytest.mark.asyncio
    async def test_metadata_includes_severity(self) -> None:
        """Metadata should include severity level."""
        result = await generate_postmortem(
            title="Test",
            incident_start="2024-06-15T14:00:00Z",
            root_cause="Test",
            summary="Test",
            user_impact_percent=80,
        )
        assert result.metadata.get("severity") == "critical"

    @pytest.mark.asyncio
    async def test_lessons_learned_detection_slow(self) -> None:
        """Should flag slow detection in lessons learned."""
        result = await generate_postmortem(
            title="Test",
            incident_start="2024-06-15T14:00:00Z",
            incident_end="2024-06-15T15:00:00Z",
            root_cause="Test",
            summary="Test",
            detection_time="2024-06-15T14:30:00Z",
        )
        data = result.result
        poorly = data["lessons_learned"]["what_went_poorly"]
        assert any("Detection" in item for item in poorly)

    @pytest.mark.asyncio
    async def test_lessons_learned_user_detected(self) -> None:
        """Should flag user-detected incidents in lessons learned."""
        result = await generate_postmortem(
            title="Test",
            incident_start="2024-06-15T14:00:00Z",
            root_cause="Test",
            summary="Test",
            detection_method="user report",
        )
        data = result.result
        poorly = data["lessons_learned"]["what_went_poorly"]
        assert any("users" in item.lower() for item in poorly)
