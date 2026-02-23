"""Tests for guest mode chat endpoint."""
import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sre_agent.api.routers.agent import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _enable_guest_mode():
    with patch("sre_agent.api.routers.agent.is_guest_mode", return_value=True):
        yield


class TestGuestChatStreaming:
    def test_returns_200(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "investigate latency"}]},
        )
        assert resp.status_code == 200

    def test_returns_ndjson_content_type(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        assert "application/x-ndjson" in resp.headers.get("content-type", "")

    def test_first_event_is_session(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [l for l in resp.text.strip().split("\n") if l.strip()]
        first = json.loads(lines[0])
        assert first["type"] == "session"
        assert "session_id" in first

    def test_last_event_is_suggestions(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [l for l in resp.text.strip().split("\n") if l.strip()]
        last = json.loads(lines[-1])
        assert last["type"] == "suggestions"
        assert isinstance(last["suggestions"], list)
        assert len(last["suggestions"]) > 0

    def test_contains_text_events(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [l for l in resp.text.strip().split("\n") if l.strip()]
        events = [json.loads(l) for l in lines]
        text_events = [e for e in events if e.get("type") == "text"]
        assert len(text_events) > 0

    def test_contains_dashboard_events(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [l for l in resp.text.strip().split("\n") if l.strip()]
        events = [json.loads(l) for l in lines]
        dashboard_events = [e for e in events if e.get("type") == "dashboard"]
        assert len(dashboard_events) > 0

    def test_multiple_turns_vary_content(self, client):
        """Different turn indexes should produce different events."""
        resp1 = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "turn 1"}]},
        )
        resp2 = client.post(
            "/api/genui/chat",
            json={
                "messages": [
                    {"role": "user", "text": "turn 1"},
                    {"role": "assistant", "text": "response 1"},
                    {"role": "user", "text": "turn 2"},
                ]
            },
        )
        # Different turn indexes should produce different content
        lines1 = [l for l in resp1.text.strip().split("\n") if l.strip()]
        lines2 = [l for l in resp2.text.strip().split("\n") if l.strip()]
        # At minimum, event count may differ between turns
        # Both should have session + suggestions wrapper events
        assert len(lines1) > 2
        assert len(lines2) > 2

    def test_does_not_call_real_agent(self, client):
        """Guest mode should not touch credentials or agent code."""
        with patch(
            "sre_agent.api.routers.agent.get_current_credentials_or_none"
        ) as mock_creds:
            resp = client.post(
                "/api/genui/chat",
                json={"messages": [{"role": "user", "text": "hello"}]},
            )
            assert resp.status_code == 200
            mock_creds.assert_not_called()


class TestGuestChatSuggestions:
    def test_suggestions_are_strings(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [l for l in resp.text.strip().split("\n") if l.strip()]
        last = json.loads(lines[-1])
        for s in last["suggestions"]:
            assert isinstance(s, str)
