"""Parallel council pipeline using ADK primitives.

Composes a SequentialAgent that:
1. Runs 4 specialist panels in parallel (via ParallelAgent)
2. Synthesizes their findings into a unified result

The pipeline writes structured findings to session state via output_key,
allowing the synthesizer to read all panel outputs.
"""

from google.adk.agents import ParallelAgent, SequentialAgent

from .panels import (
    create_alerts_panel,
    create_logs_panel,
    create_metrics_panel,
    create_trace_panel,
)
from .schemas import CouncilConfig
from .synthesizer import create_synthesizer


def create_council_pipeline(config: CouncilConfig | None = None) -> SequentialAgent:
    """Create the parallel council pipeline.

    The pipeline runs 4 specialist panels concurrently, then a synthesizer
    that merges their findings into a CouncilResult.

    Args:
        config: Council configuration. Uses defaults if not provided.

    Returns:
        A SequentialAgent composing ParallelAgent(panels) → Synthesizer.
    """
    if config is None:
        config = CouncilConfig()

    # Create the 4 specialist panels
    trace_panel = create_trace_panel()
    metrics_panel = create_metrics_panel()
    logs_panel = create_logs_panel()
    alerts_panel = create_alerts_panel()

    # Run all panels in parallel
    parallel_panels = ParallelAgent(
        name="parallel_panels",
        description=(
            "Runs Trace, Metrics, Logs, and Alerts panels concurrently. "
            "Each panel writes its PanelFinding to session state."
        ),
        sub_agents=[trace_panel, metrics_panel, logs_panel, alerts_panel],
    )

    # Synthesize findings
    synthesizer = create_synthesizer()

    # Sequential: panels first, then synthesize
    return SequentialAgent(
        name="council_pipeline",
        description=(
            "Parallel council investigation pipeline. Runs 4 specialist "
            "panels concurrently, then synthesizes their findings."
        ),
        sub_agents=[parallel_panels, synthesizer],
    )
