"""Debate pipeline with critic loop and confidence gating.

Implements the debate investigation mode:
1. Initial parallel panel analysis
2. Initial synthesis
3. Loop: critic → panels (re-analyze with feedback) → synthesizer
4. Loop exits when confidence >= threshold or max iterations reached
5. Convergence tracking records confidence progression per round
"""

import json
import logging
import time
from typing import Any

from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent
from google.genai import types as genai_types

from .critic import create_critic
from .panels import (
    create_alerts_panel,
    create_data_panel,
    create_logs_panel,
    create_metrics_panel,
    create_trace_panel,
)
from .schemas import CouncilConfig
from .synthesizer import create_synthesizer

logger = logging.getLogger(__name__)


# Key used to store convergence history in session state
CONVERGENCE_STATE_KEY = "debate_convergence_history"


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


def _build_convergence_tracker(
    config: CouncilConfig,
) -> Any:
    """Build an after_agent_callback that records convergence metrics per round.

    Tracks the confidence progression, round durations, and panel changes
    across debate iterations. Stores the history in session state under
    the CONVERGENCE_STATE_KEY for later analysis.

    Args:
        config: Council configuration.

    Returns:
        A callback function compatible with LoopAgent.after_agent_callback.
    """
    round_start_times: list[float] = []

    def convergence_tracker(
        callback_context: Any,
    ) -> None:
        """Record convergence metrics after each debate round."""
        # Initialize convergence history in state if needed
        if CONVERGENCE_STATE_KEY not in callback_context.state:
            callback_context.state[CONVERGENCE_STATE_KEY] = []
            # Clear closure state for a fresh debate session
            round_start_times.clear()

        history = callback_context.state[CONVERGENCE_STATE_KEY]
        current_round = len(history) + 1

        # Extract current confidence from synthesis
        confidence = 0.0
        synthesis_raw = callback_context.state.get("council_synthesis")
        if synthesis_raw is not None:
            if isinstance(synthesis_raw, str):
                try:
                    synthesis = json.loads(synthesis_raw)
                    confidence = float(synthesis.get("overall_confidence", 0.0))
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            elif isinstance(synthesis_raw, dict):
                confidence = float(synthesis_raw.get("overall_confidence", 0.0))

        # Extract critic gaps/contradictions count
        critic_gaps = 0
        critic_contradictions = 0
        critic_raw = callback_context.state.get("critic_report")
        if critic_raw is not None:
            if isinstance(critic_raw, str):
                try:
                    critic = json.loads(critic_raw)
                except (json.JSONDecodeError, TypeError):
                    critic = {}
            elif isinstance(critic_raw, dict):
                critic = critic_raw
            else:
                critic = {}
            critic_gaps = len(critic.get("gaps", []))
            critic_contradictions = len(critic.get("contradictions", []))

        # Calculate confidence delta from previous round
        prev_confidence = history[-1]["confidence"] if history else 0.0
        confidence_delta = confidence - prev_confidence

        # Record round duration
        now = time.time()
        if round_start_times:
            round_duration_ms = (now - round_start_times[-1]) * 1000
        else:
            round_duration_ms = 0.0
        round_start_times.append(now)

        # Build round record
        round_record = {
            "round": current_round,
            "confidence": confidence,
            "confidence_delta": confidence_delta,
            "critic_gaps": critic_gaps,
            "critic_contradictions": critic_contradictions,
            "round_duration_ms": round(round_duration_ms, 2),
            "threshold": config.confidence_threshold,
            "converged": confidence >= config.confidence_threshold,
        }
        history.append(round_record)
        callback_context.state[CONVERGENCE_STATE_KEY] = history

        logger.info(
            f"Debate round {current_round}: "
            f"confidence={confidence:.2f} (delta={confidence_delta:+.2f}), "
            f"gaps={critic_gaps}, contradictions={critic_contradictions}, "
            f"duration={round_duration_ms:.0f}ms"
        )

    return convergence_tracker


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
            create_data_panel(),
        ],
    )
    initial_synthesizer = create_synthesizer()

    # Debate loop: critic → re-run panels → re-synthesize
    # Uses both before_agent_callback (confidence gate) and
    # after_agent_callback (convergence tracking) for full observability.
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
                    create_data_panel(),
                ],
            ),
            create_synthesizer(),
        ],
        max_iterations=config.max_debate_rounds,
        before_agent_callback=_build_confidence_gate(config),
        after_agent_callback=_build_convergence_tracker(config),
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
