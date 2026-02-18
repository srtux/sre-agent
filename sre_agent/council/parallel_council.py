"""Parallel council pipeline using ADK primitives.

Composes a SequentialAgent that:
1. Runs 5 specialist panels in parallel (via ParallelAgent)
2. Synthesizes their findings into a unified result

The pipeline writes structured findings to session state via output_key,
allowing the synthesizer to read all panel outputs.
"""

from google.adk.agents import ParallelAgent, SequentialAgent

from .panels import (
    create_alerts_panel,
    create_data_panel,
    create_logs_panel,
    create_metrics_panel,
    create_trace_panel,
)
from .schemas import CouncilConfig
from .synthesizer import create_synthesizer

# Module-level singleton for the default council pipeline.
# ADK agents are stateless objects — all per-invocation data lives in
# session state, not in the agent instances themselves.  Pre-building the
# pipeline avoids re-instantiating 6 LlmAgent objects on every investigation.
_default_council_pipeline: SequentialAgent | None = None


def get_default_council_pipeline() -> SequentialAgent:
    """Return the shared default council pipeline, building it on first call.

    Thread-safe under CPython's GIL for the simple None-check assignment.
    Uses the default ``CouncilConfig`` (STANDARD mode, 3 debate rounds,
    confidence threshold 0.85, 120 s timeout).

    Returns:
        The singleton ``SequentialAgent`` for the standard council pipeline.
    """
    global _default_council_pipeline
    if _default_council_pipeline is None:
        _default_council_pipeline = create_council_pipeline(CouncilConfig())
    return _default_council_pipeline


def create_council_pipeline(config: CouncilConfig | None = None) -> SequentialAgent:
    """Create the parallel council pipeline.

    The pipeline runs 5 specialist panels concurrently, then a synthesizer
    that merges their findings into a CouncilResult.

    Args:
        config: Council configuration. Uses defaults if not provided.

    Returns:
        A SequentialAgent composing ParallelAgent(panels) -> Synthesizer.
    """
    if config is None:
        config = CouncilConfig()

    # Create the 5 specialist panels
    trace_panel = create_trace_panel()
    metrics_panel = create_metrics_panel()
    logs_panel = create_logs_panel()
    alerts_panel = create_alerts_panel()
    data_panel = create_data_panel()

    # Run all panels in parallel
    parallel_panels = ParallelAgent(
        name="parallel_panels",
        description=(
            "Runs Trace, Metrics, Logs, Alerts, and Data panels concurrently. "
            "Each panel writes its PanelFinding to session state."
        ),
        sub_agents=[trace_panel, metrics_panel, logs_panel, alerts_panel, data_panel],
    )

    # Synthesize findings
    synthesizer = create_synthesizer()

    # Sequential: panels first, then synthesize
    return SequentialAgent(
        name="council_pipeline",
        description=(
            "Parallel council investigation pipeline. Runs 5 specialist "
            "panels concurrently, then synthesizes their findings."
        ),
        sub_agents=[parallel_panels, synthesizer],
    )
