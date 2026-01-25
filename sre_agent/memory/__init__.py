"""SRE Agent Memory Module.

This module provides context retention and state management capabilities using
Vertex AI Memory Bank and a structured investigation state machine.
"""

from .manager import MemoryManager

__all__ = ["MemoryManager"]
