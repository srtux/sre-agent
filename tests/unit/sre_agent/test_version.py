"""Tests for sre_agent.version module."""

from unittest.mock import patch


class TestGetPackageVersion:
    def test_returns_installed_version(self) -> None:
        with patch("importlib.metadata.version", return_value="1.2.3"):
            from sre_agent.version import _get_package_version

            assert _get_package_version() == "1.2.3"

    def test_returns_dev_when_not_installed(self) -> None:
        import importlib.metadata

        with patch(
            "importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError,
        ):
            from sre_agent.version import _get_package_version

            assert _get_package_version() == "0.0.0-dev"


class TestGetGitSha:
    def test_prefers_build_sha_env(self) -> None:
        with patch.dict("os.environ", {"BUILD_SHA": "abc123def456789"}):
            from sre_agent.version import _get_git_sha

            result = _get_git_sha()
            assert result == "abc123def456"

    def test_falls_back_to_git_command(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=False),
            patch("subprocess.run") as mock_run,
        ):
            # Remove BUILD_SHA if present
            import os

            os.environ.pop("BUILD_SHA", None)

            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "deadbeef1234\n"

            from sre_agent.version import _get_git_sha

            assert _get_git_sha() == "deadbeef1234"

    def test_returns_unknown_on_failure(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=False),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            import os

            os.environ.pop("BUILD_SHA", None)

            from sre_agent.version import _get_git_sha

            assert _get_git_sha() == "unknown"


class TestGetBuildTimestamp:
    def test_prefers_build_timestamp_env(self) -> None:
        with patch.dict("os.environ", {"BUILD_TIMESTAMP": "2025-01-15T12:00:00Z"}):
            from sre_agent.version import _get_build_timestamp

            assert _get_build_timestamp() == "2025-01-15T12:00:00Z"

    def test_falls_back_to_current_time(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("BUILD_TIMESTAMP", None)

            from sre_agent.version import _get_build_timestamp

            result = _get_build_timestamp()
            # Should be an ISO timestamp
            assert "T" in result
            assert result.endswith("Z")


class TestGetVersionInfo:
    def test_returns_dict_with_expected_keys(self) -> None:
        from sre_agent.version import get_version_info

        info = get_version_info()
        assert "version" in info
        assert "git_sha" in info
        assert "build_timestamp" in info
        assert isinstance(info["version"], str)
        assert isinstance(info["git_sha"], str)
        assert isinstance(info["build_timestamp"], str)
