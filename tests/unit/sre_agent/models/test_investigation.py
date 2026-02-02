"""Tests for the enhanced Investigation Model.

Validates the rich investigation state tracking including:
- Phase transitions with timeline recording
- Structured findings with confidence levels
- Investigation quality scoring
- Serialization round-trips
"""

import pytest

from sre_agent.models.investigation import (
    ConfidenceLevel,
    InvestigationFinding,
    InvestigationPhase,
    InvestigationState,
    InvestigationTimeline,
    PHASE_INSTRUCTIONS,
)


class TestInvestigationPhase:
    """Tests for the InvestigationPhase enum."""

    def test_all_phases_defined(self) -> None:
        assert len(InvestigationPhase) == 5
        assert InvestigationPhase.TRIAGE.value == "triage"
        assert InvestigationPhase.COMPLETED.value == "completed"

    def test_phase_instructions_cover_all_non_completed(self) -> None:
        """Phase instructions should exist for all active phases."""
        for phase in InvestigationPhase:
            if phase != InvestigationPhase.COMPLETED:
                assert phase in PHASE_INSTRUCTIONS


class TestInvestigationFinding:
    """Tests for the InvestigationFinding model."""

    def test_create_finding(self) -> None:
        finding = InvestigationFinding(
            description="High latency on service X",
            source_tool="fetch_trace",
            confidence=ConfidenceLevel.HIGH,
            signal_type="trace",
            severity="high",
        )
        assert finding.description == "High latency on service X"
        assert finding.confidence == ConfidenceLevel.HIGH

    def test_finding_defaults(self) -> None:
        finding = InvestigationFinding(description="Test finding")
        assert finding.source_tool == "unknown"
        assert finding.confidence == ConfidenceLevel.MEDIUM
        assert finding.signal_type == "unknown"
        assert finding.timestamp  # Should have a default timestamp

    def test_finding_is_frozen(self) -> None:
        finding = InvestigationFinding(description="Test")
        with pytest.raises(Exception):
            finding.description = "Modified"  # type: ignore[misc]


class TestInvestigationTimeline:
    """Tests for the InvestigationTimeline model."""

    def test_create_timeline_entry(self) -> None:
        entry = InvestigationTimeline(
            timestamp="2024-06-15T14:00:00Z",
            event="Investigation started",
            phase="triage",
        )
        assert entry.event == "Investigation started"
        assert entry.phase == "triage"


class TestInvestigationState:
    """Tests for the enhanced InvestigationState model."""

    def test_default_state(self) -> None:
        state = InvestigationState()
        assert state.phase == InvestigationPhase.TRIAGE
        assert len(state.findings) == 0
        assert len(state.structured_findings) == 0
        assert len(state.affected_services) == 0
        assert state.investigation_score == 0.0

    def test_add_finding(self) -> None:
        state = InvestigationState()
        state.add_finding(
            description="Connection pool exhaustion detected",
            source_tool="detect_connection_pool_issues",
            confidence="high",
            signal_type="trace",
            severity="critical",
        )
        assert len(state.structured_findings) == 1
        assert len(state.findings) == 1
        assert state.structured_findings[0]["description"] == "Connection pool exhaustion detected"
        assert state.structured_findings[0]["confidence"] == "high"

    def test_add_finding_deduplicates_flat_list(self) -> None:
        state = InvestigationState()
        state.add_finding(description="Finding A")
        state.add_finding(description="Finding A")  # Duplicate
        assert len(state.findings) == 1
        assert len(state.structured_findings) == 2  # Structured keeps all

    def test_add_timeline_event(self) -> None:
        state = InvestigationState()
        state.add_timeline_event("Started triage")
        assert len(state.timeline) == 1
        assert state.timeline[0]["event"] == "Started triage"
        assert state.timeline[0]["phase"] == "triage"

    def test_transition_phase(self) -> None:
        state = InvestigationState()
        state.transition_phase(InvestigationPhase.ANALYSIS)
        assert state.phase == InvestigationPhase.ANALYSIS
        assert len(state.timeline) == 1
        assert "triage -> analysis" in state.timeline[0]["event"]

    def test_add_affected_service(self) -> None:
        state = InvestigationState()
        state.add_affected_service("checkout")
        state.add_affected_service("payment")
        state.add_affected_service("checkout")  # Duplicate
        assert len(state.affected_services) == 2

    def test_mark_signal_analyzed(self) -> None:
        state = InvestigationState()
        state.mark_signal_analyzed("trace")
        state.mark_signal_analyzed("log")
        state.mark_signal_analyzed("trace")  # Duplicate
        assert len(state.signals_analyzed) == 2

    def test_calculate_score_empty(self) -> None:
        state = InvestigationState()
        score = state.calculate_score()
        assert score == 0.0

    def test_calculate_score_full_investigation(self) -> None:
        state = InvestigationState()
        # Analyze multiple signals
        for signal in ["trace", "log", "metric", "alert", "change"]:
            state.mark_signal_analyzed(signal)
        # Add findings
        for i in range(5):
            state.add_finding(f"Finding {i}")
        # Set root cause and fix
        state.confirmed_root_cause = "Database overload"
        state.suggested_fix = "Increase connection pool"
        # Progress phases
        state.transition_phase(InvestigationPhase.REMEDIATION)
        # Add timeline events
        for _ in range(5):
            state.add_timeline_event("Event")

        score = state.calculate_score()
        assert score >= 80.0  # Should be high for a complete investigation

    def test_calculate_score_partial_investigation(self) -> None:
        state = InvestigationState()
        state.mark_signal_analyzed("trace")
        state.add_finding("One finding")
        score = state.calculate_score()
        assert 0 < score < 50

    def test_to_dict_includes_all_fields(self) -> None:
        state = InvestigationState()
        state.add_finding("Test finding", source_tool="test_tool")
        state.add_affected_service("my-service")
        state.incident_start = "2024-06-15T14:00:00Z"

        data = state.to_dict()
        assert "structured_findings" in data
        assert "affected_services" in data
        assert "incident_start" in data
        assert "investigation_score" in data
        assert "signals_analyzed" in data

    def test_from_dict_round_trip(self) -> None:
        state = InvestigationState()
        state.add_finding(
            "Test finding",
            source_tool="test_tool",
            confidence="high",
        )
        state.add_affected_service("my-service")
        state.incident_start = "2024-06-15T14:00:00Z"
        state.severity = "high"
        state.transition_phase(InvestigationPhase.ANALYSIS)

        # Serialize and deserialize
        data = state.to_dict()
        restored = InvestigationState.from_dict(data)

        assert restored.phase == InvestigationPhase.ANALYSIS
        assert len(restored.structured_findings) == 1
        assert restored.affected_services == ["my-service"]
        assert restored.incident_start == "2024-06-15T14:00:00Z"
        assert restored.severity == "high"

    def test_from_dict_handles_none(self) -> None:
        state = InvestigationState.from_dict(None)
        assert state.phase == InvestigationPhase.TRIAGE

    def test_from_dict_handles_empty(self) -> None:
        state = InvestigationState.from_dict({})
        assert state.phase == InvestigationPhase.TRIAGE

    def test_from_dict_handles_invalid_data(self) -> None:
        state = InvestigationState.from_dict({"phase": "invalid_phase"})
        assert state.phase == InvestigationPhase.TRIAGE

    def test_backward_compatibility(self) -> None:
        """Old-format data without new fields should still work."""
        old_data = {
            "phase": "analysis",
            "findings": ["old finding"],
            "hypotheses": ["old hypothesis"],
            "confirmed_root_cause": "old cause",
            "suggested_fix": "old fix",
        }
        state = InvestigationState.from_dict(old_data)
        assert state.phase == InvestigationPhase.ANALYSIS
        assert state.findings == ["old finding"]
        assert state.confirmed_root_cause == "old cause"
        # New fields should have defaults
        assert state.structured_findings == []
        assert state.affected_services == []
