import os
from unittest.mock import patch

import pytest

from sre_agent.services.session import ADKSessionManager


@pytest.fixture
def mock_vertex_ai_service():
    with patch("google.adk.sessions.VertexAiSessionService") as mock:
        yield mock


@pytest.fixture
def mock_db_service():
    with patch("sre_agent.services.session.DatabaseSessionService") as mock:
        yield mock


def test_session_manager_init_vertex_mode(mock_vertex_ai_service):
    """Test that ADKSessionManager uses 'sre_agent' as app_name in Vertex mode for consistency."""
    test_agent_id = "projects/123/locations/us-central1/reasoningEngines/456"
    test_project = "test-project"

    with patch.dict(
        os.environ,
        {"SRE_AGENT_ID": test_agent_id, "GOOGLE_CLOUD_PROJECT": test_project},
    ):
        manager = ADKSessionManager()

        # Verify correct service type was initialized
        # CHANGE: We now force "sre_agent" instead of the raw ID
        assert manager.app_name == "sre_agent"
        mock_vertex_ai_service.assert_called_once_with(
            project=test_project, location="us-central1"
        )


def test_session_manager_init_backend_remote_mode(mock_vertex_ai_service):
    """Test that RUNNING_IN_AGENT_ENGINE triggers Vertex mode with stable app_name."""
    test_project = "backend-project"

    with patch.dict(
        os.environ,
        {
            # SRE_AGENT_ID is usually MISSING in the backend
            "RUNNING_IN_AGENT_ENGINE": "true",
            "GOOGLE_CLOUD_PROJECT": test_project,
        },
        clear=True,
    ):
        manager = ADKSessionManager()

        # Verify correct service type was initialized
        assert manager.app_name == "sre_agent"
        mock_vertex_ai_service.assert_called_once_with(
            project=test_project, location="us-central1"
        )


def test_session_manager_init_local_mode(mock_db_service):
    """Test that ADKSessionManager uses default app_name in local mode."""
    with patch.dict(os.environ, {}, clear=True):
        # Ensure SRE_AGENT_ID is unset
        if "SRE_AGENT_ID" in os.environ:
            del os.environ["SRE_AGENT_ID"]

        manager = ADKSessionManager()

        # Verify default app_name
        assert manager.app_name == "sre_agent"
