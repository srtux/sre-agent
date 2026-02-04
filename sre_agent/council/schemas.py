"""Pydantic schemas for the Council investigation architecture.

Defines the data models for investigation modes, panel findings,
critic reports, and council results used throughout the council pipeline.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InvestigationMode(str, Enum):
    """Investigation mode controlling depth and parallelism.

    - FAST: Single best-fit panel, no debate (~5s).
    - STANDARD: All 4 panels in parallel, synthesized (~30s).
    - DEBATE: Parallel panels + critic loop until confidence threshold (~60s+).
    """

    FAST = "fast"
    STANDARD = "standard"
    DEBATE = "debate"


class PanelSeverity(str, Enum):
    """Severity assessment from a specialist panel."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    HEALTHY = "healthy"


class PanelFinding(BaseModel):
    """Structured finding from a specialist panel agent.

    Each panel produces one PanelFinding summarizing its analysis
    of the relevant telemetry signals.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    panel: str = Field(
        description="Panel identifier: 'trace', 'metrics', 'logs', or 'alerts'."
    )
    summary: str = Field(description="Concise summary of the panel's findings.")
    severity: PanelSeverity = Field(
        description="Assessed severity of the situation from this panel's perspective."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the assessment (0.0 = no confidence, 1.0 = certain).",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Supporting evidence items (trace IDs, metric values, log entries).",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Recommended remediation or investigation actions.",
    )


class CriticReport(BaseModel):
    """Cross-critique report from the critic agent.

    The critic examines all panel findings together, identifying
    agreements, contradictions, and gaps in the analysis.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    agreements: list[str] = Field(
        default_factory=list,
        description="Points where multiple panels agree.",
    )
    contradictions: list[str] = Field(
        default_factory=list,
        description="Conflicting findings between panels.",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Missing analysis or uncovered areas.",
    )
    revised_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Critic's revised overall confidence after cross-examination.",
    )


class CouncilResult(BaseModel):
    """Final result from a council investigation.

    Aggregates panel findings, optional critic report, and a
    synthesized conclusion with overall severity and confidence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: InvestigationMode = Field(description="Investigation mode that was used.")
    panels: list[PanelFinding] = Field(
        default_factory=list,
        description="Findings from each specialist panel.",
    )
    critic_report: CriticReport | None = Field(
        default=None,
        description="Critic's cross-examination report (None for FAST/STANDARD modes).",
    )
    synthesis: str = Field(
        default="",
        description="Synthesized conclusion merging all panel findings.",
    )
    overall_severity: PanelSeverity = Field(
        default=PanelSeverity.INFO,
        description="Overall severity assessment across all panels.",
    )
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Overall confidence in the synthesized result.",
    )
    rounds: int = Field(
        default=1,
        ge=1,
        description="Number of debate rounds completed (1 for non-debate modes).",
    )


class CouncilConfig(BaseModel):
    """Configuration for a council investigation run.

    Controls the investigation mode, debate parameters, and timeouts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: InvestigationMode = Field(
        default=InvestigationMode.STANDARD,
        description="Investigation mode to use.",
    )
    max_debate_rounds: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum debate rounds before forced synthesis.",
    )
    confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence level at which debate stops early.",
    )
    timeout_seconds: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Maximum wall-clock time for the investigation.",
    )
