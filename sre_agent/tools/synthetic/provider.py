"""Synthetic data provider for Guest Mode.

Returns realistic telemetry data matching the Cymbal Shops scenario
without requiring any GCP API calls.  Every public method returns a
``BaseToolResponse`` so tool call-sites can use a simple short-circuit:

    if is_guest_mode():
        return SyntheticDataProvider.fetch_trace(trace_id, project_id)
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus

from .scenarios import (
    ALERT_DEFS,
    ALERT_POLICIES,
    DEMO_CLUSTER_NAME,
    DEMO_PROJECT_ID,
    DEMO_REGION,
    LOG_TEMPLATES,
    METRIC_DESCRIPTORS,
    POD_NAMES,
    SERVICES,
    TRACE_IDS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RNG = random.Random(42)  # Seeded for deterministic-ish but varied data


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _incident_start() -> datetime:
    """The incident started ~90 minutes ago."""
    return _now() - timedelta(minutes=90)


def _pod_name(service: str, index: int = 0) -> str:
    pods = POD_NAMES.get(service, [f"{service}-pod-{index}"])
    return pods[index % len(pods)]


def _resource_labels(service: str, pod_index: int = 0) -> dict[str, str]:
    svc = SERVICES.get(service)
    if not svc:
        return {"project_id": DEMO_PROJECT_ID}

    if svc.resource_type == "k8s_container":
        return {
            "project_id": DEMO_PROJECT_ID,
            "cluster_name": DEMO_CLUSTER_NAME,
            "location": DEMO_REGION,
            "namespace_name": svc.namespace,
            "pod_name": _pod_name(service, pod_index),
            "container_name": service,
        }
    if svc.resource_type == "cloud_run_revision":
        return {
            "project_id": DEMO_PROJECT_ID,
            "service_name": service,
            "revision_name": f"{service}-00042-abc",
            "location": DEMO_REGION,
        }
    if svc.resource_type == "cloudsql_database":
        return {
            "project_id": DEMO_PROJECT_ID,
            "database_id": f"{DEMO_PROJECT_ID}:order-db-prod",
            "region": DEMO_REGION,
        }
    return {"project_id": DEMO_PROJECT_ID}


# ---------------------------------------------------------------------------
# Trace generation
# ---------------------------------------------------------------------------


def _build_checkout_slow_trace(trace_id: str) -> dict[str, Any]:
    """Build a degraded checkout trace showing the DB bottleneck."""
    base = _now() - timedelta(minutes=_RNG.randint(5, 80))
    spans: list[dict[str, Any]] = []

    # Root: api-gateway
    gw_span_id = "1000000000000001"
    spans.append(
        {
            "span_id": gw_span_id,
            "name": "HTTP POST /api/v1/checkout",
            "start_time": _iso(base),
            "end_time": _iso(base + timedelta(milliseconds=2950)),
            "start_time_unix": base.timestamp(),
            "end_time_unix": (base + timedelta(milliseconds=2950)).timestamp(),
            "parent_span_id": None,
            "labels": {
                "/http/method": "POST",
                "/http/url": "https://api-gateway.cymbal-shops.internal/api/v1/checkout",
                "/http/status_code": "200",
                "service.name": "api-gateway",
            },
        }
    )

    # Child: checkout-service
    co_start = base + timedelta(milliseconds=8)
    co_span_id = "2000000000000001"
    spans.append(
        {
            "span_id": co_span_id,
            "name": "checkout.ProcessOrder",
            "start_time": _iso(co_start),
            "end_time": _iso(co_start + timedelta(milliseconds=2900)),
            "start_time_unix": co_start.timestamp(),
            "end_time_unix": (co_start + timedelta(milliseconds=2900)).timestamp(),
            "parent_span_id": gw_span_id,
            "labels": {
                "service.name": "checkout-service",
                "checkout.order_id": "ord-demo-78923",
            },
        }
    )

    # Child: DB query (slow!) - N+1 queries
    for i in range(5):
        db_start = co_start + timedelta(milliseconds=20 + i * 520)
        db_dur = 480 + _RNG.randint(0, 100)
        db_span_id = f"300000000000000{i + 1}"
        spans.append(
            {
                "span_id": db_span_id,
                "name": f"DB SELECT orders (query {i + 1}/5)",
                "start_time": _iso(db_start),
                "end_time": _iso(db_start + timedelta(milliseconds=db_dur)),
                "start_time_unix": db_start.timestamp(),
                "end_time_unix": (
                    db_start + timedelta(milliseconds=db_dur)
                ).timestamp(),
                "parent_span_id": co_span_id,
                "labels": {
                    "db.system": "postgresql",
                    "db.name": "orders",
                    "db.statement": "SELECT * FROM orders WHERE user_id=$1 AND status=$2",
                    "db.operation": "SELECT",
                    "service.name": "order-db",
                    "/http/status_code": "200",
                },
            }
        )

    # Child: payment-service call (healthy)
    pay_start = co_start + timedelta(milliseconds=2650)
    spans.append(
        {
            "span_id": "4000000000000001",
            "name": "HTTP POST /api/v1/payments/charge",
            "start_time": _iso(pay_start),
            "end_time": _iso(pay_start + timedelta(milliseconds=95)),
            "start_time_unix": pay_start.timestamp(),
            "end_time_unix": (pay_start + timedelta(milliseconds=95)).timestamp(),
            "parent_span_id": co_span_id,
            "labels": {
                "/http/method": "POST",
                "/http/status_code": "200",
                "service.name": "payment-service",
            },
        }
    )

    return {
        "trace_id": trace_id,
        "project_id": DEMO_PROJECT_ID,
        "spans": spans,
        "span_count": len(spans),
        "duration_ms": 2950.0,
    }


def _build_checkout_error_trace(trace_id: str) -> dict[str, Any]:
    """Build a checkout trace that fails due to DB connection timeout."""
    base = _now() - timedelta(minutes=_RNG.randint(10, 60))
    spans: list[dict[str, Any]] = []

    gw_span_id = "5000000000000001"
    spans.append(
        {
            "span_id": gw_span_id,
            "name": "HTTP POST /api/v1/checkout",
            "start_time": _iso(base),
            "end_time": _iso(base + timedelta(milliseconds=5100)),
            "start_time_unix": base.timestamp(),
            "end_time_unix": (base + timedelta(milliseconds=5100)).timestamp(),
            "parent_span_id": None,
            "labels": {
                "/http/method": "POST",
                "/http/url": "https://api-gateway.cymbal-shops.internal/api/v1/checkout",
                "/http/status_code": "503",
                "service.name": "api-gateway",
            },
        }
    )

    co_start = base + timedelta(milliseconds=5)
    co_span_id = "6000000000000001"
    spans.append(
        {
            "span_id": co_span_id,
            "name": "checkout.ProcessOrder",
            "start_time": _iso(co_start),
            "end_time": _iso(co_start + timedelta(milliseconds=5050)),
            "start_time_unix": co_start.timestamp(),
            "end_time_unix": (co_start + timedelta(milliseconds=5050)).timestamp(),
            "parent_span_id": gw_span_id,
            "labels": {
                "service.name": "checkout-service",
                "error": "true",
                "error.message": "Connection pool exhausted",
            },
        }
    )

    # DB connection attempt that times out
    db_start = co_start + timedelta(milliseconds=15)
    spans.append(
        {
            "span_id": "7000000000000001",
            "name": "DB pool.acquire (TIMEOUT)",
            "start_time": _iso(db_start),
            "end_time": _iso(db_start + timedelta(milliseconds=5000)),
            "start_time_unix": db_start.timestamp(),
            "end_time_unix": (db_start + timedelta(milliseconds=5000)).timestamp(),
            "parent_span_id": co_span_id,
            "labels": {
                "db.system": "postgresql",
                "db.name": "orders",
                "error": "true",
                "error.message": "Connection pool exhausted: timeout after 5000ms",
                "service.name": "order-db",
                "/http/status_code": "503",
            },
        }
    )

    return {
        "trace_id": trace_id,
        "project_id": DEMO_PROJECT_ID,
        "spans": spans,
        "span_count": len(spans),
        "duration_ms": 5100.0,
    }


def _build_healthy_trace(
    trace_id: str, service: str, endpoint: str, dur_ms: float
) -> dict[str, Any]:
    """Build a simple healthy trace for a non-degraded service."""
    base = _now() - timedelta(minutes=_RNG.randint(1, 30))
    return {
        "trace_id": trace_id,
        "project_id": DEMO_PROJECT_ID,
        "spans": [
            {
                "span_id": "8000000000000001",
                "name": f"HTTP GET {endpoint}",
                "start_time": _iso(base),
                "end_time": _iso(base + timedelta(milliseconds=dur_ms)),
                "start_time_unix": base.timestamp(),
                "end_time_unix": (base + timedelta(milliseconds=dur_ms)).timestamp(),
                "parent_span_id": None,
                "labels": {
                    "/http/method": "GET",
                    "/http/url": f"https://{service}.cymbal-shops.internal{endpoint}",
                    "/http/status_code": "200",
                    "service.name": service,
                },
            }
        ],
        "span_count": 1,
        "duration_ms": dur_ms,
    }


_TRACE_BUILDERS: dict[str, Any] = {
    "checkout_slow_1": lambda tid: _build_checkout_slow_trace(tid),
    "checkout_slow_2": lambda tid: _build_checkout_slow_trace(tid),
    "checkout_error_1": lambda tid: _build_checkout_error_trace(tid),
    "checkout_healthy": lambda tid: _build_healthy_trace(
        tid, "checkout-service", "/api/v1/checkout", 85.0
    ),
    "product_healthy": lambda tid: _build_healthy_trace(
        tid, "product-catalog", "/api/v1/products", 22.0
    ),
    "cart_healthy": lambda tid: _build_healthy_trace(
        tid, "cart-service", "/api/v1/cart", 18.0
    ),
    "payment_flow": lambda tid: _build_healthy_trace(
        tid, "payment-service", "/api/v1/payments/charge", 92.0
    ),
    "recommendation": lambda tid: _build_healthy_trace(
        tid, "recommendation-service", "/api/v1/recommendations", 28.0
    ),
}


# ---------------------------------------------------------------------------
# Metric time-series generation
# ---------------------------------------------------------------------------


def _generate_time_series(
    metric_type: str,
    resource_type: str,
    resource_labels: dict[str, str],
    metric_labels: dict[str, str],
    minutes_ago: int,
    baseline: float,
    incident_multiplier: float = 1.0,
    noise_pct: float = 0.05,
) -> dict[str, Any]:
    """Generate a single time series with an incident spike."""
    points: list[dict[str, Any]] = []
    now = _now()
    incident_start = _incident_start()
    interval_sec = max(60, (minutes_ago * 60) // 60)  # ~60 data points max

    t = now - timedelta(minutes=minutes_ago)
    while t <= now:
        # Before incident: baseline + noise
        # After incident: baseline * multiplier + noise
        if t >= incident_start and incident_multiplier != 1.0:
            # Ramp up over 10 minutes
            ramp_minutes = (t - incident_start).total_seconds() / 60.0
            ramp_factor = min(1.0, ramp_minutes / 10.0)
            value = baseline * (1.0 + (incident_multiplier - 1.0) * ramp_factor)
        else:
            value = baseline

        # Add sinusoidal daily pattern + noise
        hour_frac = t.hour + t.minute / 60.0
        daily_factor = 1.0 + 0.15 * math.sin(2 * math.pi * (hour_frac - 10) / 24)
        noise = _RNG.uniform(-noise_pct, noise_pct)
        value = value * daily_factor * (1.0 + noise)

        points.append(
            {
                "timestamp": _iso(t),
                "value": round(value, 4),
            }
        )
        t += timedelta(seconds=interval_sec)

    return {
        "metric": {"type": metric_type, "labels": metric_labels},
        "resource": {"type": resource_type, "labels": resource_labels},
        "points": points,
    }


# ---------------------------------------------------------------------------
# Public API: SyntheticDataProvider
# ---------------------------------------------------------------------------


class SyntheticDataProvider:
    """Static methods returning ``BaseToolResponse`` for each tool."""

    # -- Traces --

    @staticmethod
    def fetch_trace(trace_id: str, project_id: str | None = None) -> BaseToolResponse:
        """Return a synthetic trace by ID."""
        # Check if it matches a known scenario trace
        for key, tid in TRACE_IDS.items():
            if trace_id == tid:
                builder = _TRACE_BUILDERS.get(key)
                if builder:
                    return BaseToolResponse(
                        status=ToolStatus.SUCCESS, result=builder(tid)
                    )

        # Unknown trace ID: return a generic healthy trace
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=_build_healthy_trace(trace_id, "frontend", "/", 35.0),
        )

    @staticmethod
    def list_traces(
        project_id: str | None = None,
        limit: int = 10,
        min_latency_ms: int | None = None,
        error_only: bool = False,
        **kwargs: Any,
    ) -> BaseToolResponse:
        """Return a list of synthetic trace summaries."""
        traces: list[dict[str, Any]] = []

        for key, tid in TRACE_IDS.items():
            builder = _TRACE_BUILDERS.get(key)
            if not builder:
                continue
            trace_data = builder(tid)
            dur = trace_data.get("duration_ms", 0)

            if min_latency_ms and dur < min_latency_ms:
                continue

            has_error = any(
                s.get("labels", {}).get("error") == "true"
                for s in trace_data.get("spans", [])
            )
            if error_only and not has_error:
                continue

            root_span = trace_data["spans"][0] if trace_data.get("spans") else {}
            traces.append(
                {
                    "trace_id": tid,
                    "project_id": project_id or DEMO_PROJECT_ID,
                    "name": root_span.get("name", "unknown"),
                    "start_time": root_span.get("start_time", _iso(_now())),
                    "duration_ms": dur,
                    "duration_ms_str": str(round(dur, 2)),
                    "status": root_span.get("labels", {}).get(
                        "/http/status_code", "200"
                    ),
                    "url": root_span.get("labels", {}).get("/http/url", ""),
                }
            )

            if len(traces) >= limit:
                break

        return BaseToolResponse(status=ToolStatus.SUCCESS, result=traces)

    @staticmethod
    def find_example_traces(
        project_id: str | None = None, **kwargs: Any
    ) -> BaseToolResponse:
        """Return baseline + anomaly trace pair."""
        baseline = _build_healthy_trace(
            TRACE_IDS["checkout_healthy"],
            "checkout-service",
            "/api/v1/checkout",
            85.0,
        )
        anomaly = _build_checkout_slow_trace(TRACE_IDS["checkout_slow_1"])

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "stats": {
                    "count": 50,
                    "p50_ms": 92.0,
                    "mean_ms": 485.3,
                    "stdev_ms": 890.2,
                    "error_traces_found": 3,
                },
                "baseline": {
                    "trace_id": baseline["trace_id"],
                    "duration_ms": baseline["duration_ms"],
                    "name": "HTTP GET /api/v1/checkout",
                    "_selection_reason": "Closest to P50 (92.0ms)",
                },
                "anomaly": {
                    "trace_id": anomaly["trace_id"],
                    "duration_ms": anomaly["duration_ms"],
                    "name": "HTTP POST /api/v1/checkout",
                    "has_error": False,
                    "_selection_reason": "Latency anomaly (8.42)",
                    "_anomaly_score": 8.42,
                },
                "validation": {
                    "baseline_valid": True,
                    "anomaly_valid": True,
                    "sample_adequate": True,
                    "latency_variance_detected": True,
                },
                "selection_method": "hybrid_multi_signal",
            },
        )

    # -- Logs --

    @staticmethod
    def list_log_entries(
        filter_str: str = "",
        project_id: str | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> BaseToolResponse:
        """Return synthetic log entries matching the filter."""
        entries: list[dict[str, Any]] = []
        now = _now()

        # Determine severity floor from filter (e.g. severity>=ERROR)
        severity_order = [
            "DEBUG",
            "INFO",
            "NOTICE",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "ALERT",
            "EMERGENCY",
        ]
        min_severity_idx = 0
        lower_filter = filter_str.lower()
        if "severity>=error" in lower_filter or 'severity>="error"' in lower_filter:
            min_severity_idx = severity_order.index("ERROR")
        elif (
            "severity>=warning" in lower_filter or 'severity>="warning"' in lower_filter
        ):
            min_severity_idx = severity_order.index("WARNING")
        elif (
            "severity>=critical" in lower_filter
            or 'severity>="critical"' in lower_filter
        ):
            min_severity_idx = severity_order.index("CRITICAL")

        # Determine which templates to use based on filter
        template_keys: list[str] = []

        if "error" in lower_filter or "critical" in lower_filter:
            template_keys.extend(["checkout_errors", "db_errors"])
        elif "warning" in lower_filter:
            template_keys.extend(["checkout_warnings"])
        elif "checkout" in lower_filter:
            template_keys.extend(
                [
                    "checkout_errors",
                    "checkout_warnings",
                    "deployment_event",
                ]
            )
        elif "order-db" in lower_filter or "cloudsql" in lower_filter:
            template_keys.extend(["db_errors"])
        else:
            # Mix of everything
            template_keys.extend(
                [
                    "checkout_errors",
                    "checkout_warnings",
                    "db_errors",
                    "healthy_services",
                    "deployment_event",
                ]
            )

        idx = 0
        for key in template_keys:
            templates = LOG_TEMPLATES.get(key, [])
            for tmpl in templates:
                if idx >= limit:
                    break
                # Apply severity filter
                tmpl_sev = tmpl["severity"]
                if tmpl_sev in severity_order:
                    if severity_order.index(tmpl_sev) < min_severity_idx:
                        continue
                svc = tmpl.get("service", "unknown")
                svc_def = SERVICES.get(svc)
                res_type = svc_def.resource_type if svc_def else "k8s_container"

                trace_id = TRACE_IDS.get("checkout_slow_1", "")
                if svc == "checkout-service":
                    trace_id = TRACE_IDS["checkout_slow_1"]
                elif svc == "order-db":
                    trace_id = TRACE_IDS["checkout_error_1"]

                entry_time = now - timedelta(seconds=idx * 12 + _RNG.randint(0, 5))
                entries.append(
                    {
                        "timestamp": _iso(entry_time),
                        "severity": tmpl["severity"],
                        "payload": tmpl["payload"],
                        "resource": {
                            "type": res_type,
                            "labels": _resource_labels(svc, tmpl.get("pod_index", 0)),
                        },
                        "insert_id": f"demo-log-{idx:04d}",
                        "trace": f"projects/{DEMO_PROJECT_ID}/traces/{trace_id}",
                        "span_id": None,
                        "http_request": None,
                    }
                )
                idx += 1

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"entries": entries[:limit], "next_page_token": None},
        )

    @staticmethod
    def list_error_events(
        project_id: str | None = None,
        minutes_ago: int = 60,
        **kwargs: Any,
    ) -> BaseToolResponse:
        """Return synthetic error events."""
        now = _now()
        events = [
            {
                "event_time": _iso(now - timedelta(minutes=i * 8)),
                "message": msg,
                "service_context": {"service": svc, "version": ver},
            }
            for i, (msg, svc, ver) in enumerate(
                [
                    (
                        "Connection pool exhausted: all 100 connections in use",
                        "checkout-service",
                        "v2.14.0",
                    ),
                    (
                        "FATAL: sorry, too many clients already",
                        "order-db",
                        "14.5",
                    ),
                    (
                        "Failed to acquire database connection within timeout (5000ms)",
                        "checkout-service",
                        "v2.14.0",
                    ),
                    (
                        "Circuit breaker OPEN for order-db: 15 consecutive failures",
                        "checkout-service",
                        "v2.14.0",
                    ),
                    (
                        "Order creation failed: database connection unavailable",
                        "checkout-service",
                        "v2.14.0",
                    ),
                ]
            )
        ]
        return BaseToolResponse(status=ToolStatus.SUCCESS, result=events)

    @staticmethod
    def get_logs_for_trace(
        project_id: str,
        trace_id: str,
        limit: int = 100,
        **kwargs: Any,
    ) -> BaseToolResponse:
        """Return logs correlated with a specific trace."""
        return SyntheticDataProvider.list_log_entries(
            filter_str=f'trace="projects/{project_id}/traces/{trace_id}"',
            project_id=project_id,
            limit=limit,
        )

    # -- Metrics --

    @staticmethod
    def list_time_series(
        filter_str: str = "",
        minutes_ago: int = 60,
        project_id: str | None = None,
        **kwargs: Any,
    ) -> BaseToolResponse:
        """Return synthetic time series data."""
        lower = filter_str.lower()
        series: list[dict[str, Any]] = []

        # Determine which metrics to generate
        if "latency" in lower or "http" in lower:
            # Checkout latency (degraded)
            if "checkout" in lower:
                series.append(
                    _generate_time_series(
                        metric_type="custom.googleapis.com/http/server/latency",
                        resource_type="k8s_container",
                        resource_labels=_resource_labels("checkout-service"),
                        metric_labels={
                            "service_name": "checkout-service",
                            "method": "POST",
                        },
                        minutes_ago=minutes_ago,
                        baseline=85.0,
                        incident_multiplier=33.0,  # 85ms -> ~2800ms
                    )
                )
            else:
                # General latency
                for svc_name in ["frontend", "api-gateway", "product-catalog"]:
                    svc = SERVICES[svc_name]
                    series.append(
                        _generate_time_series(
                            metric_type="custom.googleapis.com/http/server/latency",
                            resource_type=svc.resource_type,
                            resource_labels=_resource_labels(svc_name),
                            metric_labels={"service_name": svc_name},
                            minutes_ago=minutes_ago,
                            baseline=svc.latency_ms_p50,
                        )
                    )

        elif "error_rate" in lower:
            series.append(
                _generate_time_series(
                    metric_type="custom.googleapis.com/http/server/error_rate",
                    resource_type="k8s_container",
                    resource_labels=_resource_labels("checkout-service"),
                    metric_labels={"service_name": "checkout-service"},
                    minutes_ago=minutes_ago,
                    baseline=0.1,
                    incident_multiplier=52.0,  # 0.1% -> ~5.2%
                )
            )

        elif "cpu" in lower:
            target = "checkout-service" if "checkout" in lower else "frontend"
            svc = SERVICES[target]
            series.append(
                _generate_time_series(
                    metric_type="kubernetes.io/container/cpu/core_usage_time",
                    resource_type="k8s_container",
                    resource_labels=_resource_labels(target),
                    metric_labels={},
                    minutes_ago=minutes_ago,
                    baseline=0.35,
                    incident_multiplier=2.5 if target == "checkout-service" else 1.0,
                )
            )

        elif "memory" in lower:
            target = "checkout-service" if "checkout" in lower else "frontend"
            series.append(
                _generate_time_series(
                    metric_type="kubernetes.io/container/memory/used_bytes",
                    resource_type="k8s_container",
                    resource_labels=_resource_labels(target),
                    metric_labels={},
                    minutes_ago=minutes_ago,
                    baseline=256_000_000,  # 256MB
                    incident_multiplier=1.8 if target == "checkout-service" else 1.0,
                )
            )

        elif "num_backends" in lower or "connection" in lower:
            series.append(
                _generate_time_series(
                    metric_type="cloudsql.googleapis.com/database/postgresql/num_backends",
                    resource_type="cloudsql_database",
                    resource_labels=_resource_labels("order-db"),
                    metric_labels={"database": "orders"},
                    minutes_ago=minutes_ago,
                    baseline=25.0,
                    incident_multiplier=4.0,  # 25 -> 100 (max)
                )
            )

        else:
            # Default: return checkout latency
            series.append(
                _generate_time_series(
                    metric_type="custom.googleapis.com/http/server/latency",
                    resource_type="k8s_container",
                    resource_labels=_resource_labels("checkout-service"),
                    metric_labels={"service_name": "checkout-service"},
                    minutes_ago=minutes_ago,
                    baseline=85.0,
                    incident_multiplier=33.0,
                )
            )

        return BaseToolResponse(status=ToolStatus.SUCCESS, result=series)

    @staticmethod
    def list_metric_descriptors(
        filter_str: str | None = None,
        project_id: str | None = None,
        **kwargs: Any,
    ) -> BaseToolResponse:
        """Return synthetic metric descriptors."""
        descriptors = METRIC_DESCRIPTORS
        if filter_str:
            lower = filter_str.lower()
            descriptors = [d for d in descriptors if lower in d["type"].lower()]
        return BaseToolResponse(status=ToolStatus.SUCCESS, result=descriptors)

    @staticmethod
    def query_promql(
        query: str = "",
        project_id: str | None = None,
        **kwargs: Any,
    ) -> BaseToolResponse:
        """Return synthetic PromQL-format response."""
        now = _now()
        values: list[list[Any]] = []

        # Generate 60 data points over the last hour
        for i in range(60):
            ts = (now - timedelta(minutes=60 - i)).timestamp()
            incident_start = _incident_start().timestamp()
            if ts > incident_start:
                ramp = min(1.0, (ts - incident_start) / 600.0)
                val = 85.0 + 2715.0 * ramp + _RNG.uniform(-50, 50)
            else:
                val = 85.0 + _RNG.uniform(-10, 10)
            values.append([ts, str(round(val, 2))])

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {
                                "__name__": "http_server_request_duration_seconds",
                                "service": "checkout-service",
                            },
                            "values": values,
                        }
                    ],
                },
            },
        )

    # -- Alerts --

    @staticmethod
    def list_alerts(project_id: str | None = None, **kwargs: Any) -> BaseToolResponse:
        """Return synthetic active alerts."""
        incident_start = _incident_start()

        alerts = []
        for i, alert_def in enumerate(ALERT_DEFS):
            alert = dict(alert_def)
            alert["openTime"] = _iso(incident_start + timedelta(minutes=i * 3))
            alerts.append(alert)

        return BaseToolResponse(status=ToolStatus.SUCCESS, result=alerts)

    @staticmethod
    def list_alert_policies(
        project_id: str | None = None, **kwargs: Any
    ) -> BaseToolResponse:
        """Return synthetic alert policies."""
        return BaseToolResponse(status=ToolStatus.SUCCESS, result=ALERT_POLICIES)

    @staticmethod
    def get_alert(name: str, **kwargs: Any) -> BaseToolResponse:
        """Return a specific synthetic alert by name."""
        incident_start = _incident_start()

        for i, alert_def in enumerate(ALERT_DEFS):
            if alert_def["name"] == name:
                alert = dict(alert_def)
                alert["openTime"] = _iso(incident_start + timedelta(minutes=i * 3))
                return BaseToolResponse(status=ToolStatus.SUCCESS, result=alert)

        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Alert not found: {name}",
        )
