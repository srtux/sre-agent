"""Agent Engine Code Execution Sandbox for large data processing.

This module provides tools for processing large volumes of data in isolated
sandbox environments, preventing LLM context window overflow when tools
return extensive results.

Key Features:
- Sandboxed Python code execution for data analysis
- Pre-built templates for metrics, logs, traces, and time series
- Automatic summarization of large tool outputs
- Custom analysis code execution for ad-hoc processing

Usage:
    # Use processing tools directly
    from sre_agent.tools.sandbox import summarize_metric_descriptors_in_sandbox

    result = await summarize_metric_descriptors_in_sandbox(large_metrics_list)

    # Or use the executor for custom processing
    from sre_agent.tools.sandbox import SandboxExecutor

    async with await SandboxExecutor.create() as executor:
        output = await executor.execute_code("print('Hello from sandbox')")

Environment Variables:
    SRE_AGENT_SANDBOX_ENABLED: Set to "true" to enable sandbox execution.
    SRE_AGENT_SANDBOX_RESOURCE_NAME: Optional pre-created sandbox resource name.
    SRE_AGENT_SANDBOX_TTL: Sandbox time-to-live in seconds (default: 3600).

References:
    - https://docs.cloud.google.com/agent-builder/agent-engine/code-execution/overview
    - https://google.github.io/adk-docs/tools/google-cloud/code-exec-agent-engine/
"""

# Executor and utilities
from .executor import (
    DATA_PROCESSING_TEMPLATES,
    SandboxExecutor,
    get_agent_engine_resource_name,
    get_sandbox_resource_name,
    is_sandbox_enabled,
    process_data_in_sandbox,
)

# Processing tools
from .processors import (
    execute_custom_analysis_in_sandbox,
    get_sandbox_status,
    summarize_log_entries_in_sandbox,
    summarize_metric_descriptors_in_sandbox,
    summarize_time_series_in_sandbox,
    summarize_traces_in_sandbox,
)

# Schemas
from .schemas import (
    CodeExecutionOutput,
    CodeExecutionRequest,
    DataProcessingResult,
    LogEntrySummary,
    MachineConfig,
    MetricDescriptorSummary,
    SandboxConfig,
    SandboxFile,
    SandboxLanguage,
    TimeSeriesSummary,
)

__all__ = [
    "DATA_PROCESSING_TEMPLATES",
    "CodeExecutionOutput",
    "CodeExecutionRequest",
    "DataProcessingResult",
    "LogEntrySummary",
    "MachineConfig",
    "MetricDescriptorSummary",
    "SandboxConfig",
    "SandboxExecutor",
    "SandboxFile",
    "SandboxLanguage",
    "TimeSeriesSummary",
    "execute_custom_analysis_in_sandbox",
    "get_agent_engine_resource_name",
    "get_sandbox_resource_name",
    "get_sandbox_status",
    "is_sandbox_enabled",
    "process_data_in_sandbox",
    "summarize_log_entries_in_sandbox",
    "summarize_metric_descriptors_in_sandbox",
    "summarize_time_series_in_sandbox",
    "summarize_traces_in_sandbox",
]
