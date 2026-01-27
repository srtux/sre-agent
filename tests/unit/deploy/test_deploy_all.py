import os
import sys
from unittest.mock import MagicMock, patch

# Ensure root dir is for imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import deploy.deploy_all as deploy_all  # noqa: E402


def test_get_existing_agent_id_success():
    """Test that it correctly finds the agent ID when present."""
    mock_agent = MagicMock()
    mock_agent.display_name = "sre_agent"
    mock_agent.resource_name = "projects/p/locations/l/reasoningEngines/123"

    with (
        patch("vertexai.init"),
        patch("vertexai.agent_engines.list", return_value=[mock_agent]),
        patch(
            "os.getenv",
            side_effect=lambda k, d=None: "test-project"
            if k == "GOOGLE_CLOUD_PROJECT"
            else d,
        ),
    ):
        result = deploy_all.get_existing_agent_id()
        assert result == "projects/p/locations/l/reasoningEngines/123"


def test_get_existing_agent_id_not_found():
    """Test that it returns None when agent is missing."""
    with (
        patch("vertexai.init"),
        patch("vertexai.agent_engines.list", return_value=[]),
        patch("os.getenv", return_value="test-project"),
    ):
        result = deploy_all.get_existing_agent_id()
        assert result is None


def test_get_existing_agent_id_error_handling():
    """Test that it returns None on SDK errors (safe fallback)."""
    with patch("vertexai.init", side_effect=Exception("API Error")):
        result = deploy_all.get_existing_agent_id()
        assert result is None
