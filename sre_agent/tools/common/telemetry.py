"""Telemetry setup for SRE Agent."""

import json as json_mod
import logging
import os
import sys
from typing import Any


class _StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON for Cloud Logging.

    Cloud Logging automatically parses JSON payloads written to stdout,
    mapping ``severity``, ``message``, ``time``, and other well-known
    fields.  See https://cloud.google.com/logging/docs/structured-logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
            "logger": record.name,
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json_mod.dumps(log_entry, default=str)


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
    """Configures logging for the SRE Agent.

    When ``LOG_FORMAT=JSON`` is set (e.g. in Agent Engine / Cloud Run),
    logs are emitted as structured JSON so that Cloud Logging can parse
    severity, source location and message automatically.

    Args:
        level: The logging level to use (default: INFO)
    """
    # Override level from env if set
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = getattr(logging, env_level)

    use_json = os.environ.get("LOG_FORMAT", "").upper() == "JSON"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers when setup_telemetry is called more
    # than once (e.g. from both agent.py module-level and create_app).
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if use_json:
            handler.setFormatter(_StructuredJsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
            )
        root_logger.addHandler(handler)

    # Silence chatty loggers
    for logger_name in [
        "google.auth",
        "urllib3",
        "grpc",
        "httpcore",
        "httpx",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    fmt_label = "JSON (Cloud Logging)" if use_json else "TEXT"
    logging.getLogger(__name__).info(
        f"Logging configured: format={fmt_label}, level={logging.getLevelName(level)}"
    )


# Backwards compatibility alias
configure_logging = setup_telemetry
