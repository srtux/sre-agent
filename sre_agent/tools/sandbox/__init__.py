"""Agent Engine Code Execution Sandbox for large data processing.

This module provides tools for processing large volumes of data in isolated
sandbox environments, preventing LLM context window overflow when tools
return extensive results.

Key Features:
- Sandboxed Python code execution for data analysis
- Pre-built templates for metrics, logs, traces, and time series
- Automatic summarization of large tool outputs
- Custom analysis code execution for ad-hoc processing
- Local execution mode for development (without cloud infrastructure)

Execution Modes:
    1. Agent Engine Mode (automatic when SRE_AGENT_ID is set):
       Uses cloud-based sandboxes for secure, isolated execution.

    2. Local Mode (set SRE_AGENT_LOCAL_EXECUTION=true):
       Uses Python exec() locally for development/testing.
       NOTE: Less secure than Agent Engine sandbox.

Usage:
    # Use processing tools directly
    from sre_agent.tools.sandbox import summarize_metric_descriptors_in_sandbox

    result = await summarize_metric_descriptors_in_sandbox(large_metrics_list)

    # Or use the executor for custom processing
    from sre_agent.tools.sandbox import SandboxExecutor, LocalCodeExecutor

    # Cloud sandbox (Agent Engine)
    async with await SandboxExecutor.create() as executor:
        output = await executor.execute_code("print('Hello from sandbox')")

    # Local execution (development)
    executor = LocalCodeExecutor()
    output = await executor.execute_code("print('Hello locally')")

Environment Variables:
    SRE_AGENT_SANDBOX_ENABLED: Explicitly enable/disable sandbox (overrides auto-detection).
    SRE_AGENT_LOCAL_EXECUTION: Set to "true" to enable local Python execution.
    SRE_AGENT_SANDBOX_RESOURCE_NAME: Optional pre-created sandbox resource name.
    SRE_AGENT_SANDBOX_TTL: Sandbox time-to-live in seconds (default: 3600).
    SRE_AGENT_ID: When set, auto-enables Agent Engine sandbox mode.

References:
    - https://docs.cloud.google.com/agent-builder/agent-engine/code-execution/overview
    - https://google.github.io/adk-docs/tools/google-cloud/code-exec-agent-engine/
"""

# Executor and utilities
from .executor import (
    DATA_PROCESSING_TEMPLATES,
    LocalCodeExecutor,
    SandboxExecutor,
    clear_execution_logs,
    get_agent_engine_resource_name,
    get_code_executor,
    get_recent_execution_logs,
    get_sandbox_resource_name,
    is_local_execution_enabled,
    is_remote_mode,
    is_sandbox_enabled,
    process_data_in_sandbox,
    set_sandbox_event_callback,
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
    SandboxEventType,
    SandboxExecutionEvent,
    SandboxExecutionLog,
    SandboxFile,
    SandboxLanguage,
    TimeSeriesSummary,
)

__all__ = [
    "DATA_PROCESSING_TEMPLATES",
    "CodeExecutionOutput",
    "CodeExecutionRequest",
    "DataProcessingResult",
    "LocalCodeExecutor",
    "LogEntrySummary",
    "MachineConfig",
    "MetricDescriptorSummary",
    "SandboxConfig",
    "SandboxEventType",
    "SandboxExecutionEvent",
    "SandboxExecutionLog",
    "SandboxExecutor",
    "SandboxFile",
    "SandboxLanguage",
    "TimeSeriesSummary",
    "clear_execution_logs",
    "execute_custom_analysis_in_sandbox",
    "get_agent_engine_resource_name",
    "get_code_executor",
    "get_recent_execution_logs",
    "get_sandbox_resource_name",
    "get_sandbox_status",
    "is_local_execution_enabled",
    "is_remote_mode",
    "is_sandbox_enabled",
    "process_data_in_sandbox",
    "set_sandbox_event_callback",
    "summarize_log_entries_in_sandbox",
    "summarize_metric_descriptors_in_sandbox",
    "summarize_time_series_in_sandbox",
    "summarize_traces_in_sandbox",
]
