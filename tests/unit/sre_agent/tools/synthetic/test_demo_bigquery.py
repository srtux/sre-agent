"""Tests for the demo BigQuery SQL Analytics module.

Validates dataset/table listing, schema introspection, JSON key discovery,
and the simplified SQL query executor against the synthetic span data.
"""

from __future__ import annotations

import json

from sre_agent.tools.synthetic.demo_bigquery import (
    execute_demo_query,
    get_demo_datasets,
    get_demo_json_keys,
    get_demo_table_schema,
    get_demo_tables,
)

# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


class TestGetDemoDatasets:
    """Validate dataset listing."""

    def test_returns_expected_datasets(self) -> None:
        result = get_demo_datasets()
        assert result == {"datasets": ["traces", "agentops"]}

    def test_datasets_is_list(self) -> None:
        result = get_demo_datasets()
        assert isinstance(result["datasets"], list)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class TestGetDemoTables:
    """Validate table listing per dataset."""

    def test_traces_dataset_has_expected_tables(self) -> None:
        result = get_demo_tables("traces")
        assert "_AllSpans" in result["tables"]
        assert "_AllLogs" in result["tables"]

    def test_agentops_dataset_has_expected_tables(self) -> None:
        result = get_demo_tables("agentops")
        tables = result["tables"]
        assert "agent_spans_raw" in tables
        assert "agent_topology_nodes" in tables
        assert "agent_topology_edges" in tables
        assert "agent_trajectories" in tables
        assert "agent_graph_hourly" in tables

    def test_unknown_dataset_returns_empty(self) -> None:
        result = get_demo_tables("nonexistent")
        assert result == {"tables": []}


# ---------------------------------------------------------------------------
# Table Schema
# ---------------------------------------------------------------------------


class TestGetDemoTableSchema:
    """Validate table schema responses."""

    def test_allspans_schema_has_expected_columns(self) -> None:
        result = get_demo_table_schema("traces", "_AllSpans")
        schema = result["schema"]
        col_names = [col["name"] for col in schema]
        assert "span_id" in col_names
        assert "parent_span_id" in col_names
        assert "trace_id" in col_names
        assert "name" in col_names
        assert "start_time" in col_names
        assert "end_time" in col_names
        assert "duration_nano" in col_names
        assert "status" in col_names
        assert "attributes" in col_names
        assert "resource" in col_names

    def test_allspans_span_id_is_string(self) -> None:
        result = get_demo_table_schema("traces", "_AllSpans")
        schema = result["schema"]
        span_id_col = next(c for c in schema if c["name"] == "span_id")
        assert span_id_col["type"] == "STRING"

    def test_allspans_duration_is_int64(self) -> None:
        result = get_demo_table_schema("traces", "_AllSpans")
        schema = result["schema"]
        dur_col = next(c for c in schema if c["name"] == "duration_nano")
        assert dur_col["type"] == "INT64"

    def test_allspans_status_is_record(self) -> None:
        result = get_demo_table_schema("traces", "_AllSpans")
        schema = result["schema"]
        status_col = next(c for c in schema if c["name"] == "status")
        assert status_col["type"] == "RECORD"
        child_names = [f["name"] for f in status_col["fields"]]
        assert "code" in child_names
        assert "message" in child_names

    def test_allspans_attributes_is_json(self) -> None:
        result = get_demo_table_schema("traces", "_AllSpans")
        schema = result["schema"]
        attrs_col = next(c for c in schema if c["name"] == "attributes")
        assert attrs_col["type"] == "JSON"

    def test_alllogs_schema_has_timestamp(self) -> None:
        result = get_demo_table_schema("traces", "_AllLogs")
        col_names = [c["name"] for c in result["schema"]]
        assert "timestamp" in col_names

    def test_unknown_table_returns_default_schema(self) -> None:
        result = get_demo_table_schema("agentops", "agent_spans_raw")
        assert "schema" in result
        assert len(result["schema"]) > 0


# ---------------------------------------------------------------------------
# JSON Keys
# ---------------------------------------------------------------------------


class TestGetDemoJsonKeys:
    """Validate JSON key discovery."""

    def test_allspans_attributes_keys(self) -> None:
        result = get_demo_json_keys("traces", "_AllSpans", "attributes")
        keys = result["keys"]
        assert "gen_ai.operation.name" in keys
        assert "gen_ai.agent.name" in keys
        assert "gen_ai.tool.name" in keys
        assert "gen_ai.usage.input_tokens" in keys
        assert "gen_ai.usage.output_tokens" in keys
        assert "gen_ai.request.model" in keys
        assert "gen_ai.response.model" in keys
        assert "gen_ai.conversation.id" in keys
        assert "gen_ai.system" in keys

    def test_allspans_resource_keys(self) -> None:
        result = get_demo_json_keys("traces", "_AllSpans", "resource")
        keys = result["keys"]
        assert "service.name" in keys
        assert "service.version" in keys
        assert "cloud.provider" in keys
        assert "cloud.region" in keys
        assert "cloud.platform" in keys
        assert "cloud.resource_id" in keys

    def test_unknown_column_returns_empty(self) -> None:
        result = get_demo_json_keys("traces", "_AllSpans", "nonexistent")
        assert result == {"keys": []}


# ---------------------------------------------------------------------------
# Query Executor
# ---------------------------------------------------------------------------


class TestExecuteDemoQuery:
    """Validate the simplified SQL executor."""

    def test_select_star_limit_returns_rows(self) -> None:
        result = execute_demo_query("SELECT * FROM traces._AllSpans LIMIT 10")
        assert "columns" in result
        assert "rows" in result
        assert len(result["rows"]) == 10

    def test_select_star_columns_match_schema(self) -> None:
        result = execute_demo_query("SELECT * FROM traces._AllSpans LIMIT 1")
        expected_cols = {
            "span_id",
            "parent_span_id",
            "trace_id",
            "name",
            "start_time",
            "end_time",
            "duration_nano",
            "status",
            "attributes",
            "resource",
        }
        assert set(result["columns"]) == expected_cols

    def test_count_star_returns_count(self) -> None:
        result = execute_demo_query("SELECT COUNT(*) as cnt FROM traces._AllSpans")
        assert "columns" in result
        assert "rows" in result
        assert len(result["rows"]) == 1
        assert result["rows"][0]["cnt"] > 0

    def test_count_star_value_is_integer(self) -> None:
        result = execute_demo_query("SELECT COUNT(*) as cnt FROM traces._AllSpans")
        assert isinstance(result["rows"][0]["cnt"], int)

    def test_select_distinct_returns_unique_values(self) -> None:
        result = execute_demo_query(
            "SELECT DISTINCT name FROM traces._AllSpans LIMIT 100"
        )
        names = [r["name"] for r in result["rows"]]
        assert len(names) == len(set(names))
        assert len(names) > 1

    def test_select_specific_columns(self) -> None:
        result = execute_demo_query(
            "SELECT span_id, name FROM traces._AllSpans LIMIT 5"
        )
        assert result["columns"] == ["span_id", "name"]
        assert len(result["rows"]) == 5
        for row in result["rows"]:
            assert "span_id" in row
            assert "name" in row

    def test_group_by_with_count(self) -> None:
        result = execute_demo_query(
            "SELECT name, COUNT(*) as cnt FROM traces._AllSpans "
            "GROUP BY name ORDER BY cnt DESC LIMIT 5"
        )
        assert "name" in result["columns"]
        assert "cnt" in result["columns"]
        assert len(result["rows"]) <= 5
        # Should be ordered descending
        counts = [r["cnt"] for r in result["rows"]]
        assert counts == sorted(counts, reverse=True)

    def test_where_equality(self) -> None:
        result = execute_demo_query(
            "SELECT * FROM traces._AllSpans WHERE name = 'classify_intent' LIMIT 10"
        )
        for row in result["rows"]:
            assert row["name"] == "classify_intent"

    def test_where_like(self) -> None:
        result = execute_demo_query(
            "SELECT * FROM traces._AllSpans WHERE name LIKE '%intent%' LIMIT 10"
        )
        for row in result["rows"]:
            assert "intent" in row["name"].lower()

    def test_row_values_have_correct_types(self) -> None:
        result = execute_demo_query("SELECT * FROM traces._AllSpans LIMIT 1")
        row = result["rows"][0]
        assert isinstance(row["span_id"], str)
        assert isinstance(row["trace_id"], str)
        assert isinstance(row["name"], str)
        assert isinstance(row["duration_nano"], int)
        assert isinstance(row["status"], dict)
        assert isinstance(row["attributes"], str)  # JSON string
        assert isinstance(row["resource"], str)  # JSON string
        assert isinstance(row["start_time"], str)
        assert isinstance(row["end_time"], str)

    def test_attributes_are_valid_json(self) -> None:
        result = execute_demo_query("SELECT * FROM traces._AllSpans LIMIT 5")
        for row in result["rows"]:
            parsed = json.loads(row["attributes"])
            assert isinstance(parsed, dict)
            assert "gen_ai.operation.name" in parsed

    def test_resource_is_valid_json(self) -> None:
        result = execute_demo_query("SELECT * FROM traces._AllSpans LIMIT 5")
        for row in result["rows"]:
            parsed = json.loads(row["resource"])
            assert isinstance(parsed, dict)
            assert "attributes" in parsed

    def test_fallback_for_unparseable_query(self) -> None:
        result = execute_demo_query("THIS IS NOT SQL AT ALL")
        assert "columns" in result
        assert "rows" in result
        # Fallback returns up to 100 rows
        assert len(result["rows"]) <= 100

    def test_limit_respected(self) -> None:
        r3 = execute_demo_query("SELECT * FROM traces._AllSpans LIMIT 3")
        r7 = execute_demo_query("SELECT * FROM traces._AllSpans LIMIT 7")
        assert len(r3["rows"]) == 3
        assert len(r7["rows"]) == 7

    def test_order_by_duration_desc(self) -> None:
        result = execute_demo_query(
            "SELECT name, duration_nano FROM traces._AllSpans "
            "ORDER BY duration_nano DESC LIMIT 10"
        )
        durations = [r["duration_nano"] for r in result["rows"]]
        assert durations == sorted(durations, reverse=True)
