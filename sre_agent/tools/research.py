"""Online Research tools for SRE Agent.

This module provides tools for searching the web and fetching web content
to augment the agent's knowledge during investigations. Search results
are automatically persisted to memory for future reference.

Tools:
- search_google: Search Google via Custom Search JSON API
- fetch_web_page: Fetch and extract text content from a web page

Configuration:
    GOOGLE_CUSTOM_SEARCH_API_KEY: API key for Google Custom Search.
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID: Programmable Search Engine ID (cx).

    See https://developers.google.com/custom-search/v1/overview for setup.
"""

import logging
import os
import re
from html.parser import HTMLParser
from typing import Annotated, Any

import httpx

from sre_agent.memory.factory import get_memory_manager
from sre_agent.schema import BaseToolResponse, Confidence, ToolStatus
from sre_agent.tools.common.decorators import adk_tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GOOGLE_CUSTOM_SEARCH_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

_MAX_RESULTS = 10
_DEFAULT_RESULTS = 5
_MAX_PAGE_CONTENT_CHARS = 15_000
_HTTP_TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# HTML text extraction (stdlib only — no external dependencies)
# ---------------------------------------------------------------------------


class _HTMLTextExtractor(HTMLParser):
    """Extract readable text from HTML, skipping non-content elements."""

    _SKIP_TAGS: frozenset[str] = frozenset(
        {"script", "style", "noscript", "head", "nav", "footer", "svg"}
    )
    _BLOCK_TAGS: frozenset[str] = frozenset(
        {
            "p",
            "div",
            "br",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "tr",
            "td",
            "th",
            "dt",
            "dd",
            "blockquote",
            "pre",
            "section",
            "article",
        }
    )

    def __init__(self) -> None:
        super().__init__()
        self._text_parts: list[str] = []
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if lower in self._BLOCK_TAGS:
            self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._text_parts.append(data)

    def get_text(self) -> str:
        """Return cleaned text from accumulated parts."""
        text = "".join(self._text_parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content."""
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html)
        return extractor.get_text()
    except Exception:
        # Fallback: strip tags with regex
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def _extract_title(html: str) -> str | None:
    """Extract the ``<title>`` element from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # Unescape common HTML entities
        title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        return title
    return None


# ---------------------------------------------------------------------------
# Context helper (mirrors tools/memory.py pattern)
# ---------------------------------------------------------------------------


def _get_context(tool_context: Any) -> tuple[str | None, str | None]:
    """Extract session_id and user_id from tool context."""
    from sre_agent.auth import get_user_id_from_tool_context

    inv_ctx = getattr(tool_context, "invocation_context", None) or getattr(
        tool_context, "_invocation_context", None
    )
    session_id = getattr(inv_ctx, "session_id", None) if inv_ctx else None
    if inv_ctx and not session_id and hasattr(inv_ctx, "session"):
        session_id = getattr(inv_ctx.session, "id", None)

    user_id = get_user_id_from_tool_context(tool_context)
    return session_id, user_id


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@adk_tool(skip_summarization=True)
async def search_google(
    query: Annotated[
        str,
        "Search query to find technical information, documentation, or answers",
    ],
    num_results: Annotated[
        int,
        "Number of results to return (1-10, default 5)",
    ] = _DEFAULT_RESULTS,
    site_restrict: Annotated[
        str | None,
        "Optional domain to limit search (e.g. 'cloud.google.com' for GCP docs only)",
    ] = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Search Google for technical information, documentation, or answers.

    Use this when you need to:
    - Look up query syntax, API references, or configuration details.
    - Research an unfamiliar error message or status code.
    - Find best practices or recommended approaches for a GCP service.
    - Access up-to-date documentation that may have changed recently.
    - Understand a technology, protocol, or standard you are unsure about.

    Results are automatically saved to memory for future reference.

    Requires GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID
    environment variables to be configured.
    """
    api_key = os.environ.get("GOOGLE_CUSTOM_SEARCH_API_KEY", "")
    search_engine_id = os.environ.get("GOOGLE_CUSTOM_SEARCH_ENGINE_ID", "")

    if not api_key or not search_engine_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=(
                "Google Custom Search is not configured. "
                "Set GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID "
                "environment variables. "
                "See: https://developers.google.com/custom-search/v1/overview"
            ),
        )

    num_results = max(1, min(num_results, _MAX_RESULTS))

    params: dict[str, str | int] = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": num_results,
    }
    if site_restrict:
        params["siteSearch"] = site_restrict
        params["siteSearchFilter"] = "i"  # include only this site

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(GOOGLE_CUSTOM_SEARCH_ENDPOINT, params=params)
            response.raise_for_status()
            data = response.json()

    except httpx.TimeoutException:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Google Search request timed out after {_HTTP_TIMEOUT_SECONDS}s.",
        )
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500] if e.response else "unknown"
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Google Search API returned {e.response.status_code}: {error_body}",
        )
    except Exception as e:
        logger.error(f"Google Search failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Google Search request failed: {e}",
        )

    # Parse results into a clean structure
    items = data.get("items", [])
    search_info = data.get("searchInformation", {})

    results: list[dict[str, str]] = []
    for item in items:
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "display_link": item.get("displayLink", ""),
            }
        )

    # Persist a summary to memory so the agent can recall this research later
    if results and tool_context is not None:
        try:
            manager = get_memory_manager()
            session_id, user_id = _get_context(tool_context)

            top_hits = "; ".join(r["title"] for r in results[:3])
            memory_description = (
                f"Web search for '{query}': "
                f"Found {len(results)} results. "
                f"Top hits: {top_hits}"
            )
            await manager.add_finding(
                description=memory_description,
                source_tool="search_google",
                confidence=Confidence.MEDIUM,
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to save search results to memory: {e}")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "query": query,
            "total_results": search_info.get("totalResults", "0"),
            "search_time_seconds": search_info.get("searchTime", 0),
            "results": results,
        },
        metadata={
            "num_results": len(results),
            "site_restrict": site_restrict,
        },
    )


@adk_tool(skip_summarization=True)
async def fetch_web_page(
    url: Annotated[
        str,
        "Full URL of the web page to fetch (must start with http:// or https://)",
    ],
    max_chars: Annotated[
        int,
        "Maximum characters of content to return (default 15000)",
    ] = _MAX_PAGE_CONTENT_CHARS,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Fetch and extract readable text content from a web page.

    Use this after search_google to read the full content of a relevant result.
    Useful for:
    - Reading documentation pages found via search.
    - Extracting detailed error descriptions or resolution steps from knowledge bases.
    - Getting configuration examples or API reference details.
    - Reading Stack Overflow answers, blog posts, or release notes.

    HTML is automatically converted to plain text. The extracted content
    is saved to memory for future reference.

    Args:
        url: The URL to fetch. Must be a valid HTTP(S) URL.
        max_chars: Maximum characters to return (default 15000, max 50000).
        tool_context: ADK tool context (auto-injected).
    """
    if not url or not url.startswith(("http://", "https://")):
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Invalid URL. Must start with http:// or https://.",
        )

    max_chars = max(1000, min(max_chars, 50_000))

    headers = {
        "User-Agent": "AutoSRE-Agent/0.2 (research tool; +https://github.com/auto-sre)",
        "Accept": "text/html,application/xhtml+xml,text/plain,application/json",
    }

    try:
        async with httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Request timed out after {_HTTP_TIMEOUT_SECONDS}s for {url}.",
        )
    except httpx.TooManyRedirects:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Too many redirects following {url}.",
        )
    except httpx.HTTPStatusError as e:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"HTTP {e.response.status_code} fetching {url}.",
        )
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Failed to fetch {url}: {e}",
        )

    content_type = response.headers.get("content-type", "")

    # Extract text based on content type
    if "html" in content_type:
        text = _extract_text_from_html(response.text)
        title = _extract_title(response.text)
    elif "json" in content_type:
        text = response.text
        title = None
    else:
        text = response.text
        title = None

    # Truncate if needed
    truncated = False
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    # Persist content summary to memory
    if text and tool_context is not None:
        try:
            manager = get_memory_manager()
            session_id, user_id = _get_context(tool_context)

            preview = text[:200].replace("\n", " ").strip()
            page_title = title or url
            memory_description = (
                f"Fetched web page '{page_title}' ({url}): {preview}..."
            )
            await manager.add_finding(
                description=memory_description,
                source_tool="fetch_web_page",
                confidence=Confidence.MEDIUM,
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to save web page content to memory: {e}")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "url": str(response.url),
            "title": title,
            "content": text,
            "content_type": content_type,
            "truncated": truncated,
            "char_count": len(text),
        },
        metadata={
            "original_url": url,
            "status_code": response.status_code,
        },
    )
