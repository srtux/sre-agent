"""SRE Agent Memory Module.

This module provides context retention and state management capabilities using
Vertex AI Memory Bank and a structured investigation state machine.

Key Features:
- Automatic learning from tool failures (API syntax, invalid filters)
- Automatic recording of significant successful findings
- Investigation pattern learning (symptom -> tool sequence -> resolution)
- Session-to-memory sync for long-term searchability
- Structured mistake memory with self-correction detection
- Pre-tool advice injection from past mistakes
"""

from .callbacks import (
    after_agent_memory_callback,
    after_tool_memory_callback,
    before_tool_memory_callback,
    on_tool_error_memory_callback,
)
from .factory import get_adk_memory_service, get_memory_manager
from .manager import MemoryManager
from .mistake_advisor import MistakeAdvisor, get_mistake_advisor
from .mistake_learner import MistakeLearner, get_mistake_learner
from .mistake_store import MistakeMemoryStore, get_mistake_store

__all__ = [
    "MemoryManager",
    "MistakeAdvisor",
    "MistakeLearner",
    "MistakeMemoryStore",
    "after_agent_memory_callback",
    "after_tool_memory_callback",
    "before_tool_memory_callback",
    "get_adk_memory_service",
    "get_memory_manager",
    "get_mistake_advisor",
    "get_mistake_learner",
    "get_mistake_store",
    "on_tool_error_memory_callback",
]
