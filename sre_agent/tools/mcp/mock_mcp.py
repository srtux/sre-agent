"""Mock implementations for MCP tools."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MockMcpTool:
    """A mock implementation of an ADK tool for testing."""

    def __init__(self, name: str) -> None:
        """Initialize the mock tool.

        Args:
            name: The name of the tool to mock.
        """
        self.name = name

    async def run_async(
        self, args: dict[str, Any], tool_context: Any
    ) -> dict[str, Any]:
        """Simulates tool execution with mock data.

        Args:
            args: Tool arguments.
            tool_context: ADK tool context.

        Returns:
            Mock response data based on the tool name.
        """
        logger.warning(f"Using MockMcpTool for {self.name}")
        if self.name == "list_log_entries":
            return {
                "entries": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "severity": "ERROR",
                        "textPayload": "Mock log message",
                    }
                ]
            }
        if self.name == "list_timeseries":
            return {"timeSeries": []}
        if self.name == "query_range":
            return {"status": "success", "data": {"resultType": "matrix", "result": []}}
        return {"status": "success", "mock": True}


class MockMcpToolset:
    """A mock implementation of an MCP toolset."""

    async def get_tools(self) -> list[MockMcpTool]:
        """Returns a list of mock tools.

        Returns:
            List of MockMcpTool instances.
        """
        return [
            MockMcpTool("list_log_entries"),
            MockMcpTool("list_timeseries"),
            MockMcpTool("query_range"),
        ]
