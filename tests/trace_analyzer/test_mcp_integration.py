
import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio


# Mock google.adk components
mock_adk = MagicMock()
sys.modules["google.adk"] = mock_adk
sys.modules["google.adk.agents"] = mock_adk
sys.modules["google.adk.tools"] = mock_adk
sys.modules["google.adk.tools.api_registry"] = MagicMock() # Mock the registry module
sys.modules["google.adk.tools.base_toolset"] = MagicMock()

sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.trace_v1"] = MagicMock()
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.trace"] = MagicMock()
sys.modules["opentelemetry.metrics"] = MagicMock()
sys.modules["google.cloud.logging_v2"] = MagicMock()
sys.modules["google.cloud.logging_v2.services"] = MagicMock()
sys.modules["google.cloud.logging_v2.services.logging_service_v2"] = MagicMock()
sys.modules["google.cloud.errorreporting_v1beta1"] = MagicMock()
sys.modules["google.cloud.monitoring_v3"] = MagicMock()
# Mock google.auth return value explicitly on the mock object
mock_auth = MagicMock()
sys.modules["google.auth"] = mock_auth
# Use side_effect or return_value for default
# Start of mock setup
mock_auth.default.return_value = (MagicMock(), "mock-project-id")
import google  # noqa: E402

google.auth = mock_auth

class TestMCPIntegration(unittest.TestCase):

    def test_create_mcp_tools_simple(self):
        """Test that create_mcp_tools creates tools directly without lazy loading."""
        # We'll use the mock we injected into sys.modules
        mock_registry_module = sys.modules["google.adk.tools.api_registry"]
        mock_registry_cls = mock_registry_module.ApiRegistry

        # Reset mocks
        mock_registry_cls.reset_mock()

        # Reload agent to ensure it picks up the mocks and runs clean
        if "trace_analyzer.agent" in sys.modules:
            del sys.modules["trace_analyzer.agent"]
        from trace_analyzer.agent import create_mcp_tools

        # Setup registry mock instance interactions
        mock_registry_instance = mock_registry_cls.return_value
        mock_toolset = MagicMock()
        mock_toolset.get_tools = AsyncMock(return_value=["tool1", "tool2"])
        mock_toolset.close = AsyncMock()
        mock_registry_instance.get_toolset.return_value = mock_toolset

        # Run the async function
        async def run_test():
            tools, cleanup = await create_mcp_tools("test-project")

            # Verify tools were created immediately (not lazily)
            self.assertEqual(tools, ["tool1", "tool2"])

            # Verify get_tools was called
            mock_toolset.get_tools.assert_called_once()

            # Test cleanup
            await cleanup()
            mock_toolset.close.assert_called_once()

        asyncio.run(run_test())

    def test_create_mcp_tools_error_handling(self):
        """Test that create_mcp_tools handles errors and cleans up properly."""
        mock_registry_module = sys.modules["google.adk.tools.api_registry"]
        mock_registry_cls = mock_registry_module.ApiRegistry

        # Reload agent
        if "trace_analyzer.agent" in sys.modules:
            del sys.modules["trace_analyzer.agent"]
        from trace_analyzer.agent import create_mcp_tools

        # Setup mock to raise error during get_tools
        mock_registry_instance = mock_registry_cls.return_value
        mock_toolset = MagicMock()
        mock_toolset.get_tools = AsyncMock(side_effect=Exception("Connection error"))
        mock_toolset.close = AsyncMock()
        mock_registry_instance.get_toolset.return_value = mock_toolset

        async def run_test():
            with self.assertRaises(Exception) as context:
                await create_mcp_tools("test-project")

            self.assertIn("Connection error", str(context.exception))
            # Verify cleanup was attempted even on error
            mock_toolset.close.assert_called_once()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
