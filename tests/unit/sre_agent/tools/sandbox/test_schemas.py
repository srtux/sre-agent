"""Tests for sandbox schemas."""

import pytest
from pydantic import ValidationError

from sre_agent.tools.sandbox.schemas import (
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


class TestSandboxLanguage:
    def test_python_value(self) -> None:
        assert SandboxLanguage.PYTHON.value == "LANGUAGE_PYTHON"

    def test_javascript_value(self) -> None:
        assert SandboxLanguage.JAVASCRIPT.value == "LANGUAGE_JAVASCRIPT"


class TestMachineConfig:
    def test_default_value(self) -> None:
        assert MachineConfig.DEFAULT.value == "MACHINE_CONFIG_UNSPECIFIED"

    def test_vcpu4_ram4gib_value(self) -> None:
        assert MachineConfig.VCPU4_RAM4GIB.value == "MACHINE_CONFIG_VCPU4_RAM4GIB"


class TestSandboxFile:
    def test_create_sandbox_file(self) -> None:
        file = SandboxFile(name="test.txt", content=b"Hello, World!")
        assert file.name == "test.txt"
        assert file.content == b"Hello, World!"
        assert file.mime_type == "application/octet-stream"

    def test_create_sandbox_file_with_mime_type(self) -> None:
        file = SandboxFile(
            name="data.json",
            content=b'{"key": "value"}',
            mime_type="application/json",
        )
        assert file.mime_type == "application/json"

    def test_sandbox_file_immutable(self) -> None:
        file = SandboxFile(name="test.txt", content=b"content")
        with pytest.raises(ValidationError):
            file.name = "new_name.txt"  # type: ignore[misc]

    def test_sandbox_file_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            SandboxFile(name="test.txt", content=b"content", unknown_field="value")  # type: ignore[call-arg]


class TestSandboxConfig:
    def test_default_values(self) -> None:
        config = SandboxConfig()
        assert config.language == SandboxLanguage.PYTHON
        assert config.machine_config == MachineConfig.DEFAULT
        assert config.ttl_seconds == 3600
        assert config.display_name is None

    def test_custom_values(self) -> None:
        config = SandboxConfig(
            language=SandboxLanguage.JAVASCRIPT,
            machine_config=MachineConfig.VCPU4_RAM4GIB,
            ttl_seconds=7200,
            display_name="test-sandbox",
        )
        assert config.language == SandboxLanguage.JAVASCRIPT
        assert config.machine_config == MachineConfig.VCPU4_RAM4GIB
        assert config.ttl_seconds == 7200
        assert config.display_name == "test-sandbox"


class TestCodeExecutionRequest:
    def test_minimal_request(self) -> None:
        request = CodeExecutionRequest(code="print('hello')")
        assert request.code == "print('hello')"
        assert request.input_files == []
        assert request.ttl_extension_seconds is None

    def test_with_input_files(self) -> None:
        files = [SandboxFile(name="input.txt", content=b"data")]
        request = CodeExecutionRequest(code="pass", input_files=files)
        assert len(request.input_files) == 1
        assert request.input_files[0].name == "input.txt"


class TestCodeExecutionOutput:
    def test_minimal_output(self) -> None:
        output = CodeExecutionOutput()
        assert output.stdout == ""
        assert output.stderr == ""
        assert output.output_files == []
        assert output.execution_error is None

    def test_with_content(self) -> None:
        output = CodeExecutionOutput(
            stdout="Hello, World!",
            stderr="Warning: deprecated",
            execution_error=None,
        )
        assert output.stdout == "Hello, World!"
        assert output.stderr == "Warning: deprecated"

    def test_with_error(self) -> None:
        output = CodeExecutionOutput(
            stdout="",
            stderr="Traceback...",
            execution_error="SyntaxError: invalid syntax",
        )
        assert output.execution_error == "SyntaxError: invalid syntax"


class TestDataProcessingResult:
    def test_minimal_result(self) -> None:
        result = DataProcessingResult(
            summary="Processed 100 items",
            total_count=100,
        )
        assert result.summary == "Processed 100 items"
        assert result.total_count == 100
        assert result.statistics == {}
        assert result.top_items == []
        assert result.filtered_count == 0
        assert result.truncated is False

    def test_full_result(self) -> None:
        result = DataProcessingResult(
            summary="Analyzed 500 metrics",
            statistics={"by_kind": {"GAUGE": 300, "DELTA": 200}},
            top_items=[{"type": "cpu", "value": 0.95}],
            total_count=500,
            filtered_count=50,
            truncated=True,
            processing_metadata={"method": "sandbox"},
        )
        assert result.filtered_count == 50
        assert result.truncated is True
        assert "by_kind" in result.statistics


class TestMetricDescriptorSummary:
    def test_create_summary(self) -> None:
        summary = MetricDescriptorSummary(
            metric_type="compute.googleapis.com/instance/cpu/utilization",
            display_name="CPU Utilization",
            description="CPU usage percentage",
            metric_kind="GAUGE",
            value_type="DOUBLE",
            unit="%",
            label_keys=["instance_id", "zone"],
        )
        assert summary.metric_type == "compute.googleapis.com/instance/cpu/utilization"
        assert len(summary.label_keys) == 2


class TestTimeSeriesSummary:
    def test_create_summary(self) -> None:
        summary = TimeSeriesSummary(
            metric_type="cpu_utilization",
            resource_type="gce_instance",
            resource_labels={"instance_id": "12345"},
            point_count=60,
            min_value=0.1,
            max_value=0.95,
            avg_value=0.45,
            latest_value=0.5,
            latest_timestamp="2024-01-15T10:00:00Z",
        )
        assert summary.point_count == 60
        assert summary.avg_value == 0.45


class TestLogEntrySummary:
    def test_create_summary(self) -> None:
        summary = LogEntrySummary(
            severity_counts={"ERROR": 10, "WARNING": 50, "INFO": 940},
            resource_type_counts={"gce_instance": 500, "k8s_container": 500},
            top_error_messages=["Connection refused", "Timeout exceeded"],
            time_range={
                "earliest": "2024-01-15T00:00:00Z",
                "latest": "2024-01-15T23:59:59Z",
            },
            sample_entries=[{"severity": "ERROR", "message": "test error"}],
        )
        assert summary.severity_counts["ERROR"] == 10
        assert len(summary.top_error_messages) == 2
