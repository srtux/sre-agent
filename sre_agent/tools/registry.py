"""Tool Registry for categorized tool discovery and agent instruction generation.

Provides a queryable registry that organizes tools by category, enabling:
- Tool discovery by signal type or domain
- Agent instruction generation with relevant tool subsets
- Tool search by keyword
- Category-level statistics

This module builds on the existing ToolCategory enum from config.py
and provides a runtime query layer on top of the tool configurations.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .config import ToolCategory, ToolConfigManager

logger = logging.getLogger(__name__)

# Mapping from signal types to relevant tool categories
_SIGNAL_CATEGORY_MAP: dict[str, list[ToolCategory]] = {
    "trace": [ToolCategory.TRACE_FETCH, ToolCategory.TRACE_ANALYZE],
    "metrics": [ToolCategory.METRIC_FETCH, ToolCategory.METRIC_ANALYZE],
    "logs": [ToolCategory.LOG_FETCH, ToolCategory.LOG_ANALYZE],
    "alerts": [ToolCategory.ALERT],
    "slo": [ToolCategory.SLO],
    "gke": [ToolCategory.GKE],
    "remediation": [ToolCategory.REMEDIATION],
    "correlation": [ToolCategory.CORRELATION],
}

# Human-friendly category descriptions for agent instructions
_CATEGORY_DESCRIPTIONS: dict[ToolCategory, str] = {
    ToolCategory.DISCOVERY: "Find GCP projects, services, and data sources",
    ToolCategory.ORCHESTRATION: "High-level investigation flow control",
    ToolCategory.TRACE_FETCH: "Retrieve traces, spans, and distributed tracing data",
    ToolCategory.TRACE_ANALYZE: "Analyze critical paths, bottlenecks, and trace patterns",
    ToolCategory.LOG_FETCH: "Retrieve log entries from Cloud Logging",
    ToolCategory.LOG_ANALYZE: "Mine log patterns, detect anomalies in logs",
    ToolCategory.METRIC_FETCH: "Query metrics, time series, and exemplars",
    ToolCategory.METRIC_ANALYZE: "Detect metric anomalies, trends, and SLO violations",
    ToolCategory.ALERT: "Check alert policies, active incidents, and firing alerts",
    ToolCategory.SLO: "Monitor SLOs, error budgets, and burn rates",
    ToolCategory.GKE: "Debug Kubernetes clusters, pods, nodes, and workloads",
    ToolCategory.REMEDIATION: "Generate remediation suggestions, gcloud commands",
    ToolCategory.CORRELATION: "Cross-signal correlation (traces + logs + metrics)",
    ToolCategory.API_CLIENT: "Direct GCP API calls",
    ToolCategory.MCP: "Model Context Protocol tools (BigQuery, Logging, Monitoring)",
    ToolCategory.ANALYSIS: "General analysis utilities",
    ToolCategory.MEMORY: "Memory search, recall, and pattern storage",
    ToolCategory.SANDBOX: "Sandbox code execution for large data processing",
}


class ToolRegistry:
    """Queryable registry for categorized tool discovery.

    Wraps the ToolConfigManager to provide higher-level queries
    grouped by category, signal type, and keyword.
    """

    def __init__(self, config_manager: ToolConfigManager | None = None) -> None:
        """Initialize the registry.

        Args:
            config_manager: Optional config manager. Creates default if None.
        """
        if config_manager is None:
            config_manager = ToolConfigManager()
        self._config_manager = config_manager
        self._tool_map: dict[str, Callable[..., Any]] | None = None

    def set_tool_map(self, tool_map: dict[str, Callable[..., Any]]) -> None:
        """Set the mapping from tool names to tool functions.

        Args:
            tool_map: Dict mapping tool name -> function.
        """
        self._tool_map = tool_map

    def get_tools_by_category(
        self, category: ToolCategory, enabled_only: bool = True
    ) -> list[str]:
        """Get tool names in a given category.

        Args:
            category: The tool category to filter by.
            enabled_only: If True, only return enabled tools.

        Returns:
            List of tool names in the category.
        """
        tools = self._config_manager.get_configs_by_category(category)
        if enabled_only:
            return [t.name for t in tools if t.enabled]
        return [t.name for t in tools]

    def get_tools_for_signal(
        self, signal_type: str, enabled_only: bool = True
    ) -> list[str]:
        """Get tools relevant to a signal type (trace, metrics, logs, alerts).

        Args:
            signal_type: One of 'trace', 'metrics', 'logs', 'alerts', 'slo', 'gke'.
            enabled_only: If True, only return enabled tools.

        Returns:
            List of tool names relevant to the signal.
        """
        categories = _SIGNAL_CATEGORY_MAP.get(signal_type.lower(), [])
        tools: list[str] = []
        for category in categories:
            tools.extend(self.get_tools_by_category(category, enabled_only))
        return tools

    def get_category_summary(self) -> dict[str, dict[str, int]]:
        """Get a summary of tool counts per category.

        Returns:
            Dict mapping category name to counts (total, enabled, disabled).
        """
        summary: dict[str, dict[str, int]] = {}
        for category in ToolCategory:
            all_tools = self._config_manager.get_configs_by_category(category)
            enabled = [t for t in all_tools if t.enabled]
            summary[category.value] = {
                "total": len(all_tools),
                "enabled": len(enabled),
                "disabled": len(all_tools) - len(enabled),
            }
        return summary

    def search_tools(self, keyword: str) -> list[dict[str, str]]:
        """Search tools by keyword in name or description.

        Args:
            keyword: Search keyword (case-insensitive).

        Returns:
            List of dicts with 'name', 'description', 'category' keys.
        """
        keyword_lower = keyword.lower()
        results: list[dict[str, str]] = []
        for tool_config in self._config_manager.get_all_configs():
            if (
                keyword_lower in tool_config.name.lower()
                or keyword_lower in (tool_config.description or "").lower()
            ):
                results.append(
                    {
                        "name": tool_config.name,
                        "description": tool_config.description,
                        "category": tool_config.category.value,
                    }
                )
        return results

    def generate_tool_instruction(self, signal_type: str | None = None) -> str:
        """Generate a concise tool inventory for agent instructions.

        Creates a structured text summary of available tools, optionally
        filtered by signal type, suitable for injection into agent prompts.

        Args:
            signal_type: Optional signal type to focus on. None = all tools.

        Returns:
            Formatted string describing available tools by category.
        """
        lines: list[str] = ["## Available Tools\n"]

        if signal_type:
            categories = _SIGNAL_CATEGORY_MAP.get(signal_type.lower(), [])
        else:
            categories = list(ToolCategory)

        for category in categories:
            tools = self.get_tools_by_category(category, enabled_only=True)
            if not tools:
                continue
            desc = _CATEGORY_DESCRIPTIONS.get(category, category.value)
            lines.append(f"### {category.value.replace('_', ' ').title()} — {desc}")
            for tool_name in tools:
                lines.append(f"  - {tool_name}")
            lines.append("")

        return "\n".join(lines)

    def get_grouped_tools(self) -> dict[str, list[str]]:
        """Get all tools grouped by category.

        Returns:
            Dict mapping category value to list of tool names.
        """
        grouped: dict[str, list[str]] = defaultdict(list)
        for tool_config in self._config_manager.get_all_configs():
            if tool_config.enabled:
                grouped[tool_config.category.value].append(tool_config.name)
        return dict(grouped)


# Module-level singleton
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
