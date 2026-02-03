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
_LANGSMITH_OTEL_INITIALIZED = False

# ============================================================================
# LangSmith Context Variables for Thread/Session Tracking
# ============================================================================
# These ContextVars allow thread-safe tracking of session/thread info
# which get added to OTel spans for LangSmith thread grouping.

_langsmith_session_id: ContextVar[str | None] = ContextVar(
    "langsmith_session_id", default=None
)
_langsmith_user_id: ContextVar[str | None] = ContextVar(
    "langsmith_user_id", default=None
)
_langsmith_metadata: ContextVar[dict[str, Any] | None] = ContextVar(
    "langsmith_metadata", default=None
)
_langsmith_tags: ContextVar[list[str] | None] = ContextVar(
    "langsmith_tags", default=None
)


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
        # Setup LangSmith OTel if enabled (local only)
        setup_langsmith_otel()

        # Setup local Google Cloud OTel if enabled (via OTEL_TO_CLOUD override)
        setup_google_cloud_otel()

    # 2. Native ADK/GenAI Instrumentation: ALWAYS enable these as they are idempotent
    # and ensure high-fidelity traces regardless of how the exporter is set up.
    try:
        from opentelemetry.instrumentation.google_genai import (
            GoogleGenAiInstrumentor,
        )

        # instrument() is idempotent
        GoogleGenAiInstrumentor().instrument()
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
                {"service.name": os.environ.get("OTEL_SERVICE_NAME", "sre-agent")}
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


def setup_langsmith_otel() -> None:
    """Configures OpenTelemetry for LangSmith tracing if enabled locally.

    Uses the official langsmith.integrations.otel.configure() approach
    per https://docs.langchain.com/langsmith/trace-with-google-adk
    """
    global _LANGSMITH_OTEL_INITIALIZED
    if _LANGSMITH_OTEL_INITIALIZED:
        return

    val = os.environ.get("LANGSMITH_TRACING", "false").lower()
    if val != "true":
        return

    # Skip if running in Agent Engine (where native tracing is preferred)
    if os.environ.get("RUNNING_IN_AGENT_ENGINE", "false").lower() == "true":
        return

    # Validate API key exists
    api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        logging.getLogger(__name__).warning(
            "⚠️ LANGSMITH_TRACING is true but no API key found (LANGSMITH_API_KEY)."
        )
        return

    project_name = os.environ.get("LANGSMITH_PROJECT", "sre-agent")

    try:
        # Use the official LangSmith OTEL integration - this handles everything
        from langsmith.integrations.otel import configure

        # Configure LangSmith tracing - this sets up TracerProvider and exporters
        configure(project_name=project_name)

        # Instrument Google ADK to emit OpenTelemetry spans
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument()

        logging.getLogger(__name__).info(
            f"✨ LangSmith OpenTelemetry tracing enabled (Project: {project_name})"
        )
        _LANGSMITH_OTEL_INITIALIZED = True

    except ImportError as e:
        logging.getLogger(__name__).warning(
            f"LangSmith OTel dependencies missing: {e}. "
            "Install with: pip install langsmith openinference-instrumentation-google-adk"
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to setup LangSmith OTel: {e}")


# Use these functions to group traces into conversations (threads) in LangSmith.
# See: https://docs.langchain.com/langsmith/threads


def set_langsmith_session(session_id: str) -> None:
    """Set the current LangSmith session/thread ID.

    All subsequent traces will be grouped under this session ID in LangSmith,
    appearing as a single "thread" or "conversation".

    Args:
        session_id: Unique identifier for the conversation/thread.
                   Use your ADK session_id for natural grouping.
    """
    _langsmith_session_id.set(session_id)
    _add_session_to_current_span(session_id)


def set_langsmith_user(user_id: str) -> None:
    """Set the current user ID for LangSmith traces.

    This enables user-level analytics and filtering in LangSmith.

    Args:
        user_id: Unique identifier for the user (email, UUID, etc.)
    """
    _langsmith_user_id.set(user_id)
    _add_user_to_current_span(user_id)


def set_langsmith_metadata(metadata: dict[str, Any]) -> None:
    """Set custom metadata for LangSmith traces.

    Metadata can be used for filtering, grouping, and online evaluations.

    Args:
        metadata: Dictionary of key-value pairs to attach to traces.
                 Example: {"environment": "production", "version": "1.2.3"}
    """
    _langsmith_metadata.set(metadata)
    _add_metadata_to_current_span(metadata)


def add_langsmith_tags(tags: list[str]) -> None:
    """Add tags to LangSmith traces.

    Tags are useful for categorizing and filtering traces.

    Args:
        tags: List of string tags to attach.
             Example: ["production", "high-priority", "user-reported"]
    """
    current_tags = _langsmith_tags.get() or []
    new_tags = list(set(current_tags + tags))
    _langsmith_tags.set(new_tags)
    _add_tags_to_current_span(new_tags)


def get_langsmith_session() -> str | None:
    """Get the current LangSmith session ID."""
    return _langsmith_session_id.get()


def get_langsmith_user() -> str | None:
    """Get the current LangSmith user ID."""
    return _langsmith_user_id.get()


def get_langsmith_metadata() -> dict[str, Any]:
    """Get the current LangSmith metadata."""
    return _langsmith_metadata.get() or {}


def get_langsmith_tags() -> list[str]:
    """Get the current LangSmith tags."""
    return _langsmith_tags.get() or []


def _add_session_to_current_span(session_id: str) -> None:
    """Add session_id attribute to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            # LangSmith recognizes these metadata keys for thread grouping
            span.set_attribute("session_id", session_id)
            span.set_attribute("thread_id", session_id)
            span.set_attribute("langsmith.session_id", session_id)
    except Exception:
        pass  # Silently fail if OTel is not available


def _add_user_to_current_span(user_id: str) -> None:
    """Add user_id attribute to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("user_id", user_id)
            span.set_attribute("langsmith.user_id", user_id)
    except Exception:
        pass


def _add_metadata_to_current_span(metadata: dict[str, Any]) -> None:
    """Add metadata attributes to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            for key, value in metadata.items():
                # Prefix with langsmith. for clarity
                span.set_attribute(f"langsmith.metadata.{key}", str(value))
    except Exception:
        pass


def _add_tags_to_current_span(tags: list[str]) -> None:
    """Add tags to the current OTel span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("langsmith.tags", tags)
    except Exception:
        pass


# ============================================================================
# LangSmith Feedback Utilities
# ============================================================================
# Use these to send user feedback to LangSmith for online evaluations.


def send_langsmith_feedback(
    run_id: str,
    key: str,
    score: float | None = None,
    value: str | None = None,
    comment: str | None = None,
) -> bool:
    """Send feedback to LangSmith for a specific run.

    This enables online evaluations and user feedback tracking.

    Args:
        run_id: The LangSmith run ID to attach feedback to.
        key: Feedback category (e.g., "user_rating", "correctness", "helpfulness")
        score: Numeric score (0-1 scale recommended)
        value: Categorical value (e.g., "thumbs_up", "thumbs_down")
        comment: Optional text feedback

    Returns:
        True if feedback was sent successfully, False otherwise.
    """
    try:
        from langsmith import Client

        client = Client()
        client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            value=value,
            comment=comment,
        )
        logging.getLogger(__name__).debug(
            f"Sent LangSmith feedback: {key}={score if score is not None else value}"
        )
        return True
    except ImportError:
        logging.getLogger(__name__).warning(
            "langsmith not installed, cannot send feedback"
        )
        return False
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to send LangSmith feedback: {e}")
        return False


# Backwards compatibility alias
configure_logging = setup_telemetry
