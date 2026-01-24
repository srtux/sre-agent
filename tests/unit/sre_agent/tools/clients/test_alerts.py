"""Tests for Alerting tools."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.clients.alerts import (
    get_alert,
    list_alert_policies,
    list_alerts,
)


@pytest.fixture
def mock_auth():
    with patch(
        "os.getenv",
        side_effect=lambda k, d=None: "false" if k == "STRICT_EUC_ENFORCEMENT" else d,
    ):
        with patch("google.auth.default") as mock:
            mock.return_value = (MagicMock(), "test-project")
            yield mock


@pytest.fixture
def mock_authorized_session():
    with patch("sre_agent.tools.clients.alerts.AuthorizedSession") as mock:
        session_instance = MagicMock()
        mock.return_value = session_instance
        yield session_instance


@pytest.fixture
def mock_alert_policy_client():
    with patch("sre_agent.tools.clients.alerts.get_alert_policy_client") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.mark.asyncio
async def test_list_alerts_success(mock_auth, mock_authorized_session):
    """Test listing alerts successfully."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "alerts": [
            {
                "name": "projects/test-project/alerts/123",
                "state": "OPEN",
                "openTime": "2023-01-01T00:00:00Z",
            }
        ]
    }
    mock_authorized_session.get.return_value = mock_response

    # Execute
    data = await list_alerts(project_id="test-project", filter_str='state="OPEN"')

    # Verify
    assert data is not None
    assert len(data) == 1
    assert data[0]["name"] == "projects/test-project/alerts/123"

    # Verify call
    mock_authorized_session.get.assert_called_once()
    args, kwargs = mock_authorized_session.get.call_args
    assert (
        "https://monitoring.googleapis.com/v3/projects/test-project/alerts" in args[0]
    )
    assert kwargs["params"]["filter"] == 'state="OPEN"'
    # Verify quota header
    assert kwargs["headers"]["X-Goog-User-Project"] == "test-project"


@pytest.mark.asyncio
async def test_list_alerts_error(mock_auth, mock_authorized_session):
    """Test handling errors when listing alerts."""
    mock_authorized_session.get.side_effect = Exception("API Error")

    data = await list_alerts(project_id="test-project")

    assert "error" in data
    assert "API Error" in data["error"]


@pytest.mark.asyncio
async def test_get_alert_success(mock_auth, mock_authorized_session):
    """Test getting a specific alert."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "name": "projects/test-project/alerts/123",
        "state": "OPEN",
    }
    mock_authorized_session.get.return_value = mock_response

    data = await get_alert(name="projects/test-project/alerts/123")

    assert data["name"] == "projects/test-project/alerts/123"

    # Verify call
    mock_authorized_session.get.assert_called_once()
    args, kwargs = mock_authorized_session.get.call_args
    assert (
        "https://monitoring.googleapis.com/v3/projects/test-project/alerts/123"
        in args[0]
    )
    # Verify quota header extracted from name
    assert kwargs["headers"]["X-Goog-User-Project"] == "test-project"


@pytest.mark.asyncio
async def test_list_alerts_order_by_mapping(mock_auth, mock_authorized_session):
    """Test that informal orderBy fields are mapped correctly."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"alerts": []}
    mock_authorized_session.get.return_value = mock_response

    # LLM uses 'start_time desc'
    await list_alerts(project_id="test-project", order_by="start_time desc")

    # Verify it was mapped to 'open_time desc'
    _, kwargs = mock_authorized_session.get.call_args
    assert kwargs["params"]["orderBy"] == "open_time desc"

    # LLM uses 'endTime'
    await list_alerts(project_id="test-project", order_by="endTime")

    # Verify it was mapped to 'close_time'
    _, kwargs = mock_authorized_session.get.call_args
    assert kwargs["params"]["orderBy"] == "close_time"


@pytest.mark.asyncio
async def test_list_alert_policies_success(mock_alert_policy_client):
    """Test listing alert policies."""
    # Setup mock policies
    policy1 = MagicMock()
    policy1.name = "projects/test-project/alertPolicies/1"
    policy1.display_name = "High CPU"
    policy1.documentation.content = "Fix CPU"
    policy1.documentation.mime_type = "text/markdown"
    policy1.user_labels = {"env": "prod"}
    policy1.enabled = True

    condition1 = MagicMock()
    condition1.name = "projects/test-project/alertPolicies/1/conditions/1"
    condition1.display_name = "CPU > 90%"
    policy1.conditions = [condition1]

    mock_alert_policy_client.list_alert_policies.return_value = [policy1]

    # Execute
    data = await list_alert_policies(project_id="test-project")

    # Verify
    assert len(data) == 1
    assert data[0]["display_name"] == "High CPU"
    assert data[0]["conditions"][0]["display_name"] == "CPU > 90%"
    assert data[0]["documentation"]["content"] == "Fix CPU"
