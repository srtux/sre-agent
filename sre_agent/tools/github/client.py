"""GitHub REST API client for SRE Agent.

Thin async wrapper around the GitHub REST API using httpx.
Authenticates via GITHUB_TOKEN environment variable.
"""

import base64
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
_HTTP_TIMEOUT_SECONDS = 20
_DEFAULT_REPO = "srtux/sre-agent"


class GitHubAPIError(Exception):
    """Raised when a GitHub API call fails."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize with HTTP status code and error message."""
        self.status_code = status_code
        super().__init__(f"GitHub API {status_code}: {message}")


def _get_token() -> str | None:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN", "")


def _get_repo() -> str:
    """Get the target repository from environment."""
    return os.environ.get("GITHUB_REPO", _DEFAULT_REPO)


def _headers(token: str) -> dict[str, str]:
    """Build request headers with auth."""
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AutoSRE-Agent/0.2",
    }


async def get_file_content(
    path: str,
    ref: str = "main",
    repo: str | None = None,
) -> dict[str, Any]:
    """Read a file from a GitHub repository.

    Returns:
        Dict with keys: name, path, content (decoded), size, sha, html_url.
    """
    token = _get_token()
    if not token:
        raise GitHubAPIError(401, "GITHUB_TOKEN environment variable is not set.")

    repo = repo or _get_repo()
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
    params = {"ref": ref}

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.get(url, headers=_headers(token), params=params)

    if resp.status_code == 404:
        raise GitHubAPIError(404, f"File not found: {path} (ref={ref})")
    if resp.status_code != 200:
        raise GitHubAPIError(resp.status_code, resp.text[:500])

    data = resp.json()

    # Decode base64 content
    content = ""
    if data.get("encoding") == "base64" and data.get("content"):
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    elif data.get("content"):
        content = data["content"]

    return {
        "name": data.get("name", ""),
        "path": data.get("path", path),
        "content": content,
        "size": data.get("size", 0),
        "sha": data.get("sha", ""),
        "html_url": data.get("html_url", ""),
    }


async def search_code(
    query: str,
    repo: str | None = None,
    extension: str | None = None,
    per_page: int = 10,
) -> dict[str, Any]:
    """Search code in a GitHub repository.

    Returns:
        Dict with keys: total_count, items (list of {path, html_url, text_matches}).
    """
    token = _get_token()
    if not token:
        raise GitHubAPIError(401, "GITHUB_TOKEN environment variable is not set.")

    repo = repo or _get_repo()
    q = f"{query} repo:{repo}"
    if extension:
        q += f" extension:{extension}"

    params: dict[str, str | int] = {
        "q": q,
        "per_page": min(per_page, 30),
    }

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.get(
            f"{GITHUB_API_BASE}/search/code",
            headers={
                **_headers(token),
                "Accept": "application/vnd.github.text-match+json",
            },
            params=params,
        )

    if resp.status_code != 200:
        raise GitHubAPIError(resp.status_code, resp.text[:500])

    data = resp.json()
    items = []
    for item in data.get("items", []):
        matches = []
        for tm in item.get("text_matches", []):
            matches.append(tm.get("fragment", ""))
        items.append(
            {
                "path": item.get("path", ""),
                "html_url": item.get("html_url", ""),
                "text_matches": matches,
            }
        )

    return {
        "total_count": data.get("total_count", 0),
        "items": items,
    }


async def list_commits(
    repo: str | None = None,
    sha: str = "main",
    per_page: int = 10,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """List recent commits from a repository.

    Returns:
        List of dicts with keys: sha, message, author, date, html_url.
    """
    token = _get_token()
    if not token:
        raise GitHubAPIError(401, "GITHUB_TOKEN environment variable is not set.")

    repo = repo or _get_repo()
    params: dict[str, str | int] = {
        "sha": sha,
        "per_page": min(per_page, 50),
    }
    if path:
        params["path"] = path

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo}/commits",
            headers=_headers(token),
            params=params,
        )

    if resp.status_code != 200:
        raise GitHubAPIError(resp.status_code, resp.text[:500])

    commits = []
    for c in resp.json():
        commit_data = c.get("commit", {})
        author = commit_data.get("author", {})
        commits.append(
            {
                "sha": c.get("sha", "")[:12],
                "message": commit_data.get("message", "").split("\n")[0],
                "author": author.get("name", ""),
                "date": author.get("date", ""),
                "html_url": c.get("html_url", ""),
            }
        )

    return commits


async def create_branch(
    branch_name: str,
    from_ref: str = "main",
    repo: str | None = None,
) -> dict[str, Any]:
    """Create a new branch from a ref.

    Returns:
        Dict with keys: ref, sha.
    """
    token = _get_token()
    if not token:
        raise GitHubAPIError(401, "GITHUB_TOKEN environment variable is not set.")

    repo = repo or _get_repo()

    # Get the SHA of from_ref
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        ref_resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo}/git/ref/heads/{from_ref}",
            headers=_headers(token),
        )

    if ref_resp.status_code != 200:
        raise GitHubAPIError(
            ref_resp.status_code,
            f"Cannot resolve ref '{from_ref}': {ref_resp.text[:300]}",
        )

    sha = ref_resp.json()["object"]["sha"]

    # Create the new branch
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        create_resp = await client.post(
            f"{GITHUB_API_BASE}/repos/{repo}/git/refs",
            headers=_headers(token),
            json={"ref": f"refs/heads/{branch_name}", "sha": sha},
        )

    if create_resp.status_code not in (200, 201):
        raise GitHubAPIError(create_resp.status_code, create_resp.text[:500])

    return {
        "ref": f"refs/heads/{branch_name}",
        "sha": sha,
    }


async def create_or_update_file(
    path: str,
    content: str,
    message: str,
    branch: str,
    repo: str | None = None,
) -> dict[str, Any]:
    """Create or update a file in a repository.

    Returns:
        Dict with keys: path, sha, html_url.
    """
    token = _get_token()
    if not token:
        raise GitHubAPIError(401, "GITHUB_TOKEN environment variable is not set.")

    repo = repo or _get_repo()

    # Check if file exists to get its SHA (needed for updates)
    existing_sha: str | None = None
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        check_resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}",
            headers=_headers(token),
            params={"ref": branch},
        )
        if check_resp.status_code == 200:
            existing_sha = check_resp.json().get("sha")

    # Create/update the file
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    body: dict[str, Any] = {
        "message": message,
        "content": encoded,
        "branch": branch,
    }
    if existing_sha:
        body["sha"] = existing_sha

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.put(
            f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}",
            headers=_headers(token),
            json=body,
        )

    if resp.status_code not in (200, 201):
        raise GitHubAPIError(resp.status_code, resp.text[:500])

    result = resp.json().get("content", {})
    return {
        "path": result.get("path", path),
        "sha": result.get("sha", ""),
        "html_url": result.get("html_url", ""),
    }


async def create_pull_request(
    title: str,
    body: str,
    head: str,
    base: str = "main",
    draft: bool = True,
    labels: list[str] | None = None,
    repo: str | None = None,
) -> dict[str, Any]:
    """Create a pull request.

    Returns:
        Dict with keys: number, html_url, title, state, draft.
    """
    token = _get_token()
    if not token:
        raise GitHubAPIError(401, "GITHUB_TOKEN environment variable is not set.")

    repo = repo or _get_repo()

    pr_body: dict[str, Any] = {
        "title": title,
        "body": body,
        "head": head,
        "base": base,
        "draft": draft,
    }

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{GITHUB_API_BASE}/repos/{repo}/pulls",
            headers=_headers(token),
            json=pr_body,
        )

    if resp.status_code not in (200, 201):
        raise GitHubAPIError(resp.status_code, resp.text[:500])

    pr = resp.json()
    result = {
        "number": pr.get("number"),
        "html_url": pr.get("html_url", ""),
        "title": pr.get("title", ""),
        "state": pr.get("state", ""),
        "draft": pr.get("draft", True),
    }

    # Add labels if requested
    if labels and result["number"]:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            await client.post(
                f"{GITHUB_API_BASE}/repos/{repo}/issues/{result['number']}/labels",
                headers=_headers(token),
                json={"labels": labels},
            )

    return result
