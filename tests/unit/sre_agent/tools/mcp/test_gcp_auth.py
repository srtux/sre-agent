import unittest
from unittest.mock import MagicMock, patch

from sre_agent.tools.mcp.gcp import _create_header_provider


class TestGcpMcpAuth(unittest.TestCase):
    def test_header_provider_default(self):
        """Test header provider with no auth context (default)."""
        # Given
        project_id = "test-project"
        provider = _create_header_provider(project_id)

        # When
        with (
            patch(
                "sre_agent.tools.mcp.gcp.get_credentials_from_tool_context",
                return_value=None,
            ),
            patch(
                "sre_agent.tools.mcp.gcp.get_current_credentials",
                return_value=(MagicMock(token=None), "test-project"),
            ),
        ):
            headers = provider(None)

        # Then
        self.assertEqual(headers, {"x-goog-user-project": project_id})
        self.assertNotIn("Authorization", headers)

    def test_header_provider_with_token(self):
        """Test header provider injects token when present."""
        # Given
        project_id = "test-project"
        token = "fake-token-123"
        mock_creds = MagicMock()
        mock_creds.token = token
        provider = _create_header_provider(project_id)

        # When
        with patch(
            "sre_agent.tools.mcp.gcp.get_credentials_from_tool_context",
            return_value=mock_creds,
        ):
            headers = provider(None)

        # Then
        self.assertEqual(headers["x-goog-user-project"], project_id)
        self.assertEqual(headers["Authorization"], f"Bearer {token}")

    def test_header_provider_with_empty_token(self):
        """Test header provider handles credentials with empty token gracefully."""
        # Given
        project_id = "test-project"
        mock_creds = MagicMock()
        mock_creds.token = None  # No token available
        provider = _create_header_provider(project_id)

        # When
        with (
            patch(
                "sre_agent.tools.mcp.gcp.get_credentials_from_tool_context",
                return_value=mock_creds,
            ),
            patch(
                "sre_agent.tools.mcp.gcp.get_current_credentials",
                return_value=(MagicMock(token=None), "test-project"),
            ),
        ):
            headers = provider(None)

        # Then
        self.assertEqual(headers, {"x-goog-user-project": project_id})
        self.assertNotIn("Authorization", headers)
