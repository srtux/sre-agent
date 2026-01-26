# Tools Catalog & Patterns

SRE Agent tools are categorized into direct observability wrappers and high-level analysis "superpowers."

## Core Tool Categories
1. **Observability**: `fetch_trace`, `list_log_entries`, `list_time_series`.
2. **Analysis**: `analyze_critical_path`, `extract_log_patterns` (Drain3), `detect_metric_anomalies`.
3. **Correlation**: `correlate_metrics_with_traces_via_exemplars`, `correlate_logs_with_trace`.
4. **Reporting**: `generate_remediation_suggestions`, `synthesize_report`.

## Implementation Pattern
- **Decorator**: `@adk_tool` is mandatory for registration.
- **Return Type**: Must return a structured JSON string following the `BaseToolResponse` schema (status, result, metadata).
- **Extension**: New tools are added to `sre_agent/tools/analysis/` and registered in `sre_agent/agent.py` (`TOOL_NAME_MAP` and `base_tools` list).

## GenUI Adapter
Tools that provide custom visualization must be mapped in `sre_agent/tools/analysis/genui_adapter.py` to trigger the correct Flutter widget on the frontend.
