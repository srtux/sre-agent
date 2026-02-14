"""GitHub tools for SRE Agent self-healing.

Provides @adk_tool functions for reading, searching, and modifying
the agent's own source code on GitHub. Results are saved to memory.
"""

import logging
from typing import Annotated, Any

from sre_agent.memory.factory import get_memory_manager
from sre_agent.schema import BaseToolResponse, Confidence, ToolStatus
from sre_agent.tools.common.decorators import adk_tool

from .client import GitHubAPIError

logger = logging.getLogger(__name__)


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


@adk_tool(skip_summarization=True)
async def github_read_file(
    file_path: Annotated[
        str,
        "Path to the file in the repository (e.g. 'sre_agent/tools/clients/trace.py')",
    ],
    ref: Annotated[
        str,
        "Git ref to read from (branch, tag, or commit SHA)",
    ] = "main",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Read a file from the SRE Agent's own GitHub repository.

    Use this to inspect the agent's own source code when:
    - You detect an anti-pattern and want to understand the implementation.
    - You need to check the current prompt or tool configuration.
    - You want to read test files to understand expected behavior.
    - You are preparing a fix and need to see the current code.

    Returns the full file content, decoded from base64.
    """
    from .client import get_file_content

    try:
        result = await get_file_content(path=file_path, ref=ref)
    except GitHubAPIError as e:
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    except Exception as e:
        logger.error(f"github_read_file failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR, error=f"Failed to read file: {e}"
        )

    # Save to memory
    if tool_context is not None:
        try:
            manager = get_memory_manager()
            session_id, user_id = _get_context(tool_context)
            preview = result["content"][:150].replace("\n", " ")
            await manager.add_finding(
                description=f"Read source file '{file_path}' (ref={ref}): {preview}...",
                source_tool="github_read_file",
                confidence=Confidence.HIGH,
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to save to memory: {e}")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result=result,
        metadata={"ref": ref},
    )


@adk_tool(skip_summarization=True)
async def github_search_code(
    query: Annotated[
        str,
        "Search query (e.g. 'def list_log_entries', 'circuit_breaker', 'class BaseToolResponse')",
    ],
    file_extension: Annotated[
        str | None,
        "Filter by file extension (e.g. 'py', 'yaml', 'md')",
    ] = None,
    max_results: Annotated[
        int,
        "Maximum results to return (1-30, default 10)",
    ] = 10,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Search the SRE Agent's GitHub repository for code patterns.

    Use this to find where specific functions, classes, or patterns
    are defined in the codebase. Useful for:
    - Locating a tool definition before modifying it.
    - Finding all usages of a specific pattern or function.
    - Understanding how a feature is implemented across files.
    """
    from .client import search_code

    max_results = max(1, min(max_results, 30))

    try:
        result = await search_code(
            query=query,
            extension=file_extension,
            per_page=max_results,
        )
    except GitHubAPIError as e:
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    except Exception as e:
        logger.error(f"github_search_code failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR, error=f"Code search failed: {e}"
        )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result=result,
        metadata={"query": query, "extension": file_extension},
    )


@adk_tool(skip_summarization=True)
async def github_list_recent_commits(
    branch: Annotated[
        str,
        "Branch to list commits from",
    ] = "main",
    file_path: Annotated[
        str | None,
        "Optional file path to filter commits (e.g. 'sre_agent/prompt.py')",
    ] = None,
    max_results: Annotated[
        int,
        "Maximum commits to return (1-50, default 10)",
    ] = 10,
    tool_context: Any = None,
) -> BaseToolResponse:
    """List recent commits from the SRE Agent's repository.

    Use this to understand recent changes, find when a bug was
    introduced, or gather context before creating a fix PR.
    """
    from .client import list_commits

    max_results = max(1, min(max_results, 50))

    try:
        commits = await list_commits(
            sha=branch,
            per_page=max_results,
            path=file_path,
        )
    except GitHubAPIError as e:
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    except Exception as e:
        logger.error(f"github_list_recent_commits failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR, error=f"Failed to list commits: {e}"
        )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={"commits": commits, "branch": branch, "count": len(commits)},
        metadata={"branch": branch, "file_path": file_path},
    )


@adk_tool(skip_summarization=True)
async def github_create_pull_request(
    title: Annotated[
        str,
        "PR title (concise, under 72 chars)",
    ],
    description: Annotated[
        str,
        "PR body with summary of changes, motivation, and test plan",
    ],
    branch_name: Annotated[
        str,
        "Name for the new branch (e.g. 'auto-fix/improve-log-filter-validation')",
    ],
    file_changes: Annotated[
        list[dict[str, str]],
        "List of file changes. Each dict has: 'path' (file path), 'content' (new content), 'message' (commit message)",
    ],
    base_branch: Annotated[
        str,
        "Base branch for the PR",
    ] = "main",
    draft: Annotated[
        bool,
        "Create as draft PR (default True for safety)",
    ] = True,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Create a pull request with proposed changes to the SRE Agent's code.

    This is the agent's self-healing mechanism. Use this when you have
    identified a fix for an anti-pattern, bug, or improvement and want
    to propose the change via a pull request.

    Safety:
    - PRs are created as drafts by default (require human approval to merge).
    - All PRs are labeled 'agent-generated' for audit trail.
    - The CI/CD pipeline validates changes before deployment.
    - Human review is always required before merge.

    Args:
        title: Short PR title.
        description: Detailed description with motivation and test plan.
        branch_name: New branch name (must start with 'auto-fix/').
        file_changes: List of dicts with 'path', 'content', 'message'.
        base_branch: Base branch (default 'main').
        draft: Create as draft (default True).
        tool_context: ADK tool context for memory integration.
    """
    from .client import (
        create_branch,
        create_or_update_file,
        create_pull_request,
    )

    # Validate branch name prefix for safety
    if not branch_name.startswith("auto-fix/"):
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Branch name must start with 'auto-fix/' for agent-generated changes.",
        )

    if not file_changes:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="At least one file change is required.",
        )

    # Validate file_changes structure
    for i, fc in enumerate(file_changes):
        if not all(k in fc for k in ("path", "content", "message")):
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"file_changes[{i}] must have 'path', 'content', and 'message' keys.",
            )

    try:
        # Step 1: Create branch
        branch_result = await create_branch(
            branch_name=branch_name,
            from_ref=base_branch,
        )

        # Step 2: Commit each file change
        committed_files = []
        for fc in file_changes:
            file_result = await create_or_update_file(
                path=fc["path"],
                content=fc["content"],
                message=fc["message"],
                branch=branch_name,
            )
            committed_files.append(file_result)

        # Step 3: Create PR
        pr_body = f"{description}\n\n---\n*This PR was automatically generated by the SRE Agent self-healing system.*"
        pr_result = await create_pull_request(
            title=title,
            body=pr_body,
            head=branch_name,
            base=base_branch,
            draft=draft,
            labels=["agent-generated", "auto-fix"],
        )

    except GitHubAPIError as e:
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    except Exception as e:
        logger.error(f"github_create_pull_request failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Failed to create PR: {e}",
        )

    # Save to memory
    if tool_context is not None:
        try:
            manager = get_memory_manager()
            session_id, user_id = _get_context(tool_context)
            files = ", ".join(fc["path"] for fc in file_changes)
            await manager.add_finding(
                description=(
                    f"Created PR #{pr_result['number']}: {title}. "
                    f"Files changed: {files}. URL: {pr_result['html_url']}"
                ),
                source_tool="github_create_pull_request",
                confidence=Confidence.HIGH,
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to save PR to memory: {e}")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "pull_request": pr_result,
            "branch": branch_result,
            "committed_files": committed_files,
        },
        metadata={
            "pr_number": pr_result.get("number"),
            "draft": draft,
            "files_changed": len(file_changes),
        },
    )
