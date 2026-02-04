"""Council — Parallel multi-agent investigation with debate-based consensus.

This package implements the Parallel Council architecture for the SRE Agent:
- 4 specialist panels (Trace, Metrics, Logs, Alerts) running in parallel
- A critic agent for cross-critique of panel findings
- A debate loop with confidence gating for convergence
- Investigation modes: Fast, Standard, Debate
"""

from .critic import create_critic
from .debate import create_debate_pipeline
from .intent_classifier import classify_intent
from .mode_router import classify_investigation_mode
from .panels import (
    create_alerts_panel,
    create_logs_panel,
    create_metrics_panel,
    create_trace_panel,
)
from .parallel_council import create_council_pipeline
from .schemas import (
    CouncilConfig,
    CouncilResult,
    CriticReport,
    InvestigationMode,
    PanelFinding,
)
from .synthesizer import create_synthesizer

__all__ = [
    "CouncilConfig",
    "CouncilResult",
    "CriticReport",
    "InvestigationMode",
    "PanelFinding",
    "classify_intent",
    "classify_investigation_mode",
    "create_alerts_panel",
    "create_council_pipeline",
    "create_critic",
    "create_debate_pipeline",
    "create_logs_panel",
    "create_metrics_panel",
    "create_synthesizer",
    "create_trace_panel",
]
