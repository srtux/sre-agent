"""Telemetry setup for SRE Agent using OpenTelemetry."""

import logging
from typing import Any

from opentelemetry import metrics, trace


# Filter out the specific warning from google-generativeai types regarding function calls
class _FunctionCallWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return (
            "Warning: there are non-text parts in the response"
            not in record.getMessage()
        )


# Apply filter to root logger and google.generativeai logger
logging.getLogger().addFilter(_FunctionCallWarningFilter())
logging.getLogger("google.generativeai").addFilter(_FunctionCallWarningFilter())


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


def configure_logging(level: int = logging.INFO) -> None:
    """Configures standardized logging for the SRE Agent.

    If LOG_FORMAT=JSON environment variable is set, it will attempt to
    output logs in a structured JSON format suitable for GCP Cloud Logging.

    Args:
        level: The logging level to use (default: INFO)
    """
    import os
    import sys

    log_format = os.environ.get("LOG_FORMAT", "TEXT").upper()

    if log_format == "JSON":
        # Simple JSON formatter if no external library is used
        class JsonFormatter(logging.Formatter):
            """Basic JSON log formatter."""

            def format(self, record: logging.LogRecord) -> str:
                import json

                log_obj = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "severity": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "func": record.funcName,
                }
                if record.exc_info:
                    log_obj["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_obj)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logging.getLogger().handlers = [handler]
    else:
        # Modern text format
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )

    logging.getLogger().setLevel(level)
