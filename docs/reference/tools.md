# Tools & Analysis Guide

The SRE Agent's power comes from its massive "Superpower" catalog of specialized tools. This document categorizes these capabilities and provides guidelines for extending the system.

## Tool Categories

### 1. Observability (Core Pixels)
Direct wrappers around GCP APIs for raw data retrieval.
- `fetch_trace`: Retrieve full span JSON.
- `list_log_entries`: Filtered log fetching.
- `list_time_series`: Raw metric retrieval.

### 2. SRE Analysis (The Brain)
High-level tools that perform multi-step analysis or statistical processing.
- `analyze_critical_path`: Calculates which spans determine the total duration.
- `extract_log_patterns`: Clusters millions of log lines into meaningful patterns using the Drain3 algorithm.
- `detect_metric_anomalies`: Uses seasonality and z-scores to identify statistical outliers.
- `analyze_multi_window_burn_rate`: Implements Google's multi-window alerting to distinguish between fast and slow burn rates.

### 3. BigQuery Fleet Analysis
Enables fleet-wide analysis by querying telemetry data exported to BigQuery.
- `analyze_aggregate_metrics`: Health overview of all services.
- `find_exemplar_traces`: Automatically separates "Fast" from "Slow" traces for comparison.

### 4. Cross-Signal Correlation
The "Holy Grail" of observability - linking different pillars.
- `correlate_metrics_with_traces_via_exemplars`: Jumps from a chart spike to the exact request that caused it.
- `correlate_logs_with_trace`: Injects logs into the trace timeline.
- `correlate_changes_with_incident`: Templets GCP Audit Logs to find and rank deployments/config changes by correlation score.

### 5. Remediation & Reporting
Moving from "What is wrong" to "How to fix it."
- `generate_remediation_suggestions`: Proposes GKE restarts, config changes, or rollback commands.
- `generate_postmortem`: Generates a structured, blameless Markdown postmortem based on the investigation findings.
- `synthesize_report`: Generates a high-level executive summary of the investigation.

---

## Tool Implementation Pattern

Every tool follows a strict implementation pattern to ensure compatibility with both the LLM and the GenUI frontend.

### 1. The `@adk_tool` Decorator
Tools must be decorated to be registered in the ADK registry.

### 2. Structured Return Type (`BaseToolResponse`)
Tools should return a consistent structure that includes:
- `status`: SUCCESS or ERROR.
- `result`: The actual analysis data.
- `metadata`: Used by the GenUI adapter to trigger specific widgets.

### 3. Argument Mapping
LLMs are sensitive to parameter naming and descriptions. SRE Agent tools use clear, descriptive arguments with detailed docstrings.

```python
@adk_tool
async def analyze_trace_patterns(
    trace_id: str,
    project_id: str | None = None
) -> BaseToolResponse:
    """Analyze a trace for known SRE anti-patterns (e.g. Circular Dependencies)."""
    # ... logic ...
```

---

## GenUI Integration

A special class of tools integrates with the **GenUI Adapter** (`sre_agent/tools/analysis/genui_adapter.py`).
This adapter intercepts tool outputs and transforms them into JSON schemas recognized by the Flutter frontend. This is how a "Log Pattern" tool becomes a "Log Pattern Viewer widget" in the UI.

## Extending the Catalog

To add a new tool:
1.  Implement the logic in a new file under `sre_agent/tools/analysis/`.
2.  Follow the `BaseToolResponse` pattern.
3.  Register the tool in the `TOOL_NAME_MAP` and `base_tools` list in `sre_agent/agent.py`.
4.  (Optional) Add a layout mapping in `genui_adapter.py` to give it a custom UI widget.

---
*Last verified: 2026-02-02 — Auto SRE Team*
