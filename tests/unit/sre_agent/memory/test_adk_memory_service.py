"""Tests for ADK memory service factory."""

from unittest.mock import MagicMock, patch

import sre_agent.memory.factory as factory_module


class TestGetAdkMemoryService:
    """Tests for get_adk_memory_service factory."""

    def setup_method(self) -> None:
        """Reset singleton state between tests."""
        factory_module._adk_memory_service = None
        factory_module._adk_memory_service_initialized = False

    def test_returns_none_without_agent_id(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = factory_module.get_adk_memory_service()
            assert result is None

    def test_returns_none_without_project_id(self) -> None:
        env = {"SRE_AGENT_ID": "projects/test/locations/us/agents/123"}
        with patch.dict("os.environ", env, clear=True):
            result = factory_module.get_adk_memory_service()
            assert result is None

    def test_returns_service_with_full_config(self) -> None:
        env = {
            "SRE_AGENT_ID": "projects/test/locations/us/agents/123",
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_LOCATION": "us-central1",
        }
        mock_service = MagicMock()
        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "google.adk.memory.VertexAiMemoryBankService",
                return_value=mock_service,
            ) as mock_cls,
        ):
            result = factory_module.get_adk_memory_service()
            assert result is mock_service
            mock_cls.assert_called_once_with(
                project="test-project",
                location="us-central1",
                agent_engine_id="projects/test/locations/us/agents/123",
            )

    def test_caches_result(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result1 = factory_module.get_adk_memory_service()
            result2 = factory_module.get_adk_memory_service()
            assert result1 is result2
            assert result1 is None

    def test_handles_init_failure(self) -> None:
        env = {
            "SRE_AGENT_ID": "projects/test/locations/us/agents/123",
            "GOOGLE_CLOUD_PROJECT": "test-project",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "google.adk.memory.VertexAiMemoryBankService",
                side_effect=RuntimeError("init failed"),
            ),
        ):
            result = factory_module.get_adk_memory_service()
            assert result is None
