"""Tests for transform_agent_graph with hierarchical scoping and progressive disclosure.

Verifies scoped node IDs, depth/parent tracking, children_count, expandable
flags, and edge depth computation.
"""

from sre_agent.tools.analysis.genui_adapter import transform_agent_graph


def _make_span(
    *,
    span_id: str,
    name: str,
    kind: str,
    agent_name: str | None = None,
    tool_name: str | None = None,
    model_used: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    status_code: int = 1,
    duration_ms: float = 100.0,
    parent_span_id: str | None = None,
    children: list | None = None,
) -> dict:
    return {
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": name,
        "kind": kind,
        "agent_name": agent_name,
        "tool_name": tool_name,
        "model_used": model_used,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "children": children or [],
    }


def _build_graph(root_spans: list, root_agent_name: str | None = None) -> dict:
    return transform_agent_graph(
        {
            "root_spans": root_spans,
            "root_agent_name": root_agent_name,
        }
    )


def _node_by_id(result: dict, node_id: str) -> dict | None:
    return next((n for n in result["nodes"] if n["id"] == node_id), None)


def _edges_from(result: dict, source_id: str) -> list[dict]:
    return [e for e in result["edges"] if e["source_id"] == source_id]


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_empty_root_spans_returns_user_only():
    result = _build_graph([])
    assert len(result["nodes"]) == 1
    user = _node_by_id(result, "user")
    assert user is not None
    assert user["type"] == "user"
    assert user["depth"] == 0
    assert result["edges"] == []


def test_error_data_returns_empty():
    result = transform_agent_graph({"status": "error", "error": "boom"})
    assert result["nodes"] == []
    assert result["edges"] == []
    assert result["error"] == "boom"


def test_unwraps_status_result_envelope():
    inner = {
        "root_spans": [
            _make_span(
                span_id="s1",
                name="main",
                kind="agent_invocation",
                agent_name="main",
            )
        ],
        "root_agent_name": "main",
    }
    result = transform_agent_graph({"status": "success", "result": inner})
    assert _node_by_id(result, "agent:main") is not None


# ---------------------------------------------------------------------------
# Depth and parent tracking
# ---------------------------------------------------------------------------


def test_root_agent_has_depth_1_no_parent():
    result = _build_graph(
        [
            _make_span(
                span_id="s1",
                name="root",
                kind="agent_invocation",
                agent_name="sre_agent",
            )
        ],
        root_agent_name="sre_agent",
    )
    agent = _node_by_id(result, "agent:sre_agent")
    assert agent is not None
    assert agent["depth"] == 1
    assert agent["parent_agent_id"] is None
    assert agent["type"] == "agent"


def test_sub_agent_has_depth_2_and_parent():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="sub",
                kind="sub_agent_delegation",
                agent_name="trace_analyst",
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    sub = _node_by_id(result, "agent:trace_analyst")
    assert sub is not None
    assert sub["depth"] == 2
    assert sub["parent_agent_id"] == "agent:sre_agent"
    assert sub["type"] == "sub_agent"


def test_nested_sub_agent_has_depth_3():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="root_agent",
        children=[
            _make_span(
                span_id="s2",
                name="mid",
                kind="sub_agent_delegation",
                agent_name="mid_agent",
                parent_span_id="s1",
                children=[
                    _make_span(
                        span_id="s3",
                        name="deep",
                        kind="sub_agent_delegation",
                        agent_name="deep_agent",
                        parent_span_id="s2",
                    ),
                ],
            ),
        ],
    )
    result = _build_graph([root_span])
    deep = _node_by_id(result, "agent:deep_agent")
    assert deep is not None
    assert deep["depth"] == 3
    assert deep["parent_agent_id"] == "agent:mid_agent"


# ---------------------------------------------------------------------------
# Scoped tool and model nodes
# ---------------------------------------------------------------------------


def test_tool_scoped_per_agent():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="get_trace",
                kind="tool_execution",
                tool_name="get_trace",
                parent_span_id="s1",
            ),
            _make_span(
                span_id="s3",
                name="sub",
                kind="sub_agent_delegation",
                agent_name="trace_analyst",
                parent_span_id="s1",
                children=[
                    _make_span(
                        span_id="s4",
                        name="get_trace",
                        kind="tool_execution",
                        tool_name="get_trace",
                        parent_span_id="s3",
                    ),
                ],
            ),
        ],
    )
    result = _build_graph([root_span])
    # Same tool name produces two distinct scoped nodes
    tool1 = _node_by_id(result, "tool:get_trace@sre_agent")
    tool2 = _node_by_id(result, "tool:get_trace@trace_analyst")
    assert tool1 is not None
    assert tool2 is not None
    assert tool1["parent_agent_id"] == "agent:sre_agent"
    assert tool2["parent_agent_id"] == "agent:trace_analyst"
    assert tool1["depth"] == 2
    assert tool2["depth"] == 3


def test_model_scoped_per_agent():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="llm",
                kind="llm_call",
                model_used="gemini-2.5-flash",
                input_tokens=100,
                output_tokens=200,
                parent_span_id="s1",
            ),
            _make_span(
                span_id="s3",
                name="sub",
                kind="sub_agent_delegation",
                agent_name="logs_analyst",
                parent_span_id="s1",
                children=[
                    _make_span(
                        span_id="s4",
                        name="llm",
                        kind="llm_call",
                        model_used="gemini-2.5-flash",
                        input_tokens=50,
                        output_tokens=80,
                        parent_span_id="s3",
                    ),
                ],
            ),
        ],
    )
    result = _build_graph([root_span])
    m1 = _node_by_id(result, "model:gemini-2.5-flash@sre_agent")
    m2 = _node_by_id(result, "model:gemini-2.5-flash@logs_analyst")
    assert m1 is not None
    assert m2 is not None
    assert m1["total_tokens"] == 300  # 100+200
    assert m2["total_tokens"] == 130  # 50+80
    assert m1["parent_agent_id"] == "agent:sre_agent"
    assert m2["parent_agent_id"] == "agent:logs_analyst"


# ---------------------------------------------------------------------------
# Children count and expandable
# ---------------------------------------------------------------------------


def test_agent_children_count():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="get_trace",
                kind="tool_execution",
                tool_name="get_trace",
                parent_span_id="s1",
            ),
            _make_span(
                span_id="s3",
                name="llm",
                kind="llm_call",
                model_used="gemini-2.5-flash",
                input_tokens=10,
                output_tokens=20,
                parent_span_id="s1",
            ),
            _make_span(
                span_id="s4",
                name="sub",
                kind="sub_agent_delegation",
                agent_name="trace_analyst",
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    agent = _node_by_id(result, "agent:sre_agent")
    assert agent is not None
    # 3 children: tool, model, sub-agent
    assert agent["children_count"] == 3
    assert agent["expandable"] is True


def test_leaf_agent_not_expandable():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="sub",
                kind="sub_agent_delegation",
                agent_name="simple_agent",
                parent_span_id="s1",
                # No children
            ),
        ],
    )
    result = _build_graph([root_span])
    simple = _node_by_id(result, "agent:simple_agent")
    assert simple is not None
    assert simple["children_count"] == 0
    assert simple["expandable"] is False


def test_tool_and_model_never_expandable():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="agent_a",
        children=[
            _make_span(
                span_id="s2",
                name="tool",
                kind="tool_execution",
                tool_name="my_tool",
                parent_span_id="s1",
            ),
            _make_span(
                span_id="s3",
                name="llm",
                kind="llm_call",
                model_used="model_x",
                input_tokens=1,
                output_tokens=1,
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    tool = _node_by_id(result, "tool:my_tool@agent_a")
    model = _node_by_id(result, "model:model_x@agent_a")
    assert tool is not None and tool["expandable"] is False
    assert model is not None and model["expandable"] is False


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


def test_user_to_root_agent_edge():
    result = _build_graph(
        [
            _make_span(
                span_id="s1",
                name="root",
                kind="agent_invocation",
                agent_name="sre_agent",
            )
        ]
    )
    edges = _edges_from(result, "user")
    assert len(edges) == 1
    assert edges[0]["target_id"] == "agent:sre_agent"
    assert edges[0]["label"] == "invokes"


def test_agent_to_tool_edge_uses_scoped_id():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="get_logs",
                kind="tool_execution",
                tool_name="get_logs",
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    edges = _edges_from(result, "agent:sre_agent")
    tool_edges = [e for e in edges if e["label"] == "calls"]
    assert len(tool_edges) == 1
    assert tool_edges[0]["target_id"] == "tool:get_logs@sre_agent"


def test_agent_to_model_edge_uses_scoped_id():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="llm",
                kind="llm_call",
                model_used="gemini",
                input_tokens=1,
                output_tokens=1,
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    edges = _edges_from(result, "agent:sre_agent")
    gen_edges = [e for e in edges if e["label"] == "generates"]
    assert len(gen_edges) == 1
    assert gen_edges[0]["target_id"] == "model:gemini@sre_agent"


def test_delegation_edge():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="s2",
                name="sub",
                kind="sub_agent_delegation",
                agent_name="logs_analyst",
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    edges = _edges_from(result, "agent:sre_agent")
    del_edges = [e for e in edges if e["label"] == "delegates_to"]
    assert len(del_edges) == 1
    assert del_edges[0]["target_id"] == "agent:logs_analyst"


def test_edge_depth_matches_deepest_endpoint():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="root_agent",
        children=[
            _make_span(
                span_id="s2",
                name="tool",
                kind="tool_execution",
                tool_name="my_tool",
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    # root_agent is depth 1, tool is depth 2 → edge depth = 2
    edges = _edges_from(result, "agent:root_agent")
    assert len(edges) == 1
    assert edges[0]["depth"] == 2


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


def test_error_propagates_to_node_and_edge():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="agent_x",
        children=[
            _make_span(
                span_id="s2",
                name="bad_tool",
                kind="tool_execution",
                tool_name="failing_tool",
                status_code=2,
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    tool = _node_by_id(result, "tool:failing_tool@agent_x")
    assert tool is not None
    assert tool["has_error"] is True
    edges = _edges_from(result, "agent:agent_x")
    tool_edge = next(e for e in edges if e["label"] == "calls")
    assert tool_edge["has_error"] is True


# ---------------------------------------------------------------------------
# Edge aggregation (multiple calls to same tool)
# ---------------------------------------------------------------------------


def test_multiple_calls_aggregate():
    root_span = _make_span(
        span_id="s1",
        name="root",
        kind="agent_invocation",
        agent_name="agent_a",
        children=[
            _make_span(
                span_id="s2",
                name="tool1",
                kind="tool_execution",
                tool_name="search",
                duration_ms=100,
                parent_span_id="s1",
            ),
            _make_span(
                span_id="s3",
                name="tool2",
                kind="tool_execution",
                tool_name="search",
                duration_ms=300,
                parent_span_id="s1",
            ),
        ],
    )
    result = _build_graph([root_span])
    tool = _node_by_id(result, "tool:search@agent_a")
    assert tool is not None
    assert tool["call_count"] == 2
    edges = _edges_from(result, "agent:agent_a")
    search_edge = next(e for e in edges if e["label"] == "calls")
    assert search_edge["call_count"] == 2
    assert search_edge["avg_duration_ms"] == 200.0


# ---------------------------------------------------------------------------
# User node children_count
# ---------------------------------------------------------------------------


def test_user_children_count_matches_root_agents():
    root_spans = [
        _make_span(
            span_id="s1",
            name="a1",
            kind="agent_invocation",
            agent_name="agent_1",
        ),
        _make_span(
            span_id="s2",
            name="a2",
            kind="agent_invocation",
            agent_name="agent_2",
        ),
    ]
    result = _build_graph(root_spans)
    user = _node_by_id(result, "user")
    assert user is not None
    assert user["children_count"] == 2


# ---------------------------------------------------------------------------
# Full integration scenario
# ---------------------------------------------------------------------------


def test_full_agent_hierarchy():
    """Simulate a realistic Auto SRE trace hierarchy."""
    tree = _make_span(
        span_id="root",
        name="sre_agent",
        kind="agent_invocation",
        agent_name="sre_agent",
        children=[
            _make_span(
                span_id="llm1",
                name="llm",
                kind="llm_call",
                model_used="gemini-2.5-flash",
                input_tokens=500,
                output_tokens=1000,
                parent_span_id="root",
            ),
            _make_span(
                span_id="tool1",
                name="route_request",
                kind="tool_execution",
                tool_name="route_request",
                parent_span_id="root",
            ),
            _make_span(
                span_id="sub1",
                name="trace_analyst",
                kind="sub_agent_delegation",
                agent_name="trace_analyst",
                parent_span_id="root",
                children=[
                    _make_span(
                        span_id="llm2",
                        name="llm",
                        kind="llm_call",
                        model_used="gemini-2.5-flash",
                        input_tokens=200,
                        output_tokens=400,
                        parent_span_id="sub1",
                    ),
                    _make_span(
                        span_id="tool2",
                        name="get_trace",
                        kind="tool_execution",
                        tool_name="get_trace",
                        parent_span_id="sub1",
                    ),
                ],
            ),
            _make_span(
                span_id="sub2",
                name="logs_analyst",
                kind="sub_agent_delegation",
                agent_name="logs_analyst",
                parent_span_id="root",
                children=[
                    _make_span(
                        span_id="tool3",
                        name="search_logs",
                        kind="tool_execution",
                        tool_name="search_logs",
                        parent_span_id="sub2",
                    ),
                ],
            ),
        ],
    )
    result = _build_graph([tree], root_agent_name="sre_agent")
    assert result["root_agent_name"] == "sre_agent"

    # User node
    user = _node_by_id(result, "user")
    assert user["depth"] == 0
    assert user["children_count"] == 1  # one root agent

    # Root agent — 4 children: model@sre, tool@sre, trace_analyst, logs_analyst
    sre = _node_by_id(result, "agent:sre_agent")
    assert sre["depth"] == 1
    assert sre["expandable"] is True
    assert sre["children_count"] == 4

    # Sub-agents
    trace = _node_by_id(result, "agent:trace_analyst")
    assert trace["depth"] == 2
    assert trace["parent_agent_id"] == "agent:sre_agent"
    assert trace["expandable"] is True
    assert trace["children_count"] == 2  # model + tool

    logs = _node_by_id(result, "agent:logs_analyst")
    assert logs["depth"] == 2
    assert logs["parent_agent_id"] == "agent:sre_agent"
    assert logs["expandable"] is True
    assert logs["children_count"] == 1  # tool only

    # Scoped tools
    assert _node_by_id(result, "tool:route_request@sre_agent") is not None
    assert _node_by_id(result, "tool:get_trace@trace_analyst") is not None
    assert _node_by_id(result, "tool:search_logs@logs_analyst") is not None

    # Scoped models
    assert _node_by_id(result, "model:gemini-2.5-flash@sre_agent") is not None
    assert _node_by_id(result, "model:gemini-2.5-flash@trace_analyst") is not None

    # Edge count: user→sre, sre→model, sre→tool, sre→trace, sre→logs,
    #             trace→model, trace→tool, logs→tool = 8
    assert len(result["edges"]) == 8
