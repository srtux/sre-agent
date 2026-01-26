import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure the root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


# Mock vertexai and ADK features at the module level BEFORE importing deploy
def setup_deploy_mocks():
    with (
        patch("vertexai.init"),
        patch("google.adk.features.override_feature_enabled"),
        patch("vertexai.agent_engines", create=True),
    ):
        # Import as a top-level module (since no __init__.py exists)
        import deploy.deploy as deploy_mod

        return deploy_mod


deploy_mod = setup_deploy_mocks()


@pytest.fixture
def mock_agent_engines():
    # Patch agent_engines inside the deploy module
    with patch("deploy.deploy.agent_engines") as mock:
        yield mock


@pytest.fixture
def mock_flags():
    # Patch FLAGS inside the deploy module
    with patch("deploy.deploy.FLAGS") as mock:
        mock.display_name = "sre-agent"
        mock.description = "Test Description"
        mock.resource_id = None
        mock.force_new = False
        mock.service_account = "test-sa@project.iam.gserviceaccount.com"
        mock.min_instances = 1
        mock.max_instances = 2
        yield mock


def test_deploy_creates_new_when_none_exists(mock_agent_engines, mock_flags):
    """Test that it creates a new agent when no existing agent matches the name."""
    mock_agent_engines.list.return_value = []

    deploy_mod.deploy(env_vars={"TEST_VAR": "value"})

    # Should list agents to search for existing ones
    mock_agent_engines.list.assert_called_once()
    # Should call create
    mock_agent_engines.create.assert_called_once()
    # Verify some create arguments
    _, kwargs = mock_agent_engines.create.call_args
    assert "agent_engine" in kwargs
    assert kwargs["display_name"] == "sre-agent"
    assert kwargs["env_vars"]["TEST_VAR"] == "value"


def test_deploy_propagates_encryption_key(mock_agent_engines, mock_flags):
    """Test that SRE_AGENT_ENCRYPTION_KEY is automatically propagated from environment."""
    test_key = "test-secret-key-123"
    mock_agent_engines.list.return_value = []

    with patch(
        "os.getenv",
        side_effect=lambda k, d=None: test_key
        if k == "SRE_AGENT_ENCRYPTION_KEY"
        else d,
    ):
        deploy_mod.deploy()

    _, kwargs = mock_agent_engines.create.call_args
    assert "SRE_AGENT_ENCRYPTION_KEY" in kwargs["env_vars"]
    assert kwargs["env_vars"]["SRE_AGENT_ENCRYPTION_KEY"] == test_key


def test_deploy_updates_when_agent_exists_by_name(mock_agent_engines, mock_flags):
    """Test that it updates an existing agent when found by display name."""
    mock_agent = MagicMock()
    mock_agent.display_name = "sre-agent"
    mock_agent.resource_name = (
        "projects/test-project/locations/us-central1/reasoningEngines/123"
    )

    mock_agent_engines.list.return_value = [mock_agent]

    deploy_mod.deploy(env_vars={"TEST_VAR": "value"})

    # Should NOT call create
    mock_agent_engines.create.assert_not_called()
    # Should call update on the found agent
    mock_agent.update.assert_called_once()
    # Verify update arguments
    _, kwargs = mock_agent.update.call_args
    assert kwargs["agent_engine"] is not None
    assert kwargs["display_name"] == "sre-agent"
    assert kwargs["env_vars"]["TEST_VAR"] == "value"


def test_deploy_updates_when_resource_id_provided(mock_agent_engines, mock_flags):
    """Test that it updates the specific agent when resource_id is provided."""
    resource_id = "projects/test-project/locations/us-central1/reasoningEngines/456"
    mock_flags.resource_id = resource_id

    mock_agent = MagicMock()
    mock_agent.resource_name = resource_id
    mock_agent_engines.get.return_value = mock_agent

    deploy_mod.deploy(env_vars={"TEST_VAR": "value"})

    # Should check the specific ID
    mock_agent_engines.get.assert_called_with(resource_id)
    # Should call update on THAT agent
    mock_agent.update.assert_called_once()
    assert mock_agent.update.call_args.kwargs["agent_engine"] is not None
    mock_agent_engines.create.assert_not_called()


def test_deploy_forces_new_when_flag_set(mock_agent_engines, mock_flags):
    """Test that it creates a new agent even if one exists when --force_new is used."""
    mock_flags.force_new = True

    mock_agent = MagicMock()
    mock_agent.display_name = "sre-agent"
    mock_agent_engines.list.return_value = [mock_agent]

    deploy_mod.deploy(env_vars={"TEST_VAR": "value"})

    # Should call create despite the match
    mock_agent_engines.create.assert_called_once()
    # Should NOT call update
    mock_agent.update.assert_not_called()
