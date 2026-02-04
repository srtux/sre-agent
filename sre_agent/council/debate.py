"""Debate pipeline with critic loop and confidence gating.

Implements the debate investigation mode:
1. Initial parallel panel analysis
2. Initial synthesis
3. Loop: critic → panels (re-analyze with feedback) → synthesizer
4. Loop exits when confidence >= threshold or max iterations reached
"""

import json
import logging
from typing import Any

from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent
from google.genai import types as genai_types

from .critic import create_critic
from .panels import (
    create_alerts_panel,
    create_logs_panel,
    create_metrics_panel,
    create_trace_panel,
)
from .schemas import CouncilConfig
from .synthesizer import create_synthesizer

logger = logging.getLogger(__name__)


def _build_confidence_gate(
    config: CouncilConfig,
) -> Any:
    """Build a before_agent_callback that stops the loop when confidence is reached.

    The gate checks the 'council_synthesis' key in session state for the
    'overall_confidence' value. If it meets or exceeds the threshold,
    it returns a Content that signals early termination.

    Args:
        config: Council configuration with confidence_threshold.

    Returns:
        A callback function compatible with LoopAgent.before_agent_callback.
    """

    def confidence_gate(
        callback_context: Any,
    ) -> genai_types.Content | None:
        """Check if debate should stop based on confidence threshold."""
        synthesis_raw = callback_context.state.get("council_synthesis")
        if synthesis_raw is None:
            return None

        # Parse synthesis — may be a JSON string or dict
        if isinstance(synthesis_raw, str):
            try:
                synthesis = json.loads(synthesis_raw)
            except (json.JSONDecodeError, TypeError):
                return None
        elif isinstance(synthesis_raw, dict):
            synthesis = synthesis_raw
        else:
            return None

        confidence = synthesis.get("overall_confidence", 0.0)
        if (
            isinstance(confidence, (int, float))
            and confidence >= config.confidence_threshold
        ):
            logger.info(
                f"🏛️ Debate confidence gate reached: {confidence:.2f} >= "
                f"{config.confidence_threshold:.2f}. Stopping debate."
            )
            return genai_types.Content(
                parts=[
                    genai_types.Part(
                        text=(
                            f"Debate converged with confidence {confidence:.2f} "
                            f"(threshold: {config.confidence_threshold:.2f}). "
                            "Stopping further debate rounds."
                        )
                    )
                ]
            )
        return None

    return confidence_gate


def create_debate_pipeline(config: CouncilConfig | None = None) -> SequentialAgent:
    """Create the debate investigation pipeline.

    The pipeline consists of:
    1. Initial parallel panel analysis → synthesis
    2. A LoopAgent that repeatedly:
       a. Runs the critic to cross-examine findings
       b. Re-runs panels with critic feedback available in state
       c. Re-synthesizes with updated findings
       Until confidence >= threshold or max_iterations reached.

    Args:
        config: Council configuration. Uses debate defaults if not provided.

    Returns:
        A SequentialAgent composing initial analysis + debate loop.
    """
    if config is None:
        config = CouncilConfig()

    # Initial analysis: parallel panels → synthesizer
    initial_panels = ParallelAgent(
        name="initial_panels",
        description="Initial parallel panel analysis before debate.",
        sub_agents=[
            create_trace_panel(),
            create_metrics_panel(),
            create_logs_panel(),
            create_alerts_panel(),
        ],
    )
    initial_synthesizer = create_synthesizer()

    # Debate loop: critic → re-run panels → re-synthesize
    debate_loop = LoopAgent(
        name="debate_loop",
        description=(
            "Iterative debate: critic cross-examines, panels re-analyze, "
            "synthesizer re-evaluates until confidence threshold is met."
        ),
        sub_agents=[
            create_critic(),
            ParallelAgent(
                name="debate_panels",
                description="Re-run panels with critic feedback in state.",
                sub_agents=[
                    create_trace_panel(),
                    create_metrics_panel(),
                    create_logs_panel(),
                    create_alerts_panel(),
                ],
            ),
            create_synthesizer(),
        ],
        max_iterations=config.max_debate_rounds,
        before_agent_callback=_build_confidence_gate(config),
    )

    # Full pipeline: initial analysis → debate loop
    return SequentialAgent(
        name="debate_pipeline",
        description=(
            "Full debate investigation: initial parallel analysis followed by "
            "iterative critique and re-analysis until convergence."
        ),
        sub_agents=[initial_panels, initial_synthesizer, debate_loop],
    )
