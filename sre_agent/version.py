"""Build version and metadata.

Reads the package version from pyproject.toml and supplements it with
build-time metadata injected via environment variables (BUILD_SHA,
BUILD_TIMESTAMP).  These env vars are set by Cloud Build / Docker at
image build time; when running locally they fall back to git and the
current time.
"""

from __future__ import annotations

import datetime
import importlib.metadata
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

_PACKAGE_NAME = "sre-agent"


def _get_package_version() -> str:
    """Return the package version from installed metadata."""
    try:
        return importlib.metadata.version(_PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev"


def _get_git_sha() -> str:
    """Return the short git SHA, preferring the BUILD_SHA env var."""
    sha = os.environ.get("BUILD_SHA", "").strip()
    if sha:
        return sha[:12]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        logger.debug("Could not determine git SHA")
    return "unknown"


def _get_build_timestamp() -> str:
    """Return the build timestamp, preferring the BUILD_TIMESTAMP env var."""
    ts = os.environ.get("BUILD_TIMESTAMP", "").strip()
    if ts:
        return ts
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Public API ---

VERSION: str = _get_package_version()
GIT_SHA: str = _get_git_sha()
BUILD_TIMESTAMP: str = _get_build_timestamp()


def get_version_info() -> dict[str, str]:
    """Return a dict of version metadata suitable for API responses."""
    return {
        "version": VERSION,
        "git_sha": GIT_SHA,
        "build_timestamp": BUILD_TIMESTAMP,
    }
