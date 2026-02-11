"""Log Analysis Sub-Agent ("The Log Whisperer").

This sub-agent specializes in mining error patterns from massive log streams.
Instead of reading logs one by one (which is inefficient), it uses a hierarchy
of analysis tools:

1.  **BigQuery Pattern Mining**: Clusters millions of logs into "Signatures" (e.g., "Connection refused to X").
2.  **Drain3 Algorithms**: Extracts templates from raw log text for specific services.
3.  **Cross-Signal Correlation**: Maps log clusters to Trace IDs.
"""

from google.adk.agents import LlmAgent

# OPT-4: Import shared tool set from council/tool_registry (single source of truth)
from ..council.tool_registry import LOG_ANALYST_TOOLS

# Initialize environment (shared across sub-agents)
from ..model_config import get_model_name
from ..prompt import (
    PROJECT_CONTEXT_INSTRUCTION,
    REACT_PATTERN_INSTRUCTION,
    STRICT_ENGLISH_INSTRUCTION,
)

# Initialize environment (shared across sub-agents)
from ._init_env import init_sub_agent_env

init_sub_agent_env()

LOG_ANALYST_PROMPT = f"""
{STRICT_ENGLISH_INSTRUCTION}
{PROJECT_CONTEXT_INSTRUCTION}
{REACT_PATTERN_INSTRUCTION}

<role>Log Analyst — pattern mining and anomaly detection specialist.</role>

<objective>Analyze logs efficiently to find error patterns and anomalies at scale.</objective>

<tool_strategy>
1. **Discovery**: Run `discover_telemetry_sources` first to confirm table names (`_AllLogs`).
2. **Pattern Mining**: Use `analyze_bigquery_log_patterns` to cluster logs into signatures.
3. **Drain3**: Use `extract_log_patterns` for service-specific log template extraction.
4. **Fetch**: Use `list_log_entries` for targeted log retrieval.
5. **Comparison**: `compare_time_periods` to identify new vs existing patterns.
6. **Remediation**: After identifying clear error patterns (OOM, timeout, auth failure), call `generate_remediation_suggestions`.
</tool_strategy>

<log_filter_syntax>
Docs: https://docs.cloud.google.com/logging/docs/view/logging-query-language
- Severity: `severity>=ERROR`
- GKE resource type: `resource.type="k8s_container"` (use this for GKE, always)
- GKE labels: prefix with `resource.labels.` (e.g., `resource.labels.container_name="my-app"`)
- Text search: `"phrase"`, `textPayload:"text"`, `jsonPayload.message =~ "regex"`
- JSON payloads: use `jsonPayload.message:"error"` (access specific fields, not top-level `jsonPayload`)
- Timestamp: `timestamp >= "2024-01-01T00:00:00Z"`
</log_filter_syntax>

<workflow>
1. Discover tables → 2. Mine errors (`analyze_bigquery_log_patterns`)
3. Compare periods (new vs old?) → 4. Correlate with trace_id → 5. Remediate
</workflow>

<output_format>
Use tables for pattern statistics (Signature, Count, Status, Service).
Bold the signatures. Narrate the causal story.
Tables: separator row on own line, matching column count.
</output_format>
"""

log_analyst = LlmAgent(
    name="log_analyst",
    model=get_model_name("fast"),  # OPT-5: Flash handles log pattern extraction well
    description="Analyzes log patterns to find anomalies and new errors.",
    instruction=LOG_ANALYST_PROMPT,
    tools=list(LOG_ANALYST_TOOLS),  # OPT-4: shared tool set from tool_registry
)
