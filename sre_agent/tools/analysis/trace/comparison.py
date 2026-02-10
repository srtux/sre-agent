"""Trace comparison utilities for diff analysis between traces."""

import logging
from datetime import datetime
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...common import adk_tool
from ...common.telemetry import log_tool_call
from .analysis import build_call_graph, calculate_span_durations

logger = logging.getLogger(__name__)

SpanData = dict[str, Any]


@adk_tool
def compare_span_timings(
    baseline_trace_id: str,
    target_trace_id: str,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Compares timing between spans in two traces and detects performance anti-patterns."""
    log_tool_call(
        logger,
        "compare_span_timings",
        baseline_trace_id=baseline_trace_id,
        target_trace_id=target_trace_id,
    )

    try:
        baseline_result = calculate_span_durations(
            baseline_trace_id, project_id, tool_context=tool_context
        )
        target_result = calculate_span_durations(
            target_trace_id, project_id, tool_context=tool_context
        )

        if baseline_result.status == ToolStatus.ERROR:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"Baseline trace error: {baseline_result.error}",
            )
        if target_result.status == ToolStatus.ERROR:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"Target trace error: {target_result.error}",
            )

        baseline_timings = baseline_result.result.get("spans", [])
        target_timings = target_result.result.get("spans", [])

        # Anti-Pattern Detection
        patterns = []

        # N+1 Query Detection
        if target_timings:
            sorted_spans = sorted(
                [s for s in target_timings if s.get("start_time")],
                key=lambda x: x.get("start_time_unix") or x["start_time"],
            )

            if sorted_spans:
                current_run: list[SpanData] = []
                for s in sorted_spans:
                    if not current_run:
                        current_run.append(s)
                    else:
                        if s.get("name") == current_run[-1].get("name"):
                            current_run.append(s)
                        else:
                            if len(current_run) >= 3:
                                duration_sum = sum(
                                    s.get("duration_ms") or 0 for s in current_run
                                )
                                if duration_sum > 50:
                                    patterns.append(
                                        {
                                            "type": "n_plus_one",
                                            "description": f"Potential N+1 Query: '{current_run[0].get('name')}' called {len(current_run)} times sequentially.",
                                            "span_name": current_run[0].get("name"),
                                            "count": len(current_run),
                                            "total_duration_ms": duration_sum,
                                            "impact": "high"
                                            if duration_sum > 200
                                            else "medium",
                                        }
                                    )
                            current_run = [s]

                # Check last run
                if len(current_run) >= 3:
                    duration_sum = sum(s.get("duration_ms") or 0 for s in current_run)
                    if duration_sum > 50:
                        patterns.append(
                            {
                                "type": "n_plus_one",
                                "description": f"Potential N+1 Query: '{current_run[0].get('name')}' called {len(current_run)} times sequentially.",
                                "span_name": current_run[0].get("name"),
                                "count": len(current_run),
                                "total_duration_ms": duration_sum,
                                "impact": "high" if duration_sum > 200 else "medium",
                            }
                        )

        # Serial Chain Detection
        if target_timings and sorted_spans:
            sequential_chains = []
            current_chain: list[SpanData] = []
            gap_threshold_ms = 10

            for i in range(len(sorted_spans) - 1):
                curr_span = sorted_spans[i]
                next_span = sorted_spans[i + 1]

                if not (curr_span.get("end_time") and next_span.get("start_time")):
                    continue

                try:
                    if curr_span.get("end_time_unix"):
                        curr_end = curr_span["end_time_unix"] * 1000
                    else:
                        curr_end = (
                            datetime.fromisoformat(
                                curr_span["end_time"].replace("Z", "+00:00")
                            ).timestamp()
                            * 1000
                        )

                    if next_span.get("start_time_unix"):
                        next_start = next_span["start_time_unix"] * 1000
                    else:
                        next_start = (
                            datetime.fromisoformat(
                                next_span["start_time"].replace("Z", "+00:00")
                            ).timestamp()
                            * 1000
                        )

                    is_parent_child = curr_span.get("span_id") == next_span.get(
                        "parent_span_id"
                    ) or next_span.get("span_id") == curr_span.get("parent_span_id")

                    if is_parent_child:
                        if len(current_chain) >= 3:
                            sequential_chains.append(current_chain[:])
                        current_chain = []
                        continue

                    gap = next_start - curr_end

                    if gap >= 0 and gap <= gap_threshold_ms:
                        if not current_chain:
                            current_chain.append(curr_span)
                        current_chain.append(next_span)
                    else:
                        if len(current_chain) >= 3:
                            sequential_chains.append(current_chain[:])
                        current_chain = []

                except (ValueError, TypeError, KeyError):
                    continue

            if len(current_chain) >= 3:
                sequential_chains.append(current_chain[:])

            for chain in sequential_chains:
                chain_duration = sum(s.get("duration_ms") or 0 for s in chain)

                if chain_duration > 100:
                    span_names = [s.get("name") for s in chain]
                    patterns.append(
                        {
                            "type": "serial_chain",
                            "description": f"Serial Chain: {len(chain)} operations running sequentially that could potentially be parallelized.",
                            "span_names": span_names,
                            "count": len(chain),
                            "total_duration_ms": round(chain_duration, 2),
                            "impact": "high" if chain_duration > 500 else "medium",
                            "recommendation": "Consider parallelizing these operations using async/await or concurrent execution.",
                        }
                    )

        # Compare spans by name
        baseline_by_name: dict[str, list[SpanData]] = {}
        for s in baseline_timings:
            name = s.get("name")
            if name:
                if name not in baseline_by_name:
                    baseline_by_name[name] = []
                baseline_by_name[name].append(s)

        target_by_name: dict[str, list[SpanData]] = {}
        for s in target_timings:
            name = s.get("name")
            if name:
                if name not in target_by_name:
                    target_by_name[name] = []
                target_by_name[name].append(s)

        slower_spans = []
        faster_spans = []

        all_names = set(baseline_by_name.keys()) | set(target_by_name.keys())

        for name in all_names:
            baseline_spans = baseline_by_name.get(name, [])
            target_spans = target_by_name.get(name, [])

            if baseline_spans and target_spans:
                baseline_avg = sum(
                    s.get("duration_ms") or 0 for s in baseline_spans
                ) / len(baseline_spans)
                target_avg = sum(s.get("duration_ms") or 0 for s in target_spans) / len(
                    target_spans
                )

                diff_ms = target_avg - baseline_avg
                diff_pct = (diff_ms / baseline_avg * 100) if baseline_avg > 0 else 0

                comparison = {
                    "span_name": name,
                    "baseline_duration_ms": round(baseline_avg, 2),
                    "target_duration_ms": round(target_avg, 2),
                    "diff_ms": round(diff_ms, 2),
                    "diff_percent": round(diff_pct, 1),
                    "baseline_count": len(baseline_spans),
                    "target_count": len(target_spans),
                }

                if diff_pct > 10 or diff_ms > 50:
                    slower_spans.append(comparison)
                elif diff_pct < -10 or diff_ms < -50:
                    faster_spans.append(comparison)

        slower_spans.sort(key=lambda x: x["diff_ms"], reverse=True)
        faster_spans.sort(key=lambda x: x["diff_ms"])

        missing_from_target = [
            name for name in baseline_by_name if name not in target_by_name
        ]
        new_in_target = [
            name for name in target_by_name if name not in baseline_by_name
        ]

        baseline_total = sum(s.get("duration_ms") or 0 for s in baseline_timings)
        target_total = sum(s.get("duration_ms") or 0 for s in target_timings)

        result = {
            "slower_spans": slower_spans,
            "faster_spans": faster_spans,
            "missing_from_target": missing_from_target,
            "new_in_target": new_in_target,
            "patterns": patterns,
            "summary": {
                "baseline_total_ms": round(baseline_total, 2),
                "target_total_ms": round(target_total, 2),
                "total_diff_ms": round(target_total - baseline_total, 2),
                "num_slower": len(slower_spans),
                "num_faster": len(faster_spans),
            },
        }
        return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)

    except Exception as e:
        logger.error(f"compare_span_timings failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))


@adk_tool
def find_structural_differences(
    baseline_trace_id: str,
    target_trace_id: str,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Compares the call graph structure between two traces."""
    log_tool_call(
        logger,
        "find_structural_differences",
        baseline_trace_id=baseline_trace_id,
        target_trace_id=target_trace_id,
    )

    try:
        res_baseline = build_call_graph(
            baseline_trace_id, project_id, tool_context=tool_context
        )
        res_target = build_call_graph(
            target_trace_id, project_id, tool_context=tool_context
        )

        if res_baseline.status == ToolStatus.ERROR:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"Baseline graph error: {res_baseline.error}",
            )
        if res_target.status == ToolStatus.ERROR:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"Target graph error: {res_target.error}",
            )

        graph_baseline = res_baseline.result
        graph_target = res_target.result

        baseline_names = set(graph_baseline.get("span_names", []))
        target_names = set(graph_target.get("span_names", []))

        missing_spans = list(baseline_names - target_names)
        new_spans = list(target_names - baseline_names)
        common_spans = list(baseline_names & target_names)

        depth_change = graph_target.get("max_depth", 0) - graph_baseline.get(
            "max_depth", 0
        )

        result = {
            "missing_spans": missing_spans,
            "new_spans": new_spans,
            "common_spans": common_spans,
            "baseline_span_count": graph_baseline.get("total_spans", 0),
            "target_span_count": graph_target.get("total_spans", 0),
            "span_count_change": graph_target.get("total_spans", 0)
            - graph_baseline.get("total_spans", 0),
            "depth_change": depth_change,
        }

        return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)

    except Exception as e:
        error_msg = f"Structural comparison failed: {e!s}"
        logger.error(error_msg)
        return BaseToolResponse(status=ToolStatus.ERROR, error=error_msg)
