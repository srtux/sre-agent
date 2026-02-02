import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio

from server import app
from sre_agent.api.routers import agent


@pytest_asyncio.fixture
async def async_client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_debug_ui_test_alias_output(async_client, monkeypatch):
    """Verify that DEBUG_UI_TEST outputs components using the 'tool-log' alias."""
    # Mock session service
    mock_session_service = AsyncMock()
    mock_session_service.session_service = MagicMock()

    mock_session = MagicMock()
    mock_session.id = "test-session-id"
    mock_session.state = {}
    mock_session_service.get_session.return_value = mock_session
    mock_session_service.create_session.return_value = mock_session
    mock_session_service.update_session_state.return_value = None
    mock_session_service.append_event.return_value = None
    mock_session_service.sync_to_memory.return_value = None

    monkeypatch.setattr(agent, "get_session_service", lambda: mock_session_service)

    # Mock InvocationContext
    mock_inv_ctx = MagicMock()
    mock_inv_ctx.invocation_id = "test-invocation-id"
    monkeypatch.setattr(agent, "InvocationContext", lambda **kwargs: mock_inv_ctx)

    # Mock authentication
    monkeypatch.setattr(agent, "get_current_credentials_or_none", lambda: None)
    monkeypatch.setattr(agent, "get_current_project_id", lambda: "test-project")

    # Mock is_remote_mode
    monkeypatch.setattr(agent, "is_remote_mode", lambda: False)

    # Mock Runner
    mock_runner = MagicMock()
    monkeypatch.setattr(agent, "create_runner", lambda *args: mock_runner)

    response = await async_client.post(
        "/api/genui/chat",
        json={
            "messages": [{"role": "user", "text": "DEBUG_UI_TEST"}],
            "user_id": "test-user",
        },
    )

    assert response.status_code == 200

    lines = []
    async for line in response.aiter_lines():
        if line:
            lines.append(json.loads(line))

    # Verify we find the alias_test component with correct type
    found_alias_test = False
    for line in lines:
        if line.get("type") == "a2ui" and "beginRendering" in line.get("message", {}):
            msg = line["message"]["beginRendering"]
            components = msg.get("components", [])
            for comp in components:
                comp_str = json.dumps(comp)
                if "alias_test" in comp_str:
                    found_alias_test = True
                    # Assert correct type usage
                    assert comp["type"] == "tool-log", (
                        "Component type should be 'tool-log'"
                    )
                    assert comp["component"]["type"] == "tool-log"
                    assert "tool-log" in comp["component"]
                    assert "x-sre-tool-log" not in comp["component"]

    assert found_alias_test, "Did not find alias_test component in output"
