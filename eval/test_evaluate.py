"""Evaluation tests for the SRE Agent.

These tests require Google Cloud credentials (API key or Vertex AI setup) to run.
They will be skipped if the required environment variables are not set.

Required environment variables:
- GOOGLE_API_KEY or GEMINI_API_KEY: For Google AI API
- OR GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION: For Vertex AI

To run these tests locally:
1. Set up your credentials in .env file
2. Run: uv run pytest eval/test_evaluate.py -v
"""

import pytest
from conftest import (
    AGENT_MODULE,
    load_eval_set,
    make_full_config,
    make_tool_trajectory_config,
    requires_credentials,
)
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.evaluation.eval_config import EvalConfig

# ---------------------------------------------------------------------------
# Sanity
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_agent_capabilities() -> None:
    """Verify the agent can describe its own capabilities coherently."""
    eval_set = load_eval_set("basic_capabilities.test.json")
    config = EvalConfig(criteria={"response_match_score": 0.6})

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# Tool routing
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Agent may ask for clarification even when Project ID is provided"
)
async def test_tool_selection() -> None:
    """Verify correct tool selection for trace, log, and metric queries."""
    eval_set = load_eval_set("tool_selection.test.json")
    config = make_tool_trajectory_config(trajectory_score=0.8)

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_metrics_analysis() -> None:
    """Verify metric querying and anomaly detection capabilities."""
    eval_set = load_eval_set("metrics_analysis.test.json")
    config = make_tool_trajectory_config(trajectory_score=0.8)

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# End-to-end investigation
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_incident_investigation() -> None:
    """Verify multi-stage latency investigation (Aggregate > Triage > Deep Dive)."""
    eval_set = load_eval_set("incident_investigation.test.json")
    config = make_tool_trajectory_config(trajectory_score=0.8)

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# Error diagnosis
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_error_diagnosis() -> None:
    """Verify diagnosis of DB pool exhaustion, cascading timeouts, and OOM kills."""
    eval_set = load_eval_set("error_diagnosis.test.json")
    config = make_full_config()

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# Multi-signal correlation
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_multi_signal_correlation() -> None:
    """Verify cross-signal correlation for deployment regressions and SLO degradation."""
    eval_set = load_eval_set("multi_signal_correlation.test.json")
    config = make_full_config()

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# Kubernetes debugging
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_kubernetes_debugging() -> None:
    """Verify GKE debugging: pod crashloops, node pressure, HPA scaling failures."""
    eval_set = load_eval_set("kubernetes_debugging.test.json")
    config = make_tool_trajectory_config(trajectory_score=0.8)

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# SLO burn rate analysis
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_slo_burn_rate() -> None:
    """Verify error budget exhaustion detection and multi-window SLO analysis."""
    eval_set = load_eval_set("slo_burn_rate.test.json")
    config = make_tool_trajectory_config(trajectory_score=0.8)

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )


# ---------------------------------------------------------------------------
# Failure modes and edge cases
# ---------------------------------------------------------------------------


@requires_credentials
@pytest.mark.asyncio
async def test_failure_modes() -> None:
    """Verify graceful handling of invalid projects, fake metrics, rate limits, and cascading failures."""
    eval_set = load_eval_set("failure_modes.test.json")
    # Failure mode tests focus on response quality (graceful degradation)
    # rather than strict tool trajectory matching
    config = EvalConfig(
        criteria={
            "response_match_score": 0.5,
            "hallucinations_v1": 0.0,
            "safety_v1": 0.0,
        }
    )

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_MODULE,
        eval_set=eval_set,
        eval_config=config,
        print_detailed_results=False,
    )
