"""GitHub integration tools for SRE Agent self-healing.

Provides tools for the agent to read its own source code, search
for patterns, and create pull requests to fix itself.

Tools:
- github_read_file: Read a file from the agent's GitHub repository
- github_search_code: Search the codebase for patterns
- github_list_recent_commits: List recent commits for context
- github_create_pull_request: Create a PR with proposed changes
"""

from .tools import (
    github_create_pull_request,
    github_list_recent_commits,
    github_read_file,
    github_search_code,
)

__all__ = [
    "github_create_pull_request",
    "github_list_recent_commits",
    "github_read_file",
    "github_search_code",
]
