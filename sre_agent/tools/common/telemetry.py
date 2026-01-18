"""Telemetry setup for SRE Agent using OpenTelemetry and GCP OTLP."""

import logging
import os
import sys
from typing import Any

import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
import grpc
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes


# Filter out the specific warning from google-generativeai types regarding function calls
class _FunctionCallWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return (
            "Warning: there are non-text parts in the response"
            not in record.getMessage()
        )


# Apply filter to root logger and specific GenAI loggers
logging.getLogger().addFilter(_FunctionCallWarningFilter())
logging.getLogger("google.generativeai").addFilter(_FunctionCallWarningFilter())
logging.getLogger("google_genai.types").addFilter(_FunctionCallWarningFilter())
logging.getLogger("google_genai._api_client").addFilter(_FunctionCallWarningFilter())


class EmojiLoggingFilter(logging.Filter):
    """Filter to add emojis to logs from specific libraries for better visibility."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records to add emojis."""
        msg = record.getMessage()

        # LLM Call Starting/Completed (ADK messages)
        if "google_adk" in record.name or "google.adk" in record.name:
            if "Sending out request" in msg:
                record.msg = f"🧠 LLM Call Starting | {record.msg}"
            elif "Response received" in msg:
                record.msg = f"🧠 LLM Call Completed | {record.msg}"
            elif "LLM Request:" in msg or "LLM Response:" in msg:
                if len(msg) > 1000:
                    record.msg = f"{msg[:1000]}... (truncated, original len={len(msg)})"
                    record.args = ()

        # API Call Distinctions (Uvicorn access logs)
        elif "uvicorn.access" in record.name:
            if not record.msg.startswith("🌐"):
                record.msg = f"🌐 API Call | {record.msg}"

        # Tool calls from decorators or MCP
        elif "sre_agent.tools" in record.name:
            if "Tool Call" in msg and "🛠️" not in msg:
                record.msg = f"🛠️  {record.msg}"
            elif "Tool Success" in msg and "✅" not in msg:
                record.msg = f"✅ {record.msg}"
            elif "Tool Failed" in msg and "❌" not in msg:
                record.msg = f"❌ {record.msg}"
            elif "MCP Call" in msg and "🔗" not in msg:
                record.msg = f"🔗 {record.msg}"
            elif "MCP Success" in msg and "✨" not in msg:
                record.msg = f"✨ {record.msg}"

        return True


class GenAiAttributes:
    """GenAI Semantic Conventions (based on GenAI SIG)."""

    SYSTEM = "gen_ai.system"
    REQUEST_MODEL = "gen_ai.request.model"
    REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    REQUEST_TOP_P = "gen_ai.request.top_p"
    RESPONSE_ID = "gen_ai.response.id"
    RESPONSE_MODEL = "gen_ai.response.model"
    RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
    USAGE_PROMPT_TOKENS = "gen_ai.usage.prompt_tokens"
    USAGE_COMPLETION_TOKENS = "gen_ai.usage.completion_tokens"
    USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"


def get_tracer(name: str) -> trace.Tracer:
    """Returns a tracer for the given module name."""
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Returns a meter for the given module name."""
    return metrics.get_meter(name)


def log_tool_call(logger: logging.Logger, func_name: str, **kwargs: Any) -> None:
    """Logs a tool call with arguments, truncating long values.

    Args:
        logger: The logger instance to use.
        func_name: Name of the function being called.
        **kwargs: Arguments to log.
    """
    safe_args = {}
    for k, v in kwargs.items():
        val_str = str(v)
        if len(val_str) > 200:
            safe_args[k] = val_str[:200] + "... (truncated)"
        else:
            safe_args[k] = val_str

    logger.debug(f"Tool Call: {func_name} | Args: {safe_args}")


def _get_gcp_otlp_credentials() -> Any:
    """Get gRPC credentials for Google Cloud OTLP."""
    credentials, _ = google.auth.default()
    request = google.auth.transport.requests.Request()
    return google.auth.transport.grpc.AuthMetadataPlugin(  # type: ignore[no-untyped-call]
        credentials=credentials, request=request
    )


def setup_telemetry(level: int = logging.INFO) -> None:
    """Configures Telemetry (Trace, Metrics, Logs) for the SRE Agent.

    Configures:
    - Traces: OTLP gRPC to telemetry.googleapis.com
    - Metrics: OTLP gRPC to telemetry.googleapis.com
    - Logs: Structured JSON to stdout (for logging.googleapis.com agent)

    Args:
        level: The logging level to use (default: INFO)
    """
    # Override level from env if set
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = getattr(logging, env_level)

    from opentelemetry.instrumentation.logging import LoggingInstrumentor

    # Initialize Trace-Log correlation
    LoggingInstrumentor().instrument(set_logging_format=False)

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

    # Sanitize project_id if it contains commas (common issue with some env loaders)
    if project_id and "," in project_id:
        raw_pid = project_id
        project_id = project_id.split(",")[0].strip()
        print(f"⚠️  Sanitized GOOGLE_CLOUD_PROJECT from '{raw_pid}' to '{project_id}'")
        # Update env var so dependent libs (like google.auth) also see clean value
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

    # 1. Configure OpenTelemetry SDK
    if project_id:
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: "sre-agent",
                "service.namespace": "sre",
                "service.instance.id": os.environ.get("HOSTNAME", "localhost"),
                "cloud.region": os.environ.get("GCP_REGION", "global"),
                "gcp.project_id": project_id,
            }
        )

        # GCP OTLP Endpoint
        otlp_endpoint = "telemetry.googleapis.com:443"

        # Create credentials
        credentials, _ = google.auth.default()

        # Ensure quota project is set to fix INVALID_ARGUMENT errors in OTLP export
        if project_id and hasattr(credentials, "with_quota_project"):
            credentials = credentials.with_quota_project(project_id)
        request = google.auth.transport.requests.Request()

        ssl_creds = grpc.ssl_channel_credentials()
        call_creds = grpc.metadata_call_credentials(
            google.auth.transport.grpc.AuthMetadataPlugin(  # type: ignore[no-untyped-call]
                credentials=credentials, request=request
            )
        )
        composite_creds = grpc.composite_channel_credentials(ssl_creds, call_creds)

        # -- TRACES --
        if os.environ.get("OTEL_TRACES_EXPORTER", "").lower() != "none":
            span_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                credentials=composite_creds,
                headers=(("x-goog-user-project", project_id),),
            )
            span_processor = BatchSpanProcessor(span_exporter)

            # distinct: Check if a TracerProvider is already configured
            current_tracer_provider = trace.get_tracer_provider()
            if hasattr(current_tracer_provider, "add_span_processor"):
                # Provider exists (e.g. from ADK or Agent Engine), just add our exporter
                current_tracer_provider.add_span_processor(span_processor)
            else:
                # No provider yet (or it's a proxy), set ours
                tracer_provider = TracerProvider(resource=resource)
                tracer_provider.add_span_processor(span_processor)
                trace.set_tracer_provider(tracer_provider)

        # -- METRICS --
        if os.environ.get("OTEL_METRICS_EXPORTER", "").lower() != "none":
            metric_exporter = OTLPMetricExporter(
                endpoint=otlp_endpoint,
                credentials=composite_creds,
                headers=(("x-goog-user-project", project_id),),
            )
            reader = PeriodicExportingMetricReader(
                metric_exporter, export_interval_millis=60000
            )

            # The MeterProvider API is less mutable than TracerProvider in some versions,
            # but typically we just set it if we can.
            # There isn't a standard 'add_metric_reader' on the public API of the global getter
            # as reliably as span processor, but we can check.
            # However, typically default is strict.
            # We will try to set it. If it fails/warns, we might lose metrics if we can't attach.
            # SDK MeterProvider has `add_metric_reader`? It's not always exposed publicly on the instance.
            # We'll try to set strict.

            # Actually, opentelemetry.sdk.metrics.MeterProvider DOES NOT support adding readers after init easily
            # in some versions.
            # So we try to initialize a new one and set it.
            meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(meter_provider)

    else:
        # Fallback for local/testing without Project ID
        # Just set up default providers (No-op or simple) if not already set
        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            trace.set_tracer_provider(TracerProvider())
        if not isinstance(metrics.get_meter_provider(), MeterProvider):
            metrics.set_meter_provider(MeterProvider())

    # 2. Configure Logging
    _configure_logging_handlers(level, project_id)


def _configure_logging_handlers(level: int, project_id: str | None) -> None:
    """Internal helper to configure logging handlers."""
    # Silence chatty loggers that produce high-volume debug noise
    for logger_name in [
        "aiosqlite",
        "google.auth.transport.requests",
        "google.auth.transport.grpc",
        "google.auth._default",
        "urllib3.connectionpool",
        "grpc._common",
        "grpc._cython.cygrpc",
        "mcp",
        "asyncio",
        "google.cloud.aiplatform",
        "httpx",
        "httpcore",
    ]:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    log_format = os.environ.get("LOG_FORMAT", "TEXT").upper()

    if log_format == "JSON":

        class JsonFormatter(logging.Formatter):
            """Basic JSON log formatter with OTel correlation."""

            def format(self, record: logging.LogRecord) -> str:
                import json

                # Basic log structure
                log_obj = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "severity": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "func": record.funcName,
                }

                # Add Trace Context if available
                span_context = trace.get_current_span().get_span_context()
                if span_context.is_valid:
                    trace_id = format(span_context.trace_id, "032x")
                    span_id = format(span_context.span_id, "016x")
                    log_obj["trace_id"] = trace_id
                    log_obj["span_id"] = span_id

                    # GCP-specific correlation fields
                    if project_id:
                        log_obj["logging.googleapis.com/trace"] = (
                            f"projects/{project_id}/traces/{trace_id}"
                        )
                        log_obj["logging.googleapis.com/spanId"] = span_id

                # Handle exceptions
                if record.exc_info:
                    log_obj["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_obj)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler.addFilter(EmojiLoggingFilter())
        logging.getLogger().handlers = [handler]
        logging.getLogger().setLevel(level)

    else:
        # Modern text format
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )
        # Add emoji filter to all project loggers and uvicorn
        emoji_filter = EmojiLoggingFilter()

        # Add to root logger handlers
        for h in logging.getLogger().handlers:
            h.addFilter(emoji_filter)

        # Add to specific loggers that might have their own handlers (like uvicorn)
        for logger_name in [
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "google_adk",
            "google.adk",
        ]:
            logger_obj = logging.getLogger(logger_name)
            logger_obj.addFilter(emoji_filter)
            for h in logger_obj.handlers:
                h.addFilter(emoji_filter)

        # Suppress OTLP export errors if they are too noisy and failing
        # These are often due to quota or project ID mismatches in local dev
        if os.environ.get("SUPPRESS_OTEL_ERRORS", "true").lower() == "true":
            logging.getLogger(
                "opentelemetry.exporter.otlp.proto.grpc.exporter"
            ).setLevel(logging.CRITICAL)

        logging.getLogger().setLevel(level)


def set_span_attribute(key: str, value: Any) -> None:
    """Sets an attribute on the current OTel span. Safe to call if no span active."""
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(key, value)


# Backwards compatibility alias
configure_logging = setup_telemetry
