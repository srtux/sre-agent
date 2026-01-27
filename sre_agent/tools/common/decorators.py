"""Decorators for SRE Agent tools with OpenTelemetry instrumentation."""

import functools
import inspect
import logging
import os
import time
from collections.abc import Callable
from typing import Any

from .serialization import normalize_obj

logger = logging.getLogger(__name__)


def adk_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark a function as an ADK tool.

    This decorator provides:
    - OTel Spans for every execution
    - OTel Metrics (count and duration)
    - Standardized Logging of args and results/errors
    - Error handling (ensures errors are logged before raising/returning)

    Example:
        @adk_tool
        async def fetch_trace(trace_id: str) -> dict:
            ...
    """

    def should_skip_logging() -> bool:
        """Check if we should skip logging due to native instrumentation."""
        return (
            os.environ.get(
                "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", ""
            ).lower()
            == "true"
        )

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        start_time = time.time()

        # Log calling
        try:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_str = ", ".join(
                f"{k}={repr(v)[:200]}" for k, v in bound.arguments.items()
            )

            # Full args for debug
            full_arg_str = ", ".join(f"{k}={v!r}" for k, v in bound.arguments.items())
            logger.debug(f"Tool '{tool_name}' FULL ARGS: {full_arg_str}")
        except Exception:
            arg_str = f"args={args}, kwargs={kwargs}"

        if not should_skip_logging():
            logger.info(f"🛠️  Tool Call: '{tool_name}' | Args: {arg_str}")

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Check if the result indicates a tool-level error (e.g. JSON with "error" key)
            is_failed = False
            if isinstance(result, str) and '"error":' in result:
                try:
                    import json

                    data = json.loads(result)
                    if isinstance(data, dict) and "error" in data:
                        is_failed = True
                except Exception:
                    pass
            elif isinstance(result, dict) and "error" in result:
                is_failed = True
            elif (
                hasattr(result, "status")
                and str(getattr(result, "status", "")) == "error"
            ):
                # Handle both string status and Enum status
                is_failed = True
            elif hasattr(result, "error") and getattr(result, "error", None):
                is_failed = True

            if is_failed:
                logger.error(
                    f"❌ Tool Failed (Logical): '{tool_name}' | Result contains error | Duration: {duration_ms:.2f}ms"
                )
            elif not should_skip_logging():
                logger.info(
                    f"✅ Tool Success: '{tool_name}' | Duration: {duration_ms:.2f}ms"
                )

            # Do NOT normalize BaseToolResponse objects, legacy to keep for others
            from sre_agent.schema import BaseToolResponse

            if isinstance(result, BaseToolResponse):
                return result

            # Normalize result (convert GCP types to native Python types)
            return normalize_obj(result)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"❌ Tool Failed: '{tool_name}' | Duration: {duration_ms:.2f}ms | Error: {e}",
                exc_info=True,
            )
            raise e

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        start_time = time.time()

        # Log calling
        try:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_str = ", ".join(
                f"{k}={repr(v)[:200]}" for k, v in bound.arguments.items()
            )

            # Full args for debug
            full_arg_str = ", ".join(f"{k}={v!r}" for k, v in bound.arguments.items())
            logger.debug(f"Tool '{tool_name}' FULL ARGS: {full_arg_str}")
        except Exception:
            arg_str = f"args={args}, kwargs={kwargs}"

        if not should_skip_logging():
            logger.info(f"🛠️  Tool Call: '{tool_name}' | Args: {arg_str}")

        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Check if the result indicates a tool-level error
            is_failed = False
            if isinstance(result, str) and '"error":' in result:
                try:
                    import json

                    data = json.loads(result)
                    if isinstance(data, dict) and "error" in data:
                        is_failed = True
                except Exception:
                    pass
            elif isinstance(result, dict) and "error" in result:
                is_failed = True
            elif (
                hasattr(result, "status")
                and str(getattr(result, "status", "")) == "error"
            ):
                is_failed = True
            elif hasattr(result, "error") and getattr(result, "error", None):
                is_failed = True

            if is_failed:
                logger.error(
                    f"❌ Tool Failed (Logical): '{tool_name}' | Result contains error | Duration: {duration_ms:.2f}ms"
                )
            elif not should_skip_logging():
                logger.info(
                    f"✅ Tool Success: '{tool_name}' | Duration: {duration_ms:.2f}ms"
                )

            # Do NOT normalize BaseToolResponse objects
            from sre_agent.schema import BaseToolResponse

            if isinstance(result, BaseToolResponse):
                return result

            return normalize_obj(result)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"❌ Tool Failed: '{tool_name}' | Duration: {duration_ms:.2f}ms | Error: {e}",
                exc_info=True,
            )
            raise e

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
