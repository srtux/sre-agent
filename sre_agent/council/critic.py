"""Critic agent for cross-examination of panel findings.

The critic reads all panel findings from session state and identifies
agreements, contradictions, and gaps across the specialist panels.
"""

from google.adk.agents import LlmAgent

from sre_agent.model_config import get_model_name

from .prompts import CRITIC_PROMPT


def create_critic() -> LlmAgent:
    """Create the council critic agent.

    The critic reads panel findings from session state:
    - trace_finding
    - metrics_finding
    - logs_finding
    - alerts_finding

    And writes its cross-examination report to 'critic_report'.

    Returns:
        Configured LlmAgent for cross-critique.
    """
    return LlmAgent(
        name="council_critic",
        model=get_model_name("deep"),
        description=(
            "Cross-examines findings from all specialist panels to identify "
            "agreements, contradictions, and gaps in the analysis."
        ),
        instruction=CRITIC_PROMPT,
        output_key="critic_report",
    )
