"""Telemetry setup for Trace Analyzer leveraging ADK-provided OpenTelemetry."""

import logging
from opentelemetry import trace, metrics

logger = logging.getLogger(__name__)

# Filter out the specific warning from google-generativeai types regarding function calls
class _FunctionCallWarningFilter(logging.Filter):
    def filter(self, record):
        return "Warning: there are non-text parts in the response" not in record.getMessage()

# Apply filter to root logger and google.generativeai logger
logging.getLogger().addFilter(_FunctionCallWarningFilter())
logging.getLogger("google.generativeai").addFilter(_FunctionCallWarningFilter())

def get_tracer(name: str):
    """Returns a tracer for the given module name."""
    return trace.get_tracer(name)

def get_meter(name: str):
    """Returns a meter for the given module name."""
    return metrics.get_meter(name)

def log_tool_call(logger: logging.Logger, func_name: str, **kwargs):
    """
    Logs a tool call with arguments, truncating long values.
    """
    safe_args = {}
    for k, v in kwargs.items():
        val_str = str(v)
        if len(val_str) > 200:
            safe_args[k] = val_str[:200] + "... (truncated)"
        else:
            safe_args[k] = val_str
            
    logger.debug(f"🔧 Tool Call: {func_name} | Args: {safe_args}")

