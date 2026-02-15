"""Tests for the GitHub REST API client.

Covers: get_file_content, search_code, list_commits, create_branch,
create_or_update_file, create_pull_request.
All external HTTP calls are mocked via httpx.AsyncClient.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sre_agent.tools.github.client import (
    GitHubAPIError,
    create_branch,
    create_or_update_file,
    create_pull_request,
    get_file_content,
    list_commits,
    search_code,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _github_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required env vars for GitHub client."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_123")
    monkeypatch.setenv("GITHUB_REPO", "test-owner/test-repo")


@pytest.fixture
def _no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GITHUB_TOKEN is NOT set."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(
    status_code: int = 200, json_data: dict | None = None, text: str = ""
) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


# ===========================================================================
# get_file_content
# ===========================================================================


class TestGetFileContent:
    @pytest.mark.asyncio
    async def test_success_base64_decode(self) -> None:
        import base64

        content = "print('hello world')\n"
        b64 = base64.b64encode(content.encode()).decode()
        resp_data = {
            "name": "hello.py",
            "path": "src/hello.py",
            "content": b64,
            "encoding": "base64",
            "size": len(content),
            "sha": "abc123",
            "html_url": "https://github.com/test-owner/test-repo/blob/main/src/hello.py",
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, resp_data))

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await get_file_content("src/hello.py")

        assert result["content"] == content
        assert result["name"] == "hello.py"
        assert result["sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_file_not_found_raises(self) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(404))

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(GitHubAPIError, match="File not found"):
                await get_file_content("nonexistent.py")

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_token")
    async def test_no_token_raises(self) -> None:
        with pytest.raises(GitHubAPIError, match="GITHUB_TOKEN"):
            await get_file_content("any.py")

    @pytest.mark.asyncio
    async def test_non_base64_content(self) -> None:
        resp_data = {
            "name": "file.txt",
            "path": "file.txt",
            "content": "plain text content",
            "size": 18,
            "sha": "def456",
            "html_url": "https://example.com",
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, resp_data))

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await get_file_content("file.txt")

        assert result["content"] == "plain text content"

    @pytest.mark.asyncio
    async def test_server_error_raises(self) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            return_value=_mock_response(500, text="Internal Server Error")
        )

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(GitHubAPIError):
                await get_file_content("any.py")


# ===========================================================================
# search_code
# ===========================================================================


class TestSearchCode:
    @pytest.mark.asyncio
    async def test_success_with_matches(self) -> None:
        resp_data = {
            "total_count": 2,
            "items": [
                {
                    "path": "src/main.py",
                    "html_url": "https://github.com/test/repo/blob/main/src/main.py",
                    "text_matches": [{"fragment": "def hello():"}],
                },
                {
                    "path": "src/utils.py",
                    "html_url": "https://github.com/test/repo/blob/main/src/utils.py",
                    "text_matches": [],
                },
            ],
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, resp_data))

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await search_code("def hello")

        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        assert result["items"][0]["path"] == "src/main.py"
        assert result["items"][0]["text_matches"] == ["def hello():"]

    @pytest.mark.asyncio
    async def test_with_extension_filter(self) -> None:
        resp_data = {"total_count": 0, "items": []}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, resp_data))

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await search_code("class Foo", extension="py")

        assert result["total_count"] == 0
        # Verify extension was included in query
        call_kwargs = mock_client.get.call_args
        assert "extension:py" in call_kwargs.kwargs["params"]["q"]

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_token")
    async def test_no_token_raises(self) -> None:
        with pytest.raises(GitHubAPIError, match="GITHUB_TOKEN"):
            await search_code("test")


# ===========================================================================
# list_commits
# ===========================================================================


class TestListCommits:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        resp_data = [
            {
                "sha": "abc123def456789",  # pragma: allowlist secret
                "commit": {
                    "message": "Fix bug in parser\nDetailed description",
                    "author": {"name": "Test User", "date": "2026-01-15T10:00:00Z"},
                },
                "html_url": "https://github.com/test/repo/commit/abc123",
            },
        ]

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, resp_data))

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await list_commits()

        assert len(result) == 1
        assert result[0]["sha"] == "abc123def456"  # pragma: allowlist secret
        assert result[0]["message"] == "Fix bug in parser"  # First line only
        assert result[0]["author"] == "Test User"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_no_token")
    async def test_no_token_raises(self) -> None:
        with pytest.raises(GitHubAPIError, match="GITHUB_TOKEN"):
            await list_commits()


# ===========================================================================
# create_branch
# ===========================================================================


class TestCreateBranch:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        ref_resp = _mock_response(200, {"object": {"sha": "abc123"}})
        create_resp = _mock_response(
            201, {"ref": "refs/heads/auto-fix/test", "object": {"sha": "abc123"}}
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=ref_resp)
        mock_client.post = AsyncMock(return_value=create_resp)

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await create_branch("auto-fix/test")

        assert result["ref"] == "refs/heads/auto-fix/test"
        assert result["sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_bad_ref_raises(self) -> None:
        ref_resp = _mock_response(404, text="Not Found")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=ref_resp)

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(GitHubAPIError, match="Cannot resolve ref"):
                await create_branch("auto-fix/test", from_ref="nonexistent")


# ===========================================================================
# create_or_update_file
# ===========================================================================


class TestCreateOrUpdateFile:
    @pytest.mark.asyncio
    async def test_create_new_file(self) -> None:
        check_resp = _mock_response(404)
        put_resp = _mock_response(
            201,
            {
                "content": {
                    "path": "new.py",
                    "sha": "new_sha",
                    "html_url": "https://example.com",
                }
            },
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=check_resp)
        mock_client.put = AsyncMock(return_value=put_resp)

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await create_or_update_file(
                "new.py", "content", "add file", "main"
            )

        assert result["path"] == "new.py"
        assert result["sha"] == "new_sha"

    @pytest.mark.asyncio
    async def test_update_existing_file(self) -> None:
        check_resp = _mock_response(200, {"sha": "existing_sha"})
        put_resp = _mock_response(
            200,
            {
                "content": {
                    "path": "existing.py",
                    "sha": "updated_sha",
                    "html_url": "https://example.com",
                }
            },
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=check_resp)
        mock_client.put = AsyncMock(return_value=put_resp)

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await create_or_update_file(
                "existing.py", "new content", "update", "main"
            )

        assert result["sha"] == "updated_sha"
        # Verify SHA was included in PUT body
        put_call = mock_client.put.call_args
        assert put_call.kwargs["json"]["sha"] == "existing_sha"


# ===========================================================================
# create_pull_request
# ===========================================================================


class TestCreatePullRequest:
    @pytest.mark.asyncio
    async def test_success_with_labels(self) -> None:
        pr_resp = _mock_response(
            201,
            {
                "number": 42,
                "html_url": "https://github.com/test/repo/pull/42",
                "title": "Fix: improve validation",
                "state": "open",
                "draft": True,
            },
        )
        label_resp = _mock_response(200, {})

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=[pr_resp, label_resp])

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await create_pull_request(
                title="Fix: improve validation",
                body="Description",
                head="auto-fix/test",
                labels=["agent-generated", "auto-fix"],
            )

        assert result["number"] == 42
        assert result["draft"] is True
        # Verify labels were applied (second POST call)
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_success_without_labels(self) -> None:
        pr_resp = _mock_response(
            201,
            {
                "number": 43,
                "html_url": "https://github.com/test/repo/pull/43",
                "title": "Test PR",
                "state": "open",
                "draft": False,
            },
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=pr_resp)

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            result = await create_pull_request(
                title="Test PR",
                body="Description",
                head="feature",
                draft=False,
            )

        assert result["number"] == 43
        assert result["draft"] is False
        # Only one POST (no labels)
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_api_error_raises(self) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            return_value=_mock_response(422, text="Validation Failed")
        )

        with patch(
            "sre_agent.tools.github.client.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(GitHubAPIError):
                await create_pull_request("Title", "Body", "branch")


# ===========================================================================
# GitHubAPIError
# ===========================================================================


class TestGitHubAPIError:
    def test_message_format(self) -> None:
        err = GitHubAPIError(404, "Not Found")
        assert "404" in str(err)
        assert "Not Found" in str(err)
        assert err.status_code == 404
