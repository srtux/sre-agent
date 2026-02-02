"""Unit tests for InvestigationState and InvestigationPhase models.

Goal: Verify investigation state management, phase transitions,
serialization/deserialization, and edge cases.
"""

from typing import Any

import pytest

from sre_agent.models.investigation import (
    PHASE_INSTRUCTIONS,
    InvestigationPhase,
    InvestigationState,
)


class TestInvestigationPhase:
    """Tests for the InvestigationPhase enum."""

    def test_all_phases_exist(self) -> None:
        """All expected investigation phases are defined."""
        expected = {"TRIAGE", "ANALYSIS", "ROOT_CAUSE", "REMEDIATION", "COMPLETED"}
        actual = {phase.name for phase in InvestigationPhase}
        assert actual == expected

    def test_phase_values_are_lowercase(self) -> None:
        """Phase values are lowercase strings."""
        for phase in InvestigationPhase:
            assert phase.value == phase.name.lower()

    def test_phase_is_str_enum(self) -> None:
        """Phases can be used as strings."""
        assert InvestigationPhase.TRIAGE == "triage"
        assert str(InvestigationPhase.ANALYSIS) == "InvestigationPhase.ANALYSIS"

    def test_phase_from_value(self) -> None:
        """Phases can be constructed from string values."""
        assert InvestigationPhase("triage") == InvestigationPhase.TRIAGE
        assert InvestigationPhase("root_cause") == InvestigationPhase.ROOT_CAUSE

    def test_invalid_phase_raises(self) -> None:
        """Invalid phase value raises ValueError."""
        with pytest.raises(ValueError):
            InvestigationPhase("invalid_phase")


class TestInvestigationState:
    """Tests for the InvestigationState model."""

    def test_default_state(self) -> None:
        """Default state starts at TRIAGE with empty collections."""
        state = InvestigationState()
        assert state.phase == InvestigationPhase.TRIAGE
        assert state.findings == []
        assert state.hypotheses == []
        assert state.confirmed_root_cause is None
        assert state.suggested_fix is None

    def test_custom_state(self) -> None:
        """State can be created with custom values."""
        state = InvestigationState(
            phase=InvestigationPhase.ROOT_CAUSE,
            findings=["High error rate in service-a"],
            hypotheses=["Database connection pool exhausted"],
            confirmed_root_cause="Connection pool limit reached",
            suggested_fix="Increase max_connections to 200",
        )
        assert state.phase == InvestigationPhase.ROOT_CAUSE
        assert len(state.findings) == 1
        assert state.confirmed_root_cause == "Connection pool limit reached"

    def test_to_dict_roundtrip(self) -> None:
        """to_dict and from_dict are inverse operations."""
        original = InvestigationState(
            phase=InvestigationPhase.ANALYSIS,
            findings=["Latency spike at 14:00", "Error rate 5x baseline"],
            hypotheses=["Upstream dependency failure"],
            confirmed_root_cause=None,
            suggested_fix=None,
        )
        data = original.to_dict()
        restored = InvestigationState.from_dict(data)

        assert restored.phase == original.phase
        assert restored.findings == original.findings
        assert restored.hypotheses == original.hypotheses
        assert restored.confirmed_root_cause == original.confirmed_root_cause
        assert restored.suggested_fix == original.suggested_fix

    def test_to_dict_structure(self) -> None:
        """to_dict returns expected key structure."""
        state = InvestigationState(
            phase=InvestigationPhase.REMEDIATION,
            findings=["finding-1"],
            hypotheses=["hypothesis-1"],
            confirmed_root_cause="root cause",
            suggested_fix="fix it",
        )
        data = state.to_dict()
        assert data == {
            "phase": "remediation",
            "findings": ["finding-1"],
            "hypotheses": ["hypothesis-1"],
            "confirmed_root_cause": "root cause",
            "suggested_fix": "fix it",
            "structured_findings": [],
            "affected_services": [],
            "timeline": [],
            "incident_start": None,
            "incident_end": None,
            "severity": "unknown",
            "investigation_score": 0.0,
            "signals_analyzed": [],
            "changes_correlated": [],
            "slo_impact": {},
        }

    def test_from_dict_with_none(self) -> None:
        """from_dict with None returns default state."""
        state = InvestigationState.from_dict(None)
        assert state.phase == InvestigationPhase.TRIAGE
        assert state.findings == []

    def test_from_dict_with_empty_dict(self) -> None:
        """from_dict with empty dict returns default state."""
        state = InvestigationState.from_dict({})
        assert state.phase == InvestigationPhase.TRIAGE

    def test_from_dict_with_partial_data(self) -> None:
        """from_dict handles partial data gracefully."""
        data: dict[str, Any] = {"phase": "analysis", "findings": ["partial finding"]}
        state = InvestigationState.from_dict(data)
        assert state.phase == InvestigationPhase.ANALYSIS
        assert state.findings == ["partial finding"]
        assert state.hypotheses == []
        assert state.confirmed_root_cause is None

    def test_from_dict_with_invalid_phase(self) -> None:
        """from_dict with invalid phase falls back to default."""
        data: dict[str, Any] = {"phase": "not_a_real_phase"}
        state = InvestigationState.from_dict(data)
        assert state.phase == InvestigationPhase.TRIAGE

    def test_from_dict_with_corrupt_data(self) -> None:
        """from_dict with corrupt data falls back to default."""
        data: dict[str, Any] = {"phase": 12345, "findings": "not-a-list"}
        state = InvestigationState.from_dict(data)
        # Should return default state on error
        assert state.phase == InvestigationPhase.TRIAGE

    def test_all_phases_complete(self) -> None:
        """State can transition through all phases."""
        phases = [
            InvestigationPhase.TRIAGE,
            InvestigationPhase.ANALYSIS,
            InvestigationPhase.ROOT_CAUSE,
            InvestigationPhase.REMEDIATION,
            InvestigationPhase.COMPLETED,
        ]
        for phase in phases:
            state = InvestigationState(phase=phase)
            data = state.to_dict()
            restored = InvestigationState.from_dict(data)
            assert restored.phase == phase


class TestPhaseInstructions:
    """Tests for the PHASE_INSTRUCTIONS mapping."""

    def test_all_non_completed_phases_have_instructions(self) -> None:
        """Every non-COMPLETED phase has an instruction string."""
        for phase in InvestigationPhase:
            if phase != InvestigationPhase.COMPLETED:
                assert phase in PHASE_INSTRUCTIONS
                assert len(PHASE_INSTRUCTIONS[phase]) > 0

    def test_triage_instructions_mention_signals(self) -> None:
        """Triage instructions mention gathering signals."""
        instruction = PHASE_INSTRUCTIONS[InvestigationPhase.TRIAGE]
        assert "signal" in instruction.lower() or "trace" in instruction.lower()

    def test_remediation_instructions_mention_fix(self) -> None:
        """Remediation instructions mention actionable fixes."""
        instruction = PHASE_INSTRUCTIONS[InvestigationPhase.REMEDIATION]
        assert "fix" in instruction.lower() or "suggest" in instruction.lower()
