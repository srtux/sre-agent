"""Statistical analysis and anomaly detection for trace data."""

import concurrent.futures
import logging
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, cast

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...clients.trace import fetch_trace_data
from ...common import adk_tool

logger = logging.getLogger(__name__)

MAX_WORKERS = 10  # Max concurrent fetches


def _fetch_traces_parallel(
    trace_ids: list[str],
    project_id: str | None = None,
    max_traces: int = 50,
    tool_context: Any = None,
) -> list[dict[str, Any]]:
    """Fetches multiple traces in parallel."""
    from ...clients.trace import (
        _clear_thread_credentials,
        _set_thread_credentials,
        get_credentials_from_tool_context,
    )

    user_creds = get_credentials_from_tool_context(tool_context)

    def fetch_with_creds(tid: str) -> dict[str, Any]:
        try:
            if user_creds:
                _set_thread_credentials(user_creds)
            return fetch_trace_data(tid, project_id, tool_context=tool_context)
        finally:
            if user_creds:
                _clear_thread_credentials()

    # Cap the number of traces to avoid overwhelming the API
    target_ids = trace_ids[:max_traces]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_tid = {
            executor.submit(fetch_with_creds, tid): tid for tid in target_ids
        }

        for future in concurrent.futures.as_completed(future_to_tid):
            try:
                data = future.result()
                if data and "error" not in data:
                    results.append(data)
            except Exception:
                pass

    return results


def _get_span_duration_ms(span: dict[str, Any]) -> float | None:
    """Calculates span duration in milliseconds, prioritizing pre-calculated unix timestamps."""
    # 1. Check if duration is already present
    duration = span.get("duration_ms")
    if duration is not None:
        return float(duration)

    # 2. FAST PATH: Use pre-calculated unix timestamps if available
    start_unix = span.get("start_time_unix")
    end_unix = span.get("end_time_unix")

    if start_unix is not None and end_unix is not None:
        return (float(end_unix) - float(start_unix)) * 1000.0

    # 3. SLOW PATH: Fallback to string parsing
    start_str = span.get("start_time")
    end_str = span.get("end_time")

    if start_str and end_str:
        try:
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            return (end - start).total_seconds() * 1000.0
        except Exception:
            pass

    return None


@adk_tool
def compute_latency_statistics(
    trace_ids: list[str],
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Computes aggregate latency statistics for a list of traces."""
    return _compute_latency_statistics_impl(trace_ids, project_id, tool_context)


def _compute_latency_statistics_impl(
    trace_ids: list[str], project_id: str | None = None, tool_context: Any = None
) -> BaseToolResponse:
    latencies = []
    valid_traces = []

    # Track stats per span name
    span_durations = defaultdict(list)

    # Fetch traces in parallel
    valid_trace_data = _fetch_traces_parallel(
        trace_ids, project_id, tool_context=tool_context
    )

    for trace_data in valid_trace_data:
        if isinstance(trace_data, dict):
            # Calculate total duration if not present
            duration = trace_data.get("duration_ms")

            # If we have spans, we can also aggregate span-level stats
            if "spans" in trace_data:
                for s in trace_data["spans"]:
                    d = _get_span_duration_ms(s)
                    if d is not None:
                        span_durations[s.get("name", "unknown")].append(d)

            if duration is not None:
                latencies.append(float(duration))
                valid_traces.append(trace_data)

    if not latencies:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error="No valid trace durations found"
        )

    latencies.sort()
    count = len(latencies)

    stats: dict[str, Any] = {
        "count": count,
        "min": latencies[0],
        "max": latencies[-1],
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p90": latencies[int(count * 0.9)] if count > 0 else latencies[0],
        "p95": latencies[int(count * 0.95)] if count > 0 else latencies[0],
        "p99": latencies[int(count * 0.99)] if count > 0 else latencies[0],
    }

    if count > 1:
        stats["stdev"] = statistics.stdev(latencies)
        stats["variance"] = statistics.variance(latencies)
    else:
        stats["stdev"] = 0
        stats["variance"] = 0

    # Calculate per-span stats with Z-score support
    per_span_stats: dict[str, Any] = {}
    for name, durs in span_durations.items():
        if not durs:
            continue
        durs.sort()
        c = len(durs)
        span_mean = statistics.mean(durs)
        per_span_stats[name] = {
            "count": c,
            "mean": span_mean,
            "min": durs[0],
            "max": durs[-1],
            "p95": durs[int(c * 0.95)] if c > 0 else durs[0],
        }
        # Calculate stdev for Z-score anomaly detection (need at least 2 samples)
        if c > 1:
            per_span_stats[name]["stdev"] = statistics.stdev(durs)
            per_span_stats[name]["variance"] = statistics.variance(durs)
        else:
            per_span_stats[name]["stdev"] = 0
            per_span_stats[name]["variance"] = 0

    stats["per_span_stats"] = per_span_stats

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=stats)


def _detect_latency_anomalies_impl(
    baseline_stats: dict[str, Any],
    target_data: dict[str, Any],
    threshold_sigma: float = 2.0,
) -> dict[str, Any]:
    """Internal implementation of detect_latency_anomalies."""
    if "error" in baseline_stats:
        return baseline_stats

    mean = baseline_stats["mean"]
    stdev = baseline_stats["stdev"]

    if not target_data:
        return {"error": "Target trace not found or invalid"}

    target_duration = target_data.get("duration_ms")
    if target_duration is None:
        return {"error": "Target trace has no duration_ms"}

    # Z-score calculation for total trace
    if stdev > 0:
        z_score = (target_duration - mean) / stdev
    else:
        if target_duration == mean:
            z_score = 0
        else:
            z_score = 100.0 if target_duration > mean else -100.0

    is_anomaly = abs(z_score) > threshold_sigma

    anomalous_spans = []

    # Check individual spans against baseline per-span stats using Z-score
    if "per_span_stats" in baseline_stats and "spans" in target_data:
        span_stats = baseline_stats["per_span_stats"]
        for s in target_data["spans"]:
            name = s.get("name")
            dur = _get_span_duration_ms(s)

            if name in span_stats and dur is not None:
                b_span = span_stats[name]
                span_mean = b_span.get("mean", 0)
                span_stdev = b_span.get("stdev", 0)

                # Calculate Z-score for this span
                if span_stdev > 0:
                    span_z_score = (dur - span_mean) / span_stdev
                else:
                    if dur == span_mean:
                        span_z_score = 0
                    else:
                        span_z_score = 100.0 if dur > span_mean else -100.0

                # Check if anomalous
                if abs(span_z_score) > threshold_sigma and dur > 50:
                    anomalous_spans.append(
                        {
                            "span_name": name,
                            "duration_ms": dur,
                            "baseline_mean": span_mean,
                            "baseline_stdev": span_stdev,
                            "baseline_p95": b_span.get("p95", 0),
                            "z_score": round(span_z_score, 2),
                            "anomaly_type": "slow" if span_z_score > 0 else "fast",
                        }
                    )

    return {
        "is_anomaly": is_anomaly,
        "z_score": z_score,
        "target_duration": target_duration,
        "baseline_mean": mean,
        "baseline_stdev": stdev,
        "threshold_sigma": threshold_sigma,
        "deviation_ms": target_duration - mean,
        "anomalous_spans": anomalous_spans,
    }


@adk_tool
def detect_latency_anomalies(
    baseline_trace_ids: list[str],
    target_trace_id: str,
    threshold_sigma: float = 2.0,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Detects if the target trace is anomalous compared to baseline distribution."""
    # Compute baseline stats
    baseline_stats = _compute_latency_statistics_impl(
        baseline_trace_ids, project_id, tool_context=tool_context
    )
    if not isinstance(baseline_stats, BaseToolResponse):
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Invalid baseline_stats type: {type(baseline_stats)}",
        )
    if baseline_stats.status != ToolStatus.SUCCESS:
        return baseline_stats

    baseline_stats_dict = cast(dict[str, Any], baseline_stats.result)
    if not baseline_stats_dict:
        return BaseToolResponse(status=ToolStatus.ERROR, error="Baseline stats missing")

    from ...clients.trace import (
        _clear_thread_credentials,
        _set_thread_credentials,
        get_credentials_from_tool_context,
    )

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        if user_creds:
            _set_thread_credentials(user_creds)
        # Get target duration
        target_data = fetch_trace_data(
            target_trace_id, project_id, tool_context=tool_context
        )
    finally:
        if user_creds:
            _clear_thread_credentials()

    result = _detect_latency_anomalies_impl(
        baseline_stats_dict, target_data, threshold_sigma
    )
    if "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _analyze_critical_path_impl(trace_data: dict[str, Any]) -> dict[str, Any]:
    """Internal implementation of analyze_critical_path using pre-fetched data."""
    if not trace_data:
        return {"error": "Trace not found or invalid"}

    spans = trace_data.get("spans", [])
    if not spans:
        return {"critical_path": []}

    # Parse all spans into a structured format
    parsed_spans = {}
    for s in spans:
        try:
            # FAST PATH: Use unix timestamps if available
            start_unix = s.get("start_time_unix")
            end_unix = s.get("end_time_unix")

            if start_unix is not None and end_unix is not None:
                start = start_unix * 1000
                end = end_unix * 1000
            else:
                # SLOW PATH
                start = (
                    datetime.fromisoformat(
                        s["start_time"].replace("Z", "+00:00")
                    ).timestamp()
                    * 1000
                )
                end = (
                    datetime.fromisoformat(
                        s["end_time"].replace("Z", "+00:00")
                    ).timestamp()
                    * 1000
                )

            parsed_spans[s["span_id"]] = {
                "id": s["span_id"],
                "name": s.get("name"),
                "start": start,
                "end": end,
                "duration": end - start,
                "parent": s.get("parent_span_id"),
                "children": [],
            }
        except (ValueError, KeyError):
            continue

    # Build tree (children links)
    root_id = None
    for sid, s in parsed_spans.items():
        if s["parent"] and s["parent"] in parsed_spans:
            parsed_spans[s["parent"]]["children"].append(sid)
        else:
            if root_id is None:
                root_id = sid

    if not root_id:
        return {"critical_path": []}

    def calculate_critical_path_recursive(
        span_id: str,
    ) -> tuple[list[dict[str, Any]], float]:
        node = parsed_spans[span_id]

        if not node["children"]:
            return (
                [
                    {
                        "name": node["name"],
                        "span_id": node["id"],
                        "duration_ms": node["duration"],
                        "start_ms": node["start"],
                        "end_ms": node["end"],
                        "self_time_ms": node["duration"],
                    }
                ],
                node["duration"],
            )

        # Calculate self time
        child_coverage = []
        for child_id in node["children"]:
            child = parsed_spans[child_id]
            child_coverage.append((child["start"], child["end"]))

        if child_coverage:
            child_coverage.sort()
            merged = [child_coverage[0]]
            for start, end in child_coverage[1:]:
                if start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))

            children_total_time = sum(end - start for start, end in merged)
            self_time = max(0, node["duration"] - children_total_time)
        else:
            self_time = node["duration"]

        max_child_path = None
        max_child_blocking: float = 0.0

        for child_id in node["children"]:
            child_path, child_blocking = calculate_critical_path_recursive(child_id)
            child = parsed_spans[child_id]
            gap_to_parent_end = node["end"] - child["end"]

            if gap_to_parent_end > 5:
                effective_blocking = child_blocking * 0.5
            else:
                effective_blocking = child_blocking

            if effective_blocking > max_child_blocking:
                max_child_blocking = effective_blocking
                max_child_path = child_path

        current_span_info = {
            "name": node["name"],
            "span_id": node["id"],
            "duration_ms": node["duration"],
            "start_ms": node["start"],
            "end_ms": node["end"],
            "self_time_ms": self_time,
        }

        total_blocking = self_time + max_child_blocking
        full_path = (
            [current_span_info, *max_child_path]
            if max_child_path
            else [current_span_info]
        )

        return (full_path, total_blocking)

    path, total_critical_duration = calculate_critical_path_recursive(root_id)

    trace_total_dur = parsed_spans[root_id]["duration"]
    for p in path:
        p["contribution_pct"] = (
            (p["self_time_ms"] / trace_total_dur * 100) if trace_total_dur > 0 else 0
        )
        p["blocking_contribution_pct"] = (
            (p["self_time_ms"] / total_critical_duration * 100)
            if total_critical_duration > 0
            else 0
        )

    parallelism_ratio = (
        trace_total_dur / total_critical_duration
        if total_critical_duration > 0
        else 1.0
    )

    return {
        "critical_path": path,
        "total_critical_duration_ms": round(total_critical_duration, 2),
        "trace_duration_ms": round(trace_total_dur, 2),
        "parallelism_ratio": round(parallelism_ratio, 2),
        "parallelism_pct": round((1 - 1 / parallelism_ratio) * 100, 2)
        if parallelism_ratio > 1
        else 0,
    }


@adk_tool
def analyze_critical_path(
    trace_id: str, project_id: str | None = None, tool_context: Any = None
) -> BaseToolResponse:
    """Identifies the critical path of spans in a trace."""
    from ...clients.trace import (
        _clear_thread_credentials,
        _set_thread_credentials,
        get_credentials_from_tool_context,
    )

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        if user_creds:
            _set_thread_credentials(user_creds)
        trace_data = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
    finally:
        if user_creds:
            _clear_thread_credentials()

    result = _analyze_critical_path_impl(trace_data)
    if "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


@adk_tool
def perform_causal_analysis(
    baseline_trace_id: str,
    target_trace_id: str,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Enhanced root cause analysis using span-ID-level precision."""
    from ...clients.trace import (
        _clear_thread_credentials,
        _set_thread_credentials,
        get_credentials_from_tool_context,
    )

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        if user_creds:
            _set_thread_credentials(user_creds)
        baseline_data = fetch_trace_data(
            baseline_trace_id, project_id, tool_context=tool_context
        )
        target_data = fetch_trace_data(
            target_trace_id, project_id, tool_context=tool_context
        )
    finally:
        if user_creds:
            _clear_thread_credentials()

    if not baseline_data or "error" in baseline_data:
        return BaseToolResponse(status=ToolStatus.ERROR, error="Invalid baseline trace")
    if not target_data or "error" in target_data:
        return BaseToolResponse(status=ToolStatus.ERROR, error="Invalid target trace")

    baseline_spans_by_name = defaultdict(list)
    for s in baseline_data.get("spans", []):
        baseline_spans_by_name[s.get("name")].append(s)

    target_spans_by_id = {s.get("span_id"): s for s in target_data.get("spans", [])}

    cp_report = _analyze_critical_path_impl(target_data)
    critical_path = cp_report.get("critical_path", [])
    critical_path_ids = {s["span_id"] for s in critical_path}
    cp_info_map = {s["span_id"]: s for s in critical_path}

    from .analysis import _build_call_graph_impl

    target_graph = _build_call_graph_impl(target_data)

    depth_map = {}

    def traverse(node: dict[str, Any]) -> None:
        depth_map[node["span_id"]] = node["depth"]
        for child in node["children"]:
            traverse(child)

    for root in target_graph.get("span_tree", []):
        traverse(root)

    candidates = []
    for span_id, target_span in target_spans_by_id.items():
        span_name = target_span.get("name")
        baseline_instances = baseline_spans_by_name.get(span_name, [])
        if not baseline_instances:
            continue

        target_duration = _get_span_duration_ms(target_span)
        if target_duration is None:
            continue

        baseline_durations = []
        for b_span in baseline_instances:
            b_dur = _get_span_duration_ms(b_span)
            if b_dur is not None:
                baseline_durations.append(b_dur)

        if not baseline_durations:
            continue
        baseline_avg = statistics.mean(baseline_durations)
        diff_ms = target_duration - baseline_avg
        diff_percent = (diff_ms / baseline_avg * 100) if baseline_avg > 0 else 0

        if diff_ms < 10 and diff_percent < 10:
            continue

        on_critical_path = span_id in critical_path_ids
        self_time_contribution = (
            cp_info_map[span_id].get("self_time_ms", 0) if on_critical_path else 0
        )

        depth = depth_map.get(span_id, 0)
        depth_factor = min(1.0 + (depth * 0.1), 1.5)
        score = diff_ms * depth_factor
        if on_critical_path:
            score *= 2.0
            if self_time_contribution > diff_ms * 0.3:
                score *= 1.3

        candidates.append(
            {
                "span_id": span_id,
                "span_name": span_name,
                "diff_ms": round(diff_ms, 2),
                "diff_percent": round(diff_percent, 1),
                "baseline_avg_ms": round(baseline_avg, 2),
                "target_ms": round(target_duration, 2),
                "on_critical_path": on_critical_path,
                "self_time_ms": round(self_time_contribution, 2)
                if on_critical_path
                else None,
                "depth": depth,
                "confidence_score": round(score, 2),
                "is_likely_root_cause": on_critical_path
                and self_time_contribution > 50,
            }
        )

    candidates.sort(key=lambda x: x["confidence_score"], reverse=True)
    if candidates and candidates[0]["on_critical_path"]:
        candidates[0]["is_likely_root_cause"] = True

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "root_cause_candidates": candidates[:10],
            "analysis_method": "span_id_level_critical_path_analysis",
            "total_candidates": len(candidates),
            "critical_path_spans": len(critical_path),
        },
    )


@adk_tool
def analyze_trace_patterns(
    trace_ids: list[str],
    lookback_window_minutes: int = 60,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Analyzes patterns across multiple traces to detect trends and recurring issues."""
    if len(trace_ids) < 3:
        return BaseToolResponse(status=ToolStatus.ERROR, error="Need at least 3 traces")

    parsed_traces = _fetch_traces_parallel(
        trace_ids, project_id, tool_context=tool_context
    )
    if len(parsed_traces) < 3:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error="Not enough valid traces"
        )

    span_performance: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "occurrences": 0,
            "durations": [],
            "error_count": 0,
            "traces_with_span": [],
        }
    )
    trace_durations = []

    for trace in parsed_traces:
        trace_id = trace.get("trace_id", "unknown")
        trace_durations.append(trace.get("duration_ms", 0))

        for span in trace.get("spans", []):
            name = span.get("name", "unknown")
            dur = _get_span_duration_ms(span)

            if dur is not None:
                perf = span_performance[name]
                perf["occurrences"] += 1
                perf["durations"].append(dur)
                perf["traces_with_span"].append(trace_id)
                if "error" in str(span.get("labels", {})).lower():
                    perf["error_count"] += 1

    recurring_slowdowns = []
    intermittent_issues = []
    high_variance_spans = []

    for name, perf in span_performance.items():
        if perf["occurrences"] < 2:
            continue
        durs = perf["durations"]
        mean_dur = statistics.mean(durs)
        stdev_dur: float = statistics.stdev(durs) if len(durs) > 1 else 0.0
        cv = stdev_dur / mean_dur if mean_dur > 0 else 0.0

        if mean_dur > 100 and cv < 0.3:
            recurring_slowdowns.append(
                {
                    "span_name": name,
                    "avg_duration_ms": round(mean_dur, 2),
                    "occurrences": perf["occurrences"],
                    "pattern_type": "recurring_slowdown",
                }
            )
        if cv > 0.5 and mean_dur > 50:
            intermittent_issues.append(
                {
                    "span_name": name,
                    "avg_duration_ms": round(mean_dur, 2),
                    "stdev_ms": round(stdev_dur, 2),
                    "cv": round(cv, 2),
                    "occurrences": perf["occurrences"],
                }
            )
        if cv > 0.7:
            high_variance_spans.append(
                {
                    "span_name": name,
                    "cv": round(cv, 2),
                    "occurrences": perf["occurrences"],
                }
            )

    recurring_slowdowns.sort(key=lambda x: x["avg_duration_ms"], reverse=True)

    trend = "stable"
    if len(trace_durations) >= 3:
        first = statistics.mean(trace_durations[: len(trace_durations) // 2])
        second = statistics.mean(trace_durations[len(trace_durations) // 2 :])
        diff = ((second - first) / first * 100) if first > 0 else 0
        if diff > 15:
            trend = "degrading"
        elif diff < -15:
            trend = "improving"

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "traces_analyzed": len(parsed_traces),
            "overall_trend": trend,
            "patterns": {
                "recurring_slowdowns": recurring_slowdowns[:5],
                "intermittent_issues": intermittent_issues[:5],
                "high_variance_spans": high_variance_spans[:5],
            },
        },
    )


@adk_tool
def compute_service_level_stats(
    trace_ids: list[str],
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Computes stats aggregated by service name."""
    service_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "errors": 0, "total_duration": 0.0}
    )
    traces_data = _fetch_traces_parallel(
        trace_ids, project_id, tool_context=tool_context
    )

    for t_data in traces_data:
        for s in t_data.get("spans", []):
            labels = s.get("labels", {})
            svc = labels.get("service.name") or labels.get("service") or "unknown"

            dur = _get_span_duration_ms(s) or 0.0

            stats = service_stats[svc]
            stats["count"] += 1
            stats["total_duration"] += dur
            if "error" in str(labels).lower():
                stats["errors"] += 1

    result = {}
    for svc, s in service_stats.items():
        if s["count"] > 0:
            result[svc] = {
                "count": s["count"],
                "error_rate": round(s["errors"] / s["count"] * 100, 2),
                "avg_latency": round(s["total_duration"] / s["count"], 2),
            }
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)
