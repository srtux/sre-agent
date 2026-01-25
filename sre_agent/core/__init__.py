"""Core Autonomous Reliability Components.

This module implements the "Unrolled Codex" pattern for stateful,
event-driven agent execution with safety guarantees.

Components:
- Runner: Stateless execution harness
- PromptComposer: Three-tier prompt composition
- ContextCompactor: Sliding window context management
- Summarizer: Event summarization service
- PolicyEngine: Safety interception layer
- GraphService: Dependency knowledge graph
"""

from sre_agent.core.approval import (
    ApprovalStatus,
    HumanApprovalEvent,
    HumanApprovalRequest,
)
from sre_agent.core.context_compactor import ContextCompactor, WorkingContext
from sre_agent.core.graph_service import (
    BlastRadiusReport,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    EdgeType,
    GraphService,
    ServiceType,
)
from sre_agent.core.policy_engine import (
    PolicyDecision,
    PolicyEngine,
    ToolAccessLevel,
    ToolCategory,
)
from sre_agent.core.prompt_composer import PromptComposer, PromptRole
from sre_agent.core.runner import Runner, RunnerConfig
from sre_agent.core.summarizer import EventSummary, Summarizer

__all__ = [
    "ApprovalStatus",
    "BlastRadiusReport",
    "ContextCompactor",
    "DependencyEdge",
    "DependencyGraph",
    "DependencyNode",
    "EdgeType",
    "EventSummary",
    "GraphService",
    "HumanApprovalEvent",
    "HumanApprovalRequest",
    "PolicyDecision",
    "PolicyEngine",
    "PromptComposer",
    "PromptRole",
    "Runner",
    "RunnerConfig",
    "ServiceType",
    "Summarizer",
    "ToolAccessLevel",
    "ToolCategory",
    "WorkingContext",
]
