"""SRE Agent Memory Module.

This module provides context retention and state management capabilities using
Vertex AI Memory Bank and a structured investigation state machine.

Key Features:
- Automatic learning from tool failures (API syntax, invalid filters)
- Automatic recording of significant successful findings
- Investigation pattern learning (symptom -> tool sequence -> resolution)
- Session-to-memory sync for long-term searchability
"""

from .callbacks import (
    after_tool_memory_callback,
    before_tool_memory_callback,
    on_tool_error_memory_callback,
)
from .factory import get_adk_memory_service, get_memory_manager
from .manager import MemoryManager

__all__ = [
    "MemoryManager",
    "after_tool_memory_callback",
    "before_tool_memory_callback",
    "get_adk_memory_service",
    "get_memory_manager",
    "on_tool_error_memory_callback",
]
