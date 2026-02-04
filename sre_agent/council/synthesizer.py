"""Synthesizer agent for merging panel findings into a council result.

The synthesizer reads panel findings from session state (written by
panel agents via output_key) and produces a unified assessment with
overall severity and confidence scores.
"""

from google.adk.agents import LlmAgent

from sre_agent.model_config import get_model_name

from .prompts import SYNTHESIZER_PROMPT


def create_synthesizer() -> LlmAgent:
    """Create the council synthesizer agent.

    Reads panel findings from session state keys:
    - trace_finding
    - metrics_finding
    - logs_finding
    - alerts_finding
    - critic_report (if available, from debate mode)

    Produces a unified synthesis written to 'council_synthesis'.

    Returns:
        Configured LlmAgent for synthesis.
    """
    return LlmAgent(
        name="council_synthesizer",
        model=get_model_name("deep"),
        description=(
            "Synthesizes findings from all specialist panels into a "
            "unified assessment with overall severity and confidence."
        ),
        instruction=SYNTHESIZER_PROMPT,
        output_key="council_synthesis",
    )
