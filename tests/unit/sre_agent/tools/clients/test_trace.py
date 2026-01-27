"""Unit tests for the Cloud Trace client."""

from unittest.mock import MagicMock, patch

import pytest

# Global mocks to avoid segfaults/proto issues
with patch("google.cloud.trace_v1.TraceServiceClient", MagicMock()):
    from sre_agent.schema import ToolStatus
    from sre_agent.tools.clients.trace import (
        TraceFilterBuilder,
        fetch_trace,
        find_example_traces,
        validate_trace,
    )


def test_trace_filter_builder_extensive():
    builder = TraceFilterBuilder()
    builder.add_latency(500).add_root_span_name("my-op", exact=True).add_attribute(
        "key", "val", root_only=True
    )
    builder.add_span_name("sub", root_only=False)
    filter_str = builder.build()
    assert "latency:500ms" in filter_str
    assert "+root:my-op" in filter_str
    assert "^key:val" in filter_str
    assert "span:sub" in filter_str


def test_validate_trace_comprehensive():
    # Valid trace
    valid_trace = {
        "trace_id": "t1",
        "duration_ms": 100,
        "spans": [
            {
                "span_id": "s1",
                "name": "root",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T00:00:01Z",
            }
        ],
    }
    result = validate_trace(valid_trace)
    assert result["valid"] is True

    # Missing fields
    result = validate_trace({"trace_id": "t1"})
    assert result["valid"] is False
    assert "spans" in str(result["issues"])

    # Large trace
    large_trace = {
        "trace_id": "t1",
        "duration_ms": 100,
        "spans": [
            {"span_id": str(i), "name": "n", "start_time": "...", "end_time": "..."}
            for i in range(1001)
        ],
    }
    result = validate_trace(large_trace)
    assert "large trace" in str(result["issues"])


@pytest.mark.asyncio
async def test_find_example_traces_complex():
    with patch("sre_agent.tools.clients.trace.list_traces") as mock_list:
        with patch(
            "sre_agent.tools.clients.trace.get_current_project_id", return_value="proj"
        ):
            # Mock enough traces to trigger statistics.stdev
            traces = []
            for i in range(25):
                traces.append(
                    {
                        "trace_id": f"t{i}",
                        "duration_ms": 100 + i * 10,
                        "name": "op",
                        "spans": [
                            {
                                "span_id": f"s{i}",
                                "name": "n",
                                "start_time": "...",
                                "end_time": "...",
                            }
                        ],
                    }
                )

            # Mock list_traces for 3 calls (slow, all, errors)
            mock_list.side_effect = [
                {"status": ToolStatus.SUCCESS, "result": traces[20:]},  # slow
                {"status": ToolStatus.SUCCESS, "result": traces},  # all
                {"status": ToolStatus.SUCCESS, "result": [traces[5]]},  # errors
                {"status": ToolStatus.SUCCESS, "result": []},  # root name search
            ]

            result = await find_example_traces(project_id="proj")
            assert result.status == ToolStatus.SUCCESS
            final_res = result.result
            assert "baseline" in final_res
            assert "anomaly" in final_res
            assert final_res["validation"]["sample_adequate"] is True


@pytest.mark.asyncio
async def test_fetch_trace_shortcut():
    with patch("sre_agent.tools.clients.trace._fetch_trace_sync") as mock_fetch:
        mock_fetch.return_value = {"trace_id": "ok"}
        result = await fetch_trace("ok", "proj")
        assert result.status == ToolStatus.SUCCESS
        assert result.result["trace_id"] == "ok"
