"""Tests for tool configuration management."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sre_agent.tools.config import (
    ToolCategory,
    ToolConfig,
    ToolConfigManager,
    ToolTestResult,
    ToolTestStatus,
    get_tool_config_manager,
)


def test_tool_test_status_enum():
    """Test ToolTestStatus enum values."""
    assert ToolTestStatus.SUCCESS.value == "success"
    assert ToolTestStatus.FAILED.value == "failed"
    assert ToolTestStatus.TIMEOUT.value == "timeout"
    assert ToolTestStatus.NOT_TESTED.value == "not_tested"
    assert ToolTestStatus.NOT_TESTABLE.value == "not_testable"


def test_tool_category_enum():
    """Test ToolCategory enum values."""
    assert ToolCategory.API_CLIENT.value == "api_client"
    assert ToolCategory.MCP.value == "mcp"
    assert ToolCategory.ANALYSIS.value == "analysis"
    assert ToolCategory.ORCHESTRATION.value == "orchestration"
    assert ToolCategory.DISCOVERY.value == "discovery"
    assert ToolCategory.REMEDIATION.value == "remediation"
    assert ToolCategory.GKE.value == "gke"
    assert ToolCategory.SLO.value == "slo"


def test_tool_test_result_creation():
    """Test creating ToolTestResult."""
    result = ToolTestResult(
        status=ToolTestStatus.SUCCESS,
        message="Test passed",
        latency_ms=100.5,
        details={"key": "value"},
    )

    assert result.status == ToolTestStatus.SUCCESS
    assert result.message == "Test passed"
    assert result.latency_ms == 100.5
    assert result.details == {"key": "value"}
    assert result.timestamp is not None


def test_tool_config_creation():
    """Test creating ToolConfig."""
    config = ToolConfig(
        name="test_tool",
        display_name="Test Tool",
        description="A test tool",
        category=ToolCategory.ANALYSIS,
        enabled=True,
        testable=False,
    )

    assert config.name == "test_tool"
    assert config.display_name == "Test Tool"
    assert config.description == "A test tool"
    assert config.category == ToolCategory.ANALYSIS
    assert config.enabled is True
    assert config.testable is False
    assert config.last_test_result is None


def test_tool_config_to_dict():
    """Test ToolConfig serialization to dict."""
    result = ToolTestResult(
        status=ToolTestStatus.SUCCESS,
        message="Test message",
        latency_ms=50.0,
    )

    config = ToolConfig(
        name="test_tool",
        display_name="Test Tool",
        description="Test description",
        category=ToolCategory.API_CLIENT,
        enabled=False,
        testable=True,
        last_test_result=result,
    )

    data = config.to_dict()

    assert data["name"] == "test_tool"
    assert data["display_name"] == "Test Tool"
    assert data["description"] == "Test description"
    assert data["category"] == "api_client"
    assert data["enabled"] is False
    assert data["testable"] is True
    assert data["last_test_result"]["status"] == "success"
    assert data["last_test_result"]["message"] == "Test message"
    assert data["last_test_result"]["latency_ms"] == 50.0


def test_tool_config_from_dict():
    """Test ToolConfig deserialization from dict."""
    data = {
        "name": "test_tool",
        "display_name": "Test Tool",
        "description": "Test description",
        "category": "mcp",
        "enabled": True,
        "testable": False,
        "last_test_result": {
            "status": "failed",
            "message": "Test failed",
            "latency_ms": None,
            "timestamp": "2023-01-01T00:00:00",
            "details": {"error": "timeout"},
        },
    }

    config = ToolConfig.from_dict(data)

    assert config.name == "test_tool"
    assert config.display_name == "Test Tool"
    assert config.category == ToolCategory.MCP
    assert config.enabled is True
    assert config.testable is False
    assert config.last_test_result is not None
    assert config.last_test_result.status == ToolTestStatus.FAILED
    assert config.last_test_result.message == "Test failed"
    assert config.last_test_result.details == {"error": "timeout"}


def test_tool_config_from_dict_no_test_result():
    """Test ToolConfig deserialization without test result."""
    data = {
        "name": "test_tool",
        "display_name": "Test Tool",
        "description": "Test description",
        "category": "analysis",
        "enabled": False,
        "testable": True,
    }

    config = ToolConfig.from_dict(data)

    assert config.name == "test_tool"
    assert config.enabled is False
    assert config.testable is True
    assert config.last_test_result is None


def test_tool_config_manager_singleton():
    """Test ToolConfigManager singleton behavior."""
    manager1 = get_tool_config_manager()
    manager2 = get_tool_config_manager()

    assert manager1 is manager2
    assert isinstance(manager1, ToolConfigManager)


def test_tool_config_manager_get_config():
    """Test getting tool configuration."""
    manager = get_tool_config_manager()

    config = manager.get_config("list_traces")
    assert config is not None
    assert config.name == "list_traces"
    assert config.category == ToolCategory.API_CLIENT
    assert config.testable is True

    # Test non-existent tool
    config = manager.get_config("non_existent_tool")
    assert config is None


def test_tool_config_manager_get_all_configs():
    """Test getting all tool configurations."""
    manager = get_tool_config_manager()

    configs = manager.get_all_configs()
    assert len(configs) > 0
    assert all(isinstance(c, ToolConfig) for c in configs)


def test_tool_config_manager_get_configs_by_category():
    """Test getting configurations by category."""
    manager = get_tool_config_manager()

    api_configs = manager.get_configs_by_category(ToolCategory.API_CLIENT)
    assert len(api_configs) > 0
    assert all(c.category == ToolCategory.API_CLIENT for c in api_configs)

    slo_configs = manager.get_configs_by_category(ToolCategory.SLO)
    assert len(slo_configs) > 0
    assert all(c.category == ToolCategory.SLO for c in slo_configs)


def test_tool_config_manager_enabled_tools():
    """Test enabling/disabling tools."""
    manager = get_tool_config_manager()

    # Test initial state
    assert manager.is_enabled("list_traces") is True

    # Disable tool
    success = manager.set_enabled("list_traces", False)
    assert success is True
    assert manager.is_enabled("list_traces") is False

    # Enable tool
    success = manager.set_enabled("list_traces", True)
    assert success is True
    assert manager.is_enabled("list_traces") is True

    # Test non-existent tool
    success = manager.set_enabled("non_existent_tool", False)
    assert success is False


def test_tool_config_manager_get_enabled_disabled_tools():
    """Test getting lists of enabled/disabled tools."""
    manager = get_tool_config_manager()

    enabled = manager.get_enabled_tools()
    disabled = manager.get_disabled_tools()

    assert len(enabled) + len(disabled) == len(manager.get_all_configs())

    # Check that no tool is in both lists
    assert set(enabled).isdisjoint(set(disabled))


@pytest.mark.asyncio
async def test_tool_config_manager_test_tool_not_found():
    """Test testing a non-existent tool."""
    manager = get_tool_config_manager()

    result = await manager.test_tool("non_existent_tool")

    assert result.status == ToolTestStatus.FAILED
    assert "not found" in result.message


@pytest.mark.asyncio
async def test_tool_config_manager_test_tool_not_testable():
    """Test testing a non-testable tool."""
    manager = get_tool_config_manager()

    result = await manager.test_tool("analyze_critical_path")

    assert result.status == ToolTestStatus.NOT_TESTABLE
    assert "not testable" in result.message


def test_tool_config_manager_register_test_function():
    """Test registering a test function."""
    manager = get_tool_config_manager()

    async def dummy_test():
        return ToolTestResult(
            status=ToolTestStatus.SUCCESS,
            message="Dummy test passed",
        )

    manager.register_test_function("dummy_tool", dummy_test)

    # Verify it's registered (internal check)
    assert "dummy_tool" in manager._test_functions


def test_tool_config_manager_config_persistence():
    """Test configuration persistence."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.json"

        with patch("sre_agent.tools.config.CONFIG_FILE_PATH", config_path):
            # Create new manager instance to test persistence
            manager = ToolConfigManager()
            manager._initialized = False  # Reset to force re-init
            manager.__init__()

            # Modify a setting
            manager.set_enabled("list_traces", False)

            # Create new instance to test loading
            manager2 = ToolConfigManager()
            manager2._initialized = False
            manager2.__init__()

            # Check if setting was persisted
            assert manager2.is_enabled("list_traces") is False