"""Scenario definitions for synthetic telemetry data.

Defines the "Cymbal Shops" e-commerce application running on GKE,
with an active checkout latency incident caused by DB connection pool
exhaustion after a deployment introduced an N+1 query bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Project & Cluster
# ---------------------------------------------------------------------------
DEMO_PROJECT_ID = "cymbal-shops-demo"
DEMO_CLUSTER_NAME = "cymbal-shops-prod"
DEMO_CLUSTER_LOCATION = "us-central1"
DEMO_REGION = "us-central1"

# ---------------------------------------------------------------------------
# Service Definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServiceDef:
    """Definition of a microservice in the demo scenario."""

    name: str
    display_name: str
    resource_type: str  # k8s_container, cloud_run_revision, cloudsql_database
    health: str  # healthy, degraded, unhealthy
    namespace: str = "default"
    replicas: int = 3
    latency_ms_p50: float = 25.0
    latency_ms_p99: float = 80.0
    error_rate: float = 0.001
    rps: float = 500.0
    connections: list[str] = field(default_factory=list)


SERVICES: dict[str, ServiceDef] = {
    "frontend": ServiceDef(
        name="frontend",
        display_name="Frontend (Next.js)",
        resource_type="k8s_container",
        health="healthy",
        namespace="frontend",
        replicas=4,
        latency_ms_p50=35.0,
        latency_ms_p99=120.0,
        rps=2200.0,
        connections=["api-gateway"],
    ),
    "api-gateway": ServiceDef(
        name="api-gateway",
        display_name="API Gateway (Envoy)",
        resource_type="k8s_container",
        health="healthy",
        namespace="gateway",
        replicas=3,
        latency_ms_p50=12.0,
        latency_ms_p99=45.0,
        rps=1800.0,
        connections=[
            "product-catalog",
            "cart-service",
            "checkout-service",
            "recommendation-service",
        ],
    ),
    "product-catalog": ServiceDef(
        name="product-catalog",
        display_name="Product Catalog",
        resource_type="k8s_container",
        health="healthy",
        namespace="catalog",
        replicas=3,
        latency_ms_p50=18.0,
        latency_ms_p99=55.0,
        rps=1200.0,
        connections=["redis-cache"],
    ),
    "cart-service": ServiceDef(
        name="cart-service",
        display_name="Cart Service",
        resource_type="k8s_container",
        health="healthy",
        namespace="cart",
        replicas=2,
        latency_ms_p50=15.0,
        latency_ms_p99=40.0,
        rps=800.0,
        connections=["redis-cache"],
    ),
    "checkout-service": ServiceDef(
        name="checkout-service",
        display_name="Checkout Service",
        resource_type="k8s_container",
        health="degraded",
        namespace="checkout",
        replicas=4,
        latency_ms_p50=450.0,  # Degraded!
        latency_ms_p99=2800.0,  # Degraded!
        error_rate=0.052,  # Elevated
        rps=600.0,
        connections=[
            "order-db",
            "payment-service",
            "shipping-service",
            "email-service",
        ],
    ),
    "payment-service": ServiceDef(
        name="payment-service",
        display_name="Payment Service",
        resource_type="cloud_run_revision",
        health="healthy",
        namespace="",  # Cloud Run
        replicas=0,  # auto-scaled
        latency_ms_p50=85.0,
        latency_ms_p99=200.0,
        rps=400.0,
        connections=[],
    ),
    "recommendation-service": ServiceDef(
        name="recommendation-service",
        display_name="Recommendation Service",
        resource_type="k8s_container",
        health="healthy",
        namespace="recommendations",
        replicas=2,
        latency_ms_p50=22.0,
        latency_ms_p99=60.0,
        rps=900.0,
        connections=["redis-cache"],
    ),
    "shipping-service": ServiceDef(
        name="shipping-service",
        display_name="Shipping Service",
        resource_type="k8s_container",
        health="healthy",
        namespace="shipping",
        replicas=2,
        latency_ms_p50=30.0,
        latency_ms_p99=95.0,
        rps=350.0,
        connections=[],
    ),
    "email-service": ServiceDef(
        name="email-service",
        display_name="Email Service",
        resource_type="cloud_run_revision",
        health="healthy",
        namespace="",
        replicas=0,
        latency_ms_p50=40.0,
        latency_ms_p99=150.0,
        rps=200.0,
        connections=[],
    ),
    "order-db": ServiceDef(
        name="order-db",
        display_name="Order DB (Cloud SQL)",
        resource_type="cloudsql_database",
        health="unhealthy",
        namespace="",
        replicas=1,
        latency_ms_p50=850.0,  # Very slow
        latency_ms_p99=4500.0,  # Critical
        error_rate=0.12,
        rps=300.0,
        connections=[],
    ),
    "redis-cache": ServiceDef(
        name="redis-cache",
        display_name="Redis Cache (Memorystore)",
        resource_type="redis_instance",
        health="healthy",
        namespace="",
        replicas=1,
        latency_ms_p50=2.0,
        latency_ms_p99=8.0,
        rps=5000.0,
        connections=[],
    ),
}

# ---------------------------------------------------------------------------
# Pod names (deterministic for cross-referencing)
# ---------------------------------------------------------------------------
POD_NAMES: dict[str, list[str]] = {
    "frontend": [
        "frontend-7d8f9c6b5-xk2p4",
        "frontend-7d8f9c6b5-m3n7q",
        "frontend-7d8f9c6b5-abc12",
        "frontend-7d8f9c6b5-def34",
    ],
    "api-gateway": [
        "api-gateway-5b4c3d2e1-qr5t6",
        "api-gateway-5b4c3d2e1-uv7w8",
        "api-gateway-5b4c3d2e1-yz9a0",
    ],
    "checkout-service": [
        "checkout-service-6a5b4c3d2-hj8k9",
        "checkout-service-6a5b4c3d2-lm2n3",
        "checkout-service-6a5b4c3d2-op4q5",
        "checkout-service-6a5b4c3d2-rs6t7",
    ],
    "product-catalog": [
        "product-catalog-8c7d6e5f4-wx1y2",
        "product-catalog-8c7d6e5f4-za3b4",
        "product-catalog-8c7d6e5f4-cd5e6",
    ],
    "cart-service": [
        "cart-service-9d8e7f6g5-fg7h8",
        "cart-service-9d8e7f6g5-ij9k0",
    ],
    "recommendation-service": [
        "recommendation-svc-3e2f1g0h9-mn1o2",
        "recommendation-svc-3e2f1g0h9-pq3r4",
    ],
    "shipping-service": [
        "shipping-service-4f3g2h1i0-st5u6",
        "shipping-service-4f3g2h1i0-vw7x8",
    ],
}

# ---------------------------------------------------------------------------
# Deterministic trace & span IDs (seeded so agent can cross-reference)
# ---------------------------------------------------------------------------
# These are fixed IDs so the synthetic logs, traces, and alerts all correlate.
TRACE_IDS = {
    "checkout_slow_1": "a1b2c3d4e5f6789012345678abcdef01",
    "checkout_slow_2": "b2c3d4e5f6789012345678abcdef0102",
    "checkout_error_1": "c3d4e5f6789012345678abcdef010203",
    "checkout_healthy": "d4e5f6789012345678abcdef01020304",
    "product_healthy": "e5f6789012345678abcdef0102030405",
    "cart_healthy": "f6789012345678abcdef010203040506",
    "payment_flow": "0789012345678abcdef01020304050607",
    "recommendation": "1890123456789abcdef0102030405060a",
}

# ---------------------------------------------------------------------------
# Alert definitions
# ---------------------------------------------------------------------------
ALERT_DEFS: list[dict[str, Any]] = [
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alerts/alert-checkout-latency-001",
        "policy": {
            "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-latency-slo",
            "displayName": "Checkout Service P99 Latency SLO Breach",
        },
        "state": "OPEN",
        "severity": "CRITICAL",
        "openTime": None,  # Filled dynamically
        "resource": {
            "type": "k8s_container",
            "labels": {
                "project_id": DEMO_PROJECT_ID,
                "cluster_name": DEMO_CLUSTER_NAME,
                "namespace_name": "checkout",
                "container_name": "checkout-service",
            },
        },
        "metric": {
            "type": "custom.googleapis.com/http/server/latency",
            "labels": {"service_name": "checkout-service"},
        },
        "url": "https://console.cloud.google.com/monitoring/alerting",
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alerts/alert-checkout-errors-002",
        "policy": {
            "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-error-rate",
            "displayName": "Checkout Service Error Rate > 5%",
        },
        "state": "OPEN",
        "severity": "ERROR",
        "openTime": None,
        "resource": {
            "type": "k8s_container",
            "labels": {
                "project_id": DEMO_PROJECT_ID,
                "cluster_name": DEMO_CLUSTER_NAME,
                "namespace_name": "checkout",
                "container_name": "checkout-service",
            },
        },
        "metric": {
            "type": "custom.googleapis.com/http/server/error_rate",
            "labels": {"service_name": "checkout-service"},
        },
        "url": "https://console.cloud.google.com/monitoring/alerting",
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alerts/alert-db-connections-003",
        "policy": {
            "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-db-pool",
            "displayName": "Order DB Connection Pool Saturation > 95%",
        },
        "state": "OPEN",
        "severity": "CRITICAL",
        "openTime": None,
        "resource": {
            "type": "cloudsql_database",
            "labels": {
                "project_id": DEMO_PROJECT_ID,
                "database_id": f"{DEMO_PROJECT_ID}:order-db-prod",
                "region": DEMO_REGION,
            },
        },
        "metric": {
            "type": "cloudsql.googleapis.com/database/postgresql/num_backends",
            "labels": {"database": "orders"},
        },
        "url": "https://console.cloud.google.com/monitoring/alerting",
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alerts/alert-frontend-degraded-004",
        "policy": {
            "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-frontend-latency",
            "displayName": "Frontend Latency Degradation (Upstream)",
        },
        "state": "OPEN",
        "severity": "WARNING",
        "openTime": None,
        "resource": {
            "type": "k8s_container",
            "labels": {
                "project_id": DEMO_PROJECT_ID,
                "cluster_name": DEMO_CLUSTER_NAME,
                "namespace_name": "frontend",
                "container_name": "frontend",
            },
        },
        "metric": {
            "type": "custom.googleapis.com/http/server/latency",
            "labels": {"service_name": "frontend"},
        },
        "url": "https://console.cloud.google.com/monitoring/alerting",
    },
]

# ---------------------------------------------------------------------------
# Alert policy definitions
# ---------------------------------------------------------------------------
ALERT_POLICIES: list[dict[str, Any]] = [
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-latency-slo",
        "display_name": "Checkout Service P99 Latency SLO Breach",
        "documentation": {
            "content": "Triggers when checkout-service p99 latency exceeds 500ms for 5 minutes.",
            "mime_type": "text/markdown",
        },
        "user_labels": {"team": "checkout", "severity": "critical"},
        "conditions": [
            {
                "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-latency-slo/conditions/cond-1",
                "display_name": "P99 latency > 500ms for 5m",
            }
        ],
        "enabled": True,
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-error-rate",
        "display_name": "Checkout Service Error Rate > 5%",
        "documentation": {
            "content": "Triggers when checkout-service 5xx error rate exceeds 5% for 3 minutes.",
            "mime_type": "text/markdown",
        },
        "user_labels": {"team": "checkout", "severity": "high"},
        "conditions": [
            {
                "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-error-rate/conditions/cond-1",
                "display_name": "Error rate > 5% for 3m",
            }
        ],
        "enabled": True,
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-db-pool",
        "display_name": "Order DB Connection Pool Saturation > 95%",
        "documentation": {
            "content": "Triggers when PostgreSQL active connections exceed 95% of max_connections.",
            "mime_type": "text/markdown",
        },
        "user_labels": {"team": "platform", "severity": "critical"},
        "conditions": [
            {
                "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-db-pool/conditions/cond-1",
                "display_name": "Connection utilization > 95%",
            }
        ],
        "enabled": True,
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-frontend-latency",
        "display_name": "Frontend Latency Degradation (Upstream)",
        "documentation": {
            "content": "Triggers when frontend p99 latency exceeds 2x baseline due to upstream issues.",
            "mime_type": "text/markdown",
        },
        "user_labels": {"team": "frontend", "severity": "warning"},
        "conditions": [
            {
                "name": f"projects/{DEMO_PROJECT_ID}/alertPolicies/policy-frontend-latency/conditions/cond-1",
                "display_name": "P99 latency > 2x baseline for 5m",
            }
        ],
        "enabled": True,
    },
]

# ---------------------------------------------------------------------------
# Log templates
# ---------------------------------------------------------------------------
LOG_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "checkout_errors": [
        {
            "severity": "ERROR",
            "payload": {
                "message": "Connection pool exhausted: all 100 connections in use",
                "error_code": "POOL_EXHAUSTED",
                "pool_size": 100,
                "active_connections": 100,
                "waiting_requests": 47,
                "service": "checkout-service",
            },
            "service": "checkout-service",
            "pod_index": 0,
        },
        {
            "severity": "ERROR",
            "payload": {
                "message": "Failed to acquire database connection within timeout (5000ms)",
                "error_code": "CONNECTION_TIMEOUT",
                "timeout_ms": 5000,
                "pool_utilization": 1.0,
                "service": "checkout-service",
            },
            "service": "checkout-service",
            "pod_index": 1,
        },
        {
            "severity": "ERROR",
            "payload": {
                "message": "Order creation failed: database connection unavailable",
                "error_code": "DB_UNAVAILABLE",
                "order_id": "ord-demo-78923",
                "user_id": "user-demo-4521",
                "retry_count": 3,
                "service": "checkout-service",
            },
            "service": "checkout-service",
            "pod_index": 2,
        },
        {
            "severity": "CRITICAL",
            "payload": {
                "message": "Circuit breaker OPEN for order-db: 15 consecutive failures",
                "error_code": "CIRCUIT_BREAKER_OPEN",
                "target": "order-db.internal:5432",
                "failure_count": 15,
                "threshold": 10,
                "reset_timeout_seconds": 30,
                "service": "checkout-service",
            },
            "service": "checkout-service",
            "pod_index": 0,
        },
    ],
    "checkout_warnings": [
        {
            "severity": "WARNING",
            "payload": "Slow query detected: SELECT * FROM orders WHERE user_id=$1 "
            "AND status IN ($2,$3,$4) - duration 2340ms (threshold: 200ms)",
            "service": "checkout-service",
            "pod_index": 1,
        },
        {
            "severity": "WARNING",
            "payload": {
                "message": "High latency detected for POST /api/v1/checkout",
                "latency_ms": 2850,
                "threshold_ms": 500,
                "endpoint": "/api/v1/checkout",
                "method": "POST",
                "service": "checkout-service",
            },
            "service": "checkout-service",
            "pod_index": 3,
        },
        {
            "severity": "WARNING",
            "payload": "Connection pool utilization at 98% (98/100 active connections)",
            "service": "checkout-service",
            "pod_index": 2,
        },
    ],
    "db_errors": [
        {
            "severity": "ERROR",
            "payload": {
                "message": "too many clients already: max_connections=100, active=100",
                "error_code": "53300",
                "detail": "FATAL: sorry, too many clients already",
                "database": "orders",
                "user": "checkout-svc",
            },
            "service": "order-db",
            "pod_index": 0,
        },
        {
            "severity": "WARNING",
            "payload": {
                "message": "Slow query log: duration 3420ms - "
                "SELECT o.*, oi.* FROM orders o JOIN order_items oi "
                "ON o.id = oi.order_id WHERE o.user_id = $1",
                "query_duration_ms": 3420,
                "rows_examined": 45000,
                "rows_returned": 23,
                "database": "orders",
            },
            "service": "order-db",
            "pod_index": 0,
        },
    ],
    "deployment_event": [
        {
            "severity": "INFO",
            "payload": {
                "message": "Deployment checkout-service v2.14.0 rolled out successfully",
                "deployment": "checkout-service",
                "version": "v2.14.0",
                "replicas": 4,
                "strategy": "RollingUpdate",
                "image": "gcr.io/cymbal-shops-demo/checkout-service:v2.14.0",
                "changelog": "Added order history aggregation endpoint",
            },
            "service": "checkout-service",
            "pod_index": 0,
        },
    ],
    "healthy_services": [
        {
            "severity": "INFO",
            "payload": {
                "message": "Request processed successfully",
                "request_id": "req-demo-12345",
                "method": "GET",
                "path": "/api/v1/products",
                "status": 200,
                "duration_ms": 18,
                "service": "product-catalog",
            },
            "service": "product-catalog",
            "pod_index": 0,
        },
        {
            "severity": "INFO",
            "payload": {
                "message": "Cache hit for product listing",
                "cache_key": "products:featured:page1",
                "ttl_remaining_s": 245,
                "service": "product-catalog",
            },
            "service": "product-catalog",
            "pod_index": 1,
        },
        {
            "severity": "INFO",
            "payload": {
                "message": "Cart updated",
                "user_id": "user-demo-8834",
                "cart_items": 3,
                "total_cents": 8997,
                "service": "cart-service",
            },
            "service": "cart-service",
            "pod_index": 0,
        },
        {
            "severity": "INFO",
            "payload": {
                "message": "Payment processed via Stripe",
                "payment_id": "pay-demo-56789",
                "amount_cents": 8997,
                "currency": "USD",
                "status": "succeeded",
                "service": "payment-service",
            },
            "service": "payment-service",
            "pod_index": 0,
        },
    ],
}

# ---------------------------------------------------------------------------
# Metric descriptors for the demo project
# ---------------------------------------------------------------------------
METRIC_DESCRIPTORS: list[dict[str, Any]] = [
    {
        "name": f"projects/{DEMO_PROJECT_ID}/metricDescriptors/custom.googleapis.com/http/server/latency",
        "type": "custom.googleapis.com/http/server/latency",
        "metric_kind": "GAUGE",
        "value_type": "DOUBLE",
        "unit": "ms",
        "description": "HTTP server request latency in milliseconds",
        "display_name": "HTTP Server Latency",
        "labels": [
            {"key": "service_name", "description": "Name of the service"},
            {"key": "method", "description": "HTTP method"},
            {"key": "status_code", "description": "HTTP status code"},
        ],
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/metricDescriptors/custom.googleapis.com/http/server/error_rate",
        "type": "custom.googleapis.com/http/server/error_rate",
        "metric_kind": "GAUGE",
        "value_type": "DOUBLE",
        "unit": "%",
        "description": "HTTP server error rate as percentage",
        "display_name": "HTTP Error Rate",
        "labels": [
            {"key": "service_name", "description": "Name of the service"},
        ],
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/metricDescriptors/kubernetes.io/container/cpu/core_usage_time",
        "type": "kubernetes.io/container/cpu/core_usage_time",
        "metric_kind": "CUMULATIVE",
        "value_type": "DOUBLE",
        "unit": "s",
        "description": "Cumulative CPU core usage",
        "display_name": "Container CPU Usage",
        "labels": [],
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/metricDescriptors/kubernetes.io/container/memory/used_bytes",
        "type": "kubernetes.io/container/memory/used_bytes",
        "metric_kind": "GAUGE",
        "value_type": "INT64",
        "unit": "By",
        "description": "Memory usage in bytes",
        "display_name": "Container Memory Usage",
        "labels": [],
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/metricDescriptors/cloudsql.googleapis.com/database/postgresql/num_backends",
        "type": "cloudsql.googleapis.com/database/postgresql/num_backends",
        "metric_kind": "GAUGE",
        "value_type": "INT64",
        "unit": "1",
        "description": "Number of active PostgreSQL backends (connections)",
        "display_name": "PostgreSQL Active Connections",
        "labels": [
            {"key": "database", "description": "Database name"},
        ],
    },
    {
        "name": f"projects/{DEMO_PROJECT_ID}/metricDescriptors/run.googleapis.com/request_latencies",
        "type": "run.googleapis.com/request_latencies",
        "metric_kind": "DELTA",
        "value_type": "DISTRIBUTION",
        "unit": "ms",
        "description": "Cloud Run request latency distribution",
        "display_name": "Cloud Run Request Latency",
        "labels": [
            {"key": "service_name", "description": "Cloud Run service name"},
        ],
    },
]
