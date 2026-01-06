"""Statistical analysis and anomaly detection for trace data."""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import statistics
import time
import json
from collections import defaultdict
from datetime import datetime

from ..telemetry import get_tracer, get_meter

# Telemetry setup
tracer = get_tracer(__name__)
meter = get_meter(__name__)


def compute_latency_statistics(traces: List[str]) -> Dict[str, Any]:
    """
    Computes aggregate latency statistics for a list of traces.
    
    Args:
        traces: List of trace JSON strings.

    Returns:
        Dictionary containing statistical metrics.
    """
    with tracer.start_as_current_span("compute_latency_statistics"):
        latencies = []
        valid_traces = []
        
        # Track stats per span name
        span_durations = defaultdict(list)

        for t in traces:
            trace_data = t
            if isinstance(t, str):
                try:
                    trace_data = json.loads(t)
                except json.JSONDecodeError:
                    continue
            
            if isinstance(trace_data, dict):
                # Calculate total duration if not present
                duration = trace_data.get("duration_ms")
                
                # If we have spans, we can also aggregate span-level stats
                if "spans" in trace_data:
                    for s in trace_data["spans"]:
                        # Try to get duration from span
                        d = s.get("duration_ms")
                        if d is None and s.get("start_time") and s.get("end_time"):
                            try:
                                start = datetime.fromisoformat(s["start_time"].replace('Z', '+00:00'))
                                end = datetime.fromisoformat(s["end_time"].replace('Z', '+00:00'))
                                d = (end - start).total_seconds() * 1000
                            except: pass

                        if d is not None:
                            span_durations[s.get("name", "unknown")].append(d)

                if duration is not None:
                    latencies.append(float(duration))
                    valid_traces.append(trace_data)

        if not latencies:
            return {"error": "No valid trace durations found"}

        latencies.sort()
        count = len(latencies)

        stats = {
            "count": count,
            "min": latencies[0],
            "max": latencies[-1],
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p90": latencies[int(count * 0.9)] if count > 0 else 0,
            "p95": latencies[int(count * 0.95)] if count > 0 else 0,
            "p99": latencies[int(count * 0.99)] if count > 0 else 0,
        }

        if count > 1:
            stats["stdev"] = statistics.stdev(latencies)
            stats["variance"] = statistics.variance(latencies)
        else:
            stats["stdev"] = 0
            stats["variance"] = 0
            
        # Calculate per-span stats
        per_span_stats = {}
        for name, durs in span_durations.items():
            if not durs: continue
            durs.sort()
            c = len(durs)
            per_span_stats[name] = {
                "count": c,
                "mean": statistics.mean(durs),
                "min": durs[0],
                "max": durs[-1],
                "p95": durs[int(c * 0.95)] if c > 0 else 0
            }

        stats["per_span_stats"] = per_span_stats
            
        return stats


def detect_latency_anomalies(
    baseline_traces: List[str],
    target_trace: str,
    threshold_sigma: float = 2.0
) -> Dict[str, Any]:
    """
    Detects if the target trace is anomalous compared to baseline distribution using Z-score.
    Also checks individual spans for anomalies if baseline data allows.
    
    Args:
        baseline_traces: List of normal traces as JSON strings.
        target_trace: The trace to check as a JSON string.
        threshold_sigma: Number of standard deviations to consider anomalous.

    Returns:
        Anomaly report.
    """
    with tracer.start_as_current_span("detect_latency_anomalies"):
        # Compute baseline stats
        baseline_stats = compute_latency_statistics(baseline_traces)
        if "error" in baseline_stats:
            return baseline_stats
            
        mean = baseline_stats["mean"]
        stdev = baseline_stats["stdev"]

        # Get target duration
        target_data = target_trace
        if isinstance(target_trace, str):
            try:
                target_data = json.loads(target_trace)
            except json.JSONDecodeError:
                return {"error": "Invalid target trace JSON"}

        target_duration = target_data.get("duration_ms")
        if target_duration is None:
             # Try to calc from spans if needed, or error
             return {"error": "Target trace has no duration_ms"}

        # Z-score calculation for total trace
        if stdev > 0:
            z_score = (target_duration - mean) / stdev
        else:
            # If stdev is 0, any deviation is infinite anomaly, unless equal
            if target_duration == mean:
                z_score = 0
            else:
                # Fallback: if stdev is 0 (all baselines identical), use mean as scale?
                # Or just mark high.
                z_score = 100.0 if target_duration > mean else -100.0
            
        is_anomaly = abs(z_score) > threshold_sigma

        anomalous_spans = []

        # Check individual spans against baseline per-span stats
        if "per_span_stats" in baseline_stats and "spans" in target_data:
            span_stats = baseline_stats["per_span_stats"]
            for s in target_data["spans"]:
                name = s.get("name")
                # Calc duration
                dur = s.get("duration_ms")
                if dur is None and s.get("start_time"):
                     try:
                        start = datetime.fromisoformat(s["start_time"].replace('Z', '+00:00'))
                        end = datetime.fromisoformat(s["end_time"].replace('Z', '+00:00'))
                        dur = (end - start).total_seconds() * 1000
                     except: pass
                
                if name in span_stats and dur is not None:
                    b_span = span_stats[name]
                    # We don't have stdev for spans in the simple stats,
                    # so let's use a simpler heuristic: > max observed in baseline OR > 2*mean
                    # Or better: check if it exceeds p95 significantly
                    threshold = b_span["p95"] * 1.5 if b_span["p95"] > 0 else b_span["max"]
                    if dur > threshold and dur > 50: # Ignore tiny spans
                        anomalous_spans.append({
                            "span_name": name,
                            "duration_ms": dur,
                            "baseline_p95": b_span["p95"],
                            "anomaly_type": "slow"
                        })

        return {
            "is_anomaly": is_anomaly,
            "z_score": z_score,
            "target_duration": target_duration,
            "baseline_mean": mean,
            "baseline_stdev": stdev,
            "threshold_sigma": threshold_sigma,
            "deviation_ms": target_duration - mean,
            "anomalous_spans": anomalous_spans
        }


def analyze_critical_path(trace: str) -> Dict[str, Any]:
    """
    Identifies the critical path of spans in a trace.
    
    The critical path is calculated by finding the longest path through the span dependency graph.
    
    Args:
        trace: The trace data to analyze as a JSON string.
    """
    with tracer.start_as_current_span("analyze_critical_path"):
        trace_data = trace
        if isinstance(trace, str):
            try:
                trace_data = json.loads(trace)
            except json.JSONDecodeError:
                return {"error": "Invalid trace JSON"}

        spans = trace_data.get("spans", [])
        if not spans:
            return {"critical_path": []}
            
        # Parse all spans into a structured format
        parsed_spans = {}
        for s in spans:
            try:
                start = datetime.fromisoformat(s["start_time"].replace('Z', '+00:00')).timestamp() * 1000
                end = datetime.fromisoformat(s["end_time"].replace('Z', '+00:00')).timestamp() * 1000
                parsed_spans[s["span_id"]] = {
                    "id": s["span_id"],
                    "name": s.get("name"),
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "parent": s.get("parent_span_id"),
                    "children": []
                }
            except (ValueError, KeyError):
                continue

        # Build tree (children links)
        root_id = None
        for sid, s in parsed_spans.items():
            if s["parent"] and s["parent"] in parsed_spans:
                parsed_spans[s["parent"]]["children"].append(sid)
            else:
                if root_id is None: # Assume first root found is THE root for simplicity
                    root_id = sid

        if not root_id:
            return {"critical_path": []}
            
        # Critical Path Calculation:
        # For a span, the critical child is the one that ends last (pushing the boundary).
        # But simply picking the latest ending child works for synchronous blocking chains.
        # For async, it's more complex, but "Longest Path" in terms of time coverage is a good proxy.
        # We start from root.
        # If root duration is dominated by a specific child chain, we follow it.

        # Algorithm:
        # Start at root.
        # Add to path.
        # Find child with latest end time.
        # If that child's end time is close to current span's end time (within small delta),
        # it implies this child is "blocking" or extending the duration.
        # Recurse.

        path = []
        curr_id = root_id

        while curr_id:
            node = parsed_spans[curr_id]
            path.append({
                "name": node["name"],
                "span_id": node["id"],
                "duration_ms": node["duration"],
                "start_ms": node["start"],
                "end_ms": node["end"]
            })
            
            if not node["children"]:
                break
                
            # Find child that ends latest
            latest_child_id = max(node["children"], key=lambda cid: parsed_spans[cid]["end"])
            latest_child = parsed_spans[latest_child_id]
            
            # Heuristic: Only follow if child accounts for significant portion of remaining time
            # or ends very close to parent end.
            # For simplicity in this agent, we just follow the "latest ending" chain as the critical path.
            curr_id = latest_child_id
            
        # Calculate contribution percentage
        total_dur = path[0]["duration_ms"] if path else 0
        for p in path:
            p["contribution_pct"] = (p["duration_ms"] / total_dur * 100) if total_dur > 0 else 0
            
        return {"critical_path": path}


def perform_causal_analysis(
    baseline_trace: Any,
    target_trace: Any
) -> Dict[str, Any]:
    """
    Attempts to identify the root cause span for a slowdown.
    
    Args:
        baseline_trace: The reference trace data.
        target_trace: The abnormal trace data to analyze.
    """
    baseline_data = baseline_trace if isinstance(baseline_trace, dict) else json.loads(baseline_trace)
    target_data = target_trace if isinstance(target_trace, dict) else json.loads(target_trace)
    
    # 1. Compare durations to find slow spans
    from .trace_analysis import compare_span_timings
    diff_report = compare_span_timings(json.dumps(baseline_data), json.dumps(target_data))
    
    if "error" in diff_report:
        return {"error": diff_report["error"]}

    slow_spans = diff_report.get("slower_spans", [])
    if not slow_spans:
        return {"root_cause_candidates": [], "message": "No slow spans found"}

    # 2. Analyze Critical Path of the target trace
    cp_report = analyze_critical_path(target_data)
    critical_path_ids = {s["span_id"] for s in cp_report.get("critical_path", [])}
    
    # 3. Intersection: Slow spans that are ON the critical path
    candidates = []
    for s in slow_spans:
        # We need span_id for critical path check, but compare_span_timings aggregates by name.
        # We need to find if *any* span of this name is on critical path.
        # This is an approximation.
        
        # Find span instances in target to get ID
        instances = [sp for sp in target_data["spans"] if sp.get("name") == s["span_name"]]
        on_cp = any(sp["span_id"] in critical_path_ids for sp in instances)
        
        candidates.append({
            "span_name": s["span_name"],
            "diff_ms": s["diff_ms"],
            "diff_percent": s["diff_percent"],
            "on_critical_path": on_cp,
            # Heuristic score: diff * (1.5 if on_cp else 1.0)
            "score": s["diff_ms"] * (1.5 if on_cp else 1.0)
        })
        
    # Sort by score
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # Identify "Root Cause"
    # The "Root Cause" is usually the deepest span in the call graph that is slow.
    # If A calls B, and both are slow, B is likely the cause.
    # We need depth info.
    
    from .trace_analysis import build_call_graph
    target_graph = build_call_graph(target_data)
    
    # Flatten tree to map name -> depth
    depth_map = {}
    def traverse(node):
        depth_map[node["name"]] = node["depth"]
        for child in node["children"]:
            traverse(child)
            
    for root in target_graph.get("span_tree", []):
        traverse(root)

    for c in candidates:
        c["depth"] = depth_map.get(c["span_name"], 0)

    # Re-sort: Prefer deeper spans if they account for most of the diff
    # If Child diff is close to Parent diff, Child is root cause.

    final_candidates = []

    # We will iterate and try to find independent causes
    # Simplest heuristic: Just take the top ones sorted by diff_ms descending,
    # but boost depth.

    # Actually, let's keep it simple: Top slow span that is a leaf node (or near leaf) is likely root.
    for c in candidates:
        c["is_root_cause"] = False
        # If this span explains a significant part of total slowness
        if c["on_critical_path"]:
             c["is_root_cause"] = True # Provisional

    return {
        "root_cause_candidates": candidates[:5],
        "analysis_method": "critical_path_diff_intersection"
    }

def compute_service_level_stats(traces: List[str]) -> Dict[str, Any]:
    """
    Computes stats aggregated by service name (if available in labels).
    
    Args:
        traces: List of trace JSON strings.
    """
    service_stats = defaultdict(lambda: {"count": 0, "errors": 0, "total_duration": 0})

    for t in traces:
        t_data = t
        if isinstance(t, str):
            try: t_data = json.loads(t)
            except: continue
            
        for s in t_data.get("spans", []):
            # Try to find service name in labels, or default to "unknown"
            # Common conventions: service.name, app, component
            labels = s.get("labels", {})
            svc = labels.get("service.name") or labels.get("service") or labels.get("app") or "unknown"
            
            dur = 0
            if s.get("start_time") and s.get("end_time"):
                 try:
                    start = datetime.fromisoformat(s["start_time"].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(s["end_time"].replace('Z', '+00:00'))
                    dur = (end - start).total_seconds() * 1000
                 except: pass
            
            is_error = "error" in str(labels).lower()
            
            stats = service_stats[svc]
            stats["count"] += 1
            stats["total_duration"] += dur
            if is_error:
                stats["errors"] += 1

    # Finalize averages
    result = {}
    for svc, stats in service_stats.items():
        if stats["count"] > 0:
            result[svc] = {
                "request_count": stats["count"],
                "error_rate": round(stats["errors"] / stats["count"] * 100, 2),
                "avg_latency": round(stats["total_duration"] / stats["count"], 2)
            }

    return result
