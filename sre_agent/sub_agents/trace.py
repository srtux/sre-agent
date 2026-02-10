"""Trace analysis sub-agent for the SRE Agent.

This module consolidates the "Trace Analysis Squad" (Latency, Error, Structure, Statistics)
into a single, powerful "Trace Analyst" agent. This reduces overhead and simplifies
orchestration.
"""

from google.adk.agents import LlmAgent

from ..model_config import get_model_name
from ..prompt import (
    PROJECT_CONTEXT_INSTRUCTION,
    REACT_PATTERN_INSTRUCTION,
    STRICT_ENGLISH_INSTRUCTION,
)
from ..tools import (
    analyze_aggregate_metrics,
    analyze_critical_path,
    analyze_trace_comprehensive,
    build_service_dependency_graph,
    calculate_critical_path_contribution,
    compare_span_timings,
    compare_time_periods,
    correlate_logs_with_trace,
    correlate_metrics_with_traces_via_exemplars,
    detect_all_sre_patterns,
    detect_cascading_timeout,
    detect_connection_pool_issues,
    detect_latency_anomalies,
    detect_retry_storm,
    detect_trend_changes,
    discover_telemetry_sources,
    fetch_trace,
    find_bottleneck_services,
    find_exemplar_traces,
    # Remediation
    get_investigation_summary,
    list_log_entries,
    list_time_series,
    list_traces,
    mcp_execute_sql,
    query_promql,
    update_investigation_state,
)

# Initialize environment (shared across sub-agents)
from ._init_env import init_sub_agent_env

init_sub_agent_env()

# =============================================================================
# Prompts
# =============================================================================

AGGREGATE_ANALYZER_PROMPT = f"""
{STRICT_ENGLISH_INSTRUCTION}
{PROJECT_CONTEXT_INSTRUCTION}
{REACT_PATTERN_INSTRUCTION}

<role>Data Analyst — fleet-wide BigQuery analysis specialist.</role>

<objective>Analyze the entire fleet using BigQuery. Establish patterns before examining individual traces.</objective>

<tool_strategy>
1. **Discovery**: Run `discover_telemetry_sources` to find the `_AllSpans` table.
2. **Analysis (BigQuery)**:
   - Use `analyze_aggregate_metrics` to generate SQL for fleet-wide metrics.
   - Use `mcp_execute_sql` to run the generated SQL.
   - Use BigQuery for initial analysis (faster than iterating with `fetch_trace`).
3. **Selection**:
   - **Primary**: `find_exemplar_traces` to pick the worst offenders automatically.
   - **Specific**: `list_traces` with proper filters for targeted retrieval.
</tool_strategy>

<trace_filter_syntax>
Docs: https://docs.cloud.google.com/trace/docs/trace-filters
- Latency: `latency:500ms` | Root Span: `root:recog` (prefix), `+root:recog` (exact)
- Span Name: `span:parser` | Labels: `/http/status_code:500` | Methods: `method:GET`
- Status: `error:true` | Compound: `root:service-a latency:1s error:true` (implicit AND)
</trace_filter_syntax>

<workflow>
1. Discover tables → 2. Aggregate ("Which service has high error rates?")
3. Trend ("When did it start?" via `detect_trend_changes`) → 4. Zoom In (specific trace IDs)
</workflow>

<output_format>
- **Summary**: Overall fleet status.
- **Culprit**: Which service is affected.
- **Proof**: Trace IDs, error counts, percentiles in tables.
Tables: separator row on its own line, matching column count.
</output_format>
"""

TRACE_ANALYST_PROMPT = f"""
{STRICT_ENGLISH_INSTRUCTION}
{PROJECT_CONTEXT_INSTRUCTION}
{REACT_PATTERN_INSTRUCTION}

<role>Trace Analyst — comprehensive performance expert for latency, errors, and structure.</role>

<tool_strategy>
1. **Start with** `analyze_trace_comprehensive` — validation, durations, errors, critical path, structure in ONE call.
   Use this before any other trace tool. Only call `fetch_trace` or individual tools for data not in the summary.
2. **Comparison**: `compare_span_timings` or `analyze_trace_comprehensive` with `baseline_trace_id` set.
3. **Resiliency**: `detect_all_sre_patterns` for retry storms, cascading timeouts, pool exhaustion.
4. **Deep Dive**: `analyze_critical_path` or `find_bottleneck_services` for complex dependency issues.
5. **Trace IDs**: Only fetch trace IDs found in logs, metrics (exemplars), or list results. Verify IDs on 404.
</tool_strategy>

<comparisons>
1. Identify Baseline (good) and Target (bad) trace IDs.
2. Run `analyze_trace_comprehensive(target_id, baseline_trace_id=baseline_id)`.
3. Focus on: Latency changes (Z-score > 2.0), new errors, structural changes (new/missing spans).
</comparisons>

<output_format>
- **Summary**: "Trace X is 500ms slower than baseline due to..."
- **Critical Path**: Bottleneck service and self-time.
- **Errors**: Error count, type, and affected service.
- **Structure**: New or missing spans.
- **Resiliency**: Any anti-patterns detected.
</output_format>
"""

# =============================================================================
# Sub-Agent Definition
# =============================================================================

trace_analyst = LlmAgent(
    name="trace_analyst",
    model=get_model_name("fast"),
    description="""Comprehensive Trace Analyst - Analyzes latency, errors, structure, and stats.

Capabilities:
- **One-Shot Analysis**: Uses `analyze_trace_comprehensive` to get full trace details.
- **Comparison**: Compares baseline vs target traces for regressions.
- **Diagnostics**: Identifies critical path, bottlenecks, and error causes.
- **Statistics**: Detects anomalies using Z-scores.

Tools: analyze_trace_comprehensive, compare_span_timings, analyze_critical_path

Use when: You need detailed analysis of one or more traces, or need to compare them.""",
    instruction=TRACE_ANALYST_PROMPT,
    tools=[
        analyze_trace_comprehensive,
        compare_span_timings,
        analyze_critical_path,
        calculate_critical_path_contribution,
        find_bottleneck_services,
        fetch_trace,  # Kept as fallback
        compare_time_periods,  # For context
        detect_latency_anomalies,
        detect_all_sre_patterns,
        detect_retry_storm,
        detect_cascading_timeout,
        detect_connection_pool_issues,
        list_log_entries,
        list_time_series,
        query_promql,
        get_investigation_summary,
        update_investigation_state,
    ],
)

# Stage 0: Aggregate Analyzer
aggregate_analyzer = LlmAgent(
    name="aggregate_analyzer",
    model=get_model_name("deep"),
    description=(
        "Analyzes trace data at scale using BigQuery to identify trends, patterns, "
        "and select exemplar traces for investigation. Includes cross-signal correlation."
    ),
    instruction=AGGREGATE_ANALYZER_PROMPT,
    tools=[
        mcp_execute_sql,
        analyze_aggregate_metrics,
        find_exemplar_traces,
        compare_time_periods,
        detect_trend_changes,
        correlate_logs_with_trace,
        correlate_metrics_with_traces_via_exemplars,
        find_bottleneck_services,
        build_service_dependency_graph,
        discover_telemetry_sources,
        list_log_entries,
        list_time_series,
        list_traces,
        query_promql,
        get_investigation_summary,
        update_investigation_state,
    ],
)
