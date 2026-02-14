"""Tests for the GitHub @adk_tool wrapper functions.

Covers: github_read_file, github_search_code, github_list_recent_commits,
github_create_pull_request (safety validation, memory integration).

Note: tools.py uses deferred imports (inside function bodies), so we patch
at the client module level (sre_agent.tools.github.client.*).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.github.client import GitHubAPIError
from sre_agent.tools.github.tools import (
    github_create_pull_request,
    github_list_recent_commits,
    github_read_file,
    github_search_code,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT = "sre_agent.tools.github.client"


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


# ===========================================================================
# github_read_file
# ===========================================================================


class TestGithubReadFile:
    @pytest.mark.asyncio
    async def test_success_returns_content(self) -> None:
        file_data = {
            "name": "agent.py",
            "path": "sre_agent/agent.py",
            "content": "# Agent code\nclass SREAgent:\n    pass\n",
            "size": 40,
            "sha": "abc123",
            "html_url": "https://github.com/test/repo/blob/main/sre_agent/agent.py",
        }

        with patch(
            f"{_CLIENT}.get_file_content",
            new_callable=AsyncMock,
            return_value=file_data,
        ):
            result = await github_read_file.__wrapped__("sre_agent/agent.py")

        assert isinstance(result, BaseToolResponse)
        assert result.status == ToolStatus.SUCCESS
        assert result.result["content"] == file_data["content"]

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self) -> None:
        with patch(
            f"{_CLIENT}.get_file_content",
            new_callable=AsyncMock,
            side_effect=GitHubAPIError(404, "File not found: missing.py"),
        ):
            result = await github_read_file.__wrapped__("missing.py")

        assert isinstance(result, BaseToolResponse)
        assert result.status == ToolStatus.ERROR
        assert "404" in result.error

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_error(self) -> None:
        with patch(
            f"{_CLIENT}.get_file_content",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connection failed"),
        ):
            result = await github_read_file.__wrapped__("any.py")

        assert result.status == ToolStatus.ERROR
        assert "Connection failed" in result.error

    @pytest.mark.asyncio
    async def test_saves_to_memory(self, mock_tool_context: MagicMock) -> None:
        file_data = {
            "name": "test.py",
            "path": "test.py",
            "content": "# test content here\n",
            "size": 20,
            "sha": "def456",
            "html_url": "https://example.com",
        }
        mock_manager = MagicMock()
        mock_manager.add_finding = AsyncMock()

        with (
            patch(
                f"{_CLIENT}.get_file_content",
                new_callable=AsyncMock,
                return_value=file_data,
            ),
            patch(
                "sre_agent.tools.github.tools.get_memory_manager",
                return_value=mock_manager,
            ),
            patch(
                "sre_agent.auth.get_user_id_from_tool_context",
                return_value="test@example.com",
            ),
        ):
            result = await github_read_file.__wrapped__(
                "test.py", tool_context=mock_tool_context
            )

        assert result.status == ToolStatus.SUCCESS
        mock_manager.add_finding.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_memory_failure_does_not_break(
        self, mock_tool_context: MagicMock
    ) -> None:
        file_data = {
            "name": "t.py",
            "path": "t.py",
            "content": "x",
            "size": 1,
            "sha": "a",
            "html_url": "",
        }
        mock_manager = MagicMock()
        mock_manager.add_finding = AsyncMock(
            side_effect=RuntimeError("Memory error")
        )

        with (
            patch(
                f"{_CLIENT}.get_file_content",
                new_callable=AsyncMock,
                return_value=file_data,
            ),
            patch(
                "sre_agent.tools.github.tools.get_memory_manager",
                return_value=mock_manager,
            ),
            patch(
                "sre_agent.auth.get_user_id_from_tool_context",
                return_value="test@example.com",
            ),
        ):
            result = await github_read_file.__wrapped__(
                "t.py", tool_context=mock_tool_context
            )

        # Should still succeed despite memory error
        assert result.status == ToolStatus.SUCCESS


# ===========================================================================
# github_search_code
# ===========================================================================


class TestGithubSearchCode:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        search_data = {
            "total_count": 3,
            "items": [
                {
                    "path": "src/a.py",
                    "html_url": "https://example.com/a",
                    "text_matches": ["match1"],
                },
            ],
        }

        with patch(
            f"{_CLIENT}.search_code",
            new_callable=AsyncMock,
            return_value=search_data,
        ):
            result = await github_search_code.__wrapped__("class Agent")

        assert result.status == ToolStatus.SUCCESS
        assert result.result["total_count"] == 3

    @pytest.mark.asyncio
    async def test_max_results_clamped(self) -> None:
        search_data = {"total_count": 0, "items": []}

        with patch(
            f"{_CLIENT}.search_code",
            new_callable=AsyncMock,
            return_value=search_data,
        ) as mock_search:
            await github_search_code.__wrapped__("test", max_results=100)

        # Should be clamped to 30
        mock_search.assert_awaited_once()
        _, kwargs = mock_search.call_args
        assert kwargs["per_page"] == 30

    @pytest.mark.asyncio
    async def test_min_results_clamped(self) -> None:
        search_data = {"total_count": 0, "items": []}

        with patch(
            f"{_CLIENT}.search_code",
            new_callable=AsyncMock,
            return_value=search_data,
        ) as mock_search:
            await github_search_code.__wrapped__("test", max_results=0)

        _, kwargs = mock_search.call_args
        assert kwargs["per_page"] == 1

    @pytest.mark.asyncio
    async def test_api_error_returns_error(self) -> None:
        with patch(
            f"{_CLIENT}.search_code",
            new_callable=AsyncMock,
            side_effect=GitHubAPIError(403, "Rate limited"),
        ):
            result = await github_search_code.__wrapped__("test")

        assert result.status == ToolStatus.ERROR
        assert "403" in result.error


# ===========================================================================
# github_list_recent_commits
# ===========================================================================


class TestGithubListRecentCommits:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        commits = [
            {
                "sha": "abc123",
                "message": "Fix bug",
                "author": "Dev",
                "date": "2026-01-01T00:00:00Z",
                "html_url": "https://example.com",
            },
        ]

        with patch(
            f"{_CLIENT}.list_commits",
            new_callable=AsyncMock,
            return_value=commits,
        ):
            result = await github_list_recent_commits.__wrapped__()

        assert result.status == ToolStatus.SUCCESS
        assert result.result["count"] == 1
        assert result.result["commits"][0]["sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_api_error_returns_error(self) -> None:
        with patch(
            f"{_CLIENT}.list_commits",
            new_callable=AsyncMock,
            side_effect=GitHubAPIError(500, "Server error"),
        ):
            result = await github_list_recent_commits.__wrapped__()

        assert result.status == ToolStatus.ERROR


# ===========================================================================
# github_create_pull_request
# ===========================================================================


class TestGithubCreatePullRequest:
    @pytest.mark.asyncio
    async def test_branch_prefix_validation(self) -> None:
        result = await github_create_pull_request.__wrapped__(
            title="Test",
            description="Desc",
            branch_name="bad-prefix/test",
            file_changes=[{"path": "a.py", "content": "x", "message": "m"}],
        )

        assert result.status == ToolStatus.ERROR
        assert "auto-fix/" in result.error

    @pytest.mark.asyncio
    async def test_empty_file_changes_rejected(self) -> None:
        result = await github_create_pull_request.__wrapped__(
            title="Test",
            description="Desc",
            branch_name="auto-fix/test",
            file_changes=[],
        )

        assert result.status == ToolStatus.ERROR
        assert "At least one file change" in result.error

    @pytest.mark.asyncio
    async def test_invalid_file_change_structure(self) -> None:
        result = await github_create_pull_request.__wrapped__(
            title="Test",
            description="Desc",
            branch_name="auto-fix/test",
            file_changes=[{"path": "a.py"}],  # Missing 'content' and 'message'
        )

        assert result.status == ToolStatus.ERROR
        assert "file_changes[0]" in result.error

    @pytest.mark.asyncio
    async def test_success_creates_branch_commits_and_pr(self) -> None:
        branch_result = {"ref": "refs/heads/auto-fix/test", "sha": "abc123"}
        file_result = {
            "path": "fix.py",
            "sha": "new_sha",
            "html_url": "https://example.com",
        }
        pr_result = {
            "number": 99,
            "html_url": "https://github.com/test/repo/pull/99",
            "title": "Fix: test",
            "state": "open",
            "draft": True,
        }

        with (
            patch(
                f"{_CLIENT}.create_branch",
                new_callable=AsyncMock,
                return_value=branch_result,
            ),
            patch(
                f"{_CLIENT}.create_or_update_file",
                new_callable=AsyncMock,
                return_value=file_result,
            ),
            patch(
                f"{_CLIENT}.create_pull_request",
                new_callable=AsyncMock,
                return_value=pr_result,
            ),
        ):
            result = await github_create_pull_request.__wrapped__(
                title="Fix: test",
                description="Test description",
                branch_name="auto-fix/test",
                file_changes=[
                    {"path": "fix.py", "content": "# fixed", "message": "fix it"}
                ],
            )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["pull_request"]["number"] == 99
        assert result.metadata["draft"] is True
        assert result.metadata["files_changed"] == 1

    @pytest.mark.asyncio
    async def test_api_error_returns_error(self) -> None:
        with patch(
            f"{_CLIENT}.create_branch",
            new_callable=AsyncMock,
            side_effect=GitHubAPIError(422, "Branch already exists"),
        ):
            result = await github_create_pull_request.__wrapped__(
                title="Fix",
                description="Desc",
                branch_name="auto-fix/test",
                file_changes=[{"path": "a.py", "content": "x", "message": "m"}],
            )

        assert result.status == ToolStatus.ERROR
        assert "422" in result.error

    @pytest.mark.asyncio
    async def test_saves_to_memory(self, mock_tool_context: MagicMock) -> None:
        branch_result = {"ref": "refs/heads/auto-fix/mem", "sha": "abc"}
        file_result = {"path": "f.py", "sha": "s", "html_url": "url"}
        pr_result = {
            "number": 7,
            "html_url": "https://example.com/pr/7",
            "title": "T",
            "state": "open",
            "draft": True,
        }

        mock_manager = MagicMock()
        mock_manager.add_finding = AsyncMock()

        with (
            patch(
                f"{_CLIENT}.create_branch",
                new_callable=AsyncMock,
                return_value=branch_result,
            ),
            patch(
                f"{_CLIENT}.create_or_update_file",
                new_callable=AsyncMock,
                return_value=file_result,
            ),
            patch(
                f"{_CLIENT}.create_pull_request",
                new_callable=AsyncMock,
                return_value=pr_result,
            ),
            patch(
                "sre_agent.tools.github.tools.get_memory_manager",
                return_value=mock_manager,
            ),
            patch(
                "sre_agent.auth.get_user_id_from_tool_context",
                return_value="test@example.com",
            ),
        ):
            result = await github_create_pull_request.__wrapped__(
                title="T",
                description="D",
                branch_name="auto-fix/mem",
                file_changes=[{"path": "f.py", "content": "c", "message": "m"}],
                tool_context=mock_tool_context,
            )

        assert result.status == ToolStatus.SUCCESS
        mock_manager.add_finding.assert_awaited_once()
        call_kwargs = mock_manager.add_finding.call_args.kwargs
        assert "PR #7" in call_kwargs["description"]
