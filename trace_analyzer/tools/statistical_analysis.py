"""Statistical and causal analysis utilities for distributed traces."""

from typing import Any, Dict, List, Optional, Tuple, Union
import json
import math
from collections import defaultdict
import time

from ..telemetry import get_tracer, get_meter

# Telemetry setup
tracer = get_tracer(__name__)
meter = get_meter(__name__)

# Metrics
execution_duration = meter.create_histogram(
    name="trace_analyzer.tool.execution_duration",
    description="Duration of tool executions",
    unit="ms",
)
execution_count = meter.create_counter(
    name="trace_analyzer.tool.execution_count",
    description="Total number of tool calls",
    unit="1",
)
anomalies_detected = meter.create_counter(
    name="trace_analyzer.analysis.anomalies_detected",
    description="Count of structural differences or anomalies found",
    unit="1",
)

def _record_telemetry(func_name: str, success: bool = True, duration_ms: float = 0.0):
    attributes = {
        "code.function": func_name,
        "code.namespace": __name__,
        "success": str(success).lower(),
        "trace_analyzer.tool.name": func_name,
    }
    execution_count.add(1, attributes)
    execution_duration.record(duration_ms, attributes)


# Common type aliases
TraceData = Dict[str, Any]
StatsData = Dict[str, Any]


def compute_latency_statistics(traces: str) -> StatsData:
    """
    Computes comprehensive latency statistics across multiple traces.

    Aggregates timing data from multiple traces to calculate percentile
    distributions, detect high-variability spans, and identify potential
    bimodal latency patterns that suggest inconsistent behavior.

    Args:
        traces (str | list): Collection of traces to analyze, either as:
            - JSON string: '[{"trace_id": "...", "spans": [...]}, ...]'
            - List of trace dictionaries from fetch_trace
            Minimum 1 trace required; more traces yield better statistics.

    Returns:
        Statistical summary dictionary:
        - per_span_stats (dict): Statistics for each unique span name:
            - count: Number of observations
            - min, max: Min/max durations in ms
            - mean, median: Average and median durations
            - std_dev: Standard deviation
            - p50, p90, p95, p99: Percentile latencies in ms
            - coefficient_of_variation: Relative variability (std_dev/mean * 100)
        - overall_stats (dict): Aggregate stats across all spans (same fields)
        - total_traces_analyzed (int): Number of traces processed
        - unique_span_types (int): Number of distinct span names
        - anomalies (list): Spans with unusual patterns:
            - span_name: Name of anomalous span
            - anomaly_type: "high_variability" or "bimodal_distribution"
            - description: Human-readable explanation

        On error, returns {"error": "error message"}

    Anomaly Detection:
        - High variability: Coefficient of variation > 50%
        - Bimodal: Upper half mean > 3x lower half mean (suggests two modes)

    Example:
        >>> compute_latency_statistics(traces_list)
        {
            "per_span_stats": {"db-query": {"p99": 250.5, "mean": 45.2, ...}},
            "anomalies": [{"span_name": "cache", "anomaly_type": "bimodal_distribution"}]
        }
    """
    start_time = time.time()
    success = True
    
    with tracer.start_as_current_span("compute_latency_statistics") as span:
        span.set_attribute("code.function", "compute_latency_statistics")
        span.set_attribute("trace_analyzer.trace_count", len(traces))
        
        from .trace_analysis import calculate_span_durations
        
        try:
            span_durations: Dict[str, List[float]] = defaultdict(list)
            all_durations: List[float] = []
            
            if isinstance(traces, str):
                try:
                    traces = json.loads(traces)
                except json.JSONDecodeError as e:
                    return {"error": f"Failed to parse traces JSON: {str(e)}"}

            if not isinstance(traces, list):
                return {"error": f"Expected traces to be a list, but got {type(traces).__name__}"}

            for trace in traces:
                # Delegate parsing/error checking to the tool
                timings = calculate_span_durations(trace)
                if timings and isinstance(timings[0], dict) and "error" in timings[0]:
                    continue
                for s in timings:
                    duration = s.get("duration_ms")
                    name = s.get("name")
                    if duration is not None and name:
                        span_durations[name].append(duration)
                        all_durations.append(duration)
            
            if not all_durations:
                return {"error": "No valid duration data found in traces"}
            
            def calc_stats(durations: List[float]) -> Dict[str, float]:
                """Helper to calculate standard statistical metrics for a list of values."""
                if not durations:
                    return {}
                n = len(durations)
                sorted_d = sorted(durations)
                mean = sum(durations) / n
                # Variance = mean squared deviation
                variance = sum((x - mean) ** 2 for x in durations) / n
                std_dev = math.sqrt(variance)
                
                return {
                    "count": n,
                    "min": round(sorted_d[0], 2),
                    "max": round(sorted_d[-1], 2),
                    "mean": round(mean, 2),
                    "median": round(sorted_d[n // 2], 2),
                    "std_dev": round(std_dev, 2),
                    # Calculate percentiles (approximate method for simplicity)
                    "p50": round(sorted_d[int(n * 0.50)], 2),
                    "p90": round(sorted_d[int(n * 0.90)] if n > 1 else sorted_d[0], 2),
                    "p95": round(sorted_d[int(n * 0.95)] if n > 1 else sorted_d[0], 2),
                    "p99": round(sorted_d[int(n * 0.99)] if n > 1 else sorted_d[0], 2),
                    # Coeff of variation = std_dev / mean (relative variability)
                    "coefficient_of_variation": round(std_dev / mean * 100, 2) if mean > 0 else 0,
                }
            
            per_span_stats = {
                name: calc_stats(durations) 
                for name, durations in span_durations.items()
            }
            
            # Identify anomalous spans (high coefficient of variation or outliers)
            anomalies = []
            for name, stats in per_span_stats.items():
                cv = stats.get("coefficient_of_variation", 0)
                if cv > 50:  # High variability (>50%) suggests unstable performance
                    anomalies.append({
                        "span_name": name,
                        "anomaly_type": "high_variability",
                        "coefficient_of_variation": cv,
                        "description": f"Span '{name}' has highly variable latency (CV={cv}%)"
                    })
                
                # Check for bimodal distribution hint (simplified heuristic)
                durations = span_durations[name]
                if len(durations) >= 10:
                    sorted_d = sorted(durations)
                    mid = len(sorted_d) // 2
                    lower_half_mean = sum(sorted_d[:mid]) / mid
                    upper_len = len(sorted_d) - mid
                    upper_half_mean = sum(sorted_d[mid:]) / upper_len if upper_len > 0 else 0
                    
                    if lower_half_mean > 0 and upper_half_mean > lower_half_mean * 3:
                        anomalies.append({
                            "span_name": name,
                            "anomaly_type": "bimodal_distribution",
                            "lower_mean": round(lower_half_mean, 2),
                            "upper_mean": round(upper_half_mean, 2),
                            "description": f"Span '{name}' may have bimodal latency (fast: {lower_half_mean:.0f}ms, slow: {upper_half_mean:.0f}ms)"
                        })
            
            if anomalies:
                anomalies_detected.add(len(anomalies), {"type": "statistical_anomaly"})
            
            return {
                "per_span_stats": per_span_stats,
                "overall_stats": calc_stats(all_durations),
                "total_traces_analyzed": len(traces),
                "unique_span_types": len(per_span_stats),
                "anomalies": anomalies,
            }
        except Exception as e:
            span.record_exception(e)
            success = False
            raise e
        finally:
            duration_ms = (time.time() - start_time) * 1000
            _record_telemetry("compute_latency_statistics", success, duration_ms)


def detect_latency_anomalies(
    baseline_traces: str,
    target_trace: str,
    threshold_std_devs: float = 2.0,
) -> Dict[str, Any]:
    """
    Detects statistically anomalous spans using z-score analysis.

    Compares each span in the target trace against baseline statistics to
    identify spans that deviate significantly from normal behavior.
    Z-score = (observed_value - mean) / standard_deviation

    Args:
        baseline_traces (str | list): Collection of normal/baseline traces to
            establish expected patterns. More traces = more accurate baseline.
            Can be JSON string or list of trace dictionaries.
        target_trace (str | dict): Single trace to analyze for anomalies.
            Can be JSON string or dictionary from fetch_trace.
        threshold_std_devs (float, optional): Number of standard deviations
            from mean to consider anomalous.
            Default: 2.0 (catches ~5% of normal distribution)
            Common values:
            - 1.5: More sensitive, more false positives
            - 2.0: Balanced (default)
            - 3.0: High confidence, may miss subtle anomalies

    Returns:
        Anomaly detection results dictionary:
        - anomalous_spans (list): Spans exceeding threshold:
            - span_name: Name of the span
            - duration_ms: Observed duration
            - baseline_mean: Expected mean from baseline
            - baseline_std_dev: Standard deviation from baseline
            - z_score: How many std devs from mean (positive = slower)
            - anomaly_type: "slow", "fast", or "new_span"
            - severity: "high" (>3 std devs) or "medium" (>threshold)
            - description: Human-readable explanation
        - normal_spans (list): Spans within normal range (same fields)
        - threshold_std_devs (float): The threshold used
        - baseline_trace_count (int): Number of baseline traces
        - summary (dict):
            - total_spans_analyzed: Total spans in target
            - anomalous_count, normal_count: Counts
            - anomaly_rate: Percentage of anomalous spans

        On error, returns {"error": "error message"}

    Example:
        >>> detect_latency_anomalies(baseline_traces, slow_trace, threshold_std_devs=2.5)
        {"anomalous_spans": [{"span_name": "db-query", "z_score": 4.2, "severity": "high"}]}
    """
    start_time = time.time()
    success = True
    
    with tracer.start_as_current_span("detect_latency_anomalies") as span:
        span.set_attribute("code.function", "detect_latency_anomalies")
        
        from .trace_analysis import calculate_span_durations
        
        try:
            # Build baseline statistics
            baseline_stats = compute_latency_statistics(baseline_traces)
            if "error" in baseline_stats:
                return {"error": baseline_stats["error"]}
            
            per_span_stats = baseline_stats.get("per_span_stats", {})
            
            # Analyze target trace
            target_timings = calculate_span_durations(target_trace)
            if target_timings and isinstance(target_timings[0], dict) and "error" in target_timings[0]:
                return {"error": f"Target trace error: {target_timings[0]['error']}"}
            
            anomalous_spans = []
            normal_spans = []
            
            for s in target_timings:
                name = s.get("name")
                duration = s.get("duration_ms")
                
                if not name or duration is None:
                    continue
                
                baseline = per_span_stats.get(name)
                if not baseline:
                    # New span not present in baseline stats
                    anomalous_spans.append({
                        "span_name": name,
                        "duration_ms": duration,
                        "anomaly_type": "new_span",
                        "z_score": None,
                        "description": f"Span '{name}' not seen in baseline traces"
                    })
                    continue
                
                mean = baseline.get("mean", 0)
                std_dev = baseline.get("std_dev", 1)
                
                if std_dev == 0:
                    std_dev = 1  # Avoid division by zero if variance is 0
                
                # Calculate z-score
                z_score = (duration - mean) / std_dev
                
                span_result = {
                    "span_name": name,
                    "duration_ms": round(duration, 2),
                    "baseline_mean": mean,
                    "baseline_std_dev": std_dev,
                    "z_score": round(z_score, 2),
                }
                
                if abs(z_score) > threshold_std_devs:
                    span_result["anomaly_type"] = "slow" if z_score > 0 else "fast"
                    span_result["severity"] = "high" if abs(z_score) > 3 else "medium"
                    span_result["description"] = f"Span '{name}' is {abs(z_score):.1f} std devs {'above' if z_score > 0 else 'below'} baseline"
                    anomalous_spans.append(span_result)
                else:
                    normal_spans.append(span_result)
            
            # Sort anomalies by z-score magnitude
            anomalous_spans.sort(key=lambda x: abs(x.get("z_score") or 0), reverse=True)
            
            if anomalous_spans:
                anomalies_detected.add(len(anomalous_spans), {"type": "z_score_anomaly"})
            
            return {
                "anomalous_spans": anomalous_spans,
                "normal_spans": normal_spans,
                "threshold_std_devs": threshold_std_devs,
                "baseline_trace_count": len(baseline_traces),
                "summary": {
                    "total_spans_analyzed": len(target_timings),
                    "anomalous_count": len(anomalous_spans),
                    "normal_count": len(normal_spans),
                    "anomaly_rate": round(len(anomalous_spans) / max(len(target_timings), 1) * 100, 1),
                }
            }
        except Exception as e:
            span.record_exception(e)
            success = False
            raise e
        finally:
            duration_ms = (time.time() - start_time) * 1000
            _record_telemetry("detect_latency_anomalies", success, duration_ms)


def analyze_critical_path(trace: str) -> Dict[str, Any]:
    """
    Identifies the critical path - the sequence of spans determining total latency.

    The critical path is the longest execution path through the trace's call tree.
    Only optimizing spans ON the critical path will reduce overall latency.
    Spans off the critical path complete while waiting for critical path operations.

    Args:
        trace (str | dict): Trace data to analyze, either as:
            - JSON string: '{"trace_id": "...", "spans": [...]}'
            - Dictionary from fetch_trace

    Returns:
        Critical path analysis dictionary:
        - critical_path (list): Ordered list of spans on the critical path:
            - span_name: Name of the span
            - duration_ms: Duration of this span
            - percentage_of_total: What % of total time this span represents
        - total_critical_duration_ms (float): Sum of critical path durations
        - path_length (int): Number of spans on the critical path
        - optimization_opportunities (list): Top 5 spans contributing >10% of
            total latency (best candidates for optimization):
            - span_name, duration_ms, percentage_of_total
        - summary (str): Human-readable summary

        On error, returns {"error": "error message"}

    Use Case:
        When a request is slow, focus optimization efforts on critical path spans.
        A 50% improvement to a span taking 10% of critical path time yields only
        5% overall improvement. Target the biggest contributors first.

    Example:
        >>> analyze_critical_path(slow_trace)
        {
            "critical_path": [{"span_name": "api-handler", ...}, {"span_name": "db-query", ...}],
            "total_critical_duration_ms": 450.5,
            "optimization_opportunities": [{"span_name": "db-query", "percentage_of_total": 65}]
        }
    """
    start_time = time.time()
    success = True
    
    with tracer.start_as_current_span("analyze_critical_path") as span:
        span.set_attribute("code.function", "analyze_critical_path")
        
        from .trace_analysis import calculate_span_durations, build_call_graph
        try:
            try:
                if isinstance(trace, str):
                    trace = json.loads(trace)
            except Exception:
                pass # Let tools handle it or fail later

            if isinstance(trace, dict) and "error" in trace:
                return {"error": trace["error"]}
            
            timings = calculate_span_durations(trace)
            # check for error in timings
            if timings and isinstance(timings[0], dict) and "error" in timings[0]:
                 return {"error": timings[0]["error"]}

            graph = build_call_graph(trace)
            if "error" in graph:
                 return {"error": graph["error"]}
            
            span_by_id = {s.get("span_id"): s for s in timings}
            
            # Find the root span(s) and trace the longest path
            root_spans = graph.get("root_spans", [])
            
            def get_critical_path(span_id: str) -> Tuple[float, List[Dict]]:
                """Recursively find the critical path from this span."""
                s = span_by_id.get(span_id, {})
                duration = s.get("duration_ms") or 0
                
                # Find children using the graph structure
                children_ids = []
                for tree in graph.get("span_tree", []):
                    def find_children_recursive(node):
                        if node.get("span_id") == span_id:
                            return [c.get("span_id") for c in node.get("children", [])]
                        for child in node.get("children", []):
                            result = find_children_recursive(child)
                            if result:
                                return result
                        return None
                    result = find_children_recursive(tree)
                    if result:
                        children_ids = result
                        break
                
                if not children_ids:
                    return duration, [s]
                
                # Find the child that contributes to the longest path (critical path)
                max_child_duration = 0
                max_child_path = []
                for child_id in children_ids:
                    child_duration, child_path = get_critical_path(child_id)
                    if child_duration > max_child_duration:
                        max_child_duration = child_duration
                        max_child_path = child_path
                
                # Critical path length = current span duration + longest child path
                # (Assuming synchronous calls - if async, logic would be more complex)
                return duration + max_child_duration, [s] + max_child_path
            
            # Get critical path from each root
            best_path = []
            best_duration = 0.0
            for root_id in root_spans:
                duration, path = get_critical_path(root_id)
                if duration > best_duration:
                    best_duration = duration
                    best_path = path
            
            # Identify optimization opportunities (slowest spans on critical path)
            critical_path_simplified = [
                {
                    "span_name": s.get("name"),
                    "duration_ms": s.get("duration_ms"),
                    "percentage_of_total": round((s.get("duration_ms") or 0) / max(best_duration, 1) * 100, 1),
                }
                for s in best_path if s.get("name")
            ]
            
            optimization_opportunities = sorted(
                [s for s in critical_path_simplified if s["percentage_of_total"] > 10],
                key=lambda x: x["duration_ms"] or 0,
                reverse=True
            )[:5]
            
            span.set_attribute("trace_analyzer.critical_path_length", len(critical_path_simplified))
            
            return {
                "critical_path": critical_path_simplified,
                "total_critical_duration_ms": round(best_duration, 2),
                "path_length": len(critical_path_simplified),
                "optimization_opportunities": optimization_opportunities,
                "summary": f"Critical path has {len(critical_path_simplified)} spans taking {best_duration:.0f}ms total"
            }
        except Exception as e:
            span.record_exception(e)
            success = False
            raise e
        finally:
            duration_ms = (time.time() - start_time) * 1000
            _record_telemetry("analyze_critical_path", success, duration_ms)


def perform_causal_analysis(
    baseline_trace: str,
    target_trace: str,
) -> Dict[str, Any]:
    """
    Identifies the root cause of performance differences between traces.

    Uses dependency analysis and propagation tracking to distinguish between
    spans that are the ROOT CAUSE of slowdowns vs. spans that are VICTIMS
    (slow because their dependencies were slow).

    Args:
        baseline_trace (str | dict): The reference/normal trace representing
            expected behavior. Can be JSON string or dictionary.
        target_trace (str | dict): The trace with performance issues to analyze.
            Can be JSON string or dictionary.

    Returns:
        Causal analysis dictionary:
        - root_cause_candidates (list): Top 5 ranked candidates:
            - span_name: Name of the span
            - slowdown_ms: How much slower than baseline
            - slowdown_percent: Percentage increase
            - is_root_cause (bool): True if this span originated the slowdown
            - parent_span: Name of parent span (if any)
            - parent_is_slow (bool): Whether parent also slowed down
            - confidence: "high", "medium", or "low"
            - hypothesis: Human-readable explanation of why this might be root cause
        - propagation_chains (list): How slowdowns cascaded:
            - origin: The root cause span
            - affected_spans: List of downstream spans affected
            - description: Explanation of the propagation
        - conclusion (str): Overall assessment
        - overall_confidence: "high", "medium", or "low"
        - total_slowdown_ms (float): Total latency increase

        On error, returns {"error": "error message"}

    Root Cause Identification:
        A span is likely a ROOT CAUSE if:
        - Its parent is NOT slow (slowdown originated here), OR
        - It accounts for >80% of its parent's slowdown (slowdown passed up)

        A span is likely a VICTIM if:
        - Its parent is slow AND it accounts for <80% of parent's slowdown

    Example:
        >>> perform_causal_analysis(normal_trace, slow_trace)
        {
            "root_cause_candidates": [
                {"span_name": "redis-lookup", "is_root_cause": true, "confidence": "high",
                 "hypothesis": "'redis-lookup' is likely the root cause - 250% slower with no slow parent"}
            ],
            "conclusion": "Root cause identified: redis-lookup"
        }
    """
    start_time = time.time()
    success = True
    
    with tracer.start_as_current_span("perform_causal_analysis") as span:
        span.set_attribute("code.function", "perform_causal_analysis")
        
        from .trace_analysis import (
            compare_span_timings,
            build_call_graph,
        )
        
        try:
            timing_diff = compare_span_timings(baseline_trace, target_trace)
            target_graph = build_call_graph(target_trace)
            
            slower_spans = timing_diff.get("slower_spans", [])
            
            if not slower_spans:
                return {
                    "root_cause_candidates": [],
                    "conclusion": "No significant slowdowns detected",
                    "confidence": "high"
                }
            
            # Build parent-child relationships for target trace
            parent_map: Dict[str, str] = {}
            def build_parent_map(node: Dict[str, Any], parent_name: Optional[str] = None):
                name = node.get("name")
                if name and parent_name:
                    parent_map[name] = parent_name
                for child in node.get("children", []):
                    build_parent_map(child, name)
            
            for tree in target_graph.get("span_tree", []):
                build_parent_map(tree)
            
            # Analyze each slower span to determine if it's a victim or culprit
            root_cause_candidates = []
            
            for slow_span in slower_spans[:10]:  # Top 10 slowest
                span_name = slow_span.get("span_name")
                diff_ms = slow_span.get("diff_ms", 0)
                diff_pct = slow_span.get("diff_percent", 0)
                
                if not span_name:
                    continue
        
                # Check if parent is also slow (propagation) or this is the origin
                parent_name = parent_map.get(span_name)
                parent_span_data = next((s for s in slower_spans if s.get("span_name") == parent_name), None)
                parent_is_slow = parent_span_data is not None
                
                # A span is a root cause if its parent is NOT slow, OR if it explains most of the parent's slowness
                is_root_cause = True
                if parent_is_slow:
                    parent_diff_ms = parent_span_data.get("diff_ms", 0)
                    # If this span's slowdown accounts for a significant portion of parent's slowdown,
                    # it is likely the root cause (passed up the stack)
                    if parent_diff_ms > 0:
                        ratio = diff_ms / parent_diff_ms
                        if ratio < 0.8: # If it explains < 80% of parent slowdown, it's likely just a victim or partial contributor
                             is_root_cause = False
                    else:
                        # Should not happen if parent_is_slow is True, but safety check
                        is_root_cause = False

                candidate = {
                    "span_name": span_name,
                    "slowdown_ms": diff_ms,
                    "slowdown_percent": diff_pct,
                    "is_root_cause": is_root_cause,
                    "parent_span": parent_name,
                    "parent_is_slow": parent_is_slow,
                }
                
                # Assign confidence based on magnitude vs parent slowness
                if not parent_is_slow and diff_pct > 100:
                    candidate["confidence"] = "high"
                    candidate["hypothesis"] = f"'{span_name}' is likely the root cause - {diff_pct:.0f}% slower with no slow parent"
                elif not parent_is_slow:
                    candidate["confidence"] = "medium"
                    candidate["hypothesis"] = f"'{span_name}' may be a root cause - independently slow"
                else:
                    candidate["confidence"] = "low"
                    candidate["hypothesis"] = f"'{span_name}' slowdown likely caused by parent '{parent_name}'"
                
                root_cause_candidates.append(candidate)
            
            # Sort by likelihood (root causes first, then by magnitude)
            root_cause_candidates.sort(
                key=lambda x: (not x["is_root_cause"], -x["slowdown_ms"])
            )
            
            # Build propagation chain (Root Cause -> Victim 1 -> Victim 2)
            propagation_chain = []
            for candidate in root_cause_candidates:
                if candidate["is_root_cause"]:
                    chain = [candidate["span_name"]]
                    # Find children that are also slow
                    for other in root_cause_candidates:
                        if other.get("parent_span") == candidate["span_name"]:
                            chain.append(other["span_name"])
                    if len(chain) > 1:
                        propagation_chain.append({
                            "origin": candidate["span_name"],
                            "affected_spans": chain[1:],
                            "description": f"Slowdown in '{candidate['span_name']}' propagated to {len(chain)-1} downstream spans"
                        })
            
            # Determine overall conclusion
            high_confidence_causes = [c for c in root_cause_candidates if c["confidence"] == "high"]
            
            if len(high_confidence_causes) == 1:
                conclusion = f"Root cause identified: {high_confidence_causes[0]['hypothesis']}"
                overall_confidence = "high"
            elif len(high_confidence_causes) > 1:
                # type: ignore[name-defined] 
                conclusion = f"Multiple potential root causes: {', '.join(str(c['span_name']) for c in high_confidence_causes[:3])}"
                overall_confidence = "medium"
            else:
                conclusion = "Root cause unclear - slowdown may be distributed across multiple spans"
                overall_confidence = "low"
                
            if high_confidence_causes:
                anomalies_detected.add(len(high_confidence_causes), {"type": "root_cause"})
            
            return {
                "root_cause_candidates": root_cause_candidates[:5],
                "propagation_chains": propagation_chain,
                "conclusion": conclusion,
                "overall_confidence": overall_confidence,
                "total_slowdown_ms": timing_diff.get("summary", {}).get("total_diff_ms", 0),
            }
        except Exception as e:
            span.record_exception(e)
            success = False
            raise e
        finally:
            duration_ms = (time.time() - start_time) * 1000
            _record_telemetry("perform_causal_analysis", success, duration_ms)


def compute_service_level_stats(traces: str) -> Dict[str, Any]:
    """
    Aggregates statistics at the service level from span naming patterns.

    Groups spans by service name (extracted from span names like "ServiceName/Method"
    or "service.method") and computes per-service latency statistics. Also maps
    service-to-service dependencies from the call graph.

    Args:
        traces (str | list): Collection of traces to analyze, either as:
            - JSON string: '[{"trace_id": "...", "spans": [...]}, ...]'
            - List of trace dictionaries

    Returns:
        Service-level statistics dictionary:
        - services (dict): Statistics per service name:
            - call_count: Total invocations across all traces
            - total_time_ms: Cumulative time spent in this service
            - mean_ms: Average latency per call
            - max_ms, min_ms: Latency range
        - service_dependencies (list): Service-to-service calls:
            - from_service: Calling service
            - to_service: Called service
            - call_count: Number of calls observed
        - hotspots (list): Top 5 services by total time:
            - service: Service name
            - total_time_ms: Cumulative time
            - percentage: % of total analyzed time
        - total_services (int): Number of unique services
        - total_time_analyzed_ms (float): Sum of all span durations

        On error, returns {"error": "error message"}

    Service Name Extraction:
        Extracts service name from span name patterns:
        - "ServiceName/MethodName" → "ServiceName"
        - "service.method.action" → "service"
        - "SERVICE_NAME" → "SERVICE_NAME"

    Example:
        >>> compute_service_level_stats(traces)
        {
            "services": {"payment-service": {"mean_ms": 45.2, "call_count": 150}},
            "hotspots": [{"service": "database", "percentage": 65.2}],
            "service_dependencies": [{"from_service": "api", "to_service": "database", "call_count": 50}]
        }
    """
    start_time = time.time()
    success = True
    
    with tracer.start_as_current_span("compute_service_level_stats") as span:
        span.set_attribute("code.function", "compute_service_level_stats")
        
        from .trace_analysis import calculate_span_durations, build_call_graph
        try:
            service_durations: Dict[str, List[float]] = defaultdict(list)
            service_calls: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
            
            if isinstance(traces, str):
                try:
                    traces = json.loads(traces)
                except json.JSONDecodeError as e:
                    return {"error": f"Failed to parse traces JSON: {str(e)}"}

            if not isinstance(traces, list):
                return {"error": f"Expected traces to be a list, but got {type(traces).__name__}"}

            for trace in traces:
                # Delegate parsing to tools
                timings = calculate_span_durations(trace)
                if timings and isinstance(timings[0], dict) and "error" in timings[0]:
                    continue
                
                # build_call_graph also handles strings/dicts, but we need graph for dependencies
                graph = build_call_graph(trace)
                if "error" in graph:
                     continue
                
                for s in timings:
                    name = s.get("name", "")
                    duration = s.get("duration_ms")
                    
                    # Extract service name (common patterns: "ServiceName/Method", "service.method", "SERVICE")
                    service = name.split("/")[0].split(".")[0].strip()
                    if service and duration is not None:
                        service_durations[service].append(duration)
                
                # Track service dependencies from call graph
                def track_dependencies(node: Dict[str, Any], parent_service: Optional[str] = None):
                    name = node.get("name", "")
                    service = name.split("/")[0].split(".")[0].strip()
                    if parent_service and service and parent_service != service:
                        service_calls[parent_service][service] += 1
                    for child in node.get("children", []):
                        track_dependencies(child, service or parent_service)
                
                for tree in graph.get("span_tree", []):
                    track_dependencies(tree)
            
            # Compute per-service stats
            services = {}
            total_time = 0.0
            
            for service, durations in service_durations.items():
                if not durations:
                    continue
                mean = sum(durations) / len(durations)
                services[service] = {
                    "call_count": len(durations),
                    "total_time_ms": round(sum(durations), 2),
                    "mean_ms": round(mean, 2),
                    "max_ms": round(max(durations), 2),
                    "min_ms": round(min(durations), 2),
                }
                total_time += sum(durations)
            
            # Identify hotspots (services consuming most time)
            hotspots = sorted(
                [
                    {
                        "service": name,
                        "total_time_ms": stats["total_time_ms"],
                        "percentage": round(stats["total_time_ms"] / max(total_time, 1) * 100, 1),
                    }
                    for name, stats in services.items()
                ],
                key=lambda x: x["total_time_ms"],
                reverse=True
            )[:5]
            
            # Format service dependencies
            dependencies = [
                {
                    "from_service": caller,
                    "to_service": callee,
                    "call_count": count
                }
                for caller, callees in service_calls.items()
                for callee, count in callees.items()
            ]
            
            return {
                "services": services,
                "service_dependencies": dependencies,
                "hotspots": hotspots,
                "total_services": len(services),
                "total_time_analyzed_ms": round(total_time, 2),
            }
        except Exception as e:
            span.record_exception(e)
            success = False
            raise e
        finally:
            duration_ms = (time.time() - start_time) * 1000
            _record_telemetry("compute_service_level_stats", success, duration_ms)
