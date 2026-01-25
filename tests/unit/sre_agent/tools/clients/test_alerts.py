"""Tests for Alerting tools."""

from unittest.mock import MagicMock, patch

import pytest

# Mock these globally to avoid segfaults
with patch("google.cloud.monitoring_v3.ListAlertPoliciesRequest", MagicMock()):
    with patch("google.cloud.monitoring_v3.GetAlertPolicyRequest", MagicMock()):
        from sre_agent.tools.clients.alerts import (
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

    data = await list_alerts(project_id="test-project", filter_str='state="OPEN"')

    assert data is not None
    assert len(data) == 1
    assert data[0]["name"] == "projects/test-project/alerts/123"


@pytest.mark.asyncio
async def test_list_alert_policies_success(mock_alert_policy_client):
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

    data = await list_alert_policies(project_id="test-project")

    assert len(data) == 1
    assert data[0]["display_name"] == "High CPU"
