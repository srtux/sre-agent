"""Pydantic schemas for SRE Agent structured outputs.

This module defines Pydantic schemas for:
- Individual findings (LatencyDiff, ErrorDiff, StructureDiff)
- Sub-agent output reports (LatencyAnalysisReport, ErrorAnalysisReport, etc.)
- Aggregate report (TraceComparisonReport)
- Statistical analysis outputs
- Observability data structures (logs, metrics, errors)
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolStatus(str, Enum):
    """Status of a tool execution."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class InvestigationPhase(str, Enum):
    """State of the SRE investigation."""

    INITIATED = "initiated"
    TRIAGE = "triage"
    DEEP_DIVE = "deep_dive"
    REMEDIATION = "remediation"
    RESOLVED = "resolved"


class BaseToolResponse(BaseModel):
    """Standardized envelope for all tool responses."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: ToolStatus = Field(description="Execution status")
    result: Any | None = Field(default=None, description="Tool result data on success")
    error: str | None = Field(
        default=None, description="Detailed error message on failure"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )


class Severity(str, Enum):
    """Severity level for findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Confidence(str, Enum):
    """Confidence level for analysis conclusions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Trace Analysis Schemas
# =============================================================================


class SpanInfo(BaseModel):
    """Information about a single span in a trace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_id: str = Field(description="Unique identifier for the span")
    name: str = Field(description="Name/operation of the span")
    duration_ms: float | None = Field(
        default=None, description="Duration in milliseconds"
    )
    parent_span_id: str | None = Field(
        default=None, description="Parent span ID if nested"
    )
    has_error: bool = Field(default=False, description="Whether this span has errors")
    labels: dict[str, str] = Field(
        default_factory=dict, description="Span labels/attributes"
    )


class LatencyDiff(BaseModel):
    """Latency difference for a specific span type."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_name: str = Field(description="Name of the span being compared")
    baseline_ms: float = Field(description="Duration in baseline trace (ms)")
    target_ms: float = Field(description="Duration in target trace (ms)")
    diff_ms: float = Field(description="Difference in milliseconds")
    diff_percent: float = Field(description="Percentage change")
    severity: Severity = Field(description="Impact severity")


class ErrorDiff(BaseModel):
    """Error difference between traces."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_name: str = Field(description="Span where the error occurred")
    error_type: str = Field(description="Type or category of error")
    error_message: str | None = Field(default=None, description="Error message")
    status_code: int | str | None = Field(default=None, description="Status code")
    is_new: bool = Field(description="True if this error is new in the target trace")


class StructureDiff(BaseModel):
    """Structural difference in the call graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_type: Literal["added", "removed", "modified"] = Field(
        description="Type of structural change"
    )
    span_name: str = Field(description="Name of the affected span")
    description: str = Field(description="Description of the structural change")


class TraceSummary(BaseModel):
    """Summary information for a single trace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str = Field(description="Unique trace identifier")
    span_count: int = Field(description="Total number of spans")
    total_duration_ms: float = Field(description="Total trace duration in ms")
    error_count: int = Field(default=0, description="Number of error spans")
    max_depth: int = Field(default=0, description="Maximum call tree depth")


class TraceComparisonReport(BaseModel):
    """Complete trace comparison analysis report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_summary: TraceSummary = Field(description="Summary of baseline trace")
    target_summary: TraceSummary = Field(description="Summary of target trace")
    overall_assessment: Literal["healthy", "degraded", "critical"] = Field(
        description="Overall health assessment"
    )
    latency_findings: list[LatencyDiff] = Field(
        default_factory=list, description="List of latency differences found"
    )
    error_findings: list[ErrorDiff] = Field(
        default_factory=list, description="List of error differences found"
    )
    structure_findings: list[StructureDiff] = Field(
        default_factory=list, description="List of structural differences found"
    )
    root_cause_hypothesis: str = Field(description="Hypothesis for the root cause")
    recommendations: list[str] = Field(
        default_factory=list, description="List of actionable recommendations"
    )


class MemoryItem(BaseModel):
    """A single finding or fact stored in memory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_tool: str = Field(description="Tool that generated this finding")
    confidence: Confidence = Field(description="Confidence in this finding")
    timestamp: str = Field(description="ISO 8601 timestamp")
    description: str = Field(description="Human-readable description of finding")
    structured_data: dict[str, Any] | None = Field(
        default=None, description="Raw structured data for programmatic use"
    )


class AgentHandoff(BaseModel):
    """Structured context for handing off between sub-agents."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_agent: str = Field(description="Agent initiating the handoff")
    target_agent: str = Field(description="Target agent")
    task_description: str = Field(
        description="Specific instructions for the target agent"
    )
    current_state: InvestigationPhase = Field(description="Current investigation phase")
    context_summary: str = Field(description="Summary of relevant findings so far")
    relevant_findings: list[MemoryItem] = Field(
        default_factory=list, description="Specific findings to pass along"
    )


# =============================================================================
# Sub-Agent Output Schemas
# =============================================================================


class LatencyAnalysisReport(BaseModel):
    """Output schema for the latency_analyzer sub-agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_trace_id: str = Field(description="ID of the baseline trace")
    target_trace_id: str = Field(description="ID of the target trace being analyzed")
    overall_diff_ms: float = Field(description="Total difference in duration (ms)")
    top_slowdowns: list[LatencyDiff] = Field(
        default_factory=list, description="Top span slowdowns sorted by impact"
    )
    improvements: list[LatencyDiff] = Field(
        default_factory=list, description="Spans that improved in performance"
    )
    root_cause_hypothesis: str = Field(description="Hypothesis for why latency changed")


class ErrorInfo(BaseModel):
    """Detailed information about an error occurrence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_name: str = Field(description="Name of the span with error")
    error_type: str = Field(description="Category or type of error")
    status_code: int | str | None = Field(
        default=None, description="HTTP or gRPC status code"
    )
    error_message: str | None = Field(
        default=None, description="Detailed error message"
    )
    service_name: str | None = Field(
        default=None, description="Service where error originated"
    )


class ErrorAnalysisReport(BaseModel):
    """Output schema for the error_analyzer sub-agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_error_count: int = Field(description="Total errors in baseline trace")
    target_error_count: int = Field(description="Total errors in target trace")
    net_change: int = Field(description="Net change in error count")
    new_errors: list[ErrorInfo] = Field(
        default_factory=list, description="Errors present only in target"
    )
    resolved_errors: list[ErrorInfo] = Field(
        default_factory=list, description="Errors present only in baseline"
    )
    common_errors: list[ErrorInfo] = Field(
        default_factory=list, description="Errors present in both"
    )
    error_pattern_analysis: str = Field(description="Analysis of error patterns")
    recommendations: list[str] = Field(
        default_factory=list, description="Fix recommendations"
    )


class StructuralChange(BaseModel):
    """A single structural change in the call graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_type: Literal["added", "removed", "depth_change", "fanout_change"] = Field(
        description="Type of structural change"
    )
    span_name: str = Field(description="Name of the span affected")
    description: str = Field(description="Description of the change")
    possible_reason: str | None = Field(
        default=None, description="Inferred reason for change"
    )


class StructureAnalysisReport(BaseModel):
    """Output schema for the structure_analyzer sub-agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_span_count: int = Field(description="Span count in baseline")
    baseline_depth: int = Field(description="Call depth in baseline")
    target_span_count: int = Field(description="Span count in target")
    target_depth: int = Field(description="Call depth in target")
    missing_operations: list[StructuralChange] = Field(
        default_factory=list, description="Operations missing in target"
    )
    new_operations: list[StructuralChange] = Field(
        default_factory=list, description="Operations added in target"
    )
    call_pattern_changes: list[str] = Field(
        default_factory=list, description="High-level pattern changes"
    )
    behavioral_impact: str = Field(description="Assessment of behavioral impact")


class LatencyDistribution(BaseModel):
    """Statistical distribution of latency values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sample_size: int = Field(description="Number of samples")
    mean_ms: float = Field(description="Mean latency (ms)")
    median_ms: float = Field(description="Median latency (ms)")
    p90_ms: float = Field(description="90th percentile latency (ms)")
    p95_ms: float = Field(description="95th percentile latency (ms)")
    p99_ms: float = Field(description="99th percentile latency (ms)")
    std_dev_ms: float = Field(description="Standard deviation (ms)")
    coefficient_of_variation: float = Field(
        description="Coefficient of variation (std_dev / mean)"
    )


class AnomalyFinding(BaseModel):
    """A span identified as anomalous via statistical analysis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_name: str = Field(description="Name of the anomalous span")
    observed_ms: float = Field(description="Observed duration (ms)")
    expected_ms: float = Field(description="Expected/Baseline duration (ms)")
    z_score: float = Field(description="Z-score indicating deviation magnitude")
    severity: Severity = Field(description="Severity of the anomaly")


class CriticalPathSegment(BaseModel):
    """A segment of the critical path through a trace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_name: str = Field(description="Name of the span")
    duration_ms: float = Field(description="Duration (ms)")
    percentage_of_total: float = Field(
        description="Percentage of total critical path duration"
    )
    is_optimization_target: bool = Field(
        default=False, description="Whether this span matches optimization criteria"
    )


class StatisticalAnalysisReport(BaseModel):
    """Output schema for the statistics_analyzer sub-agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    latency_distribution: LatencyDistribution = Field(
        description="Latency distribution metrics"
    )
    anomaly_threshold: float = Field(description="Threshold used for anomaly detection")
    anomalies: list[AnomalyFinding] = Field(
        default_factory=list, description="Detected anomalies"
    )
    critical_path: list[CriticalPathSegment] = Field(
        default_factory=list, description="Critical path analysis"
    )
    optimization_opportunities: list[str] = Field(
        default_factory=list, description="Identified optimization opportunities"
    )


class RootCauseCandidate(BaseModel):
    """A candidate root cause identified by causal analysis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rank: int = Field(description="Rank of probability (1 = highest)")
    span_name: str = Field(description="Span suspected as root cause")
    slowdown_ms: float = Field(description="Associated slowdown (ms)")
    confidence: Confidence = Field(description="Confidence in this candidate")
    reasoning: str = Field(description="Reasoning for selection")


class CausalChainLink(BaseModel):
    """A link in the causal chain showing issue propagation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_name: str = Field(description="Span name")
    effect_type: Literal["root_cause", "direct_effect", "cascaded_effect"] = Field(
        description="Type of effect in the chain"
    )
    latency_contribution_ms: float = Field(description="Latency contribution (ms)")


class CausalAnalysisReport(BaseModel):
    """Output schema for the causality_analyzer sub-agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    causal_chain: list[CausalChainLink] = Field(
        default_factory=list, description="Chain of causality"
    )
    root_cause_candidates: list[RootCauseCandidate] = Field(
        default_factory=list, description="Ranked list of root causes"
    )
    propagation_depth: int = Field(default=0, description="Depth of issue propagation")
    primary_root_cause: str = Field(description="Primary identified root cause")
    confidence: Confidence = Field(description="Overall confidence")
    conclusion: str = Field(description="Final conclusion")
    recommended_actions: list[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )


class ServiceImpact(BaseModel):
    """Impact assessment for a single service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service_name: str = Field(description="Name of the service")
    impact_type: Literal["latency", "error_rate", "throughput", "availability"] = Field(
        description="Type of metric impacted"
    )
    severity: Severity = Field(description="Severity of impact")
    baseline_value: float = Field(description="Baseline metric value")
    current_value: float = Field(description="Current metric value")
    change_percent: float = Field(description="Percentage change")
    affected_operations: list[str] = Field(
        default_factory=list, description="Operations affected in this service"
    )


class ServiceImpactReport(BaseModel):
    """Output schema for the service_impact sub-agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_services_analyzed: int = Field(description="Total count of services")
    impacted_services_count: int = Field(description="Count of impacted services")
    service_impacts: list[ServiceImpact] = Field(
        default_factory=list, description="Details of service impacts"
    )
    cross_service_effects: list[str] = Field(
        default_factory=list, description="Observed cross-service propagation"
    )
    blast_radius_assessment: str = Field(
        description="Assessment of overall blast radius"
    )


# =============================================================================
# Observability Data Schemas
# =============================================================================


class LogEntry(BaseModel):
    """Represents a single log entry from Cloud Logging."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str = Field(description="ISO 8601 timestamp")
    severity: str = Field(description="Log severity (INFO, ERROR, etc.)")
    payload: str = Field(description="Text payload or stringified JSON payload")
    resource: dict[str, Any] = Field(description="Monitored resource attributes")


class TimeSeriesPoint(BaseModel):
    """Represents a single point in a time series."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str = Field(description="ISO 8601 timestamp")
    value: float = Field(description="Metric value")


class TimeSeries(BaseModel):
    """Represents a time series from Cloud Monitoring."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: dict[str, Any] = Field(description="Metric labels and type")
    resource: dict[str, Any] = Field(description="Resource labels and type")
    points: list[TimeSeriesPoint] = Field(description="List of data points")


class ErrorEvent(BaseModel):
    """Represents an error event from Cloud Error Reporting."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_time: str = Field(description="ISO 8601 timestamp of event")
    message: str = Field(description="Error message or stack trace")
    service_context: dict[str, Any] = Field(description="Service and version context")


# =============================================================================
# Agent Trace / Debugging Schemas
# =============================================================================


class GenAIOperationType(str, Enum):
    """GenAI semantic convention operation types for agent spans."""

    INVOKE_AGENT = "invoke_agent"
    EXECUTE_TOOL = "execute_tool"
    GENERATE_CONTENT = "generate_content"
    CHAT = "chat"
    UNKNOWN = "unknown"


class AgentSpanKind(str, Enum):
    """Classification of agent trace spans."""

    AGENT_INVOCATION = "agent_invocation"
    LLM_CALL = "llm_call"
    TOOL_EXECUTION = "tool_execution"
    SUB_AGENT_DELEGATION = "sub_agent_delegation"
    UNKNOWN = "unknown"


class AgentSpanInfo(BaseModel):
    """A span enriched with GenAI semantic convention attributes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    span_id: str = Field(description="Unique span identifier")
    parent_span_id: str | None = Field(
        default=None, description="Parent span ID if nested"
    )
    name: str = Field(description="Span name / operation")
    kind: AgentSpanKind = Field(description="Classified span kind")
    operation: GenAIOperationType = Field(
        default=GenAIOperationType.UNKNOWN, description="GenAI operation type"
    )
    start_time_iso: str = Field(description="Start time in ISO 8601")
    end_time_iso: str = Field(description="End time in ISO 8601")
    duration_ms: float = Field(description="Duration in milliseconds")
    # GenAI attributes
    agent_name: str | None = Field(default=None, description="gen_ai.agent.name")
    agent_id: str | None = Field(default=None, description="gen_ai.agent.id")
    tool_name: str | None = Field(default=None, description="gen_ai.tool.name")
    tool_call_id: str | None = Field(default=None, description="gen_ai.tool.call.id")
    model_requested: str | None = Field(
        default=None, description="gen_ai.request.model"
    )
    model_used: str | None = Field(default=None, description="gen_ai.response.model")
    input_tokens: int | None = Field(
        default=None, description="gen_ai.usage.input_tokens"
    )
    output_tokens: int | None = Field(
        default=None, description="gen_ai.usage.output_tokens"
    )
    finish_reasons: list[str] = Field(
        default_factory=list, description="gen_ai.response.finish_reasons"
    )
    status_code: int = Field(
        default=0, description="OTel status code: 0=UNSET, 1=OK, 2=ERROR"
    )
    error_message: str | None = Field(
        default=None, description="Error message if status=ERROR"
    )
    attributes: dict[str, str] = Field(
        default_factory=dict, description="Additional span attributes"
    )
    children: list["AgentSpanInfo"] = Field(
        default_factory=list, description="Child spans in the interaction tree"
    )


class AgentInteractionGraph(BaseModel):
    """Full reconstructed agent interaction graph from a single trace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str = Field(description="Trace ID")
    project_id: str = Field(description="GCP project ID")
    reasoning_engine_id: str | None = Field(
        default=None, description="Vertex Reasoning Engine resource ID"
    )
    root_agent_name: str | None = Field(
        default=None, description="Name of the root agent"
    )
    root_spans: list[AgentSpanInfo] = Field(
        default_factory=list, description="Top-level spans (tree roots)"
    )
    total_spans: int = Field(default=0, description="Total span count")
    total_duration_ms: float = Field(default=0.0, description="Total trace duration")
    total_input_tokens: int = Field(default=0, description="Sum of input tokens")
    total_output_tokens: int = Field(default=0, description="Sum of output tokens")
    total_llm_calls: int = Field(default=0, description="Count of LLM calls")
    total_tool_executions: int = Field(
        default=0, description="Count of tool executions"
    )
    unique_agents: list[str] = Field(
        default_factory=list, description="Distinct agent names"
    )
    unique_tools: list[str] = Field(
        default_factory=list, description="Distinct tool names"
    )
    unique_models: list[str] = Field(
        default_factory=list, description="Distinct model names"
    )


class AgentRunSummary(BaseModel):
    """Summary of a single agent run (one trace)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str = Field(description="Trace ID")
    root_agent_name: str | None = Field(default=None, description="Root agent name")
    start_time: str = Field(description="ISO 8601 start time")
    duration_ms: float = Field(description="Total duration in ms")
    total_input_tokens: int = Field(default=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, description="Total output tokens")
    tool_call_count: int = Field(default=0, description="Number of tool calls")
    llm_call_count: int = Field(default=0, description="Number of LLM calls")
    sub_agent_count: int = Field(
        default=0, description="Number of sub-agent delegations"
    )
    has_error: bool = Field(default=False, description="Whether any span had an error")
    span_count: int = Field(default=0, description="Total span count")


class AgentAntiPattern(BaseModel):
    """An anti-pattern detected in agent interaction traces."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pattern_type: str = Field(
        description="Type: excessive_retries, token_waste, long_chain, redundant_tool_calls"
    )
    severity: Severity = Field(description="Severity of the anti-pattern")
    description: str = Field(description="Human-readable description")
    affected_spans: list[str] = Field(
        default_factory=list, description="Span IDs affected"
    )
    recommendation: str = Field(description="Actionable recommendation")
    metric_value: float | None = Field(
        default=None, description="Quantitative metric for the pattern"
    )
