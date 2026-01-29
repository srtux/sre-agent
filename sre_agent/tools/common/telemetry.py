"""Telemetry setup for SRE Agent."""

import logging
import os
import sys
from typing import Any


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


def setup_telemetry(level: int = logging.INFO) -> None:
    """Configures basic logging for the SRE Agent.

    Args:
        level: The logging level to use (default: INFO)
    """
    # Override level from env if set
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = getattr(logging, env_level)

    # Simple logging configuration
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    # Silence chatty loggers
    for logger_name in [
        "google.auth",
        "urllib3",
        "grpc",
        "httpcore",
        "httpx",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "✅ Basic monitoring configured (Custom Telemetry/Arize removed)"
    )

    # Setup LangSmith OTel if enabled (local only)
    setup_langsmith_otel()


def setup_langsmith_otel() -> None:
    """Configures OpenTelemetry for LangSmith tracing if enabled locally."""
    if os.environ.get("LANGSMITH_TRACING", "false").lower() != "true":
        return

    # Skip if running in Agent Engine (where native tracing is preferred)
    if os.environ.get("RUNNING_IN_AGENT_ENGINE", "false").lower() == "true":
        return

    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # 1. Setup Resource
        project_name = os.environ.get("LANGSMITH_PROJECT") or os.environ.get(
            "LANGSMITH_PROJECT", "sre-agent"
        )
        resource = Resource.create(
            {
                "service.name": project_name,
            }
        )

        # 2. Setup Provider and Exporter
        # LangSmith OTLP endpoint (HTTP)
        api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get(
            "LANGCHAIN_API_KEY"
        )
        if not api_key:
            logging.getLogger(__name__).warning(
                "⚠️ LANGSMITH_TRACING is true but no API key found."
            )
            return

        exporter = OTLPSpanExporter(
            endpoint="https://api.smith.langchain.com/v1/traces",
            headers={"x-api-key": api_key},
        )

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # 3. Instrument Google ADK
        GoogleADKInstrumentor().instrument()

        logging.getLogger(__name__).info(
            f"✨ LangSmith OpenTelemetry tracing enabled (Project: {project_name})"
        )
    except ImportError:
        logging.getLogger(__name__).debug(
            "LangSmith OTel dependencies missing, skipping."
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to setup LangSmith OTel: {e}")


# Backwards compatibility alias
configure_logging = setup_telemetry
