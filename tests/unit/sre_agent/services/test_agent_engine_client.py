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
        from sre_agent.services import agent_engine_client as client_module

        client_module._client = None

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SRE_AGENT_ID", None)
            client = get_agent_engine_client()
            assert client is None

    def test_returns_client_when_configured(self) -> None:
        """Test that get_agent_engine_client returns client when configured."""
        # Reset singleton
        from sre_agent.services import agent_engine_client as client_module

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
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "new-session-123"
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            session_id = await client.get_or_create_session(
                user_id="test-user",
                access_token="test-token",
                project_id="test-project",
            )

            assert session_id == "new-session-123"
            mock_session_manager.get_or_create_session.assert_called_once_with(
                session_id=None,
                user_id="test-user",
                project_id="test-project",
            )

    @pytest.mark.asyncio
    async def test_get_or_create_session_returns_existing(
        self, client: AgentEngineClient
    ) -> None:
        """Test get_or_create_session returns existing session."""
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "existing-session"
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            session_id = await client.get_or_create_session(
                user_id="test-user",
                session_id="existing-session",
            )

            assert session_id == "existing-session"
            mock_session_manager.get_or_create_session.assert_called_once_with(
                session_id="existing-session",
                user_id="test-user",
                project_id=None,
            )

    @pytest.mark.asyncio
    async def test_ensure_initialized(self, client: AgentEngineClient) -> None:
        """Test that _ensure_initialized calls vertexai.init and agent_engines.get."""
        with (
            patch("vertexai.init") as mock_init,
            patch("vertexai.agent_engines", create=True) as mock_agent_engines,
        ):
            mock_get = mock_agent_engines.get
            mock_agent = MagicMock()
            mock_agent.query = MagicMock()
            mock_get.return_value = mock_agent

            await client._ensure_initialized()

            assert client._initialized is True
            assert client._adk_app == mock_agent
            mock_init.assert_called_once_with(
                project="test-project", location="us-central1"
            )
            mock_get.assert_called_once()
            resource_name = mock_get.call_args[0][0]
            assert "test-agent-123" in resource_name

    @pytest.mark.asyncio
    async def test_stream_query_uninitialized(self, client: AgentEngineClient) -> None:
        """Test that stream_query initializes the client if needed."""
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.state = {}
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )

        with (
            patch(
                "sre_agent.services.session.get_session_service",
                return_value=mock_session_manager,
            ),
            patch.object(
                client, "_ensure_initialized", new_callable=AsyncMock
            ) as mock_init,
        ):
            # Mock the query call
            mock_agent = MagicMock()
            mock_agent.async_stream_query.return_value = (
                AsyncMock()
            )  # mock as async generator
            client._adk_app = mock_agent

            generator = client.stream_query(user_id="user", message="msg")
            async for _ in generator:
                pass

            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_query_yields_events(self, client: AgentEngineClient) -> None:
        """Test stream_query yields events from Agent Engine using stream_query."""
        # Mock Session Manager
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.state = {}  # Initial state
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )
        mock_session_manager.update_session_state = AsyncMock()

        # Mock ADK App
        mock_adk_app = MagicMock()

        # Mock async_stream_query returning an async generator
        async def mock_stream_generator(*args, **kwargs):
            events = [
                {"content": {"parts": [{"text": "Hello, I'm the agent!"}]}},
                {
                    "content": {
                        "parts": [{"function_call": {"name": "test_tool", "args": {}}}]
                    }
                },
            ]
            for event in events:
                yield event

        mock_adk_app.async_stream_query = MagicMock(side_effect=mock_stream_generator)
        # Ensure it doesn't try to call stream_query first
        del mock_adk_app.stream_query

        client._initialized = True
        client._adk_app = mock_adk_app

        with (
            patch(
                "sre_agent.services.session.get_session_service",
                return_value=mock_session_manager,
            ),
            patch(
                "sre_agent.services.agent_engine_client.encrypt_token",
                side_effect=lambda x: x,
            ),
        ):
            events: list[dict] = []
            async for event in client.stream_query(
                user_id="test-user",
                message="Hello",
                access_token="test-token",
                project_id="test-project",
            ):
                events.append(event)

            # Should have session event + content events
            assert len(events) >= 1
            assert events[0]["type"] == "session"
            assert events[0]["session_id"] == "test-session"

            # Verify session state update (EUC propagation)
            mock_session_manager.update_session_state.assert_called_once()
            state_delta = mock_session_manager.update_session_state.call_args[0][1]
            assert state_delta["_user_access_token"] == "test-token"
            assert state_delta["_user_project_id"] == "test-project"

            # Verify events from generator
            content_events = [e for e in events if e.get("type", "") != "session"]
            assert len(content_events) == 2

            # Verify async_stream_query was called with correct args
            mock_adk_app.async_stream_query.assert_called_once()
            call_kwargs = mock_adk_app.async_stream_query.call_args.kwargs
            assert call_kwargs["message"] == "Hello"
            assert call_kwargs["user_id"] == "test-user"
            assert call_kwargs["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_stream_query_sync_iterator_fallback(
        self, client: AgentEngineClient
    ) -> None:
        """Test stream_query handles synchronous iterator fallback."""
        # Mock Session Manager
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.state = {}
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )
        mock_session_manager.update_session_state = AsyncMock()

        # Mock ADK App
        mock_adk_app = MagicMock()
        # Delete async_stream_query to force fallback to stream_query
        del mock_adk_app.async_stream_query

        # Mock sync stream_query returning a direct list (which is an iterator)
        def mock_sync_stream(*args, **kwargs):
            return iter(
                [
                    {"content": {"parts": [{"text": "Sync response 1"}]}},
                    {"content": {"parts": [{"text": "Sync response 2"}]}},
                ]
            )

        mock_adk_app.stream_query = MagicMock(side_effect=mock_sync_stream)

        client._initialized = True
        client._adk_app = mock_adk_app

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            events: list[dict] = []
            async for event in client.stream_query(
                user_id="test-user",
                message="Hello sync",
            ):
                events.append(event)

            # verify we got events back
            text_events = [
                e["content"]["parts"][0]["text"]
                for e in events
                if e.get("type", "") != "session"
            ]
            assert "Sync response 1" in text_events
            assert "Sync response 2" in text_events
            mock_adk_app.stream_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_sessions_async(self, client: AgentEngineClient) -> None:
        """Test list_sessions using async_list_sessions."""
        mock_adk_app = MagicMock()
        mock_adk_app.async_list_sessions = AsyncMock(return_value=[{"id": "s1"}])
        client._initialized = True
        client._adk_app = mock_adk_app

        sessions = await client.list_sessions(user_id="user")
        assert sessions == [{"id": "s1"}]
        mock_adk_app.async_list_sessions.assert_called_once_with(user_id="user")

    @pytest.mark.asyncio
    async def test_list_sessions_sync_fallback(self, client: AgentEngineClient) -> None:
        """Test list_sessions using sync list_sessions fallback."""
        mock_adk_app = MagicMock()
        mock_adk_app.list_sessions = MagicMock(return_value=[{"id": "s1"}])
        # Force hasattr(mock_adk_app, 'async_list_sessions') to be False
        del mock_adk_app.async_list_sessions

        client._initialized = True
        client._adk_app = mock_adk_app

        sessions = await client.list_sessions(user_id="user")
        assert sessions == [{"id": "s1"}]
        mock_adk_app.list_sessions.assert_called_once_with(user_id="user")

    @pytest.mark.asyncio
    async def test_delete_session_async(self, client: AgentEngineClient) -> None:
        """Test delete_session using async_delete_session."""
        mock_adk_app = MagicMock()
        mock_adk_app.async_delete_session = AsyncMock()
        client._initialized = True
        client._adk_app = mock_adk_app

        result = await client.delete_session(user_id="user", session_id="s1")
        assert result is True
        mock_adk_app.async_delete_session.assert_called_once_with(
            user_id="user", session_id="s1"
        )

    @pytest.mark.asyncio
    async def test_delete_session_sync_fallback(
        self, client: AgentEngineClient
    ) -> None:
        """Test delete_session using sync delete_session fallback."""
        mock_adk_app = MagicMock()
        mock_adk_app.delete_session = MagicMock()
        # Force hasattr(mock_adk_app, 'async_delete_session') to be False
        del mock_adk_app.async_delete_session

        client._initialized = True
        client._adk_app = mock_adk_app

        result = await client.delete_session(user_id="user", session_id="s1")
        assert result is True
        mock_adk_app.delete_session.assert_called_once_with(
            user_id="user", session_id="s1"
        )

    @pytest.mark.asyncio
    async def test_stream_query_handles_list_get_error(
        self, client: AgentEngineClient
    ) -> None:
        """Test stream_query handles the 'list object has no attribute get' error."""
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.state = {}
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )
        mock_session_manager.update_session_state = AsyncMock()

        mock_adk_app = MagicMock()
        # Delete async_stream_query to force fallback to stream_query
        del mock_adk_app.async_stream_query

        async def mock_error_generator(*args, **kwargs):
            # Simulate the error that happens during iteration
            raise AttributeError("'list' object has no attribute 'get'")
            yield {}  # To keep it a generator

        mock_adk_app.stream_query = MagicMock(side_effect=mock_error_generator)

        client._initialized = True
        client._adk_app = mock_adk_app

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            events = []
            async for event in client.stream_query(
                user_id="test-user", message="trigger error"
            ):
                events.append(event)

            # Look for error event
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) == 1
            assert (
                "invalid response format" in error_events[0]["error"].lower()
                or "invalid response" in error_events[0]["error"].lower()
            )

    @pytest.mark.asyncio
    async def test_stream_query_handles_value_error(
        self, client: AgentEngineClient
    ) -> None:
        """Test stream_query handles ValueError (malformed JSON from Agent Engine)."""
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.state = {}
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )
        mock_session_manager.update_session_state = AsyncMock()

        mock_adk_app = MagicMock()
        del mock_adk_app.async_stream_query

        async def mock_value_error_generator(*args, **kwargs):
            raise ValueError("Can only parse array of JSON objects")
            yield {}

        mock_adk_app.stream_query = MagicMock(side_effect=mock_value_error_generator)

        client._initialized = True
        client._adk_app = mock_adk_app

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            events = []
            async for event in client.stream_query(user_id="u", message="m"):
                events.append(event)

            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) == 1
            assert "invalid response" in error_events[0]["error"].lower()
            assert "upstream error" in error_events[0]["error"].lower()

    @pytest.mark.asyncio
    async def test_async_stream_query_handles_errors(
        self, client: AgentEngineClient
    ) -> None:
        """Test that async_stream_query path also handles ValueError and AttributeError."""
        mock_session_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.state = {}
        mock_session_manager.get_or_create_session = AsyncMock(
            return_value=mock_session
        )

        client._initialized = True

        # Test path for ValueError
        mock_adk_app_v = MagicMock()

        async def mock_v_err(*args, **kwargs):
            raise ValueError("Can only parse array of JSON objects")
            yield {}

        mock_adk_app_v.async_stream_query = MagicMock(side_effect=mock_v_err)
        client._adk_app = mock_adk_app_v

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            events = []
            async for event in client.stream_query(user_id="u", message="m"):
                events.append(event)
            assert any(
                "roles/aiplatform.user" in e.get("error", "").lower() for e in events
            )

        # Test path for AttributeError
        mock_adk_app_a = MagicMock()

        async def mock_a_err(*args, **kwargs):
            raise AttributeError("'list' object has no attribute 'get'")
            yield {}

        mock_adk_app_a.async_stream_query = MagicMock(side_effect=mock_a_err)
        client._adk_app = mock_adk_app_a

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            events = []
            async for event in client.stream_query(user_id="u", message="m"):
                events.append(event)

            # Check for specifically yielded error in AttributeError path
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) == 1
            assert "roles/aiplatform.user" in error_events[0]["error"].lower()
