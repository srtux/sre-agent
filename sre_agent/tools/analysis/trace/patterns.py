"""SRE Pattern Detection - Detects common distributed systems anti-patterns.

This module provides detection for patterns that commonly indicate issues in
distributed systems, helping SREs quickly identify root causes.

Patterns detected:
- Retry storms: Excessive retries indicating downstream issues
- Cascading timeouts: Timeout propagation through service chain
- Connection pool exhaustion: Long waits for connections
- Lock contention: Spans waiting on locks/mutexes (Future)
- Cold start latency: Unusually slow first requests (Future)
- Thundering herd: Many parallel requests to same resource (Future)
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...clients.trace import fetch_trace_data
from ...common import adk_tool
from ...common.telemetry import log_tool_call

logger = logging.getLogger(__name__)

# Pattern indicator keywords in span names and labels
RETRY_INDICATORS = ["retry", "attempt", "backoff", "reconnect"]
TIMEOUT_INDICATORS = [
    "timeout",
    "deadline",
    "exceeded",
    "timed out",
    "context deadline",
]
CONNECTION_INDICATORS = ["connection", "pool", "acquire", "checkout", "wait"]


def _parse_timestamp(ts: str) -> float | None:
    """Parse ISO timestamp to milliseconds since epoch."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000
    except (ValueError, TypeError):
        return None


def _get_span_duration(span: dict[str, Any]) -> float | None:
    """Get span duration in milliseconds."""
    if "duration_ms" in span:
        return float(span["duration_ms"])

    start = _parse_timestamp(span.get("start_time", ""))
    end = _parse_timestamp(span.get("end_time", ""))
    if start and end:
        return end - start
    return None


def _contains_indicator(text: str, indicators: list[str]) -> bool:
    """Check if text contains any of the indicator keywords."""
    text_lower = text.lower()
    return any(ind in text_lower for ind in indicators)


def _extract_span_info(span: dict[str, Any]) -> dict[str, Any]:
    """Extract key info from a span for pattern reporting."""
    return {
        "span_id": span.get("span_id"),
        "span_name": span.get("name"),
        "duration_ms": _get_span_duration(span),
        "parent_span_id": span.get("parent_span_id"),
        "labels": span.get("labels", {}),
    }


@adk_tool
def detect_retry_storm(
    trace_id: str,
    project_id: str | None = None,
    threshold: int = 3,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Detect retry storm patterns in a trace."""
    log_tool_call(logger, "detect_retry_storm", trace_id=trace_id)

    try:
        trace = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
        if "error" in trace:
            return BaseToolResponse(status=ToolStatus.ERROR, error=trace["error"])

        spans = trace.get("spans", [])
        retry_patterns = []

        # Group spans by name to find repeated operations
        spans_by_name = defaultdict(list)
        for s in spans:
            name = s.get("name", "")
            spans_by_name[name].append(s)

        for name, span_list in spans_by_name.items():
            # Check if name contains retry indicators
            is_retry_span = _contains_indicator(name, RETRY_INDICATORS)

            # Or check if we have many sequential spans with the same name
            if len(span_list) >= threshold or is_retry_span:
                # Sort by start time
                sorted_spans = sorted(
                    span_list,
                    key=lambda s: _parse_timestamp(s.get("start_time", "")) or 0,
                )

                # Check for sequential pattern (small gaps between spans)
                sequential_count = 1
                for i in range(1, len(sorted_spans)):
                    prev_end = _parse_timestamp(sorted_spans[i - 1].get("end_time", ""))
                    curr_start = _parse_timestamp(sorted_spans[i].get("start_time", ""))
                    if prev_end and curr_start:
                        gap_ms = curr_start - prev_end
                        # If gap is small (< 1 second), likely retries
                        if 0 <= gap_ms < 1000:
                            sequential_count += 1

                if sequential_count >= threshold or is_retry_span:
                    total_duration = sum(_get_span_duration(s) or 0 for s in span_list)

                    # Check for exponential backoff pattern
                    durations = [_get_span_duration(s) or 0 for s in sorted_spans]
                    has_backoff = False
                    if len(durations) >= 3:
                        # Check if durations are increasing
                        increasing = all(
                            durations[i] <= durations[i + 1] * 1.5
                            for i in range(len(durations) - 1)
                        )
                        has_backoff = increasing

                    retry_patterns.append(
                        {
                            "pattern_type": "retry_storm",
                            "span_name": name,
                            "retry_count": len(span_list),
                            "total_duration_ms": round(total_duration, 2),
                            "has_exponential_backoff": has_backoff,
                            "impact": "high" if len(span_list) >= 5 else "medium",
                            "recommendation": (
                                "Investigate downstream service health. "
                                "Consider circuit breaker pattern if not implemented."
                            ),
                        }
                    )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "trace_id": trace_id,
                "patterns_found": len(retry_patterns),
                "retry_patterns": retry_patterns,
                "has_retry_storm": len(retry_patterns) > 0,
            },
        )

    except Exception as e:
        logger.error(f"detect_retry_storm failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))


@adk_tool
def detect_cascading_timeout(
    trace_id: str,
    project_id: str | None = None,
    timeout_threshold_ms: float = 1000,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Detect cascading timeout patterns in a trace."""
    log_tool_call(logger, "detect_cascading_timeout", trace_id=trace_id)

    try:
        trace = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
        if "error" in trace:
            return BaseToolResponse(status=ToolStatus.ERROR, error=trace["error"])

        spans = trace.get("spans", [])
        timeout_spans = []

        # Find spans that look like timeouts
        for s in spans:
            name = s.get("name", "")
            labels = s.get("labels", {})
            labels_str = str(labels).lower()

            is_timeout = (
                _contains_indicator(name, TIMEOUT_INDICATORS)
                or _contains_indicator(labels_str, TIMEOUT_INDICATORS)
                or labels.get("error.type") == "timeout"
                or "deadline" in labels_str
            )

            duration = _get_span_duration(s) or 0

            if is_timeout or duration >= timeout_threshold_ms:
                timeout_spans.append(
                    {
                        **_extract_span_info(s),
                        "is_explicit_timeout": is_timeout,
                        "start_ms": _parse_timestamp(s.get("start_time", "")),
                    }
                )

        # Sort by start time to detect cascade
        timeout_spans.sort(key=lambda s: s.get("start_ms") or 0)

        # Detect cascade: child times out, then parent times out
        cascade_chains: list[dict[str, Any]] = []
        if len(timeout_spans) >= 2:
            # Build parent-child relationships
            parent_map = {s.get("span_id"): s.get("parent_span_id") for s in spans}

            # Check for timeout propagation chains
            for timeout_span in timeout_spans:
                chain = [timeout_span]
                current_id = timeout_span.get("parent_span_id")

                # Walk up the tree looking for parent timeouts
                while current_id:
                    parent_timeout = next(
                        (t for t in timeout_spans if t.get("span_id") == current_id),
                        None,
                    )
                    if parent_timeout:
                        chain.append(parent_timeout)
                    current_id = parent_map.get(current_id)

                if len(chain) >= 2:
                    cascade_chains.append(
                        {
                            "chain_length": len(chain),
                            "origin_span": chain[0]["span_name"],
                            "affected_spans": [c["span_name"] for c in chain],
                            "total_timeout_duration_ms": sum(
                                c.get("duration_ms") or 0 for c in chain
                            ),
                        }
                    )

        # Remove duplicate chains (subsets of longer chains)
        unique_chains: list[dict[str, Any]] = []
        for c in sorted(
            cascade_chains, key=lambda ch: ch["chain_length"], reverse=True
        ):
            affected = set(c["affected_spans"])
            is_subset = any(
                affected <= set(uc["affected_spans"]) for uc in unique_chains
            )
            if not is_subset:
                unique_chains.append(c)

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "trace_id": trace_id,
                "timeout_spans_count": len(timeout_spans),
                "timeout_spans": timeout_spans[:10],
                "cascade_detected": len(unique_chains) > 0,
                "cascade_chains": unique_chains,
                "impact": "critical" if len(unique_chains) > 0 else "low",
                "recommendation": (
                    "Review timeout configuration. Consider deadline propagation "
                    "and ensure child timeouts are shorter than parent timeouts."
                    if unique_chains
                    else "No cascading timeout detected."
                ),
            },
        )

    except Exception as e:
        logger.error(f"detect_cascading_timeout failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))


@adk_tool
def detect_connection_pool_issues(
    trace_id: str,
    project_id: str | None = None,
    wait_threshold_ms: float = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Detect connection pool exhaustion or contention patterns."""
    log_tool_call(logger, "detect_connection_pool_issues", trace_id=trace_id)

    try:
        trace = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
        if "error" in trace:
            return BaseToolResponse(status=ToolStatus.ERROR, error=trace["error"])

        spans = trace.get("spans", [])
        pool_issues = []

        for s in spans:
            name = s.get("name", "")
            labels = (s.get("labels", {}),)

            # Check for connection-related spans
            if not _contains_indicator(name, CONNECTION_INDICATORS):
                continue

            duration = _get_span_duration(s) or 0

            # Check for long waits
            if duration >= wait_threshold_ms:
                # Look for specific pool metrics in labels
                pool_size = (
                    labels[0].get("pool.size") or labels[0].get("db.pool_size")
                    if isinstance(labels, tuple)
                    else labels.get("pool.size")
                )
                active_connections = (
                    labels[0].get("pool.active")
                    or labels[0].get("db.active_connections")
                    if isinstance(labels, tuple)
                    else labels.get("pool.active")
                )
                waiting = (
                    labels[0].get("pool.waiting")
                    or labels[0].get("db.waiting_requests")
                    if isinstance(labels, tuple)
                    else labels.get("pool.waiting")
                )

                pool_issues.append(
                    {
                        "span_name": name,
                        "wait_duration_ms": round(duration, 2),
                        "pool_size": pool_size,
                        "active_connections": active_connections,
                        "waiting_requests": waiting,
                        "severity": (
                            "high"
                            if duration >= wait_threshold_ms * 5
                            else "medium"
                            if duration >= wait_threshold_ms * 2
                            else "low"
                        ),
                    }
                )

        # Calculate overall impact
        total_wait = sum(p["wait_duration_ms"] for p in pool_issues)

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "trace_id": trace_id,
                "issues_found": len(pool_issues),
                "pool_issues": pool_issues,
                "total_wait_ms": round(total_wait, 2),
                "has_pool_exhaustion": len(pool_issues) > 0
                and total_wait >= wait_threshold_ms * 3,
                "recommendation": (
                    "Consider increasing connection pool size or reducing connection hold time. "
                    "Review connection lifecycle and ensure proper connection release."
                    if pool_issues
                    else "No connection pool issues detected."
                ),
            },
        )

    except Exception as e:
        logger.error(f"detect_connection_pool_issues failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))


@adk_tool
def detect_all_sre_patterns(
    trace_id: str, project_id: str | None = None, tool_context: Any = None
) -> BaseToolResponse:
    """Run all SRE pattern detection checks on a trace."""
    log_tool_call(logger, "detect_all_sre_patterns", trace_id=trace_id)

    try:
        results: dict[str, Any] = {
            "trace_id": trace_id,
            "patterns": [],
            "overall_health": "healthy",
            "recommendations": [],
        }

        # Retry storm detection
        retry_res = detect_retry_storm(trace_id, project_id, tool_context=tool_context)
        if retry_res.status == ToolStatus.SUCCESS and retry_res.result.get(
            "has_retry_storm"
        ):
            results["patterns"].extend(retry_res.result["retry_patterns"])
            results["recommendations"].append(
                {
                    "pattern": "retry_storm",
                    "action": "Investigate downstream service health and implement circuit breakers",
                }
            )

        # Cascading timeout detection
        timeout_res = detect_cascading_timeout(
            trace_id, project_id, tool_context=tool_context
        )
        if timeout_res.status == ToolStatus.SUCCESS and timeout_res.result.get(
            "cascade_detected"
        ):
            results["patterns"].append(
                {
                    "pattern_type": "cascading_timeout",
                    "chains": timeout_res.result["cascade_chains"],
                    "impact": timeout_res.result["impact"],
                }
            )
            results["recommendations"].append(
                {
                    "pattern": "cascading_timeout",
                    "action": "Review timeout configuration and implement deadline propagation",
                }
            )

        # Connection pool detection
        pool_res = detect_connection_pool_issues(
            trace_id, project_id, tool_context=tool_context
        )
        if pool_res.status == ToolStatus.SUCCESS and pool_res.result.get(
            "has_pool_exhaustion"
        ):
            results["patterns"].append(
                {
                    "pattern_type": "connection_pool_exhaustion",
                    "issues": pool_res.result["pool_issues"],
                    "total_wait_ms": pool_res.result["total_wait_ms"],
                }
            )
            results["recommendations"].append(
                {
                    "pattern": "connection_pool_exhaustion",
                    "action": "Increase pool size or optimize connection lifecycle",
                }
            )

        # Determine overall health
        if any(p.get("impact") == "critical" for p in results["patterns"]):
            results["overall_health"] = "critical"
        elif any(p.get("impact") == "high" for p in results["patterns"]):
            results["overall_health"] = "degraded"
        elif results["patterns"]:
            results["overall_health"] = "warning"

        results["patterns_detected"] = len(results["patterns"])

        return BaseToolResponse(status=ToolStatus.SUCCESS, result=results)

    except Exception as e:
        logger.error(f"detect_all_sre_patterns failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
