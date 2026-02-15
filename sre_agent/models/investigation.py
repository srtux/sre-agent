"""Investigation state and phase management for SRE Agent.

Provides a rich state model for tracking SRE investigations through their
full lifecycle, from initial triage to postmortem generation.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class InvestigationPhase(str, Enum):
    """Phases of an SRE investigation."""

    TRIAGE = "triage"
    ANALYSIS = "analysis"
    ROOT_CAUSE = "root_cause"
    REMEDIATION = "remediation"
    COMPLETED = "completed"


class ConfidenceLevel(str, Enum):
    """Confidence level for findings and hypotheses."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InvestigationFinding(BaseModel):
    """A structured finding from the investigation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str = Field(description="Human-readable description")
    source_tool: str = Field(
        default="unknown", description="Tool that produced this finding"
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM, description="Confidence in this finding"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the finding was recorded",
    )
    signal_type: str = Field(
        default="unknown",
        description="Signal type: trace, log, metric, alert, change",
    )
    severity: str = Field(default="info", description="Finding severity")


class InvestigationTimeline(BaseModel):
    """A timeline entry tracking phase transitions and key events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str = Field(description="ISO 8601 timestamp")
    event: str = Field(description="What happened")
    phase: str = Field(default="", description="Investigation phase at this point")


class InvestigationState(BaseModel):
    """Tracks the current state of an investigation.

    Enhanced with:
    - Structured findings with confidence levels
    - Phase transition timeline
    - Affected services tracking
    - Incident metadata (start/end times, severity)
    - Scores for investigation quality
    """

    # NOTE: frozen=True intentionally omitted — this model uses mutating methods
    # (add_finding, add_timeline_event, transition_phase, etc.) that require
    # in-place mutation. See AGENTS.md for the project-wide frozen=True pattern.
    model_config = ConfigDict(extra="forbid")

    phase: InvestigationPhase = InvestigationPhase.TRIAGE
    findings: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    confirmed_root_cause: str | None = None
    suggested_fix: str | None = None

    # Enhanced fields
    structured_findings: list[dict[str, Any]] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    timeline: list[dict[str, str]] = Field(default_factory=list)
    incident_start: str | None = None
    incident_end: str | None = None
    severity: str = "unknown"
    investigation_score: float = 0.0
    signals_analyzed: list[str] = Field(default_factory=list)
    changes_correlated: list[dict[str, Any]] = Field(default_factory=list)
    slo_impact: dict[str, Any] = Field(default_factory=dict)

    def add_finding(
        self,
        description: str,
        source_tool: str = "unknown",
        confidence: str = "medium",
        signal_type: str = "unknown",
        severity: str = "info",
    ) -> None:
        """Add a structured finding to the investigation."""
        finding = InvestigationFinding(
            description=description,
            source_tool=source_tool,
            confidence=ConfidenceLevel(confidence),
            signal_type=signal_type,
            severity=severity,
        )
        self.structured_findings.append(finding.model_dump())
        # Keep backward compatibility with flat findings list
        if description not in self.findings:
            self.findings.append(description)

    def add_timeline_event(self, event: str) -> None:
        """Record a timestamped event in the investigation timeline."""
        entry = InvestigationTimeline(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            phase=self.phase.value,
        )
        self.timeline.append(entry.model_dump())

    def transition_phase(self, new_phase: InvestigationPhase) -> None:
        """Transition to a new phase, recording the change in timeline."""
        old_phase = self.phase
        self.phase = new_phase
        self.add_timeline_event(
            f"Phase transition: {old_phase.value} -> {new_phase.value}"
        )

    def add_affected_service(self, service_name: str) -> None:
        """Track a service as affected by the incident."""
        if service_name not in self.affected_services:
            self.affected_services.append(service_name)

    def mark_signal_analyzed(self, signal_type: str) -> None:
        """Record that a signal type has been analyzed."""
        if signal_type not in self.signals_analyzed:
            self.signals_analyzed.append(signal_type)

    def calculate_score(self) -> float:
        """Calculate an investigation quality score (0-100).

        Scores based on:
        - Number of signals analyzed (traces, logs, metrics, alerts, changes)
        - Number of structured findings
        - Whether a root cause was identified
        - Whether remediation was suggested
        - Timeline completeness
        """
        score = 0.0

        # Signal coverage (up to 30 points)
        all_signals = {"trace", "log", "metric", "alert", "change"}
        covered = len(set(self.signals_analyzed) & all_signals)
        score += (covered / len(all_signals)) * 30

        # Findings depth (up to 20 points)
        finding_count = len(self.structured_findings)
        score += min(20, finding_count * 4)

        # Root cause identified (20 points)
        if self.confirmed_root_cause:
            score += 20

        # Remediation suggested (15 points)
        if self.suggested_fix:
            score += 15

        # Timeline completeness (up to 10 points)
        timeline_count = len(self.timeline)
        score += min(10, timeline_count * 2)

        # Phase progression (5 points for reaching remediation+)
        advanced_phases = {
            InvestigationPhase.REMEDIATION,
            InvestigationPhase.COMPLETED,
        }
        if self.phase in advanced_phases:
            score += 5

        self.investigation_score = min(100.0, round(score, 1))
        return self.investigation_score

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for session state."""
        return {
            "phase": self.phase.value,
            "findings": self.findings,
            "hypotheses": self.hypotheses,
            "confirmed_root_cause": self.confirmed_root_cause,
            "suggested_fix": self.suggested_fix,
            "structured_findings": self.structured_findings,
            "affected_services": self.affected_services,
            "timeline": self.timeline,
            "incident_start": self.incident_start,
            "incident_end": self.incident_end,
            "severity": self.severity,
            "investigation_score": self.investigation_score,
            "signals_analyzed": self.signals_analyzed,
            "changes_correlated": self.changes_correlated,
            "slo_impact": self.slo_impact,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "InvestigationState":
        """Reconstruct state from session dictionary."""
        if not data:
            return cls()

        try:
            return cls(
                phase=InvestigationPhase(data.get("phase", "triage")),
                findings=data.get("findings", []),
                hypotheses=data.get("hypotheses", []),
                confirmed_root_cause=data.get("confirmed_root_cause"),
                suggested_fix=data.get("suggested_fix"),
                structured_findings=data.get("structured_findings", []),
                affected_services=data.get("affected_services", []),
                timeline=data.get("timeline", []),
                incident_start=data.get("incident_start"),
                incident_end=data.get("incident_end"),
                severity=data.get("severity", "unknown"),
                investigation_score=data.get("investigation_score", 0.0),
                signals_analyzed=data.get("signals_analyzed", []),
                changes_correlated=data.get("changes_correlated", []),
                slo_impact=data.get("slo_impact", {}),
            )
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse investigation state from data: {data}")
            return cls()


PHASE_INSTRUCTIONS = {
    InvestigationPhase.TRIAGE: (
        "Focus on gathering high-level signals (Traces, Alerts, Key Metrics). "
        "Identify which service is most likely the source of the issue."
    ),
    InvestigationPhase.ANALYSIS: (
        "Deep dive into logs and specific metric windows. "
        "Correlate anomalies across different services and signals."
    ),
    InvestigationPhase.ROOT_CAUSE: (
        "Identify the primary failure mode (e.g., OOM, saturated connection pool, "
        "failed dependency, code regression). Formulate a clear explanation."
    ),
    InvestigationPhase.REMEDIATION: (
        "Suggest actionable fixes and estimate their risk/impact. "
        "Provide verification steps to ensure the fix works."
    ),
}
