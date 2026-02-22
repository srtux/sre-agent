"""Telemetry setup for SRE Agent."""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    pass

from dotenv import load_dotenv

# Ensure environment variables are loaded for configuration
load_dotenv()

_TELEMETRY_INITIALIZED = False
_LANGFUSE_OTEL_INITIALIZED = False

# ============================================================================
# Langfuse Context Variables for Thread/Session Tracking
# ============================================================================
# These ContextVars allow thread-safe tracking of session/thread info
# which get added to OTel spans for Langfuse session grouping.

_langfuse_session_id: ContextVar[str | None] = ContextVar(
    "langfuse_session_id", default=None
)
_langfuse_user_id: ContextVar[str | None] = ContextVar("langfuse_user_id", default=None)
_langfuse_metadata: ContextVar[dict[str, Any] | None] = ContextVar(
    "langfuse_metadata", default=None
)
_langfuse_tags: ContextVar[list[str] | None] = ContextVar("langfuse_tags", default=None)


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


class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to logs."""

    # ANSI Escape Codes
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    BLUE = "\x1b[34;20m"
    CYAN = "\x1b[36;20m"
    RESET = "\x1b[0m"

    FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    FORMATS: ClassVar[dict[int, str]] = {
        logging.DEBUG: CYAN
        + "%(asctime)s"
        + RESET
        + " "
        + BLUE
        + "[%(levelname)s]"
        + RESET
        + " %(name)s: %(message)s",
        logging.INFO: CYAN
        + "%(asctime)s"
        + RESET
        + " "
        + GREEN
        + "[%(levelname)s]"
        + RESET
        + " %(name)s: %(message)s",
        logging.WARNING: CYAN
        + "%(asctime)s"
        + RESET
        + " "
        + YELLOW
        + "[%(levelname)s]"
        + RESET
        + " %(name)s: %(message)s",
        logging.ERROR: CYAN
        + "%(asctime)s"
        + RESET
        + " "
        + RED
        + "[%(levelname)s]"
        + RESET
        + " %(name)s: %(message)s",
        logging.CRITICAL: CYAN
        + "%(asctime)s"
        + RESET
        + " "
        + BOLD_RED
        + "[%(levelname)s]"
        + RESET
        + " %(name)s: %(message)s",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        log_fmt = self.FORMATS.get(record.levelno, self.FORMAT)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format for GCP/Agent Engine."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a structured JSON object.

        Includes GCP-specific fields for log correlation with Cloud Trace.
        """
        # Try to get trace and span IDs from OpenTelemetry
        trace_id = None
        span_id = None
        try:
            from opentelemetry import trace

            span_context = trace.get_current_span().get_span_context()
            if span_context.is_valid:
                trace_id = trace.format_trace_id(span_context.trace_id)
                span_id = trace.format_span_id(span_context.span_id)
        except Exception:
            pass

        # Fallback: Check our manual trace_id ContextVar in auth.py
        if not trace_id:
            try:
                from sre_agent.auth import get_trace_id

                trace_id = get_trace_id()
            except Exception:
                pass

        # Build GCP structured log payload
        # See: https://cloud.google.com/logging/docs/agent/logging/configuration#special-fields
        log_data = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
            "name": record.name,
        }

        # Inject trace correlation if available
        if trace_id:
            # Format: projects/[PROJECT_ID]/traces/[TRACE_ID]
            # Since project_id isn't always easily known here, we often just use the hex ID
            # and Cloud Logging often correlates it if it matches the active span.
            # But the full URI is better.
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
                "GCP_PROJECT_ID"
            )
            if project_id:
                log_data["logging.googleapis.com/trace"] = (
                    f"projects/{project_id}/traces/{trace_id}"
                )
            else:
                log_data["logging.googleapis.com/trace"] = trace_id

        if span_id:
            log_data["logging.googleapis.com/spanId"] = span_id

        # Add all extra fields from record
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_telemetry(level: int = logging.INFO) -> None:
    """Configures basic logging for the SRE Agent.

    Args:
        level: The logging level to use (default: INFO)
    """
    global _TELEMETRY_INITIALIZED
    if _TELEMETRY_INITIALIZED:
        return
    # Override level from env if set
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = getattr(logging, env_level)

    # 0. Check if logging is already configured to avoid double-logging
    root_logger = logging.getLogger()
    if root_logger.handlers:
        logging.getLogger(__name__).debug(
            "Logging already configured with handlers. Skipping root handler setup."
        )
    else:
        # Use ColorFormatter or JsonFormatter based on environment
        handler = logging.StreamHandler(sys.stdout)
        log_format = os.environ.get("LOG_FORMAT", "COLOR").upper()
        if log_format == "JSON":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(ColorFormatter())

        root_logger.setLevel(level)
        root_logger.addHandler(handler)

    # Silence chatty loggers
    for logger_name in [
        "google.auth",
        "google.api_core",
        "google.cloud",
        "urllib3",
        "grpc",
        "httpcore",
        "httpx",
        "aiosqlite",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("✅ Basic monitoring configured")

    _TELEMETRY_INITIALIZED = True

    # Bridge OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT to ADK internal env var
    # This ensures that ADK's native tracing honors the standard OTEL toggle
    if (
        os.environ.get(
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
        ).lower()
        == "true"
    ):
        os.environ["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"] = "true"

    # 1. Skip expensive OTel initialization if already handled by Platform/ADK
    # This addresses the "double-initialization" concern in Agent Engine.
    if is_otel_initialized():
        logging.getLogger(__name__).info(
            "🚀 OpenTelemetry already initialized by platform/ADK. Skipping manual setup."
        )
    else:
        # Setup Langfuse OTel if enabled (local only)
        setup_langfuse_otel()

        # Setup local Google Cloud OTel if enabled (via OTEL_TO_CLOUD override)
        setup_google_cloud_otel()

    # 2. Native ADK/GenAI Instrumentation: ALWAYS enable these as they are idempotent
    # and ensure high-fidelity traces regardless of how the exporter is set up.
    try:
        from opentelemetry.instrumentation.google_genai import (
            GoogleGenAiSdkInstrumentor,
        )

        # instrument() is idempotent
        GoogleGenAiSdkInstrumentor().instrument()
        logging.getLogger(__name__).info(
            "✨ Google GenAI Native instrumentation enabled"
        )
    except ImportError:
        logging.getLogger(__name__).debug("GoogleGenAiInstrumentor not found.")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to instrument Google GenAI: {e}")


def is_otel_initialized() -> bool:
    """Checks if OpenTelemetry has already been initialized with a real provider."""
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        # Default providers are ProxyTracerProvider (SDK) or NoOpTracerProvider (API)
        # If it's a real SDK TracerProvider, it's considered initialized.
        from opentelemetry.sdk.trace import TracerProvider

        return isinstance(provider, TracerProvider)
    except (ImportError, Exception):
        return False


def setup_google_cloud_otel() -> None:
    """Configures manual OpenTelemetry for Google Cloud Trace if enabled.

    Used primarily for local development via OTEL_TO_CLOUD=true.
    In production (Agent Engine), this is skipped to avoid conflicts with
    native platform exporters.
    """
    # 1. Skip if running in Agent Engine (where native tracing is preferred)
    if os.environ.get("RUNNING_IN_AGENT_ENGINE", "false").lower() == "true":
        return

    # 2. Check for manual activation flag (local only)
    if os.environ.get("OTEL_TO_CLOUD", "false").lower() != "true":
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # 1. Configure Cloud Trace
        # Check if we already have a TracerProvider
        tracer_provider = trace.get_tracer_provider()
        if not isinstance(tracer_provider, TracerProvider):
            # If default/proxy, create a new one
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create(
                {
                    "service.name": os.environ.get("OTEL_SERVICE_NAME", "sre-agent"),
                    "cloud.platform": "gcp.agent_engine",
                }
            )
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)

        # Add Cloud Trace exporter
        cloud_trace_exporter = CloudTraceSpanExporter()  # type: ignore[no-untyped-call]
        tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))

        logging.getLogger(__name__).info("✨ Google Cloud Trace enabled")

        # 2. Configure Cloud Logging (Optional / via same flag for now)
        # Note: This hijacks the python root logger to send logs to Cloud Logging
        if (
            os.environ.get(
                "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED", "false"
            ).lower()
            == "true"
        ):
            # from opentelemetry.exporter.cloud_logging import CloudLoggingHandler
            # from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            # from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

            # Use Google Cloud's logging handler for direct log export
            # OR use OTel Logging (experimental).
            # Standard practice is often just CloudLoggingHandler from google-cloud-logging
            # But here we are looking at OTel wrapper.
            # Let's verify imports first. opentelemetry-exporter-gcp-logging provides CloudLoggingHandler?
            # Actually opentelemetry.exporter.cloud_logging is correct for the OTel package.

            # Simpler approach: verify if we want FULL OTel logging or just Span links.
            # For now, let's stick to Tracing as it's the primary request.
            # Adding Logging can double-log if not careful with stdout.
            pass

    except ImportError as e:
        logging.getLogger(__name__).warning(
            f"Google Cloud OTel dependencies missing: {e}"
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to setup Google Cloud OTel: {e}")


def bridge_otel_context(
    trace_id: str | None = None,
    span_id: str | None = None,
    trace_flags: str | None = "01",
) -> Any:
    """Bridges a manual trace ID into the OpenTelemetry context.

    This ensures that subsequent spans created by SDKs (like Vertex AI)
    are linked to the original trace from the proxy.

    Args:
        trace_id: 32-char hex trace ID.
        span_id: 16-char hex span ID (parent).
        trace_flags: 2-char hex flags (default "01" for sampled).

    Returns:
        The token for the attached context, which should be detached in `finally`.
    """
    if not trace_id:
        return None

    try:
        from opentelemetry import context as otel_context
        from opentelemetry import trace as otel_trace
        from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

        # 1. Parse IDs
        t_id = int(trace_id, 16)
        # If span_id is missing, generate a deterministic one from trace_id
        # to avoid OTel rejecting a zero span ID.
        if span_id:
            s_id = int(span_id, 16)
        else:
            s_id = int(trace_id[:16], 16)

        # 2. Parse Flags safely
        t_flags = TraceFlags.DEFAULT
        if trace_flags == "01":
            t_flags = TraceFlags.SAMPLED
        elif trace_flags:
            try:
                t_flags = TraceFlags(int(trace_flags, 16))
            except (ValueError, TypeError):
                pass

        # 3. Create SpanContext
        span_context = SpanContext(
            trace_id=t_id,
            span_id=s_id,
            is_remote=True,
            trace_flags=t_flags,  # type: ignore[arg-type]
        )

        # 4. Wrap in a NonRecordingSpan
        span = NonRecordingSpan(span_context)

        # 5. Attach to current context
        parent_context = otel_trace.set_span_in_context(span)
        token = otel_context.attach(parent_context)

        logging.getLogger(__name__).debug(
            f"🌉 Bridged OTel context for trace: {trace_id}"
        )
        return token

    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to bridge OTel context: {e}")
        return None


def setup_langfuse_otel() -> None:
    """Configures OpenTelemetry for Langfuse tracing if enabled locally.

    Uses the OTLP exporter pointed at the Langfuse OTLP endpoint.
    See: https://langfuse.com/integrations/native/opentelemetry
    """
    global _LANGFUSE_OTEL_INITIALIZED
    if _LANGFUSE_OTEL_INITIALIZED:
        return

    val = os.environ.get("LANGFUSE_TRACING", "false").lower()
    if val != "true":
        return

    # Skip if running in Agent Engine (where native tracing is preferred)
    if os.environ.get("RUNNING_IN_AGENT_ENGINE", "false").lower() == "true":
        return

    # Validate keys exist
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        logging.getLogger(__name__).warning(
            "⚠️ LANGFUSE_TRACING is true but LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set."
        )
        return

    # Default to local self-hosted Langfuse; override for cloud
    base_url = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")

    try:
        import base64

        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        # Build Basic auth header for Langfuse OTLP endpoint
        auth_token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
        endpoint = f"{base_url.rstrip('/')}/api/public/otel/v1/traces"
        headers = {"Authorization": f"Basic {auth_token}"}

        # Create TracerProvider (or reuse existing SDK one)
        tracer_provider = trace.get_tracer_provider()
        if not isinstance(tracer_provider, TracerProvider):
            resource = Resource.create(
                {
                    "service.name": os.environ.get("OTEL_SERVICE_NAME", "sre-agent"),
                    "cloud.platform": "gcp.agent_engine",
                }
            )
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)

        # Add Langfuse OTLP exporter
        langfuse_exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers=headers,
        )
        tracer_provider.add_span_processor(SimpleSpanProcessor(langfuse_exporter))

        # Instrument Google ADK to emit OpenTelemetry spans
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument()

        logging.getLogger(__name__).info(
            f"✨ Langfuse OpenTelemetry tracing enabled (Host: {base_url})"
        )
        _LANGFUSE_OTEL_INITIALIZED = True

    except ImportError as e:
        logging.getLogger(__name__).warning(
            f"Langfuse OTel dependencies missing: {e}. "
            "Install with: pip install langfuse opentelemetry-exporter-otlp "
            "openinference-instrumentation-google-adk"
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to setup Langfuse OTel: {e}")


# Use these functions to group traces into sessions in Langfuse.
# See: https://langfuse.com/docs/tracing-features/sessions


def set_langfuse_session(session_id: str) -> None:
    """Set the current Langfuse session ID.

    All subsequent traces will be grouped under this session ID in Langfuse.

    Args:
        session_id: Unique identifier for the conversation/session.
                   Use your ADK session_id for natural grouping.
    """
    _langfuse_session_id.set(session_id)
    _add_session_to_current_span(session_id)


def set_langfuse_user(user_id: str) -> None:
    """Set the current user ID for Langfuse traces.

    This enables user-level analytics and filtering in Langfuse.

    Args:
        user_id: Unique identifier for the user (email, UUID, etc.)
    """
    _langfuse_user_id.set(user_id)
    _add_user_to_current_span(user_id)


def set_langfuse_metadata(metadata: dict[str, Any]) -> None:
    """Set custom metadata for Langfuse traces.

    Metadata can be used for filtering, grouping, and evaluations.

    Args:
        metadata: Dictionary of key-value pairs to attach to traces.
                 Example: {"environment": "production", "version": "1.2.3"}
    """
    _langfuse_metadata.set(metadata)
    _add_metadata_to_current_span(metadata)


def add_langfuse_tags(tags: list[str]) -> None:
    """Add tags to Langfuse traces.

    Tags are useful for categorizing and filtering traces.

    Args:
        tags: List of string tags to attach.
             Example: ["production", "high-priority", "user-reported"]
    """
    current_tags = _langfuse_tags.get() or []
    new_tags = list(set(current_tags + tags))
    _langfuse_tags.set(new_tags)
    _add_tags_to_current_span(new_tags)


def get_langfuse_session() -> str | None:
    """Get the current Langfuse session ID."""
    return _langfuse_session_id.get()


def get_langfuse_user() -> str | None:
    """Get the current Langfuse user ID."""
    return _langfuse_user_id.get()


def get_langfuse_metadata() -> dict[str, Any]:
    """Get the current Langfuse metadata."""
    return _langfuse_metadata.get() or {}


def get_langfuse_tags() -> list[str]:
    """Get the current Langfuse tags."""
    return _langfuse_tags.get() or []


def _add_session_to_current_span(session_id: str) -> None:
    """Add session_id attribute to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            # Langfuse recognizes these attribute keys for session grouping
            span.set_attribute("session_id", session_id)
            span.set_attribute("langfuse.session.id", session_id)
    except Exception:
        pass  # Silently fail if OTel is not available


def _add_user_to_current_span(user_id: str) -> None:
    """Add user_id attribute to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("user_id", user_id)
            span.set_attribute("langfuse.user.id", user_id)
    except Exception:
        pass


def _add_metadata_to_current_span(metadata: dict[str, Any]) -> None:
    """Add metadata attributes to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            for key, value in metadata.items():
                span.set_attribute(f"langfuse.metadata.{key}", str(value))
    except Exception:
        pass


def _add_tags_to_current_span(tags: list[str]) -> None:
    """Add tags to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("langfuse.tags", tags)
    except Exception:
        pass


# ============================================================================
# Langfuse Score/Feedback Utilities
# ============================================================================
# Use these to send user feedback to Langfuse for evaluations.


def send_langfuse_score(
    trace_id: str,
    name: str,
    value: float | str,
    comment: str | None = None,
) -> bool:
    """Send a score to Langfuse for a specific trace.

    This enables evaluations and user feedback tracking.

    Args:
        trace_id: The trace ID to attach the score to.
        name: Score category (e.g., "user_rating", "correctness", "helpfulness")
        value: Numeric score (0-1 scale) or categorical string value
        comment: Optional text feedback

    Returns:
        True if score was sent successfully, False otherwise.
    """
    try:
        from langfuse import Langfuse

        client = Langfuse()
        client.score(  # type: ignore[attr-defined]
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )
        client.flush()
        logging.getLogger(__name__).debug(f"Sent Langfuse score: {name}={value}")
        return True
    except ImportError:
        logging.getLogger(__name__).warning("langfuse not installed, cannot send score")
        return False
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to send Langfuse score: {e}")
        return False


# Backwards compatibility alias
configure_logging = setup_telemetry
