"""Tests for sandbox executor."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.tools.sandbox.executor import (
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
from sre_agent.tools.sandbox.schemas import (
    CodeExecutionOutput,
    MachineConfig,
    SandboxConfig,
    SandboxExecutionEvent,
    SandboxFile,
    SandboxLanguage,
)


class TestIsEnabled:
    def test_sandbox_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert is_sandbox_enabled() is False

    def test_sandbox_enabled_when_true(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            assert is_sandbox_enabled() is True

    def test_sandbox_enabled_case_insensitive(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "TRUE"}):
            assert is_sandbox_enabled() is True

    def test_sandbox_disabled_when_false(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}):
            assert is_sandbox_enabled() is False


class TestGetSandboxResourceName:
    def test_returns_none_when_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert get_sandbox_resource_name() is None

    def test_returns_value_when_set(self) -> None:
        expected = "projects/test/locations/us-central1/reasoningEngines/123/sandboxEnvironments/456"
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_RESOURCE_NAME": expected}):
            assert get_sandbox_resource_name() == expected


class TestGetAgentEngineResourceName:
    def test_returns_none_when_agent_id_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert get_agent_engine_resource_name() is None

    def test_returns_none_when_project_not_set(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_ID": "123"}, clear=True):
            assert get_agent_engine_resource_name() is None

    def test_returns_resource_name_when_configured(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SRE_AGENT_ID": "engine-123",
                "GOOGLE_CLOUD_PROJECT": "my-project",
                "GOOGLE_CLOUD_LOCATION": "us-central1",
            },
        ):
            result = get_agent_engine_resource_name()
            assert (
                result
                == "projects/my-project/locations/us-central1/reasoningEngines/engine-123"
            )

    def test_uses_default_location(self) -> None:
        with patch.dict(
            os.environ,
            {"SRE_AGENT_ID": "engine-123", "GOOGLE_CLOUD_PROJECT": "my-project"},
            clear=True,
        ):
            result = get_agent_engine_resource_name()
            assert "us-central1" in result  # type: ignore[operator]


class TestSandboxExecutor:
    def test_init_with_sandbox_name(self) -> None:
        executor = SandboxExecutor(sandbox_name="test-sandbox")
        assert executor.sandbox_name == "test-sandbox"
        assert executor._owns_sandbox is False

    def test_init_without_sandbox_name(self) -> None:
        executor = SandboxExecutor()
        assert executor.sandbox_name is None
        assert executor._owns_sandbox is True

    def test_init_with_config(self) -> None:
        config = SandboxConfig(
            language=SandboxLanguage.JAVASCRIPT,
            ttl_seconds=7200,
        )
        executor = SandboxExecutor(config=config)
        assert executor.config.language == SandboxLanguage.JAVASCRIPT
        assert executor.config.ttl_seconds == 7200

    def test_default_config(self) -> None:
        executor = SandboxExecutor()
        assert executor.config.language == SandboxLanguage.PYTHON
        assert executor.config.machine_config == MachineConfig.DEFAULT

    @pytest.mark.asyncio
    async def test_create_with_existing_sandbox(self) -> None:
        executor = await SandboxExecutor.create(sandbox_name="existing-sandbox")
        assert executor.sandbox_name == "existing-sandbox"

    @pytest.mark.asyncio
    async def test_create_uses_env_sandbox(self) -> None:
        with patch.dict(
            os.environ,
            {"SRE_AGENT_SANDBOX_RESOURCE_NAME": "env-sandbox"},
        ):
            executor = await SandboxExecutor.create()
            assert executor.sandbox_name == "env-sandbox"

    @pytest.mark.asyncio
    async def test_execute_code_without_sandbox_raises(self) -> None:
        executor = SandboxExecutor()
        # No sandbox name set
        with pytest.raises(RuntimeError, match="No sandbox available"):
            await executor.execute_code("print('test')")

    @pytest.mark.asyncio
    async def test_execute_code_success(self) -> None:
        executor = SandboxExecutor(sandbox_name="test-sandbox")

        # Mock the vertexai SDK response: ExecuteSandboxEnvironmentResponse
        # has .outputs (list of Chunk).  stdout/stderr arrive in a JSON chunk
        # using keys "msg_out" and "msg_err" per the Vertex AI documentation.
        mock_stdout_chunk = MagicMock()
        mock_stdout_chunk.mime_type = "application/json"
        mock_stdout_chunk.data = json.dumps(
            {"msg_out": '{"result": "success"}', "msg_err": ""}
        ).encode("utf-8")
        mock_stdout_chunk.metadata = None  # No file_name → stdout/stderr

        mock_response = MagicMock()
        mock_response.outputs = [mock_stdout_chunk]

        mock_client = MagicMock()
        mock_client.agent_engines.sandboxes.execute_code.return_value = mock_response

        with patch.dict("sys.modules", {"vertexai": MagicMock()}):
            import sys

            sys.modules["vertexai"].Client.return_value = mock_client
            with patch("fastapi.concurrency.run_in_threadpool") as mock_threadpool:
                # Make run_in_threadpool execute the lambda synchronously
                mock_threadpool.side_effect = lambda fn: fn()

                output = await executor.execute_code("print('hello')")

        assert output.stdout == '{"result": "success"}'
        assert output.stderr == ""
        assert output.execution_error is None

    @pytest.mark.asyncio
    async def test_execute_code_with_output_files(self) -> None:
        """Output file chunks are returned as SandboxFile objects."""
        executor = SandboxExecutor(sandbox_name="test-sandbox")

        # stdout/stderr chunk (uses msg_out/msg_err per Vertex AI docs)
        mock_stdout_chunk = MagicMock()
        mock_stdout_chunk.mime_type = "application/json"
        mock_stdout_chunk.data = json.dumps({"msg_out": "done", "msg_err": ""}).encode(
            "utf-8"
        )
        mock_stdout_chunk.metadata = None

        # File chunk with file_name in metadata.attributes
        mock_file_chunk = MagicMock()
        mock_file_chunk.mime_type = "application/json"
        mock_file_chunk.data = b'{"from_file": true}'
        mock_file_chunk.metadata = MagicMock()
        mock_file_chunk.metadata.attributes = {"file_name": b"output.json"}

        mock_response = MagicMock()
        mock_response.outputs = [mock_stdout_chunk, mock_file_chunk]

        mock_client = MagicMock()
        mock_client.agent_engines.sandboxes.execute_code.return_value = mock_response

        with patch.dict("sys.modules", {"vertexai": MagicMock()}):
            import sys

            sys.modules["vertexai"].Client.return_value = mock_client
            with patch("fastapi.concurrency.run_in_threadpool") as mock_threadpool:
                mock_threadpool.side_effect = lambda fn: fn()

                output = await executor.execute_code("print('done')")

        assert output.stdout == "done"
        assert len(output.output_files) == 1
        assert output.output_files[0].name == "output.json"
        assert output.output_files[0].content == b'{"from_file": true}'

    @pytest.mark.asyncio
    async def test_execute_code_handles_error(self) -> None:
        executor = SandboxExecutor(sandbox_name="test-sandbox")

        with patch.dict("sys.modules", {"vertexai": MagicMock()}):
            import sys

            sys.modules["vertexai"].Client.side_effect = Exception("API Error")

            output = await executor.execute_code("print('hello')")

        assert output.execution_error is not None
        assert "API Error" in output.execution_error

    @pytest.mark.asyncio
    async def test_execute_data_processing(self) -> None:
        executor = SandboxExecutor(sandbox_name="test-sandbox")

        # Mock execute_code
        executor.execute_code = AsyncMock(  # type: ignore[method-assign]
            return_value=CodeExecutionOutput(
                stdout='{"count": 10}',
                stderr="",
            )
        )

        output = await executor.execute_data_processing(
            data=[{"id": i} for i in range(10)],
            processing_code="print(len(data))",
        )

        assert output.stdout == '{"count": 10}'
        # Verify execute_code was called with input files
        executor.execute_code.assert_called_once()  # type: ignore[union-attr]
        call_args = executor.execute_code.call_args  # type: ignore[union-attr]
        assert len(call_args.kwargs.get("input_files", [])) == 1

    @pytest.mark.asyncio
    async def test_cleanup_when_owns_sandbox(self) -> None:
        executor = SandboxExecutor()  # owns_sandbox = True
        executor.sandbox_name = "test-sandbox"

        mock_client = MagicMock()
        executor._client = mock_client

        with patch("fastapi.concurrency.run_in_threadpool") as mock_threadpool:
            mock_threadpool.side_effect = lambda fn: fn()
            await executor.cleanup()

        mock_client.agent_engines.sandboxes.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_skipped_when_not_owned(self) -> None:
        executor = SandboxExecutor(sandbox_name="external-sandbox")
        # owns_sandbox = False because we passed sandbox_name

        mock_client = MagicMock()
        executor._client = mock_client

        await executor.cleanup()

        mock_client.agent_engines.sandboxes.delete.assert_not_called()


class TestDataProcessingTemplates:
    def test_summarize_metrics_template_exists(self) -> None:
        assert "summarize_metrics" in DATA_PROCESSING_TEMPLATES
        assert "json" in DATA_PROCESSING_TEMPLATES["summarize_metrics"]

    def test_summarize_timeseries_template_exists(self) -> None:
        assert "summarize_timeseries" in DATA_PROCESSING_TEMPLATES
        assert "statistics" in DATA_PROCESSING_TEMPLATES["summarize_timeseries"]

    def test_summarize_logs_template_exists(self) -> None:
        assert "summarize_logs" in DATA_PROCESSING_TEMPLATES
        assert "severity" in DATA_PROCESSING_TEMPLATES["summarize_logs"]

    def test_summarize_traces_template_exists(self) -> None:
        assert "summarize_traces" in DATA_PROCESSING_TEMPLATES
        assert "latency" in DATA_PROCESSING_TEMPLATES["summarize_traces"]


class TestProcessDataInSandbox:
    @pytest.mark.asyncio
    async def test_unknown_template_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown template"):
            await process_data_in_sandbox(
                data=[{"test": 1}],
                template_name="nonexistent_template",
            )

    @pytest.mark.asyncio
    async def test_process_with_provided_executor(self) -> None:
        mock_executor = MagicMock(spec=SandboxExecutor)
        mock_executor.execute_data_processing = AsyncMock(
            return_value=CodeExecutionOutput(
                stdout='{"total_count": 5, "summary": "test"}',
                stderr="",
            )
        )

        result = await process_data_in_sandbox(
            data=[{"id": i} for i in range(5)],
            template_name="summarize_metrics",
            sandbox_executor=mock_executor,
        )

        assert result["total_count"] == 5
        mock_executor.execute_data_processing.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_handles_execution_error(self) -> None:
        mock_executor = MagicMock(spec=SandboxExecutor)
        mock_executor.execute_data_processing = AsyncMock(
            return_value=CodeExecutionOutput(
                stdout="",
                stderr="",
                execution_error="SyntaxError",
            )
        )

        with pytest.raises(RuntimeError, match="Sandbox processing failed"):
            await process_data_in_sandbox(
                data=[{"id": 1}],
                template_name="summarize_metrics",
                sandbox_executor=mock_executor,
            )

    @pytest.mark.asyncio
    async def test_process_parses_output_file(self) -> None:
        mock_executor = MagicMock(spec=SandboxExecutor)
        mock_executor.execute_data_processing = AsyncMock(
            return_value=CodeExecutionOutput(
                stdout="",  # Empty stdout
                stderr="",
                output_files=[
                    SandboxFile(
                        name="output.json",
                        content=b'{"from_file": true}',
                    )
                ],
            )
        )

        result = await process_data_in_sandbox(
            data=[{"id": 1}],
            template_name="summarize_metrics",
            sandbox_executor=mock_executor,
        )

        assert result["from_file"] is True


# Tests for new functionality (auto-detection, local execution, events)


class TestIsRemoteMode:
    def test_returns_false_when_agent_id_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert is_remote_mode() is False

    def test_returns_true_when_agent_id_set(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_ID": "test-agent-123"}):
            assert is_remote_mode() is True


class TestIsLocalExecutionEnabled:
    def test_returns_false_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert is_local_execution_enabled() is False

    def test_returns_true_when_enabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}):
            assert is_local_execution_enabled() is True


class TestAutoDetectSandbox:
    def test_sandbox_auto_enabled_in_agent_engine(self) -> None:
        """Sandbox should be auto-enabled when SRE_AGENT_ID is set."""
        with patch.dict(os.environ, {"SRE_AGENT_ID": "agent-123"}, clear=True):
            assert is_sandbox_enabled() is True

    def test_sandbox_auto_enabled_with_local_execution(self) -> None:
        """Sandbox should be auto-enabled when local execution is enabled."""
        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}, clear=True):
            assert is_sandbox_enabled() is True

    def test_explicit_false_overrides_auto_detect(self) -> None:
        """Explicit SRE_AGENT_SANDBOX_ENABLED=false should override auto-detect."""
        with patch.dict(
            os.environ,
            {"SRE_AGENT_ID": "agent-123", "SRE_AGENT_SANDBOX_ENABLED": "false"},
        ):
            assert is_sandbox_enabled() is False


class TestLocalCodeExecutor:
    @pytest.mark.asyncio
    async def test_execute_simple_code(self) -> None:
        executor = LocalCodeExecutor()
        output = await executor.execute_code("print('Hello, World!')")

        assert "Hello, World!" in output.stdout
        assert output.execution_error is None

    @pytest.mark.asyncio
    async def test_execute_with_input_files(self) -> None:
        executor = LocalCodeExecutor()
        input_file = SandboxFile(name="data.txt", content=b"test data")

        output = await executor.execute_code(
            'with open("data.txt", "r") as f: print(f.read())',
            input_files=[input_file],
        )

        assert "test data" in output.stdout
        assert output.execution_error is None

    @pytest.mark.asyncio
    async def test_execute_generates_output_file(self) -> None:
        executor = LocalCodeExecutor()
        output = await executor.execute_code(
            'with open("output.json", "w") as f: f.write(\'{"result": 42}\')'
        )

        assert output.execution_error is None
        assert len(output.output_files) == 1
        assert output.output_files[0].name == "output.json"
        assert b'"result": 42' in output.output_files[0].content

    @pytest.mark.asyncio
    async def test_execute_handles_syntax_error(self) -> None:
        executor = LocalCodeExecutor()
        output = await executor.execute_code("this is not valid python")

        assert output.execution_error is not None
        assert "syntax" in output.execution_error.lower()

    @pytest.mark.asyncio
    async def test_execute_data_processing(self) -> None:
        executor = LocalCodeExecutor()
        output = await executor.execute_data_processing(
            data=[{"id": 1}, {"id": 2}, {"id": 3}],
            processing_code='import json; print(json.dumps({"count": len(data)}))',
        )

        assert output.execution_error is None
        result = json.loads(output.stdout)
        assert result["count"] == 3


class TestEventCallback:
    def test_set_and_clear_callback(self) -> None:
        events: list[SandboxExecutionEvent] = []

        def callback(event: SandboxExecutionEvent) -> None:
            events.append(event)

        set_sandbox_event_callback(callback)
        # Clear callback
        set_sandbox_event_callback(None)

        # Verify callback is cleared (no exception)
        assert True


class TestExecutionLogs:
    def test_clear_execution_logs(self) -> None:
        clear_execution_logs()
        logs = get_recent_execution_logs()
        assert logs == []

    @pytest.mark.asyncio
    async def test_execution_logs_stored(self) -> None:
        """Test that execution logs are stored after processing."""
        clear_execution_logs()

        mock_executor = MagicMock(spec=LocalCodeExecutor)
        mock_executor.execute_data_processing = AsyncMock(
            return_value=CodeExecutionOutput(
                stdout='{"result": "test"}',
                stderr="",
            )
        )

        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}):
            await process_data_in_sandbox(
                data=[{"id": 1}],
                template_name="summarize_metrics",
                sandbox_executor=mock_executor,
            )

        logs = get_recent_execution_logs(limit=1)
        assert len(logs) == 1
        assert logs[0].template_name == "summarize_metrics"
        assert logs[0].success is True


class TestGetCodeExecutor:
    @pytest.mark.asyncio
    async def test_returns_local_executor_when_local_enabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}, clear=True):
            executor = await get_code_executor()
            assert isinstance(executor, LocalCodeExecutor)
