"""
Google Cloud Observability OpenTelemetry Schema Documentation.

This module documents the schema for the _AllSpans table in Google Cloud Observability,
which follows the OpenTelemetry (OTel) convention for distributed tracing.

Reference: https://opentelemetry.io/docs/specs/otel/trace/api/
"""

from typing import TypedDict, Literal, Any


class SpanStatus(TypedDict):
    """Status of a span execution.

    Attributes:
        code: Status code (0=UNSET, 1=OK, 2=ERROR)
        message: Optional status message, usually for errors
    """
    code: int
    message: str


class SpanEvent(TypedDict):
    """Event/log attached to a span.

    Events represent discrete occurrences during a span's lifetime.
    Common uses: exceptions, log messages, annotations.

    Attributes:
        name: Event name (e.g., "exception", "log_message")
        time: When the event occurred
        attributes: JSON key-value pairs with event details
    """
    name: str
    time: str  # TIMESTAMP as ISO string
    attributes: dict[str, Any]


class SpanLink(TypedDict):
    """Link to a causally related span.

    Links connect spans that are related but not in a parent-child relationship.
    Common uses: batch processing, fan-out operations, async messaging.

    Attributes:
        trace_id: Trace ID of the linked span
        span_id: Span ID of the linked span
        trace_state: Trace state at the time of the link
        attributes: JSON key-value pairs describing the link relationship
    """
    trace_id: str
    span_id: str
    trace_state: str
    attributes: dict[str, Any]


class ResourceAttributes(TypedDict, total=False):
    """Resource attributes identifying the service/application.

    Common attributes following OTel semantic conventions:
        service.name: Logical service name
        service.version: Service version
        service.instance.id: Unique instance identifier
        host.name: Hostname
        host.id: Host unique identifier
        cloud.provider: Cloud provider (gcp, aws, azure)
        cloud.region: Cloud region
        k8s.namespace.name: Kubernetes namespace
        k8s.pod.name: Kubernetes pod name
        k8s.deployment.name: Kubernetes deployment name
    """
    pass


class Resource(TypedDict):
    """Information about the service/application that produced the span.

    Attributes:
        attributes: Resource-level attributes (service name, host, etc.)
    """
    attributes: ResourceAttributes


class InstrumentationScope(TypedDict):
    """Information about the instrumentation library.

    Attributes:
        name: Library name (e.g., "opentelemetry.instrumentation.flask")
        version: Library version
        schema_url: URL to the schema version used
    """
    name: str
    version: str
    schema_url: str


# Span kind enumeration
SpanKind = Literal[
    0,  # SPAN_KIND_UNSPECIFIED
    1,  # SPAN_KIND_INTERNAL
    2,  # SPAN_KIND_SERVER
    3,  # SPAN_KIND_CLIENT
    4,  # SPAN_KIND_PRODUCER
    5,  # SPAN_KIND_CONSUMER
]


class SpanAttributes(TypedDict, total=False):
    """Common span attributes following OTel semantic conventions.

    HTTP attributes:
        http.method: HTTP method (GET, POST, etc.)
        http.status_code: HTTP response status code
        http.url: Full HTTP URL
        http.target: HTTP request target
        http.host: HTTP host header
        http.scheme: HTTP scheme (http, https)
        http.user_agent: User agent string
        http.request_content_length: Request body size
        http.response_content_length: Response body size

    RPC attributes:
        rpc.system: RPC system (grpc, java_rmi, etc.)
        rpc.service: Service name
        rpc.method: Method name
        rpc.grpc.status_code: gRPC status code

    Database attributes:
        db.system: Database system (mysql, postgresql, mongodb, etc.)
        db.name: Database name
        db.statement: Database statement/query
        db.operation: Database operation (SELECT, INSERT, etc.)
        db.connection_string: Connection string (sanitized)

    Messaging attributes:
        messaging.system: Messaging system (kafka, rabbitmq, etc.)
        messaging.destination: Destination name (topic, queue)
        messaging.operation: Operation (send, receive, process)
        messaging.message_id: Message identifier

    Error attributes:
        error: Boolean indicating error
        error.type: Error type/class
        error.message: Error message
        error.stack: Stack trace

    Custom attributes:
        Any application-specific attributes
    """
    pass


class OtelSpan(TypedDict):
    """Complete OpenTelemetry span record from Google Cloud Observability.

    This represents a single row in the _AllSpans table.

    Attributes:
        trace_id: Unique identifier for the trace (128-bit, hex string)
        span_id: Unique identifier for this span (64-bit, hex string)
        trace_state: W3C trace state for vendor-specific data propagation
        parent_span_id: Span ID of the parent span (NULL for root spans)
        name: Span name/operation (e.g., "HTTP GET /api/users")
        kind: Span kind (SERVER=2, CLIENT=3, PRODUCER=4, CONSUMER=5, INTERNAL=1)
        start_time: When the span started (TIMESTAMP)
        end_time: When the span ended (TIMESTAMP)
        duration_nano: Span duration in nanoseconds
        attributes: Key-value pairs with span details (http.method, etc.)
        status: Span execution status (code and message)
        events: List of events/logs attached to this span
        links: List of links to causally related spans
        resource: Information about the service that produced this span
        instrumentation_scope: Information about the instrumentation library
    """
    trace_id: str
    span_id: str
    trace_state: str
    parent_span_id: str | None
    name: str
    kind: SpanKind
    start_time: str  # TIMESTAMP as ISO string
    end_time: str    # TIMESTAMP as ISO string
    duration_nano: int
    attributes: SpanAttributes
    status: SpanStatus
    events: list[SpanEvent]
    links: list[SpanLink]
    resource: Resource
    instrumentation_scope: InstrumentationScope


# Query helper constants
SPAN_KIND_NAMES = {
    0: "UNSPECIFIED",
    1: "INTERNAL",
    2: "SERVER",
    3: "CLIENT",
    4: "PRODUCER",
    5: "CONSUMER",
}

STATUS_CODE_NAMES = {
    0: "UNSET",
    1: "OK",
    2: "ERROR",
}

# Common semantic convention attribute keys
class SemanticConventions:
    """OpenTelemetry semantic convention attribute keys."""

    # Service
    SERVICE_NAME = "service.name"
    SERVICE_VERSION = "service.version"
    SERVICE_INSTANCE_ID = "service.instance.id"

    # HTTP
    HTTP_METHOD = "http.method"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_URL = "http.url"
    HTTP_TARGET = "http.target"
    HTTP_HOST = "http.host"
    HTTP_SCHEME = "http.scheme"
    HTTP_USER_AGENT = "http.user_agent"
    HTTP_REQUEST_CONTENT_LENGTH = "http.request_content_length"
    HTTP_RESPONSE_CONTENT_LENGTH = "http.response_content_length"

    # RPC
    RPC_SYSTEM = "rpc.system"
    RPC_SERVICE = "rpc.service"
    RPC_METHOD = "rpc.method"
    RPC_GRPC_STATUS_CODE = "rpc.grpc.status_code"

    # Database
    DB_SYSTEM = "db.system"
    DB_NAME = "db.name"
    DB_STATEMENT = "db.statement"
    DB_OPERATION = "db.operation"

    # Messaging
    MESSAGING_SYSTEM = "messaging.system"
    MESSAGING_DESTINATION = "messaging.destination"
    MESSAGING_OPERATION = "messaging.operation"
    MESSAGING_MESSAGE_ID = "messaging.message_id"

    # Error
    ERROR = "error"
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"
    ERROR_STACK = "error.stack"

    # Host
    HOST_NAME = "host.name"
    HOST_ID = "host.id"

    # Cloud
    CLOUD_PROVIDER = "cloud.provider"
    CLOUD_REGION = "cloud.region"
    CLOUD_ACCOUNT_ID = "cloud.account.id"

    # Kubernetes
    K8S_NAMESPACE_NAME = "k8s.namespace.name"
    K8S_POD_NAME = "k8s.pod.name"
    K8S_DEPLOYMENT_NAME = "k8s.deployment.name"
    K8S_CONTAINER_NAME = "k8s.container.name"


# Example queries using the schema

EXAMPLE_QUERIES = {
    "top_errors_by_service": """
        SELECT
            resource.attributes.service_name as service_name,
            COUNT(*) as error_count,
            ARRAY_AGG(DISTINCT status.message IGNORE NULLS LIMIT 10) as error_messages,
            ARRAY_AGG(DISTINCT name LIMIT 10) as error_operations
        FROM `{project_id}.{dataset_id}._AllSpans`
        WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            AND status.code = 2  -- ERROR
        GROUP BY service_name
        ORDER BY error_count DESC
        LIMIT 20
    """,

    "analyze_spans_with_exceptions": """
        SELECT
            trace_id,
            span_id,
            name,
            resource.attributes.service_name as service_name,
            event.name as exception_type,
            JSON_EXTRACT_SCALAR(event.attributes, '$.exception.message') as exception_message,
            JSON_EXTRACT_SCALAR(event.attributes, '$.exception.stacktrace') as stack_trace
        FROM `{project_id}.{dataset_id}._AllSpans`,
        UNNEST(events) as event
        WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            AND event.name = 'exception'
        LIMIT 100
    """,

    "trace_links_analysis": """
        SELECT
            trace_id,
            span_id,
            name,
            ARRAY_LENGTH(links) as link_count,
            link.trace_id as linked_trace_id,
            link.span_id as linked_span_id,
            JSON_EXTRACT_SCALAR(link.attributes, '$.link.type') as link_type
        FROM `{project_id}.{dataset_id}._AllSpans`,
        UNNEST(links) as link
        WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            AND ARRAY_LENGTH(links) > 0
        LIMIT 100
    """,

    "instrumentation_library_usage": """
        SELECT
            instrumentation_scope.name as library_name,
            instrumentation_scope.version as library_version,
            COUNT(DISTINCT resource.attributes.service_name) as service_count,
            COUNT(*) as span_count
        FROM `{project_id}.{dataset_id}._AllSpans`
        WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        GROUP BY library_name, library_version
        ORDER BY span_count DESC
    """,

    "http_endpoint_latency_with_attributes": """
        SELECT
            JSON_EXTRACT_SCALAR(attributes, '$.http.method') as http_method,
            JSON_EXTRACT_SCALAR(attributes, '$.http.target') as http_target,
            JSON_EXTRACT_SCALAR(attributes, '$.http.status_code') as status_code,
            COUNT(*) as request_count,
            APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(50)] as p50_ms,
            APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(95)] as p95_ms,
            APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(99)] as p99_ms
        FROM `{project_id}.{dataset_id}._AllSpans`
        WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            AND kind = 2  -- SERVER
            AND JSON_EXTRACT_SCALAR(attributes, '$.http.method') IS NOT NULL
        GROUP BY http_method, http_target, status_code
        HAVING request_count >= 10
        ORDER BY p99_ms DESC
        LIMIT 50
    """,
}
