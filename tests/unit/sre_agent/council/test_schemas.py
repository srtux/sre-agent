"""Tests for council schema validation.

Validates Pydantic models for investigation modes, panel findings,
critic reports, council results, and council configuration.
"""

import pytest
from pydantic import ValidationError

from sre_agent.council.schemas import (
    CouncilConfig,
    CouncilResult,
    CriticReport,
    InvestigationMode,
    PanelFinding,
    PanelSeverity,
)


class TestInvestigationMode:
    """Tests for InvestigationMode enum."""

    def test_all_modes_exist(self) -> None:
        """All three investigation modes should be defined."""
        assert InvestigationMode.FAST == "fast"
        assert InvestigationMode.STANDARD == "standard"
        assert InvestigationMode.DEBATE == "debate"

    def test_mode_from_string(self) -> None:
        """Modes should be constructable from string values."""
        assert InvestigationMode("fast") == InvestigationMode.FAST
        assert InvestigationMode("standard") == InvestigationMode.STANDARD
        assert InvestigationMode("debate") == InvestigationMode.DEBATE

    def test_invalid_mode_raises(self) -> None:
        """Invalid mode string should raise ValueError."""
        with pytest.raises(ValueError):
            InvestigationMode("invalid")


class TestPanelSeverity:
    """Tests for PanelSeverity enum."""

    def test_all_severities_exist(self) -> None:
        """All four severity levels should be defined."""
        assert PanelSeverity.CRITICAL == "critical"
        assert PanelSeverity.WARNING == "warning"
        assert PanelSeverity.INFO == "info"
        assert PanelSeverity.HEALTHY == "healthy"


class TestPanelFinding:
    """Tests for PanelFinding model."""

    def test_valid_finding(self) -> None:
        """A valid PanelFinding should be constructable."""
        finding = PanelFinding(
            panel="trace",
            summary="High latency in checkout service",
            severity=PanelSeverity.WARNING,
            confidence=0.85,
            evidence=["trace-id-123: 500ms", "p99 latency spike at 14:00"],
            recommended_actions=["Scale checkout-service pods"],
        )
        assert finding.panel == "trace"
        assert finding.confidence == 0.85
        assert len(finding.evidence) == 2

    def test_finding_with_defaults(self) -> None:
        """PanelFinding should work with default lists."""
        finding = PanelFinding(
            panel="metrics",
            summary="All metrics within normal range",
            severity=PanelSeverity.HEALTHY,
            confidence=0.95,
        )
        assert finding.evidence == []
        assert finding.recommended_actions == []

    def test_frozen_model(self) -> None:
        """PanelFinding should be immutable."""
        finding = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.INFO,
            confidence=0.5,
        )
        with pytest.raises(ValidationError):
            finding.panel = "metrics"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity=PanelSeverity.INFO,
                confidence=0.5,
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_confidence_out_of_range(self) -> None:
        """Confidence outside 0.0-1.0 should be rejected."""
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity=PanelSeverity.INFO,
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity=PanelSeverity.INFO,
                confidence=-0.1,
            )

    def test_confidence_boundary_values(self) -> None:
        """Confidence at boundaries should be accepted."""
        low = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.INFO,
            confidence=0.0,
        )
        high = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.INFO,
            confidence=1.0,
        )
        assert low.confidence == 0.0
        assert high.confidence == 1.0

    def test_invalid_severity_rejected(self) -> None:
        """Invalid severity string should be rejected."""
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity="unknown",  # type: ignore[arg-type]
                confidence=0.5,
            )


class TestCriticReport:
    """Tests for CriticReport model."""

    def test_valid_report(self) -> None:
        """A valid CriticReport should be constructable."""
        report = CriticReport(
            agreements=["Both trace and metrics show latency spike at 14:00"],
            contradictions=["Trace says healthy but logs show errors"],
            gaps=["No alert data analyzed"],
            revised_confidence=0.72,
        )
        assert len(report.agreements) == 1
        assert len(report.contradictions) == 1
        assert report.revised_confidence == 0.72

    def test_report_with_defaults(self) -> None:
        """CriticReport should work with default lists."""
        report = CriticReport(revised_confidence=0.9)
        assert report.agreements == []
        assert report.contradictions == []
        assert report.gaps == []

    def test_frozen_model(self) -> None:
        """CriticReport should be immutable."""
        report = CriticReport(revised_confidence=0.8)
        with pytest.raises(ValidationError):
            report.revised_confidence = 0.9  # type: ignore[misc]


class TestCouncilResult:
    """Tests for CouncilResult model."""

    def test_valid_result(self) -> None:
        """A full CouncilResult should be constructable."""
        finding = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.WARNING,
            confidence=0.8,
        )
        critic = CriticReport(revised_confidence=0.75)
        result = CouncilResult(
            mode=InvestigationMode.DEBATE,
            panels=[finding],
            critic_report=critic,
            synthesis="Checkout service experiencing latency issues",
            overall_severity=PanelSeverity.WARNING,
            overall_confidence=0.75,
            rounds=2,
        )
        assert result.mode == InvestigationMode.DEBATE
        assert len(result.panels) == 1
        assert result.critic_report is not None
        assert result.rounds == 2

    def test_result_with_defaults(self) -> None:
        """CouncilResult should work with defaults for FAST mode."""
        result = CouncilResult(
            mode=InvestigationMode.FAST,
            synthesis="All healthy",
            overall_confidence=0.95,
        )
        assert result.panels == []
        assert result.critic_report is None
        assert result.overall_severity == PanelSeverity.INFO
        assert result.rounds == 1

    def test_result_frozen(self) -> None:
        """CouncilResult should be immutable."""
        result = CouncilResult(mode=InvestigationMode.FAST)
        with pytest.raises(ValidationError):
            result.mode = InvestigationMode.DEBATE  # type: ignore[misc]

    def test_result_serialization_roundtrip(self) -> None:
        """CouncilResult should serialize and deserialize cleanly."""
        finding = PanelFinding(
            panel="metrics",
            summary="High CPU",
            severity=PanelSeverity.CRITICAL,
            confidence=0.9,
            evidence=["cpu_usage > 95%"],
            recommended_actions=["Scale up"],
        )
        original = CouncilResult(
            mode=InvestigationMode.STANDARD,
            panels=[finding],
            synthesis="Critical CPU issue",
            overall_severity=PanelSeverity.CRITICAL,
            overall_confidence=0.9,
        )
        data = original.model_dump()
        restored = CouncilResult.model_validate(data)
        assert restored == original


class TestCouncilConfig:
    """Tests for CouncilConfig model."""

    def test_default_config(self) -> None:
        """Default config should use STANDARD mode with sensible defaults."""
        config = CouncilConfig()
        assert config.mode == InvestigationMode.STANDARD
        assert config.max_debate_rounds == 3
        assert config.confidence_threshold == 0.85
        assert config.timeout_seconds == 120

    def test_debate_config(self) -> None:
        """Debate config should accept custom parameters."""
        config = CouncilConfig(
            mode=InvestigationMode.DEBATE,
            max_debate_rounds=5,
            confidence_threshold=0.9,
            timeout_seconds=300,
        )
        assert config.mode == InvestigationMode.DEBATE
        assert config.max_debate_rounds == 5

    def test_invalid_debate_rounds(self) -> None:
        """Debate rounds outside 1-10 should be rejected."""
        with pytest.raises(ValidationError):
            CouncilConfig(max_debate_rounds=0)
        with pytest.raises(ValidationError):
            CouncilConfig(max_debate_rounds=11)

    def test_invalid_timeout(self) -> None:
        """Timeout outside 10-600 should be rejected."""
        with pytest.raises(ValidationError):
            CouncilConfig(timeout_seconds=5)
        with pytest.raises(ValidationError):
            CouncilConfig(timeout_seconds=700)

    def test_frozen_config(self) -> None:
        """CouncilConfig should be immutable."""
        config = CouncilConfig()
        with pytest.raises(ValidationError):
            config.mode = InvestigationMode.FAST  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            CouncilConfig(unknown="value")  # type: ignore[call-arg]
