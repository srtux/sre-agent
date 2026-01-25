import json

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.trace.filters import (
    TraceQueryBuilder,
    TraceSelector,
    build_trace_filter,
    select_traces_from_statistical_outliers,
    select_traces_manually,
)


def test_builder_init():
    builder = TraceQueryBuilder()
    assert builder.build() == ""


def test_span_name():
    builder = TraceQueryBuilder()
    builder.span_name("my-span")
    assert builder.build() == "span:my-span"

    builder.clear()
    builder.span_name("my-span", match_exact=True)
    assert builder.build() == "+span:my-span"

    builder.clear()
    builder.span_name("my-span", root_only=True)
    assert builder.build() == "root:my-span"


def test_latency():
    builder = TraceQueryBuilder()
    builder.latency(min_latency_ms=500)
    assert builder.build() == "latency:500ms"


def test_attribute():
    builder = TraceQueryBuilder()
    builder.attribute("key", "value")
    assert builder.build() == "key:value"

    builder.clear()
    builder.attribute("key", "value", match_exact=True)
    assert builder.build() == "+key:value"

    builder.clear()
    builder.attribute("key", "value", root_only=True)
    assert builder.build() == "^key:value"

    builder.clear()
    builder.attribute("key", "value", match_exact=True, root_only=True)
    # The implementation produces "+^key:value" because match_exact adds "+" and root_only adds "^".
    # Docs example shows "+^url:[VALUE]", so this is correct.
    assert builder.build() == "+^key:value"


def test_complex_query():
    builder = TraceQueryBuilder()
    (
        builder.span_name("root_op", root_only=True)
        .latency(min_latency_ms=100)
        .status(500)
        .method("GET")
    )

    assert (
        builder.build() == "root:root_op latency:100ms /http/status_code:500 method:GET"
    )


def test_mix_root_and_normal():
    builder = TraceQueryBuilder()
    builder.span_name("main", root_only=True).span_name("db_query")
    assert builder.build() == "root:main span:db_query"


def test_url_method():
    builder = TraceQueryBuilder()
    builder.url("/api/v1").method("POST", root_only=True)
    assert builder.build() == "url:/api/v1 ^method:POST"

    builder.clear()
    builder.url("/api/v1", root_only=True)
    assert builder.build() == "^url:/api/v1"


def test_internal_add_term():
    builder = TraceQueryBuilder()
    builder._add_term("raw", root_only=False)
    assert builder.build() == "raw"
    builder.clear()
    builder._add_term("raw", root_only=True)
    assert builder.build() == "^raw"


def test_selector_statistical_outliers():
    selector = TraceSelector()
    traces = [
        {"traceId": "t1", "latency": 100},
        {"traceId": "t2", "latency": 110},
        {"traceId": "t3", "latency": 1000},  # Outlier
    ]
    # Mean ~403, Stdev ~517. 403 + 2*517 = 1437. Wait, 1000 is not 2 stdevs from mean if we only have 3 points.

    # Let's use more points to make it more obvious
    traces = [{"traceId": f"t{i}", "latency": 10} for i in range(10)]
    traces.append({"traceId": "outlier", "latency": 1000})
    # Mean: (10*10 + 1000) / 11 = 100
    # Stdev: roughly 300
    # Threshold: 100 + 600 = 700. 1000 > 700.

    outliers = selector.from_statistical_outliers(traces)
    assert "outlier" in outliers
    assert len(outliers) == 1

    assert selector.from_statistical_outliers([]) == []


def test_select_traces_tool():
    traces = [{"traceId": "outlier", "latency": 1000}] + [
        {"traceId": f"t{i}", "latency": 10} for i in range(20)
    ]

    # Test valid JSON list
    resp = select_traces_from_statistical_outliers(json.dumps(traces))
    assert resp["status"] == ToolStatus.SUCCESS
    assert "outlier" in resp["result"]["trace_ids"]

    # Test direct list
    resp = select_traces_from_statistical_outliers(traces)
    assert resp["status"] == ToolStatus.SUCCESS
    assert "outlier" in resp["result"]["trace_ids"]

    # Test invalid JSON
    resp = select_traces_from_statistical_outliers("{ invalid }")
    assert resp["status"] == ToolStatus.ERROR
    assert "Invalid JSON" in resp["error"]

    # Test JSON but not list
    resp = select_traces_from_statistical_outliers('{"key": "val"}')
    assert resp["status"] == ToolStatus.ERROR
    assert "not a list" in resp["error"]

    # Test invalid type
    resp = select_traces_from_statistical_outliers(123)
    assert resp["status"] == ToolStatus.ERROR
    assert "must be JSON string or list" in resp["error"]


def test_select_traces_manually():
    resp = select_traces_manually(["t1", "t2"])
    assert resp["status"] == ToolStatus.SUCCESS
    assert resp["result"]["trace_ids"] == ["t1", "t2"]


def test_build_trace_filter_helper():
    f = build_trace_filter(
        min_latency_ms=500,
        error_only=True,
        service_name="frontend",
        http_status=500,
        attributes={"env": "prod"},
    )
    assert "latency:500ms" in f
    assert "error:true" in f
    assert "service.name:frontend" in f
    assert "/http/status_code:500" in f
    assert "env:prod" in f

    # Test custom filter override
    assert build_trace_filter(custom_filter="some filter") == "some filter"

    # Test empty
    assert build_trace_filter() == ""
