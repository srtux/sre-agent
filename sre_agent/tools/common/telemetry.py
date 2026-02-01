"""Telemetry setup for SRE Agent."""

import logging
import os
import sys
from contextvars import ContextVar
from typing import Any, ClassVar

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

    # Use ColorFormatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Silence chatty loggers
    for logger_name in [
        "google.auth",
        "urllib3",
        "grpc",
        "httpcore",
        "httpx",
        "opentelemetry.instrumentation.google_genai.otel_wrapper",
        "aiosqlite",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "✅ Basic monitoring configured (Custom Telemetry/Arize removed)"
    )

    _TELEMETRY_INITIALIZED = True

    # Setup LangSmith OTel if enabled (local only)
    setup_langsmith_otel()


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


# ============================================================================
# LangSmith Thread/Session Management
# ============================================================================
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
            f"Sent LangSmith feedback: {key}={score or value}"
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
