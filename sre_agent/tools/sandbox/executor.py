"""Agent Engine Sandbox Executor for Code Execution.

This module provides utilities for managing Agent Engine Code Execution sandboxes,
enabling the agent to process large volumes of data in isolated environments
without exceeding LLM context windows.

Usage:
    from sre_agent.tools.sandbox.executor import SandboxExecutor

    executor = await SandboxExecutor.create()
    result = await executor.execute_code("print('Hello')")
    await executor.cleanup()

Reference:
    https://docs.cloud.google.com/agent-builder/agent-engine/code-execution/overview
"""

import json
import logging
import os
import time
import uuid
from collections.abc import Callable
from typing import Any

from .schemas import (
    CodeExecutionOutput,
    MachineConfig,
    SandboxConfig,
    SandboxEventType,
    SandboxExecutionEvent,
    SandboxExecutionLog,
    SandboxFile,
)

logger = logging.getLogger(__name__)

# Global event callback - can be set by the application to receive sandbox events
_event_callback: Callable[[SandboxExecutionEvent], None] | None = None
_execution_logs: list[SandboxExecutionLog] = []  # Store recent execution logs
MAX_EXECUTION_LOGS = 100  # Keep last 100 execution logs


def set_sandbox_event_callback(
    callback: Callable[[SandboxExecutionEvent], None] | None,
) -> None:
    """Set a callback function to receive sandbox execution events.

    This allows applications to monitor and display sandbox activity in real-time.

    Args:
        callback: Function to call with each sandbox event, or None to disable.
    """
    global _event_callback
    _event_callback = callback


def get_recent_execution_logs(limit: int = 10) -> list[SandboxExecutionLog]:
    """Get recent sandbox execution logs.

    Args:
        limit: Maximum number of logs to return.

    Returns:
        List of recent execution logs, most recent first.
    """
    return list(reversed(_execution_logs[-limit:]))


def clear_execution_logs() -> None:
    """Clear all stored execution logs."""
    global _execution_logs
    _execution_logs = []


def _emit_event(event: SandboxExecutionEvent) -> None:
    """Emit a sandbox execution event.

    Args:
        event: The event to emit.
    """
    logger.debug(
        f"Sandbox event: {event.event_type.value} - {event.output_summary or ''}"
    )
    if _event_callback:
        try:
            _event_callback(event)
        except Exception as e:
            logger.warning(f"Event callback failed: {e}")


def _store_execution_log(log: SandboxExecutionLog) -> None:
    """Store an execution log, maintaining the max size limit.

    Args:
        log: The execution log to store.
    """
    global _execution_logs
    _execution_logs.append(log)
    if len(_execution_logs) > MAX_EXECUTION_LOGS:
        _execution_logs = _execution_logs[-MAX_EXECUTION_LOGS:]


# Environment variable keys for sandbox configuration
SANDBOX_RESOURCE_NAME_KEY = "SRE_AGENT_SANDBOX_RESOURCE_NAME"
AGENT_ENGINE_RESOURCE_NAME_KEY = "SRE_AGENT_ID"
SANDBOX_TTL_SECONDS_KEY = "SRE_AGENT_SANDBOX_TTL"
SANDBOX_ENABLED_KEY = "SRE_AGENT_SANDBOX_ENABLED"
LOCAL_EXECUTION_KEY = "SRE_AGENT_LOCAL_EXECUTION"


def is_remote_mode() -> bool:
    """Check if running in Agent Engine (remote mode)."""
    return bool(os.environ.get(AGENT_ENGINE_RESOURCE_NAME_KEY))


def is_local_execution_enabled() -> bool:
    """Check if local code execution is enabled.

    Local execution uses Python's exec() in a restricted namespace.
    This is less secure than Agent Engine sandbox but allows testing locally.
    """
    return os.environ.get(LOCAL_EXECUTION_KEY, "false").lower() == "true"


def is_sandbox_enabled() -> bool:
    """Check if sandbox execution is enabled.

    Sandbox is enabled if:
    1. Explicitly set via SRE_AGENT_SANDBOX_ENABLED=true, OR
    2. Running in Agent Engine (SRE_AGENT_ID is set), OR
    3. Local execution is enabled via SRE_AGENT_LOCAL_EXECUTION=true
    """
    # Explicit enable/disable takes precedence
    explicit_setting = os.environ.get(SANDBOX_ENABLED_KEY, "").lower()
    if explicit_setting == "true":
        return True
    if explicit_setting == "false":
        return False

    # Auto-enable in Agent Engine mode
    if is_remote_mode():
        return True

    # Check local execution mode
    if is_local_execution_enabled():
        return True

    return False


def get_sandbox_resource_name() -> str | None:
    """Get configured sandbox resource name from environment."""
    return os.environ.get(SANDBOX_RESOURCE_NAME_KEY)


def get_agent_engine_resource_name() -> str | None:
    """Get Agent Engine resource name from environment.

    Format: projects/{project}/locations/{location}/reasoningEngines/{engine_id}
    """
    agent_id = os.environ.get(AGENT_ENGINE_RESOURCE_NAME_KEY)
    if not agent_id:
        return None

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        return None

    return f"projects/{project}/locations/{location}/reasoningEngines/{agent_id}"


class SandboxExecutor:
    """Manages Agent Engine sandbox lifecycle and code execution.

    This class provides an async context manager pattern for sandbox operations,
    automatically handling sandbox creation, code execution, and cleanup.

    Attributes:
        sandbox_name: Full resource name of the sandbox.
        config: Sandbox configuration settings.
        _client: Vertex AI client instance.
    """

    def __init__(
        self,
        sandbox_name: str | None = None,
        config: SandboxConfig | None = None,
    ) -> None:
        """Initialize the sandbox executor.

        Args:
            sandbox_name: Existing sandbox resource name, or None to create new.
            config: Configuration for sandbox creation.
        """
        self.sandbox_name = sandbox_name
        self.config = config or SandboxConfig()
        self._client: Any = None
        self._owns_sandbox = sandbox_name is None  # We created it, we clean it up

    @classmethod
    async def create(
        cls,
        sandbox_name: str | None = None,
        config: SandboxConfig | None = None,
        project_id: str | None = None,
        location: str | None = None,
    ) -> "SandboxExecutor":
        """Create a SandboxExecutor with an active sandbox.

        Args:
            sandbox_name: Use existing sandbox, or None to auto-create.
            config: Configuration for new sandbox creation.
            project_id: GCP project ID (defaults to env GOOGLE_CLOUD_PROJECT).
            location: GCP location (defaults to us-central1).

        Returns:
            Initialized SandboxExecutor with ready sandbox.

        Raises:
            RuntimeError: If sandbox creation fails.
        """
        executor = cls(sandbox_name=sandbox_name, config=config)

        # Check environment for pre-configured sandbox
        if not executor.sandbox_name:
            executor.sandbox_name = get_sandbox_resource_name()

        # If no sandbox name, create one
        if not executor.sandbox_name:
            await executor._create_sandbox(project_id, location)

        return executor

    async def _create_sandbox(
        self,
        project_id: str | None = None,
        location: str | None = None,
    ) -> None:
        """Create a new sandbox environment.

        Args:
            project_id: GCP project ID.
            location: GCP location.
        """
        from fastapi.concurrency import run_in_threadpool

        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project_id:
            raise RuntimeError(
                "Project ID required for sandbox creation. "
                "Set GOOGLE_CLOUD_PROJECT environment variable."
            )

        logger.info(f"Creating sandbox in {project_id}/{location}")

        try:
            # Import here to avoid loading at module level
            import vertexai
            from vertexai import types

            # Initialize client
            client = vertexai.Client(project=project_id, location=location)

            # Create or get agent engine
            agent_engine_name = get_agent_engine_resource_name()
            if not agent_engine_name:
                # Create a temporary agent engine for sandbox
                logger.info("Creating temporary agent engine for sandbox")
                agent_engine = await run_in_threadpool(client.agent_engines.create)
                agent_engine_name = agent_engine.api_resource.name
                logger.info(f"Created agent engine: {agent_engine_name}")

            # Create sandbox
            display_name = self.config.display_name or "sre-agent-data-processor"
            ttl = f"{self.config.ttl_seconds}s"

            spec = {
                "code_execution_environment": {
                    "code_language": self.config.language.value,
                }
            }

            # Add machine config if not default
            if self.config.machine_config != MachineConfig.DEFAULT:
                spec["code_execution_environment"]["machine_config"] = (
                    self.config.machine_config.value
                )

            operation = await run_in_threadpool(
                lambda: client.agent_engines.sandboxes.create(
                    spec=spec,
                    name=agent_engine_name,
                    config=types.CreateAgentEngineSandboxConfig(
                        display_name=display_name, ttl=ttl
                    ),
                )
            )

            self.sandbox_name = operation.response.name
            self._client = client
            self._owns_sandbox = True
            logger.info(f"Created sandbox: {self.sandbox_name}")

        except ImportError as e:
            logger.warning(
                f"Vertex AI SDK not available for sandbox creation: {e}. "
                "Install google-cloud-aiplatform[agent-engines] for sandbox support."
            )
            raise RuntimeError(f"Sandbox creation requires Vertex AI SDK: {e}") from e
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}", exc_info=True)
            raise RuntimeError(f"Sandbox creation failed: {e}") from e

    async def execute_code(
        self,
        code: str,
        input_files: list[SandboxFile] | None = None,
        ttl_extension_seconds: int | None = None,
    ) -> CodeExecutionOutput:
        """Execute code in the sandbox.

        Args:
            code: Python code to execute.
            input_files: Optional files to make available in sandbox.
            ttl_extension_seconds: Extend sandbox TTL after execution.

        Returns:
            CodeExecutionOutput with stdout, stderr, and output files.
        """
        if not self.sandbox_name:
            raise RuntimeError("No sandbox available. Call create() first.")

        from fastapi.concurrency import run_in_threadpool

        try:
            import vertexai

            if not self._client:
                project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
                location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
                self._client = vertexai.Client(project=project_id, location=location)

            # Prepare input data
            input_data: dict[str, Any] = {"code": code}

            if input_files:
                input_data["files"] = [
                    {"name": f.name, "content": f.content} for f in input_files
                ]

            # Execute code
            logger.debug(f"Executing code in sandbox: {self.sandbox_name}")
            response = await run_in_threadpool(
                lambda: self._client.agent_engines.sandboxes.execute_code(
                    name=self.sandbox_name, input_data=input_data
                )
            )

            # Parse response
            stdout = ""
            stderr = ""
            output_files: list[SandboxFile] = []

            if hasattr(response, "stdout") and response.stdout:
                stdout = (
                    response.stdout.decode("utf-8")
                    if isinstance(response.stdout, bytes)
                    else str(response.stdout)
                )

            if hasattr(response, "stderr") and response.stderr:
                stderr = (
                    response.stderr.decode("utf-8")
                    if isinstance(response.stderr, bytes)
                    else str(response.stderr)
                )

            if hasattr(response, "files") and response.files:
                for file_info in response.files:
                    output_files.append(
                        SandboxFile(
                            name=file_info.get("name", "output"),
                            content=file_info.get("content", b""),
                        )
                    )

            return CodeExecutionOutput(
                stdout=stdout,
                stderr=stderr,
                output_files=output_files,
            )

        except Exception as e:
            logger.error(f"Code execution failed: {e}", exc_info=True)
            return CodeExecutionOutput(
                stdout="",
                stderr="",
                execution_error=str(e),
            )

    async def execute_data_processing(
        self,
        data: list[dict[str, Any]] | dict[str, Any],
        processing_code: str,
        data_variable_name: str = "data",
    ) -> CodeExecutionOutput:
        """Execute data processing code with pre-loaded data.

        This method serializes data to JSON, loads it in the sandbox,
        and executes the provided processing code.

        Args:
            data: Data to process (will be JSON serialized).
            processing_code: Python code to process the data.
            data_variable_name: Variable name to assign the data.

        Returns:
            CodeExecutionOutput with processing results.
        """
        # Serialize data to JSON file
        json_bytes = json.dumps(data, default=str).encode("utf-8")
        input_file = SandboxFile(name="input_data.json", content=json_bytes)

        # Wrap code to load data first
        full_code = f"""
import json

# Load input data
with open("input_data.json", "r") as f:
    {data_variable_name} = json.load(f)

# User processing code
{processing_code}
"""

        return await self.execute_code(full_code, input_files=[input_file])

    async def cleanup(self) -> None:
        """Delete the sandbox if we created it."""
        if not self._owns_sandbox or not self.sandbox_name:
            return

        try:
            from fastapi.concurrency import run_in_threadpool

            if self._client:
                await run_in_threadpool(
                    lambda: self._client.agent_engines.sandboxes.delete(
                        name=self.sandbox_name
                    )
                )
                logger.info(f"Deleted sandbox: {self.sandbox_name}")
        except Exception as e:
            logger.warning(f"Failed to delete sandbox: {e}")

    async def __aenter__(self) -> "SandboxExecutor":
        """Async context manager entry."""
        if not self.sandbox_name:
            await self._create_sandbox()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit with cleanup."""
        await self.cleanup()


class LocalCodeExecutor:
    """Local code executor for development environments.

    This executor runs Python code locally using exec() in a restricted namespace.
    It provides similar functionality to SandboxExecutor but without cloud infrastructure.

    SECURITY NOTE: This executor does NOT provide the same isolation as Agent Engine
    sandboxes. It should only be used in trusted development environments.

    Usage:
        executor = LocalCodeExecutor()
        output = await executor.execute_code("print('Hello')")
    """

    def __init__(self) -> None:
        """Initialize the local code executor."""
        self._temp_dir: str | None = None

    async def execute_code(
        self,
        code: str,
        input_files: list[SandboxFile] | None = None,
        ttl_extension_seconds: int | None = None,
    ) -> CodeExecutionOutput:
        """Execute code locally using Python's exec().

        Args:
            code: Python code to execute.
            input_files: Optional files to make available.
            ttl_extension_seconds: Ignored (for API compatibility).

        Returns:
            CodeExecutionOutput with stdout, stderr, and output files.
        """
        import io
        import tempfile
        from contextlib import redirect_stderr, redirect_stdout

        start_time = time.time()

        # Emit start event
        _emit_event(
            SandboxExecutionEvent(
                event_type=SandboxEventType.CODE_EXECUTION_STARTED,
                execution_mode="local",
                code_snippet=code[:500] if code else None,
                input_data_summary=f"{len(input_files or [])} input files",
            )
        )

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        output_files: list[SandboxFile] = []

        try:
            # Create a temporary directory for file I/O
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write input files
                if input_files:
                    for f in input_files:
                        file_path = os.path.join(temp_dir, f.name)
                        with open(file_path, "wb") as fh:
                            fh.write(f.content)

                # Change to temp directory for file operations
                original_cwd = os.getcwd()
                os.chdir(temp_dir)

                try:
                    # Create restricted namespace with safe builtins
                    safe_builtins = {
                        "print": print,
                        "len": len,
                        "range": range,
                        "enumerate": enumerate,
                        "zip": zip,
                        "map": map,
                        "filter": filter,
                        "sorted": sorted,
                        "reversed": reversed,
                        "list": list,
                        "dict": dict,
                        "set": set,
                        "tuple": tuple,
                        "str": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "None": None,
                        "True": True,
                        "False": False,
                        "min": min,
                        "max": max,
                        "sum": sum,
                        "abs": abs,
                        "round": round,
                        "isinstance": isinstance,
                        "hasattr": hasattr,
                        "getattr": getattr,
                        "open": open,  # Needed for file I/O
                        "__import__": __import__,  # Needed for imports
                    }

                    namespace: dict[str, Any] = {"__builtins__": safe_builtins}

                    # Execute code with captured output
                    with (
                        redirect_stdout(stdout_capture),
                        redirect_stderr(stderr_capture),
                    ):
                        exec(code, namespace)

                    # Check for output files
                    for filename in os.listdir(temp_dir):
                        if filename.startswith("output") or filename.endswith(".json"):
                            file_path = os.path.join(temp_dir, filename)
                            if os.path.isfile(file_path):
                                with open(file_path, "rb") as fh:
                                    output_files.append(
                                        SandboxFile(name=filename, content=fh.read())
                                    )

                finally:
                    os.chdir(original_cwd)

            duration_ms = (time.time() - start_time) * 1000
            output = CodeExecutionOutput(
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                output_files=output_files,
            )

            # Emit completion event
            _emit_event(
                SandboxExecutionEvent(
                    event_type=SandboxEventType.CODE_EXECUTION_COMPLETED,
                    execution_mode="local",
                    duration_ms=duration_ms,
                    output_summary=f"stdout: {len(output.stdout)} chars, {len(output_files)} output files",
                )
            )

            return output

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Local code execution failed: {e}", exc_info=True)

            # Emit failure event
            _emit_event(
                SandboxExecutionEvent(
                    event_type=SandboxEventType.CODE_EXECUTION_FAILED,
                    execution_mode="local",
                    duration_ms=duration_ms,
                    error_message=str(e),
                )
            )

            return CodeExecutionOutput(
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                execution_error=str(e),
            )

    async def execute_data_processing(
        self,
        data: list[dict[str, Any]] | dict[str, Any],
        processing_code: str,
        data_variable_name: str = "data",
    ) -> CodeExecutionOutput:
        """Execute data processing code with pre-loaded data.

        Args:
            data: Data to process (will be JSON serialized).
            processing_code: Python code to process the data.
            data_variable_name: Variable name to assign the data.

        Returns:
            CodeExecutionOutput with processing results.
        """
        json_bytes = json.dumps(data, default=str).encode("utf-8")
        input_file = SandboxFile(name="input_data.json", content=json_bytes)

        full_code = f"""
import json

# Load input data
with open("input_data.json", "r") as f:
    {data_variable_name} = json.load(f)

# User processing code
{processing_code}
"""

        return await self.execute_code(full_code, input_files=[input_file])

    async def cleanup(self) -> None:
        """No-op for local executor (cleanup happens automatically)."""
        pass

    async def __aenter__(self) -> "LocalCodeExecutor":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.cleanup()


async def get_code_executor() -> SandboxExecutor | LocalCodeExecutor:
    """Get the appropriate code executor based on environment.

    Returns:
        SandboxExecutor if running in Agent Engine, LocalCodeExecutor otherwise.
    """
    if is_remote_mode():
        # Use Agent Engine sandbox
        return await SandboxExecutor.create()
    elif is_local_execution_enabled():
        # Use local executor
        return LocalCodeExecutor()
    else:
        # Default to sandbox executor (will fail if not configured)
        return await SandboxExecutor.create()


# Pre-built code templates for common data processing tasks
DATA_PROCESSING_TEMPLATES = {
    "summarize_metrics": """
import json
from collections import defaultdict

# Analyze metric descriptors
result = {
    "total_count": len(data),
    "by_metric_kind": defaultdict(int),
    "by_value_type": defaultdict(int),
    "top_metrics": [],
    "summary": ""
}

for metric in data:
    result["by_metric_kind"][metric.get("metric_kind", "UNKNOWN")] += 1
    result["by_value_type"][metric.get("value_type", "UNKNOWN")] += 1

# Get top metrics (first 20)
result["top_metrics"] = [
    {
        "type": m.get("type", ""),
        "display_name": m.get("display_name", ""),
        "description": m.get("description", "")[:100],
    }
    for m in data[:20]
]

result["summary"] = f"Found {result['total_count']} metric descriptors. "
result["summary"] += f"Types: {dict(result['by_metric_kind'])}. "
result["summary"] += f"Value types: {dict(result['by_value_type'])}."

# Convert defaultdicts to regular dicts for JSON
result["by_metric_kind"] = dict(result["by_metric_kind"])
result["by_value_type"] = dict(result["by_value_type"])

# Write output
with open("output.json", "w") as f:
    json.dump(result, f)

print(json.dumps(result))
""",
    "summarize_timeseries": """
import json
from collections import defaultdict

result = {
    "total_series": len(data),
    "by_metric_type": defaultdict(int),
    "by_resource_type": defaultdict(int),
    "statistics": [],
    "summary": ""
}

for series in data:
    metric_type = series.get("metric", {}).get("type", "unknown")
    resource_type = series.get("resource", {}).get("type", "unknown")
    result["by_metric_type"][metric_type] += 1
    result["by_resource_type"][resource_type] += 1

    # Calculate stats for each series
    points = series.get("points", [])
    if points:
        values = [p.get("value", 0) for p in points if p.get("value") is not None]
        if values:
            result["statistics"].append({
                "metric_type": metric_type,
                "resource_type": resource_type,
                "resource_labels": series.get("resource", {}).get("labels", {}),
                "point_count": len(points),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else None,
            })

# Truncate statistics to top 50 by point count
result["statistics"] = sorted(
    result["statistics"],
    key=lambda x: x["point_count"],
    reverse=True
)[:50]

result["by_metric_type"] = dict(result["by_metric_type"])
result["by_resource_type"] = dict(result["by_resource_type"])

result["summary"] = f"Analyzed {result['total_series']} time series. "
result["summary"] += f"Metric types: {len(result['by_metric_type'])}. "
result["summary"] += f"Resource types: {len(result['by_resource_type'])}."

with open("output.json", "w") as f:
    json.dump(result, f)

print(json.dumps(result))
""",
    "summarize_logs": """
import json
from collections import defaultdict

result = {
    "total_entries": len(data),
    "by_severity": defaultdict(int),
    "by_resource_type": defaultdict(int),
    "error_messages": defaultdict(int),
    "time_range": {"earliest": None, "latest": None},
    "sample_entries": [],
    "summary": ""
}

for entry in data:
    severity = entry.get("severity", "DEFAULT")
    result["by_severity"][severity] += 1

    resource = entry.get("resource", {})
    resource_type = resource.get("type", "unknown")
    result["by_resource_type"][resource_type] += 1

    # Track error messages
    if severity in ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]:
        payload = entry.get("payload", "")
        if isinstance(payload, str) and len(payload) < 200:
            result["error_messages"][payload[:100]] += 1

    # Track time range
    timestamp = entry.get("timestamp", "")
    if timestamp:
        if not result["time_range"]["earliest"] or timestamp < result["time_range"]["earliest"]:
            result["time_range"]["earliest"] = timestamp
        if not result["time_range"]["latest"] or timestamp > result["time_range"]["latest"]:
            result["time_range"]["latest"] = timestamp

# Sample entries (first 10 of each severity)
severity_samples = defaultdict(list)
for entry in data:
    sev = entry.get("severity", "DEFAULT")
    if len(severity_samples[sev]) < 3:
        severity_samples[sev].append({
            "timestamp": entry.get("timestamp", ""),
            "severity": sev,
            "payload": str(entry.get("payload", ""))[:200],
        })

result["sample_entries"] = [
    sample
    for samples in severity_samples.values()
    for sample in samples
][:20]

# Top error messages
result["top_error_messages"] = sorted(
    [{"message": k, "count": v} for k, v in result["error_messages"].items()],
    key=lambda x: x["count"],
    reverse=True
)[:10]

result["by_severity"] = dict(result["by_severity"])
result["by_resource_type"] = dict(result["by_resource_type"])
del result["error_messages"]

result["summary"] = f"Analyzed {result['total_entries']} log entries. "
result["summary"] += f"Severities: {dict(result['by_severity'])}. "
if result["time_range"]["earliest"]:
    result["summary"] += f"Time range: {result['time_range']['earliest']} to {result['time_range']['latest']}."

with open("output.json", "w") as f:
    json.dump(result, f)

print(json.dumps(result))
""",
    "summarize_traces": """
import json
from collections import defaultdict

result = {
    "total_traces": len(data),
    "by_service": defaultdict(int),
    "by_status": defaultdict(int),
    "latency_stats": {
        "min_ms": float("inf"),
        "max_ms": 0,
        "total_ms": 0,
        "count": 0
    },
    "error_traces": [],
    "slow_traces": [],
    "summary": ""
}

SLOW_THRESHOLD_MS = 1000  # 1 second

for trace in data:
    spans = trace.get("spans", [])

    # Find root span for duration
    root_duration_ms = 0
    has_error = False
    services = set()

    for span in spans:
        # Track services
        labels = span.get("labels", {})
        service = labels.get("service.name") or labels.get("g.co/r/service_name", "unknown")
        services.add(service)

        # Check for errors
        status = span.get("status", {})
        if status.get("code") == 2 or span.get("has_error"):
            has_error = True

        # Track duration for root spans
        if not span.get("parent_span_id"):
            duration = span.get("duration_ms", 0)
            root_duration_ms = max(root_duration_ms, duration)

    for svc in services:
        result["by_service"][svc] += 1

    result["by_status"]["error" if has_error else "ok"] += 1

    if root_duration_ms > 0:
        result["latency_stats"]["min_ms"] = min(result["latency_stats"]["min_ms"], root_duration_ms)
        result["latency_stats"]["max_ms"] = max(result["latency_stats"]["max_ms"], root_duration_ms)
        result["latency_stats"]["total_ms"] += root_duration_ms
        result["latency_stats"]["count"] += 1

    # Track problem traces
    trace_id = trace.get("trace_id", "unknown")
    if has_error and len(result["error_traces"]) < 10:
        result["error_traces"].append({"trace_id": trace_id, "duration_ms": root_duration_ms})
    if root_duration_ms > SLOW_THRESHOLD_MS and len(result["slow_traces"]) < 10:
        result["slow_traces"].append({"trace_id": trace_id, "duration_ms": root_duration_ms})

# Calculate average
if result["latency_stats"]["count"] > 0:
    result["latency_stats"]["avg_ms"] = result["latency_stats"]["total_ms"] / result["latency_stats"]["count"]
else:
    result["latency_stats"]["avg_ms"] = 0

if result["latency_stats"]["min_ms"] == float("inf"):
    result["latency_stats"]["min_ms"] = 0

result["by_service"] = dict(result["by_service"])
result["by_status"] = dict(result["by_status"])

result["summary"] = f"Analyzed {result['total_traces']} traces. "
result["summary"] += f"Services: {list(result['by_service'].keys())[:5]}. "
result["summary"] += f"Errors: {result['by_status'].get('error', 0)}. "
result["summary"] += f"Avg latency: {result['latency_stats']['avg_ms']:.2f}ms."

with open("output.json", "w") as f:
    json.dump(result, f)

print(json.dumps(result))
""",
}


async def process_data_in_sandbox(
    data: list[dict[str, Any]] | dict[str, Any],
    template_name: str,
    sandbox_executor: SandboxExecutor | LocalCodeExecutor | None = None,
) -> dict[str, Any]:
    """Process data using a predefined template in a sandbox or local executor.

    Automatically selects the appropriate executor based on environment:
    - Agent Engine mode: Uses cloud sandbox for isolation
    - Local mode with SRE_AGENT_LOCAL_EXECUTION=true: Uses local Python exec()

    All execution events are logged and can be retrieved via get_recent_execution_logs()
    for transparency into sandbox operations.

    Args:
        data: Data to process.
        template_name: Name of processing template to use.
        sandbox_executor: Optional existing executor, or creates new one.

    Returns:
        Processed results as a dictionary.

    Raises:
        ValueError: If template name is unknown.
        RuntimeError: If processing fails.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    events: list[SandboxExecutionEvent] = []

    if template_name not in DATA_PROCESSING_TEMPLATES:
        raise ValueError(
            f"Unknown template: {template_name}. "
            f"Available: {list(DATA_PROCESSING_TEMPLATES.keys())}"
        )

    template_code = DATA_PROCESSING_TEMPLATES[template_name]

    # Determine execution mode and input size
    execution_mode = "local" if is_local_execution_enabled() else "agent_engine"
    input_count = len(data) if isinstance(data, list) else 1

    # Emit data loading event
    data_event = SandboxExecutionEvent(
        event_type=SandboxEventType.DATA_LOADED,
        execution_mode=execution_mode,
        input_data_summary=f"{input_count} items, template: {template_name}",
    )
    _emit_event(data_event)
    events.append(data_event)

    # Use provided executor or create appropriate one based on environment
    if sandbox_executor:
        output = await sandbox_executor.execute_data_processing(
            data=data, processing_code=template_code
        )
    else:
        executor = await get_code_executor()
        async with executor:
            output = await executor.execute_data_processing(
                data=data, processing_code=template_code
            )

    # Parse output
    total_duration_ms = (time.time() - start_time) * 1000

    if output.execution_error:
        # Store failed execution log
        _store_execution_log(
            SandboxExecutionLog(
                request_id=request_id,
                template_name=template_name,
                execution_mode=execution_mode,
                events=events,
                total_duration_ms=total_duration_ms,
                success=False,
                input_item_count=input_count,
                output_item_count=0,
            )
        )
        raise RuntimeError(f"Sandbox processing failed: {output.execution_error}")

    try:
        # Try to parse JSON from stdout
        result = json.loads(output.stdout)
        output_count = len(result) if isinstance(result, list) else 1

        # Emit output event
        output_event = SandboxExecutionEvent(
            event_type=SandboxEventType.OUTPUT_GENERATED,
            execution_mode=execution_mode,
            duration_ms=total_duration_ms,
            output_summary=f"Generated {output_count} output items",
        )
        _emit_event(output_event)
        events.append(output_event)

        # Store successful execution log
        _store_execution_log(
            SandboxExecutionLog(
                request_id=request_id,
                template_name=template_name,
                execution_mode=execution_mode,
                events=events,
                total_duration_ms=total_duration_ms,
                success=True,
                input_item_count=input_count,
                output_item_count=output_count,
            )
        )

        return result  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        # Try output file
        for file in output.output_files:
            if file.name == "output.json":
                result = json.loads(file.content.decode("utf-8"))
                output_count = len(result) if isinstance(result, list) else 1

                # Store successful execution log
                _store_execution_log(
                    SandboxExecutionLog(
                        request_id=request_id,
                        template_name=template_name,
                        execution_mode=execution_mode,
                        events=events,
                        total_duration_ms=total_duration_ms,
                        success=True,
                        input_item_count=input_count,
                        output_item_count=output_count,
                    )
                )

                return result  # type: ignore[no-any-return]

        # Store failed execution log
        _store_execution_log(
            SandboxExecutionLog(
                request_id=request_id,
                template_name=template_name,
                execution_mode=execution_mode,
                events=events,
                total_duration_ms=total_duration_ms,
                success=False,
                input_item_count=input_count,
                output_item_count=0,
            )
        )

        raise RuntimeError(
            f"Could not parse sandbox output: {output.stdout[:500]}"
        ) from e
