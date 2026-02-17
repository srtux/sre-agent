"""Tests for the online research tools (fetch_web_page).

Patterns: AsyncMock for httpx, env-var gating, BaseToolResponse validation,
memory integration verification.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.research import (
    _extract_text_from_html,
    _extract_title,
    fetch_web_page,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tool_context() -> MagicMock:
    """Create a mock tool context with invocation_context."""
    mock_ctx = MagicMock()
    mock_inv_ctx = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "test-session-123"
    mock_inv_ctx.session = mock_session
    mock_ctx.invocation_context = mock_inv_ctx
    return mock_ctx


SAMPLE_SEARCH_RESPONSE = {
    "searchInformation": {
        "totalResults": "42",
        "searchTime": 0.23,
    },
    "items": [
        {
            "title": "Cloud Logging query syntax",
            "link": "https://cloud.google.com/logging/docs/view/query-library",
            "snippet": "Use the Logging query language to query and filter logs.",
            "displayLink": "cloud.google.com",
        },
        {
            "title": "Advanced filters for Cloud Monitoring",
            "link": "https://cloud.google.com/monitoring/docs/filters",
            "snippet": "Learn to build advanced monitoring filters.",
            "displayLink": "cloud.google.com",
        },
    ],
}

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Test Page Title</title>
<style>body { color: black; }</style>
<script>console.log("skip me");</script>
</head><body>
<nav>Skip navigation</nav>
<h1>Main Heading</h1>
<p>First paragraph with <b>bold</b> text.</p>
<p>Second paragraph.</p>
<footer>Footer content</footer>
</body></html>"""


# ---------------------------------------------------------------------------
# HTML extraction unit tests
# ---------------------------------------------------------------------------


class TestHTMLTextExtractor:
    """Tests for the HTML-to-text extraction utilities."""

    def test_extract_text_strips_tags(self) -> None:
        text = _extract_text_from_html("<p>Hello <b>world</b></p>")
        assert "Hello" in text
        assert "world" in text
        assert "<p>" not in text

    def test_extract_text_skips_script_and_style(self) -> None:
        text = _extract_text_from_html(SAMPLE_HTML)
        assert "console.log" not in text
        assert "color: black" not in text

    def test_extract_text_skips_nav_and_footer(self) -> None:
        text = _extract_text_from_html(SAMPLE_HTML)
        assert "Skip navigation" not in text
        assert "Footer content" not in text

    def test_extract_text_includes_content(self) -> None:
        text = _extract_text_from_html(SAMPLE_HTML)
        assert "Main Heading" in text
        assert "First paragraph" in text
        assert "Second paragraph" in text

    def test_extract_title(self) -> None:
        title = _extract_title(SAMPLE_HTML)
        assert title == "Test Page Title"

    def test_extract_title_missing(self) -> None:
        assert _extract_title("<html><body>No title</body></html>") is None

    def test_extract_title_with_entities(self) -> None:
        html = "<html><head><title>Foo &amp; Bar</title></head></html>"
        assert _extract_title(html) == "Foo & Bar"

    def test_extract_text_handles_malformed_html(self) -> None:
        """Should not raise on malformed HTML."""
        text = _extract_text_from_html("<p>Unclosed <b>tag")
        assert "Unclosed" in text

    def test_extract_text_empty_input(self) -> None:
        assert _extract_text_from_html("") == ""


# ---------------------------------------------------------------------------
# search_google tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# fetch_web_page tests
# ---------------------------------------------------------------------------


class TestFetchWebPage:
    """Tests for the fetch_web_page tool."""

    @pytest.mark.asyncio
    async def test_invalid_url(self) -> None:
        """Non-HTTP URLs should be rejected."""
        result = await fetch_web_page(url="ftp://example.com", tool_context=None)
        assert result.status == ToolStatus.ERROR
        assert "Invalid URL" in result.error

    @pytest.mark.asyncio
    async def test_empty_url(self) -> None:
        result = await fetch_web_page(url="", tool_context=None)
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_successful_html_fetch(self, mock_tool_context: MagicMock) -> None:
        """HTML pages should be converted to text with title extracted."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.url = "https://example.com/page"
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_manager = AsyncMock()
        mock_manager.add_finding = AsyncMock()

        with (
            patch(
                "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
            ),
            patch(
                "sre_agent.tools.research.get_memory_manager", return_value=mock_manager
            ),
            patch("sre_agent.tools.research._get_context", return_value=("s1", "u1")),
        ):
            result = await fetch_web_page(
                url="https://example.com/page",
                tool_context=mock_tool_context,
            )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["title"] == "Test Page Title"
        assert "Main Heading" in result.result["content"]
        assert "First paragraph" in result.result["content"]
        assert result.result["truncated"] is False
        assert result.metadata["status_code"] == 200

        # Verify memory was called
        mock_manager.add_finding.assert_called_once()

    @pytest.mark.asyncio
    async def test_plain_text_fetch(self) -> None:
        """Plain text responses should be returned as-is."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "Plain text content here"
        mock_response.url = "https://example.com/file.txt"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
        ):
            result = await fetch_web_page(
                url="https://example.com/file.txt",
                tool_context=None,
            )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["content"] == "Plain text content here"
        assert result.result["title"] is None

    @pytest.mark.asyncio
    async def test_content_truncation(self) -> None:
        """Long content should be truncated and flagged."""
        long_text = "A" * 20_000
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = long_text
        mock_response.url = "https://example.com/long"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
        ):
            result = await fetch_web_page(
                url="https://example.com/long",
                max_chars=5000,
                tool_context=None,
            )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["truncated"] is True
        assert result.result["char_count"] == 5000

    @pytest.mark.asyncio
    async def test_max_chars_clamped(self) -> None:
        """max_chars should be clamped to [1000, 50000]."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "x" * 2000
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
        ):
            # Request 100 — should be clamped to 1000
            result = await fetch_web_page(
                url="https://example.com", max_chars=100, tool_context=None
            )
            assert result.result["char_count"] == 1000

    @pytest.mark.asyncio
    async def test_fetch_timeout(self) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
        ):
            result = await fetch_web_page(url="https://example.com", tool_context=None)

        assert result.status == ToolStatus.ERROR
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_fetch_http_error(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_resp
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
        ):
            result = await fetch_web_page(
                url="https://example.com/missing", tool_context=None
            )

        assert result.status == ToolStatus.ERROR
        assert "404" in result.error

    @pytest.mark.asyncio
    async def test_fetch_too_many_redirects(self) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TooManyRedirects("too many")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
        ):
            result = await fetch_web_page(
                url="https://example.com/loop", tool_context=None
            )

        assert result.status == ToolStatus.ERROR
        assert "redirect" in result.error.lower()

    @pytest.mark.asyncio
    async def test_memory_failure_does_not_break_fetch(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Memory save failures should not break the page fetch."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Hello</p></body></html>"
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_manager = AsyncMock()
        mock_manager.add_finding = AsyncMock(side_effect=RuntimeError("memory boom"))

        with (
            patch(
                "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
            ),
            patch(
                "sre_agent.tools.research.get_memory_manager", return_value=mock_manager
            ),
            patch("sre_agent.tools.research._get_context", return_value=("s1", "u1")),
        ):
            result = await fetch_web_page(
                url="https://example.com",
                tool_context=mock_tool_context,
            )

        assert result.status == ToolStatus.SUCCESS
        assert "Hello" in result.result["content"]

    @pytest.mark.asyncio
    async def test_json_content_type(self) -> None:
        """JSON responses should be returned as-is without HTML parsing."""
        json_text = '{"error": "not_found", "message": "Resource not found"}'
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = json_text
        mock_response.url = "https://api.example.com/v1/resource"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sre_agent.tools.research.httpx.AsyncClient", return_value=mock_client
        ):
            result = await fetch_web_page(
                url="https://api.example.com/v1/resource",
                tool_context=None,
            )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["content"] == json_text
        assert result.result["title"] is None
