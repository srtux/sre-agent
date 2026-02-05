"""Pydantic schemas for GCP Troubleshooting Playbooks.

These schemas define the structure for hierarchical troubleshooting
playbooks that guide SRE agents through diagnostic workflows.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlaybookCategory(str, Enum):
    """Categories for organizing playbooks by GCP service domain."""

    COMPUTE = "compute"
    DATA = "data"
    STORAGE = "storage"
    MESSAGING = "messaging"
    AI_ML = "ai_ml"
    OBSERVABILITY = "observability"
    SECURITY = "security"
    NETWORKING = "networking"
    MANAGEMENT = "management"


class PlaybookSeverity(str, Enum):
    """Severity levels for troubleshooting issues."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DiagnosticStep(BaseModel):
    """A single diagnostic step in a troubleshooting workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_number: int = Field(description="Order of the step in the workflow")
    title: str = Field(description="Brief title for the step")
    description: str = Field(description="Detailed description of what to do")
    command: str | None = Field(
        default=None, description="CLI command or API call to execute"
    )
    tool_name: str | None = Field(
        default=None, description="SRE Agent tool to invoke for this step"
    )
    tool_params: dict[str, Any] | None = Field(
        default=None, description="Parameters for the tool"
    )
    expected_outcome: str | None = Field(
        default=None, description="What success looks like"
    )
    failure_action: str | None = Field(
        default=None, description="What to do if this step fails"
    )
    documentation_url: str | None = Field(
        default=None, description="Link to official documentation"
    )


class TroubleshootingIssue(BaseModel):
    """A specific issue that can occur with a GCP service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issue_id: str = Field(description="Unique identifier for the issue")
    title: str = Field(description="Short title describing the issue")
    description: str = Field(description="Detailed description of the issue")
    symptoms: list[str] = Field(description="Observable symptoms of this issue")
    root_causes: list[str] = Field(description="Common root causes")
    severity: PlaybookSeverity = Field(description="Typical severity of this issue")
    diagnostic_steps: list[DiagnosticStep] = Field(
        description="Steps to diagnose the issue"
    )
    remediation_steps: list[DiagnosticStep] = Field(
        description="Steps to fix the issue"
    )
    prevention_tips: list[str] = Field(
        default_factory=list, description="How to prevent this issue"
    )
    related_metrics: list[str] = Field(
        default_factory=list, description="Metrics to monitor for this issue"
    )
    related_logs: list[str] = Field(
        default_factory=list, description="Log patterns to watch for"
    )
    error_codes: list[str] = Field(
        default_factory=list, description="Associated error codes"
    )
    documentation_urls: list[str] = Field(
        default_factory=list, description="Links to official documentation"
    )


class Playbook(BaseModel):
    """A troubleshooting playbook for a specific GCP service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    playbook_id: str = Field(description="Unique identifier for the playbook")
    service_name: str = Field(description="Name of the GCP service")
    display_name: str = Field(description="Human-readable name")
    category: PlaybookCategory = Field(description="Service category")
    description: str = Field(description="Overview of what this playbook covers")
    version: str = Field(default="1.0.0", description="Playbook version")
    issues: list[TroubleshootingIssue] = Field(
        description="Issues covered by this playbook"
    )
    general_diagnostic_steps: list[DiagnosticStep] = Field(
        default_factory=list,
        description="General diagnostic steps for the service",
    )
    best_practices: list[str] = Field(
        default_factory=list, description="General best practices"
    )
    key_metrics: list[str] = Field(
        default_factory=list, description="Important metrics to monitor"
    )
    key_logs: list[str] = Field(
        default_factory=list, description="Important log sources"
    )
    related_services: list[str] = Field(
        default_factory=list, description="Related GCP services"
    )
    documentation_urls: list[str] = Field(
        default_factory=list, description="Official documentation links"
    )


class PlaybookSearchResult(BaseModel):
    """Result from searching playbooks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    playbook_id: str
    service_name: str
    issue_id: str | None = None
    issue_title: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_reason: str
