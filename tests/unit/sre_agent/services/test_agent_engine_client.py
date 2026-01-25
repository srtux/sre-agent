"""Tests for Agent Engine client."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.services.agent_engine_client import (
    AgentEngineClient,
    AgentEngineConfig,
    get_agent_engine_client,
    is_remote_mode,
)


class TestAgentEngineConfig:
    """Tests for AgentEngineConfig."""

    def test_from_env_returns_none_without_agent_id(self) -> None:
        """Test that from_env returns None when SRE_AGENT_ID is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env vars
            for key in ["SRE_AGENT_ID", "GOOGLE_CLOUD_PROJECT", "GCP_PROJECT_ID"]:
                os.environ.pop(key, None)

            config = AgentEngineConfig.from_env()
            assert config is None

    def test_from_env_returns_none_without_project(self) -> None:
        """Test that from_env returns None when project is not set."""
        with patch.dict(
            os.environ,
            {"SRE_AGENT_ID": "test-agent"},
            clear=True,
        ):
            # Clear project vars
            for key in ["GOOGLE_CLOUD_PROJECT", "GCP_PROJECT_ID"]:
                os.environ.pop(key, None)

            config = AgentEngineConfig.from_env()
            assert config is None

    def test_from_env_returns_config_with_all_vars(self) -> None:
        """Test that from_env returns config when all vars are set."""
        with patch.dict(
            os.environ,
            {
                "SRE_AGENT_ID": "test-agent-123",
                "GOOGLE_CLOUD_PROJECT": "my-project",
                "GOOGLE_CLOUD_LOCATION": "us-west1",
            },
            clear=True,
        ):
            config = AgentEngineConfig.from_env()
            assert config is not None
            assert config.agent_id == "test-agent-123"
            assert config.project_id == "my-project"
            assert config.location == "us-west1"

    def test_from_env_uses_default_location(self) -> None:
        """Test that from_env uses default location if not specified."""
        with patch.dict(
            os.environ,
            {
                "SRE_AGENT_ID": "test-agent",
                "GOOGLE_CLOUD_PROJECT": "my-project",
            },
            clear=True,
        ):
            # Clear location vars
            for key in [
                "AGENT_ENGINE_LOCATION",
                "GCP_LOCATION",
                "GOOGLE_CLOUD_LOCATION",
            ]:
                os.environ.pop(key, None)

            config = AgentEngineConfig.from_env()
            assert config is not None
            assert config.location == "us-central1"


class TestIsRemoteMode:
    """Tests for is_remote_mode function."""

    def test_is_remote_mode_true_when_agent_id_set(self) -> None:
        """Test is_remote_mode returns True when SRE_AGENT_ID is set."""
        with patch.dict(os.environ, {"SRE_AGENT_ID": "test-agent"}):
            assert is_remote_mode() is True

    def test_is_remote_mode_false_when_agent_id_not_set(self) -> None:
        """Test is_remote_mode returns False when SRE_AGENT_ID is not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SRE_AGENT_ID", None)
            assert is_remote_mode() is False


class TestGetAgentEngineClient:
    """Tests for get_agent_engine_client function."""

    def test_returns_none_when_not_configured(self) -> None:
        """Test that get_agent_engine_client returns None when not configured."""
        # Reset singleton
        import sre_agent.services.agent_engine_client as client_module

        client_module._client = None

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SRE_AGENT_ID", None)
            client = get_agent_engine_client()
            assert client is None

    def test_returns_client_when_configured(self) -> None:
        """Test that get_agent_engine_client returns client when configured."""
        # Reset singleton
        import sre_agent.services.agent_engine_client as client_module

        client_module._client = None

        with patch.dict(
            os.environ,
            {
                "SRE_AGENT_ID": "test-agent",
                "GOOGLE_CLOUD_PROJECT": "my-project",
            },
        ):
            client = get_agent_engine_client()
            assert client is not None
            assert isinstance(client, AgentEngineClient)

        # Reset singleton after test
        client_module._client = None


class TestAgentEngineClient:
    """Tests for AgentEngineClient."""

    @pytest.fixture
    def config(self) -> AgentEngineConfig:
        """Create a test config."""
        return AgentEngineConfig(
            project_id="test-project",
            location="us-central1",
            agent_id="test-agent-123",
        )

    @pytest.fixture
    def client(self, config: AgentEngineConfig) -> AgentEngineClient:
        """Create a test client."""
        return AgentEngineClient(config)

    def test_client_initialization(
        self, client: AgentEngineClient, config: AgentEngineConfig
    ) -> None:
        """Test client is initialized with config."""
        assert client.config == config
        assert client._initialized is False
        assert client._adk_app is None

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new(
        self, client: AgentEngineClient
    ) -> None:
        """Test get_or_create_session creates new session."""
        mock_adk_app = MagicMock()
        mock_adk_app.async_create_session = AsyncMock(
            return_value={"id": "new-session-123"}
        )

        # Skip actual initialization
        client._initialized = True
        client._adk_app = mock_adk_app

        session_id = await client.get_or_create_session(
            user_id="test-user",
            access_token="test-token",
            project_id="test-project",
        )

        assert session_id == "new-session-123"
        mock_adk_app.async_create_session.assert_called_once()

        # Verify initial state contains EUC
        call_args = mock_adk_app.async_create_session.call_args
        state = call_args.kwargs.get("state", {})
        assert "_user_access_token" in state
        assert state["_user_access_token"] == "test-token"
        assert "_user_project_id" in state
        assert state["_user_project_id"] == "test-project"

    @pytest.mark.asyncio
    async def test_get_or_create_session_returns_existing(
        self, client: AgentEngineClient
    ) -> None:
        """Test get_or_create_session returns existing session."""
        mock_adk_app = MagicMock()
        mock_adk_app.async_get_session = AsyncMock(
            return_value={"id": "existing-session"}
        )

        client._initialized = True
        client._adk_app = mock_adk_app

        session_id = await client.get_or_create_session(
            user_id="test-user",
            session_id="existing-session",
        )

        assert session_id == "existing-session"
        mock_adk_app.async_get_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_query_yields_events(
        self, client: AgentEngineClient
    ) -> None:
        """Test stream_query yields events from Agent Engine."""
        mock_adk_app = MagicMock()
        mock_adk_app.async_create_session = AsyncMock(
            return_value={"id": "test-session"}
        )

        # Create async generator for stream_query
        async def mock_stream():
            yield {
                "content": {
                    "parts": [{"text": "Hello, I'm the agent!"}]
                }
            }
            yield {
                "content": {
                    "parts": [{"function_call": {"name": "test_tool", "args": {}}}]
                }
            }

        mock_adk_app.async_stream_query = mock_stream

        client._initialized = True
        client._adk_app = mock_adk_app

        events: list[dict] = []
        async for event in client.stream_query(
            user_id="test-user",
            message="Hello",
            access_token="test-token",
        ):
            events.append(event)

        # Should have session event + content events
        assert len(events) >= 1
        assert events[0]["type"] == "session"
