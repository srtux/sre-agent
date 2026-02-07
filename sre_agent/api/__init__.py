"""SRE Agent API module.

This module provides modular FastAPI routers refactored from the monolithic server.py.
"""

from . import middleware  # noqa: F401
from .app import create_app
from .dependencies import get_session_manager, get_tool_context

__all__ = [
    "create_app",
    "get_session_manager",
    "get_tool_context",
]
