"""Tests for the Tool Registry categorized discovery module.

Validates that:
- ToolRegistry groups tools by category correctly
- Signal-type-based tool discovery works
- Tool search by keyword works
- Category summaries are accurate
- Tool instruction generation produces expected format
- Singleton pattern works correctly
"""

from unittest.mock import MagicMock

from sre_agent.tools.config import ToolCategory, ToolConfig
from sre_agent.tools.registry import (
    _CATEGORY_DESCRIPTIONS,
    _SIGNAL_CATEGORY_MAP,
    ToolRegistry,
    get_tool_registry,
)


def _make_config_manager(
    tools: list[ToolConfig] | None = None,
) -> MagicMock:
    """Create a mock ToolConfigManager with predefined tools for testing.

    Uses a mock to avoid the singleton pattern of the real ToolConfigManager.
    """
    manager = MagicMock()
    tool_list = tools or []

    def get_configs_by_category(category: ToolCategory) -> list[ToolConfig]:
        return [t for t in tool_list if t.category == category]

    def get_all_configs() -> list[ToolConfig]:
        return list(tool_list)

    manager.get_configs_by_category = get_configs_by_category
    manager.get_all_configs = get_all_configs
    return manager


def _make_tool(
    name: str,
    category: ToolCategory,
    enabled: bool = True,
    description: str = "",
) -> ToolConfig:
    """Create a ToolConfig for testing."""
    return ToolConfig(
        name=name,
        display_name=name.replace("_", " ").title(),
        description=description or f"Test tool: {name}",
        category=category,
        enabled=enabled,
    )


class TestToolRegistryByCategory:
    """Tests for category-based tool grouping."""

    def test_get_tools_by_category(self) -> None:
        """Should return tools matching the category."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH),
            _make_tool("list_traces", ToolCategory.TRACE_FETCH),
            _make_tool("list_log_entries", ToolCategory.LOG_FETCH),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        trace_tools = registry.get_tools_by_category(ToolCategory.TRACE_FETCH)
        assert "fetch_trace" in trace_tools
        assert "list_traces" in trace_tools
        assert "list_log_entries" not in trace_tools

    def test_enabled_only_filter(self) -> None:
        """Should filter out disabled tools when enabled_only=True."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH, enabled=True),
            _make_tool("list_traces", ToolCategory.TRACE_FETCH, enabled=False),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        enabled = registry.get_tools_by_category(
            ToolCategory.TRACE_FETCH, enabled_only=True
        )
        assert "fetch_trace" in enabled
        assert "list_traces" not in enabled

        all_tools = registry.get_tools_by_category(
            ToolCategory.TRACE_FETCH, enabled_only=False
        )
        assert "list_traces" in all_tools

    def test_empty_category(self) -> None:
        """Should return empty list for empty category."""
        manager = _make_config_manager([])
        registry = ToolRegistry(config_manager=manager)

        result = registry.get_tools_by_category(ToolCategory.SANDBOX)
        assert result == []


class TestToolRegistryBySignal:
    """Tests for signal-type-based tool discovery."""

    def test_trace_signal(self) -> None:
        """Trace signal should return trace_fetch and trace_analyze tools."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH),
            _make_tool("analyze_critical_path", ToolCategory.TRACE_ANALYZE),
            _make_tool("list_log_entries", ToolCategory.LOG_FETCH),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        trace_tools = registry.get_tools_for_signal("trace")
        assert "fetch_trace" in trace_tools
        assert "analyze_critical_path" in trace_tools
        assert "list_log_entries" not in trace_tools

    def test_metrics_signal(self) -> None:
        """Metrics signal should return metric_fetch and metric_analyze tools."""
        tools = [
            _make_tool("query_promql", ToolCategory.METRIC_FETCH),
            _make_tool("detect_metric_anomalies", ToolCategory.METRIC_ANALYZE),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        metric_tools = registry.get_tools_for_signal("metrics")
        assert "query_promql" in metric_tools
        assert "detect_metric_anomalies" in metric_tools

    def test_logs_signal(self) -> None:
        """Logs signal should return log_fetch and log_analyze tools."""
        tools = [
            _make_tool("list_log_entries", ToolCategory.LOG_FETCH),
            _make_tool("extract_log_patterns", ToolCategory.LOG_ANALYZE),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        log_tools = registry.get_tools_for_signal("logs")
        assert "list_log_entries" in log_tools
        assert "extract_log_patterns" in log_tools

    def test_unknown_signal_returns_empty(self) -> None:
        """Unknown signal type should return empty list."""
        manager = _make_config_manager([])
        registry = ToolRegistry(config_manager=manager)
        assert registry.get_tools_for_signal("unknown") == []

    def test_case_insensitive(self) -> None:
        """Signal type lookup should be case-insensitive."""
        tools = [_make_tool("list_alerts", ToolCategory.ALERT)]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        assert "list_alerts" in registry.get_tools_for_signal("ALERTS")
        assert "list_alerts" in registry.get_tools_for_signal("alerts")


class TestToolSearch:
    """Tests for keyword-based tool search."""

    def test_search_by_name(self) -> None:
        """Should find tools matching name keyword."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH),
            _make_tool("list_traces", ToolCategory.TRACE_FETCH),
            _make_tool("list_log_entries", ToolCategory.LOG_FETCH),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        results = registry.search_tools("trace")
        names = [r["name"] for r in results]
        assert "fetch_trace" in names
        assert "list_traces" in names
        assert "list_log_entries" not in names

    def test_search_by_description(self) -> None:
        """Should find tools matching description keyword."""
        tools = [
            _make_tool(
                "my_tool",
                ToolCategory.ANALYSIS,
                description="Analyze kubernetes pods",
            ),
            _make_tool(
                "other_tool",
                ToolCategory.ANALYSIS,
                description="Check metrics",
            ),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        results = registry.search_tools("kubernetes")
        assert len(results) == 1
        assert results[0]["name"] == "my_tool"

    def test_search_case_insensitive(self) -> None:
        """Search should be case-insensitive."""
        tools = [_make_tool("Fetch_Trace", ToolCategory.TRACE_FETCH)]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        results = registry.search_tools("fetch")
        assert len(results) == 1

    def test_search_no_results(self) -> None:
        """Should return empty list when no match."""
        manager = _make_config_manager([])
        registry = ToolRegistry(config_manager=manager)
        assert registry.search_tools("nonexistent") == []

    def test_search_result_format(self) -> None:
        """Search results should contain name, description, category."""
        tools = [_make_tool("fetch_trace", ToolCategory.TRACE_FETCH)]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        results = registry.search_tools("trace")
        assert len(results) == 1
        assert "name" in results[0]
        assert "description" in results[0]
        assert "category" in results[0]


class TestCategorySummary:
    """Tests for category summary statistics."""

    def test_summary_counts(self) -> None:
        """Should return correct counts per category."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH, enabled=True),
            _make_tool("list_traces", ToolCategory.TRACE_FETCH, enabled=True),
            _make_tool("disabled_trace", ToolCategory.TRACE_FETCH, enabled=False),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        summary = registry.get_category_summary()
        trace_summary = summary.get("trace_fetch", {})
        assert trace_summary["total"] == 3
        assert trace_summary["enabled"] == 2
        assert trace_summary["disabled"] == 1


class TestToolInstructionGeneration:
    """Tests for agent instruction text generation."""

    def test_generates_all_categories(self) -> None:
        """Should include sections for all categories with tools."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH),
            _make_tool("list_log_entries", ToolCategory.LOG_FETCH),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        text = registry.generate_tool_instruction()
        assert "Available Tools" in text
        assert "fetch_trace" in text
        assert "list_log_entries" in text

    def test_signal_type_filter(self) -> None:
        """Should only include categories for the given signal type."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH),
            _make_tool("list_log_entries", ToolCategory.LOG_FETCH),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        text = registry.generate_tool_instruction(signal_type="trace")
        assert "fetch_trace" in text
        assert "list_log_entries" not in text

    def test_empty_categories_excluded(self) -> None:
        """Empty categories should not appear in output."""
        manager = _make_config_manager([])
        registry = ToolRegistry(config_manager=manager)

        text = registry.generate_tool_instruction()
        # Should only have the header line
        assert "Available Tools" in text


class TestGroupedTools:
    """Tests for get_grouped_tools method."""

    def test_groups_by_category(self) -> None:
        """Should group enabled tools by category value."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH),
            _make_tool("list_traces", ToolCategory.TRACE_FETCH),
            _make_tool("list_log_entries", ToolCategory.LOG_FETCH),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        grouped = registry.get_grouped_tools()
        assert "trace_fetch" in grouped
        assert len(grouped["trace_fetch"]) == 2
        assert "log_fetch" in grouped
        assert len(grouped["log_fetch"]) == 1

    def test_excludes_disabled(self) -> None:
        """Disabled tools should not appear in grouped output."""
        tools = [
            _make_tool("fetch_trace", ToolCategory.TRACE_FETCH, enabled=True),
            _make_tool("list_traces", ToolCategory.TRACE_FETCH, enabled=False),
        ]
        manager = _make_config_manager(tools)
        registry = ToolRegistry(config_manager=manager)

        grouped = registry.get_grouped_tools()
        assert len(grouped.get("trace_fetch", [])) == 1


class TestSignalCategoryMap:
    """Tests for the signal-to-category mapping constants."""

    def test_all_signals_mapped(self) -> None:
        """All expected signal types should have category mappings."""
        expected = {"trace", "metrics", "logs", "alerts", "slo", "gke"}
        assert expected.issubset(set(_SIGNAL_CATEGORY_MAP.keys()))

    def test_trace_maps_to_fetch_and_analyze(self) -> None:
        """Trace signal should map to both fetch and analyze categories."""
        categories = _SIGNAL_CATEGORY_MAP["trace"]
        assert ToolCategory.TRACE_FETCH in categories
        assert ToolCategory.TRACE_ANALYZE in categories


class TestCategoryDescriptions:
    """Tests for category description constants."""

    def test_all_categories_described(self) -> None:
        """Every ToolCategory should have a description."""
        for category in ToolCategory:
            assert category in _CATEGORY_DESCRIPTIONS, (
                f"Missing description for {category}"
            )


class TestSingleton:
    """Tests for the module-level singleton."""

    def test_get_tool_registry_returns_instance(self) -> None:
        """get_tool_registry should return a ToolRegistry."""
        registry = get_tool_registry()
        assert isinstance(registry, ToolRegistry)
