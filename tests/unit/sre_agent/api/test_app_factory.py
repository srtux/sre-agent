"""Unit tests for the FastAPI application factory.

Goal: Verify create_app correctly assembles the application with all routers,
middleware, patches, and optional features.
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestCreateApp:
    """Tests for the create_app factory function."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """create_app returns a properly configured FastAPI instance."""
        with (
            patch("sre_agent.tools.common.telemetry.setup_telemetry"),
            patch("sre_agent.tools.test_functions.register_all_test_functions"),
        ):
            from sre_agent.api.app import create_app

            app = create_app(title="Test App", include_adk_routes=False)
            assert isinstance(app, FastAPI)
            assert app.title == "Test App"

    def test_create_app_includes_health_router(self) -> None:
        """App includes the health check endpoint."""
        with (
            patch("sre_agent.tools.common.telemetry.setup_telemetry"),
            patch("sre_agent.tools.test_functions.register_all_test_functions"),
        ):
            from sre_agent.api.app import create_app

            app = create_app(include_adk_routes=False)
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/health")
            # Health endpoint should exist (may return 200 or 503 depending on state)
            assert response.status_code in (200, 503)

    def test_create_app_calls_telemetry_setup(self) -> None:
        """create_app initializes telemetry."""
        with (
            patch("sre_agent.tools.common.telemetry.setup_telemetry") as mock_telemetry,
            patch("sre_agent.tools.test_functions.register_all_test_functions"),
        ):
            from sre_agent.api.app import create_app

            create_app(include_adk_routes=False)
            mock_telemetry.assert_called_once()


class TestMCPPatch:
    """Tests for the MCP Pydantic bridge patch."""

    def test_mcp_patch_succeeds(self) -> None:
        """MCP patch applies without error."""
        from sre_agent.api.app import _apply_mcp_patch

        # Should not raise
        _apply_mcp_patch()

    def test_mcp_patch_handles_import_error(self) -> None:
        """MCP patch gracefully handles missing mcp package."""
        with patch.dict(
            "sys.modules", {"mcp": None, "mcp.client": None, "mcp.client.session": None}
        ):
            # Should not raise even if mcp is not available
            from sre_agent.api.app import _apply_mcp_patch

            _apply_mcp_patch()


class TestPydanticPatch:
    """Tests for the Pydantic TypeAdapter patch."""

    def test_pydantic_patch_succeeds(self) -> None:
        """Pydantic patch applies without error."""
        from sre_agent.api.app import _patch_pydantic

        _patch_pydantic()  # Should not raise

    def test_pydantic_patch_strips_config_for_basemodel(self) -> None:
        """Patched TypeAdapter strips config for BaseModel subclasses."""
        from sre_agent.api.app import _patch_pydantic

        _patch_pydantic()

        from pydantic import BaseModel, ConfigDict, TypeAdapter

        class TestModel(BaseModel):
            model_config = ConfigDict(frozen=True)
            name: str

        # This should not raise PydanticUserError even with config kwarg
        adapter = TypeAdapter(
            TestModel, config=ConfigDict(arbitrary_types_allowed=True)
        )
        assert adapter is not None


class TestJsonSchemaFeature:
    """Tests for the JSON schema feature toggle."""

    def test_enable_json_schema_succeeds(self) -> None:
        """JSON schema feature enables without error."""
        from sre_agent.api.app import _enable_json_schema_feature

        # Should not raise (may log warning if ADK not available)
        _enable_json_schema_feature()
