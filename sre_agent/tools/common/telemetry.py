"""Telemetry setup for SRE Agent using OpenTelemetry and GCP OTLP."""

import logging
import os
import sys
from typing import Any

import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
from opentelemetry import metrics, trace


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
                if len(msg) > 200:
                    record.msg = f"{msg[:200]}... (truncated, original len={len(msg)})"
                    record.args = ()

        # API Call Distinctions (Uvicorn access logs)
        elif "uvicorn.access" in record.name:
            if "GET /health" in msg:
                return False
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
    """Configures OpenTelemetry and Logging for the SRE Agent.

    Args:
        level: The logging level to use (default: INFO)
    """
    import logging
    import os

    from opentelemetry import metrics, trace

    # Override level from env if set
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = getattr(logging, env_level)

    # Strictly enforce clean environment
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")
    if project_id and "," in project_id:
        project_id = project_id.split(",")[0].strip()

    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        if "PROJECT_ID" in os.environ:
            os.environ["PROJECT_ID"] = project_id

    # 1. Configure Logging handlers early to capture initialization logs
    _configure_logging_handlers(level, project_id)

    # 2. Check for DISABLE_TELEMETRY environment variable early
    if os.environ.get("DISABLE_TELEMETRY", "").lower() == "true":
        logging.getLogger(__name__).info(
            "Telemetry setup disabled via DISABLE_TELEMETRY env var"
        )
        return

    # Priority 1: Arize AX
    arize_enabled = False
    if os.environ.get("USE_ARIZE", "").lower() == "true":
        try:
            from arize.otel import register
            from openinference.instrumentation.google_adk import GoogleADKInstrumentor

            space_id = os.environ.get("ARIZE_SPACE_ID")
            api_key = os.environ.get("ARIZE_API_KEY")
            project_name = os.environ.get("ARIZE_PROJECT_NAME", "AutoSRE")

            # Arize consumes GOOGLE_API_KEY for ADK-level tracing
            gemini_key = os.environ.get("GEMINI_API_KEY")
            if gemini_key and not os.environ.get("GOOGLE_API_KEY"):
                os.environ["GOOGLE_API_KEY"] = gemini_key

            if space_id and api_key:
                # 1. Register with Arize AX (sets global TracerProvider)
                arize_tp = register(
                    space_id=space_id,
                    api_key=api_key,
                    project_name=project_name,
                )

                # 2. Instrument Google ADK for Arize AX
                GoogleADKInstrumentor().instrument(tracer_provider=arize_tp)

                logging.getLogger(__name__).info(
                    f"✅ Arize AX enabled (Project: {project_name}). Skipping Google Cloud Trace."
                )
                arize_enabled = True
            else:
                logging.getLogger(__name__).warning(
                    "USE_ARIZE is true but ARIZE_SPACE_ID or ARIZE_API_KEY is missing"
                )
        except ImportError:
            logging.getLogger(__name__).warning(
                "Arize dependencies not found. Please install with 'uv sync --extra arize'"
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to setup Arize: {e}")

    # 3. Initialize Log Correlation (Works with any global TracerProvider)
    try:
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        LoggingInstrumentor().instrument(set_logging_format=False)
    except Exception as e:
        logging.getLogger(__name__).debug(f"LoggingInstrumentor failed: {e}")

    logging.getLogger(__name__).info(
        f"Setting up telemetry with project_id: '{project_id}'"
    )

    if project_id:
        import google.auth
        import google.auth.transport.grpc
        import google.auth.transport.requests
        import grpc
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.semconv.resource import ResourceAttributes

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

        # -- TRACES Sidecar (GCP) --
        # Only set up GCP TracerProvider if Arize hasn't already claimed it
        if (
            not arize_enabled
            and os.environ.get("OTEL_TRACES_EXPORTER", "").lower() != "none"
        ):
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            span_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                credentials=composite_creds,
            )
            span_processor = BatchSpanProcessor(span_exporter)

            current_tp = trace.get_tracer_provider()
            is_proxy = "ProxyTracerProvider" in type(current_tp).__name__

            if is_proxy:
                tp = TracerProvider(resource=resource)
                tp.add_span_processor(span_processor)
                trace.set_tracer_provider(tp)
                logging.getLogger(__name__).info("✅ Google Cloud Trace enabled.")
            else:
                logging.getLogger(__name__).info(
                    f"TracerProvider already set to {type(current_tp).__name__}; skipping GCP Trace setup."
                )

        # -- METRICS --
        if os.environ.get("OTEL_METRICS_EXPORTER", "").lower() != "none":
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            metric_exporter = OTLPMetricExporter(
                endpoint=otlp_endpoint,
                credentials=composite_creds,
            )
            reader = PeriodicExportingMetricReader(
                metric_exporter, export_interval_millis=60000
            )

            try:
                current_mp = metrics.get_meter_provider()
                if "ProxyMeterProvider" in type(current_mp).__name__:
                    mp = MeterProvider(resource=resource, metric_readers=[reader])
                    metrics.set_meter_provider(mp)
                else:
                    logging.getLogger(__name__).info(
                        "Existing MeterProvider found. Skipping GCP metrics sidecar."
                    )
            except Exception as e:
                logging.getLogger(__name__).debug(f"Failed to set MeterProvider: {e}")

    else:
        # Fallback for local/testing without Project ID
        if not arize_enabled:
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.trace import TracerProvider

            if "ProxyTracerProvider" in type(trace.get_tracer_provider()).__name__:
                trace.set_tracer_provider(TracerProvider())
            if "ProxyMeterProvider" in type(metrics.get_meter_provider()).__name__:
                metrics.set_meter_provider(MeterProvider())


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
        "graphviz",
    ]:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    log_format = os.environ.get("LOG_FORMAT", "TEXT").upper()

    if log_format == "JSON":

        class JsonFormatter(logging.Formatter):
            """Basic JSON log formatter with OTel correlation."""

            def format(self, record: logging.LogRecord) -> str:
                from .serialization import json_dumps

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

                return json_dumps(log_obj)

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


class ArizeSessionContext:
    """Context manager that supports both sync and async context protocols.

    This ensures compatibility when used in asynchronous generators or with
    different calling patterns (with vs async with).
    """

    def __init__(self, session_id: str, user_id: str = ""):
        """Initialize the Arize session context.

        Args:
            session_id: The session ID to track.
            user_id: The user ID to track.
        """
        self.session_id = session_id
        self.user_id = user_id
        self.cm: Any = None

    def _get_cm(self) -> Any:
        import contextlib
        import os

        @contextlib.contextmanager
        def _null_context() -> Any:
            yield

        # Constraint: Use ARIZE only when running locally (not in Agent Engine)
        # SRE_AGENT_ID is set in Agent Engine environments.
        is_prod = os.environ.get("SRE_AGENT_ID") is not None
        use_arize = os.environ.get("USE_ARIZE", "").lower() == "true"

        if is_prod or not use_arize:
            return _null_context()

        try:
            from openinference.instrumentation import using_attributes

            return using_attributes(session_id=self.session_id, user_id=self.user_id)
        except ImportError:
            return _null_context()

    def __enter__(self) -> Any:
        """Enter the synchronous context block."""
        self.cm = self._get_cm()
        return self.cm.__enter__()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        """Exit the synchronous context block."""
        if self.cm:
            return self.cm.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self) -> Any:
        """Enter the asynchronous context block."""
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        """Exit the asynchronous context block."""
        return self.__exit__(exc_type, exc_val, exc_tb)


def using_arize_session(session_id: str, user_id: str = "") -> Any:
    """Returns a context manager for Arize session/user attributes.

    Args:
        session_id: The session ID to attach to traces.
        user_id: The user ID to attach to traces.

    Returns:
        A context manager that sets OTel attributes for Arize.
        Supports both synchronous and asynchronous 'with' blocks.
    """
    return ArizeSessionContext(session_id=session_id, user_id=user_id)
