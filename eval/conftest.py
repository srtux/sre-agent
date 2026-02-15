"""Shared fixtures and configuration for agent evaluation tests.

Provides common utilities for credential checking, eval set loading,
and eval config construction used across all eval test modules.
"""

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation.eval_set import EvalSet

load_dotenv()

# Directory containing eval test data files
EVAL_DIR = Path(__file__).parent

# Agent module path for the SRE Agent
AGENT_MODULE = "sre_agent.agent"

# Placeholder project IDs used in test data files
_PLACEHOLDER_PROJECT_IDS = [
    "TEST_PROJECT_ID",
    "microservices-prod",
    "search-prod",
    "ecommerce-prod",
    "web-platform-prod",
    "payments-prod",
]


def has_eval_credentials() -> bool:
    """Check if API credentials are available for evaluation tests."""
    has_api_key = bool(
        os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    )
    has_vertexai = bool(
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        and os.environ.get("GOOGLE_CLOUD_LOCATION")
        and os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
    )
    return has_api_key or has_vertexai


requires_credentials = pytest.mark.skipif(
    not has_eval_credentials(),
    reason=(
        "Evaluation tests require Google AI API key or Vertex AI credentials. "
        "Set GOOGLE_API_KEY or "
        "(GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION + GOOGLE_GENAI_USE_VERTEXAI)."
    ),
)


def load_eval_set(file_name: str) -> EvalSet:
    """Load and parse an evaluation set from a JSON file.

    Performs dynamic project ID replacement so test data works with any GCP
    project.

    Args:
        file_name: Name of the JSON file in the eval directory
            (e.g. ``"basic_capabilities.test.json"``).

    Returns:
        Parsed EvalSet object.
    """
    file_path = EVAL_DIR / file_name
    eval_data_raw = file_path.read_text()

    actual_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if actual_project_id:
        for placeholder in _PLACEHOLDER_PROJECT_IDS:
            eval_data_raw = eval_data_raw.replace(placeholder, actual_project_id)

    eval_data = json.loads(eval_data_raw)

    try:
        return EvalSet(**eval_data)
    except Exception:
        if hasattr(EvalSet, "model_validate"):
            return EvalSet.model_validate(eval_data)
        return EvalSet.parse_obj(eval_data)


def load_eval_config() -> dict:
    """Load the shared evaluation criteria from ``test_config.json``.

    Returns:
        Criteria dictionary suitable for :class:`EvalConfig`.
    """
    config_path = EVAL_DIR / "test_config.json"
    with open(config_path) as f:
        return json.load(f)["criteria"]


def make_tool_trajectory_config(
    trajectory_score: float = 0.8,
    response_score: float = 0.0,
) -> EvalConfig:
    """Create an EvalConfig focused on tool trajectory evaluation.

    Args:
        trajectory_score: Minimum tool trajectory match score.
        response_score: Minimum response match score (often 0.0 when
            we only care about tool selection).

    Returns:
        Configured EvalConfig.
    """
    return EvalConfig(
        criteria={
            "tool_trajectory_avg_score": trajectory_score,
            "response_match_score": response_score,
        }
    )


def make_full_config() -> EvalConfig:
    """Create an EvalConfig using the full shared criteria from test_config.json.

    Returns:
        Configured EvalConfig with all quality criteria.
    """
    return EvalConfig(criteria=load_eval_config())
