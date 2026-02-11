"""Metrics Analysis Sub-Agent.

Responsible for all time-series analysis:
1. Quantify: Measure the magnitude using PromQL.
2. Correlate: Use Exemplars to jump from a Metric Spike -> Trace ID.
3. Contextualize: Compare current metrics with historical baselines.
"""

from google.adk.agents import LlmAgent

# OPT-4: Import shared tool set from council/tool_registry (single source of truth)
from ..council.tool_registry import METRICS_ANALYZER_TOOLS

# Initialize environment (shared across sub-agents)
from ..model_config import get_model_name
from ..prompt import (
    PROJECT_CONTEXT_INSTRUCTION,
    REACT_PATTERN_INSTRUCTION,
    STRICT_ENGLISH_INSTRUCTION,
)
from ..resources.gcp_metrics import COMMON_GCP_METRICS

# Initialize environment (shared across sub-agents)
from ._init_env import init_sub_agent_env

init_sub_agent_env()


# =============================================================================
# Prompts
# =============================================================================

SMART_METRICS_LIST = "\n".join(
    [f"- **{k}**: {', '.join(v)}" for k, v in COMMON_GCP_METRICS.items()]
)

METRICS_ANALYZER_PROMPT = f"""
{STRICT_ENGLISH_INSTRUCTION}
{PROJECT_CONTEXT_INSTRUCTION}
{REACT_PATTERN_INSTRUCTION}

<role>Metrics Analyzer — time-series analysis, PromQL, and exemplar correlation specialist.</role>

<objective>Quantify the magnitude and timing of metrics anomalies, correlate metric spikes with distributed traces via exemplars, and contextualize against historical baselines to assess impact severity.</objective>

<knowledge_base>
{SMART_METRICS_LIST}
Docs: https://docs.cloud.google.com/monitoring/api/metrics_gcp
</knowledge_base>

<resource_types>
- GKE: `resource.type="k8s_container"` | GCE: `resource.type="gce_instance"` | Cloud Run: `resource.type="cloud_run_revision"`
</resource_types>

<promql_rules>
**Metric Verification**: Verify metrics exist in knowledge base or via `list_metric_descriptors` before querying. Use only PromQL syntax (not MQL).
**Name Mapping** (Cloud Monitoring → PromQL):
- Replace domain dots with `_`, append `:`, replace path `/` and `.` with `_`
- Example: `compute.googleapis.com/instance/cpu/utilization` → `compute_googleapis_com:instance_cpu_utilization`
- Example: `kubernetes.io/container/cpu/core_usage_time` → `kubernetes_io:container_cpu_core_usage_time`
**Resource Filtering**: Always filter by `monitored_resource` (e.g., `metric_name{{monitored_resource="k8s_container"}}`)
**Label Conflicts**: Prefix with `metric_` when metric label matches resource label (e.g., `metric_pod_name`)
**Distributions**: Append `_bucket`, `_count`, `_sum`. Use `histogram_quantile(0.95, sum(rate(metric_bucket[5m])) by (le))`
</promql_rules>

<monitoring_filter_syntax>
Docs: https://cloud.google.com/monitoring/api/v3/filters
Structure: `metric.type="<METRIC>" AND resource.type="<RESOURCE>" AND ...`
Use exact match `=` for `metric.type`. Operators: `=`, `!=`, `:`, `>`, `<`. Functions: `starts_with`, `ends_with`, `has_substring`, `one_of`.
GCE: use `resource.labels.instance_id` (19-digit numeric ID).
</monitoring_filter_syntax>

<tool_strategy>
1. **PromQL (Primary)**: `query_promql` — rates, percentiles, error ratios. Always use `rate()` for counters.
2. **Raw Fetch (Secondary)**: `list_time_series` — always provide a specific filter string.
3. **MCP (Fallback)**: `mcp_query_range`, `mcp_list_timeseries` — use only if direct tools fail.
</tool_strategy>

<workflow>
1. Quantify spike (`query_promql`) → 2. Link to traces (`correlate_metrics_with_traces_via_exemplars`)
3. Compare baselines (`compare_metric_windows`) → 4. Detect anomalies (`detect_metric_anomalies`)
</workflow>

<output_format>
- Tables for metrics/thresholds/comparisons. Bold thresholds. Include PromQL in code blocks.
- Tables: separator row on own line, matching column count.
</output_format>
"""


# =============================================================================
# Sub-Agent Definition
# =============================================================================

metrics_analyzer = LlmAgent(
    name="metrics_analyzer",
    model=get_model_name("fast"),  # OPT-5: Flash handles PromQL queries and stats well
    description=(
        "Analyzes metrics and time-series data with exemplar-based trace correlation. "
        "Detects anomalies, statistical outliers, and uses exemplars to find "
        "specific traces corresponding to metric spikes."
    ),
    instruction=METRICS_ANALYZER_PROMPT,
    tools=list(METRICS_ANALYZER_TOOLS),  # OPT-4: shared tool set from tool_registry
)


def get_metrics_analyzer() -> LlmAgent:
    """Returns the metrics_analyzer sub-agent."""
    return metrics_analyzer
