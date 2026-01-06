"""Tools for interacting with the Google Cloud Trace API."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
import json
import time
import logging
import statistics

from google.cloud import trace_v1
from google.protobuf.timestamp_pb2 import Timestamp

from ..telemetry import get_tracer, get_meter, log_tool_call

logger = logging.getLogger(__name__)

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

def _record_telemetry(func_name: str, success: bool = True, duration_ms: float = 0.0):
    attributes = {
        "code.function": func_name,
        "code.namespace": __name__,
        "success": str(success).lower(),
        "trace_analyzer.tool.name": func_name,
    }
    logger.debug(f"Recording telemetry for {func_name}: success={success}, duration={duration_ms}ms, attributes={attributes}")
    execution_count.add(1, attributes)
    execution_duration.record(duration_ms, attributes)


def get_current_time() -> str:
    """
    Returns the current UTC time in ISO format. 
    Use this to calculate relative time ranges (e.g., 'now - 1 hour') for list_traces.
    """
    return datetime.now(timezone.utc).isoformat()


def _get_project_id() -> str:
    """Get the GCP project ID from environment."""
    project_id = os.environ.get("TRACE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT or TRACE_PROJECT_ID environment variable must be set")
    return project_id


def fetch_trace(project_id: str, trace_id: str) -> str:
    """
    Fetches a specific trace by ID.
    
    Args:
        project_id: The Google Cloud Project ID.
        trace_id: The unique hex ID of the trace.
    
    Returns:
        A dictionary representation of the trace, including all spans.
    """
    start_time = time.time()
    success = True
    
    with tracer.start_as_current_span("fetch_trace") as span:
        span.set_attribute("trace_analyzer.project_id", project_id)
        span.set_attribute("trace_analyzer.trace_id", trace_id)
        span.set_attribute("trace_analyzer.trace_id", trace_id)
        span.set_attribute("code.function", "fetch_trace")
        
        log_tool_call(logger, "fetch_trace", project_id=project_id, trace_id=trace_id)
        
        try:
            client = trace_v1.TraceServiceClient()
            
            trace_obj = client.get_trace(project_id=project_id, trace_id=trace_id)
            
            spans = []
            trace_start = None
            trace_end = None

            for span_proto in trace_obj.spans:
                # span_proto.start_time is a standard python datetime in newer google-cloud libraries (proto-plus)
                s_start = span_proto.start_time.timestamp()
                s_end = span_proto.end_time.timestamp()

                if trace_start is None or s_start < trace_start:
                    trace_start = s_start
                if trace_end is None or s_end > trace_end:
                    trace_end = s_end

                spans.append({
                    "span_id": span_proto.span_id,
                    "name": span_proto.name,
                    "start_time": span_proto.start_time.isoformat(),
                    "end_time": span_proto.end_time.isoformat(),
                    "parent_span_id": span_proto.parent_span_id,
                    "labels": dict(span_proto.labels),
                })
            
            duration_ms = (trace_end - trace_start) * 1000 if trace_start and trace_end else 0

            result = {
                "trace_id": trace_obj.trace_id,
                "project_id": trace_obj.project_id,
                "spans": spans,
                "span_count": len(spans),
                "duration_ms": duration_ms
            }
            span.set_attribute("trace_analyzer.span_count", len(spans))
            return json.dumps(result)
            
        except Exception as e:
            span.record_exception(e)
            success = False
            error_msg = f"Failed to fetch trace: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        finally:
            duration_ms = (time.time() - start_time) * 1000
            _record_telemetry("fetch_trace", success, duration_ms)


def list_traces(
    project_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 10,
    filter_str: str = "",
    min_latency_ms: Optional[int] = None,
    error_only: bool = False,
    attributes: Optional[Dict[str, str]] = None
) -> str:
    """
    Lists recent traces with advanced filtering capabilities.
    
    Args:
        project_id: The GCP project ID.
        start_time: ISO timestamp for start of window.
        end_time: ISO timestamp for end of window.
        limit: Max number of traces to return.
        filter_str: Raw filter string (overrides other filters if provided).
        min_latency_ms: Minimum latency in milliseconds.
        error_only: If True, filters for traces with errors (label:error:true or /http/status_code:500).
        attributes: Dictionary of attribute key-values to filter by (exact match).
    
    Returns:
        List of trace summaries.
    """
    ts_start = time.time()
    success = True

    with tracer.start_as_current_span("list_traces") as span:
        span.set_attribute("trace_analyzer.project_id", project_id)

        log_tool_call(logger, "list_traces", project_id=project_id, start_time=start_time, end_time=end_time, limit=limit, filter_str=filter_str, min_latency_ms=min_latency_ms, error_only=error_only, attributes=attributes)

        # Build filter string if not provided
        final_filter = filter_str
        if not final_filter:
            filters = []
            if min_latency_ms:
                filters.append(f"latency:{min_latency_ms}ms")

            if error_only:
                # Common ways to find errors in Cloud Trace.
                # "error:true" matches the standard error label.
                filters.append("error:true")

            if attributes:
                for k, v in attributes.items():
                    # Standard Cloud Trace filter is key:value
                    filters.append(f"{k}:{v}")

            final_filter = " ".join(filters)

        span.set_attribute("trace_analyzer.filter", final_filter)
        
        try:
            client = trace_v1.TraceServiceClient()
            
            now = datetime.now(timezone.utc)
            if not end_time:
                end_dt = now
            else:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                
            if not start_time:
                start_dt = now - timedelta(hours=1)
            else:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            
            # Note: proto-plus handles datetime conversion automatically for Timestamp fields
            
            request = trace_v1.ListTracesRequest(
                project_id=project_id,
                start_time=start_dt, # Pass datetime directly
                end_time=end_dt,     # Pass datetime directly
                page_size=limit,
                filter=final_filter,
                # Use ROOTSPAN view to get at least the root span for duration calculation.
                # MINIMAL view only returns trace_id and project_id.
                view=trace_v1.ListTracesRequest.ViewType.ROOTSPAN
            )
            
            traces = []
            page_result = client.list_traces(request=request)
            
            for trace in page_result:
                # Calculate duration
                duration_ms = 0
                start_ts = None

                # In ROOTSPAN view, we should have at least the root span.
                if trace.spans:
                    # Just use the root span's duration as a proxy if we don't have all spans.
                    # Usually root span covers the whole request.
                    # Or check all available spans.
                    starts = []
                    ends = []
                    for s in trace.spans:
                         # s.start_time is datetime
                         starts.append(s.start_time.timestamp())
                         ends.append(s.end_time.timestamp())

                    if starts and ends:
                        start_ts = min(starts)
                        duration_ms = (max(ends) - start_ts) * 1000

                traces.append({
                    "trace_id": trace.trace_id,
                    "timestamp": datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat() if start_ts else None,
                    "duration_ms": duration_ms,
                    "project_id": trace.project_id
                })
                
                if len(traces) >= limit:
                    break
            
            return json.dumps(traces)

        except Exception as e:
            span.record_exception(e)
            success = False
            error_msg = f"Failed to list traces: {str(e)}"
            logger.error(error_msg)
            return json.dumps([{"error": error_msg}])
        finally:
            duration_ms = (time.time() - ts_start) * 1000
            _record_telemetry("list_traces", success, duration_ms)


def find_example_traces() -> str:
    """
    Intelligently discovers representative baseline and anomaly traces.
    
    Returns:
        JSON string with 'baseline' and 'anomaly' keys containing trace summaries.
    """
    ts_start = time.time()
    success = True
    
    with tracer.start_as_current_span("find_example_traces") as span:
        log_tool_call(logger, "find_example_traces")
        try:
            try:
                project_id = _get_project_id()
            except ValueError:
                return json.dumps({"error": "GOOGLE_CLOUD_PROJECT not set"})
            
            # 1. Fetch a larger batch of recent traces to build a statistical model
            raw_traces = list_traces(project_id, limit=50)
            traces = json.loads(raw_traces)

            if isinstance(traces, list) and len(traces) > 0 and "error" in traces[0]:
                return raw_traces

            if not traces:
                return json.dumps({"error": "No traces found in the last hour."})

            # 2. Extract Latencies
            valid_traces = [t for t in traces if t.get("duration_ms", 0) > 0]
            if not valid_traces:
                 # If we only got 0-duration traces, maybe the ViewType failed to return spans?
                 # But we fixed it to ROOTSPAN. So it means traces are weird or empty.
                 return json.dumps({"error": "No traces with valid duration found."})

            latencies = [t["duration_ms"] for t in valid_traces]
            latencies.sort()

            # 3. Calculate Stats
            p50 = statistics.median(latencies)
            p95 = latencies[int(len(latencies) * 0.95)]
            mean = statistics.mean(latencies)
            stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0

            span.set_attribute("trace_stats.p50", p50)
            span.set_attribute("trace_stats.p95", p95)

            # 4. Find Baseline (Closest to P50)
            baseline = min(valid_traces, key=lambda x: abs(x["duration_ms"] - p50))

            # 5. Find Anomaly
            anomaly = None
            candidates = [t for t in valid_traces if t["duration_ms"] > p95]
            if candidates:
                anomaly = candidates[-1] # The slowest
            else:
                anomaly = valid_traces[-1]

            if abs(anomaly["duration_ms"] - baseline["duration_ms"]) < (stdev * 0.5):
                error_traces_json = list_traces(project_id, limit=1, error_only=True)
                error_traces = json.loads(error_traces_json)
                if error_traces and not (isinstance(error_traces, list) and "error" in error_traces[0]):
                    if error_traces:
                        anomaly = error_traces[0]
                        anomaly["note"] = "Explicit error trace found"

            return json.dumps({
                "stats": {
                    "count": len(valid_traces),
                    "p50_ms": round(p50, 2),
                    "p95_ms": round(p95, 2),
                    "mean_ms": round(mean, 2)
                },
                "baseline": baseline,
                "anomaly": anomaly
            })

        except Exception as e:
            span.record_exception(e)
            success = False
            error_msg = f"Failed to find example traces: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        finally:
            duration_ms = (time.time() - ts_start) * 1000
            _record_telemetry("find_example_traces", success, duration_ms)


def get_trace_by_url(url: str) -> str:
    """
    Parses a Cloud Console URL to extract trace ID and fetch the trace.
    
    Args:
        url: The full URL from Google Cloud Console trace view.
    
    Returns:
        The fetched trace data.
    """
    ts_start = time.time()
    success = True
    
    with tracer.start_as_current_span("get_trace_by_url") as span:
        span.set_attribute("trace_analyzer.url", url)
        span.set_attribute("code.function", "get_trace_by_url")
        
        log_tool_call(logger, "get_trace_by_url", url=url)
        
        try:
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            project_id = params.get("project", [None])[0]
            
            trace_id = None
            if "tid" in params:
                 trace_id = params["tid"][0]
            elif "details" in parsed.path:
                parts = parsed.path.split("/")
                if "details" in parts:
                    idx = parts.index("details")
                    if idx + 1 < len(parts):
                        trace_id = parts[idx+1]
            
            if not project_id or not trace_id:
                return json.dumps({"error": "Could not parse project_id or trace_id from URL"})
                
            return fetch_trace(project_id, trace_id)

        except Exception as e:
            span.record_exception(e)
            success = False
            error_msg = f"Failed to parse URL/fetch trace: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        finally:
            duration_ms = (time.time() - ts_start) * 1000
            _record_telemetry("get_trace_by_url", success, duration_ms)
