"""Tests for sandbox executor."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.tools.sandbox.executor import (
    DATA_PROCESSING_TEMPLATES,
    SandboxExecutor,
    get_agent_engine_resource_name,
    get_sandbox_resource_name,
    is_sandbox_enabled,
    process_data_in_sandbox,
)
from sre_agent.tools.sandbox.schemas import (
    CodeExecutionOutput,
    MachineConfig,
    SandboxConfig,
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
            assert result == "projects/my-project/locations/us-central1/reasoningEngines/engine-123"

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
        executor = await SandboxExecutor.create(
            sandbox_name="existing-sandbox"
        )
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

        # Mock the vertexai module
        mock_response = MagicMock()
        mock_response.stdout = b'{"result": "success"}'
        mock_response.stderr = b""
        mock_response.files = []

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
