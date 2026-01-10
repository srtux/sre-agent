import logging
from typing import Any

logger = logging.getLogger(__name__)


class MockMcpTool:
    def __init__(self, name: str):
        self.name = name

    async def run_async(self, args: dict, tool_context: Any) -> dict:
        logger.warning(f"Using MockMcpTool for {self.name}")
        if self.name == "list_log_entries":
            return {"entries": []}
        elif self.name == "list_timeseries":
            return {
                "timeSeries": [
                    {
                        "points": [
                            {
                                "value": {"doubleValue": 0.5},
                                "interval": {"endTime": "2024-01-01T00:00:00Z"},
                            }
                        ]
                    }
                ]
            }
        elif self.name == "query_range":
            return {"result": []}
        return {"mock_result": "success"}


class MockMcpToolset:
    async def get_tools(self) -> list[MockMcpTool]:
        return [
            MockMcpTool("list_log_entries"),
            MockMcpTool("list_timeseries"),
            MockMcpTool("query_range"),
            MockMcpTool("execute_sql"),
            MockMcpTool("list_dataset_ids"),
            MockMcpTool("list_table_ids"),
            MockMcpTool("get_table_info"),
        ]
