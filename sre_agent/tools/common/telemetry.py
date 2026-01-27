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


# Backwards compatibility alias
configure_logging = setup_telemetry
