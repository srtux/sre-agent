"""Investigation state and phase management for SRE Agent."""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class InvestigationPhase(str, Enum):
    """Phases of an SRE investigation."""

    TRIAGE = "triage"
    ANALYSIS = "analysis"
    ROOT_CAUSE = "root_cause"
    REMEDIATION = "remediation"
    COMPLETED = "completed"


class InvestigationState(BaseModel):
    """Tracks the current state of an investigation."""

    phase: InvestigationPhase = InvestigationPhase.TRIAGE
    findings: list[str] = []
    hypotheses: list[str] = []
    confirmed_root_cause: str | None = None
    suggested_fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for session state."""
        return {
            "phase": self.phase.value,
            "findings": self.findings,
            "hypotheses": self.hypotheses,
            "confirmed_root_cause": self.confirmed_root_cause,
            "suggested_fix": self.suggested_fix,
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
