"""Pydantic schemas for the Council investigation architecture.

Defines the data models for investigation modes, panel findings,
critic reports, and council results used throughout the council pipeline.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RoutingDecision(str, Enum):
    """Top-level routing decision for the SRE agent orchestrator.

    Determines how to handle a user query:
    - DIRECT: Simple data retrieval — call individual tools (logs, metrics, traces, alerts).
    - SUB_AGENT: Analysis tasks — delegate to a specialist sub-agent.
    - COUNCIL: Complex multi-signal investigation — start a council meeting.
    """

    DIRECT = "direct"
    SUB_AGENT = "sub_agent"
    COUNCIL = "council"


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


# =============================================================================
# Agent Activity Tracking Schemas
# =============================================================================


class AgentType(str, Enum):
    """Types of agents in the council hierarchy."""

    ROOT = "root"
    ORCHESTRATOR = "orchestrator"
    PANEL = "panel"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    SUB_AGENT = "sub_agent"


class ToolCallRecord(BaseModel):
    """Record of a single tool call made by an agent.

    Tracks the tool name, arguments, result summary, timing,
    and whether it produced dashboard-visualizable data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str = Field(description="Unique identifier for this tool call.")
    tool_name: str = Field(description="Name of the tool that was called.")
    args_summary: str = Field(
        default="",
        description="Brief summary of the arguments passed to the tool.",
    )
    result_summary: str = Field(
        default="",
        description="Brief summary of the tool result.",
    )
    status: str = Field(
        default="completed",
        description="Status: 'pending', 'completed', or 'error'.",
    )
    duration_ms: int = Field(
        default=0,
        ge=0,
        description="Time taken for the tool call in milliseconds.",
    )
    timestamp: str = Field(
        default="",
        description="ISO timestamp when the tool was called.",
    )
    dashboard_category: str | None = Field(
        default=None,
        description="Dashboard category if this tool produces visualization data.",
    )


class LLMCallRecord(BaseModel):
    """Record of an LLM inference call made by an agent.

    Tracks the model used, token counts, and timing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str = Field(description="Unique identifier for this LLM call.")
    model: str = Field(description="Model identifier used for this call.")
    input_tokens: int = Field(default=0, ge=0, description="Number of input tokens.")
    output_tokens: int = Field(default=0, ge=0, description="Number of output tokens.")
    duration_ms: int = Field(
        default=0,
        ge=0,
        description="Time taken for the LLM call in milliseconds.",
    )
    timestamp: str = Field(
        default="",
        description="ISO timestamp when the LLM was called.",
    )


class AgentActivity(BaseModel):
    """Activity record for a single agent in the council hierarchy.

    Tracks the agent's identity, status, tool calls, LLM calls,
    and relationships to other agents.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str = Field(description="Unique identifier for this agent instance.")
    agent_name: str = Field(description="Human-readable name of the agent.")
    agent_type: AgentType = Field(description="Type of agent in the hierarchy.")
    parent_id: str | None = Field(
        default=None,
        description="ID of the parent agent, or None for root.",
    )
    status: str = Field(
        default="pending",
        description="Status: 'pending', 'running', 'completed', 'error'.",
    )
    started_at: str = Field(default="", description="ISO timestamp when agent started.")
    completed_at: str = Field(
        default="", description="ISO timestamp when agent completed."
    )
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list,
        description="List of tool calls made by this agent.",
    )
    llm_calls: list[LLMCallRecord] = Field(
        default_factory=list,
        description="List of LLM inference calls made by this agent.",
    )
    output_summary: str = Field(
        default="",
        description="Brief summary of the agent's output or findings.",
    )


class CouncilActivityGraph(BaseModel):
    """Complete activity graph for a council investigation.

    Contains all agent activities, their relationships, and
    aggregated statistics for visualization.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    investigation_id: str = Field(
        description="Unique identifier for this investigation."
    )
    mode: InvestigationMode = Field(description="Investigation mode used.")
    started_at: str = Field(description="ISO timestamp when investigation started.")
    completed_at: str = Field(
        default="", description="ISO timestamp when investigation completed."
    )
    agents: list[AgentActivity] = Field(
        default_factory=list,
        description="All agents that participated in the investigation.",
    )
    total_tool_calls: int = Field(
        default=0, ge=0, description="Total number of tool calls across all agents."
    )
    total_llm_calls: int = Field(
        default=0, ge=0, description="Total number of LLM calls across all agents."
    )
    debate_rounds: int = Field(
        default=1, ge=1, description="Number of debate rounds completed."
    )

    def get_agent_by_id(self, agent_id: str) -> AgentActivity | None:
        """Find an agent by its ID."""
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None

    def get_children(self, parent_id: str) -> list[AgentActivity]:
        """Get all direct children of an agent."""
        return [a for a in self.agents if a.parent_id == parent_id]

    def get_root_agents(self) -> list[AgentActivity]:
        """Get agents with no parent (root level)."""
        return [a for a in self.agents if a.parent_id is None]


class ClassificationContext(BaseModel):
    """Optional context for adaptive classification.

    Provides investigation history, alert severity, and resource
    budget to help the LLM classifier make better routing decisions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_history: list[str] = Field(
        default_factory=list,
        description="Recent investigation queries from this session.",
    )
    alert_severity: str | None = Field(
        default=None,
        description="Alert severity if triggered by an alert (e.g., 'critical', 'warning').",
    )
    remaining_token_budget: int | None = Field(
        default=None,
        description="Remaining token budget for the session, if tracked.",
    )
    previous_modes: list[str] = Field(
        default_factory=list,
        description="Investigation modes used in previous turns this session.",
    )


class AdaptiveClassificationResult(BaseModel):
    """Result from the adaptive classifier.

    Extends the basic classification with reasoning and provenance tracking.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: InvestigationMode = Field(
        description="The recommended investigation mode.",
    )
    signal_type: str = Field(
        default="trace",
        description="Best-fit signal type for FAST mode panel routing.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Classifier confidence in the mode selection.",
    )
    reasoning: str = Field(
        default="",
        description="Explanation of why this mode was selected.",
    )
    classifier_used: str = Field(
        default="rule_based",
        description="Which classifier produced this result: 'rule_based', 'llm_augmented', or 'fallback'.",
    )
