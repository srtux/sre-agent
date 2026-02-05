"""Unit tests for Cloud Asset Inventory client."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.clients.asset_inventory import (
    get_asset_history,
    get_resource_config,
    list_assets,
    search_assets,
    search_iam_policies,
)


@pytest.fixture
def mock_session():
    """Create a mock authorized session."""
    with patch(
        "sre_agent.tools.clients.asset_inventory._get_authorized_session"
    ) as mock_factory:
        session = MagicMock()
        mock_factory.return_value = session
        yield session


class TestSearchAssets:
    """Tests for search_assets function."""

    @pytest.mark.asyncio
    async def test_search_assets_success(self, mock_session):
        """Test successful asset search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "name": "//compute.googleapis.com/projects/test/zones/us-central1-a/instances/vm-1",
                    "assetType": "compute.googleapis.com/Instance",
                    "displayName": "vm-1",
                    "location": "us-central1-a",
                    "labels": {"env": "prod"},
                    "state": "RUNNING",
                    "project": "projects/test",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await search_assets(
            query="state:RUNNING",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["asset_count"] == 1
        assert result.result["assets"][0]["name"].endswith("vm-1")

    @pytest.mark.asyncio
    async def test_search_assets_with_types(self, mock_session):
        """Test search with asset type filter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        await search_assets(
            query="labels.env:prod",
            asset_types=["compute.googleapis.com/Instance"],
            project_id="test-project",
        )

        # Verify the request was made with correct parameters
        call_args = mock_session.get.call_args
        assert "assetTypes" in call_args.kwargs["params"]

    @pytest.mark.asyncio
    async def test_search_assets_no_project(self):
        """Test search without project ID."""
        with patch(
            "sre_agent.tools.clients.asset_inventory.get_current_project_id",
            return_value=None,
        ):
            result = await search_assets(query="test")
            assert result.status == ToolStatus.ERROR
            assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_search_assets_error(self, mock_session):
        """Test search with API error."""
        mock_session.get.side_effect = Exception("API error")

        result = await search_assets(
            query="test",
            project_id="test-project",
        )

        assert result.status == ToolStatus.ERROR
        assert "Failed to search assets" in result.error


class TestListAssets:
    """Tests for list_assets function."""

    @pytest.mark.asyncio
    async def test_list_assets_success(self, mock_session):
        """Test successful asset listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "//compute.googleapis.com/projects/test/instances/vm-1",
                    "assetType": "compute.googleapis.com/Instance",
                    "updateTime": "2024-01-01T00:00:00Z",
                    "resource": {
                        "version": "v1",
                        "data": {"name": "vm-1", "status": "RUNNING"},
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_assets(project_id="test-project")

        assert result.status == ToolStatus.SUCCESS
        assert result.result["asset_count"] == 1

    @pytest.mark.asyncio
    async def test_list_assets_with_iam(self, mock_session):
        """Test listing assets with IAM policies."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "//storage.googleapis.com/projects/test/buckets/bucket-1",
                    "assetType": "storage.googleapis.com/Bucket",
                    "iamPolicy": {
                        "version": 1,
                        "bindings": [
                            {
                                "role": "roles/viewer",
                                "members": ["user:test@example.com"],
                            }
                        ],
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_assets(
            content_type="IAM_POLICY",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["assets"][0]["iam_policy"] is not None


class TestGetAssetHistory:
    """Tests for get_asset_history function."""

    @pytest.mark.asyncio
    async def test_get_history_success(self, mock_session):
        """Test successful history retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "asset": {
                        "name": "//compute.googleapis.com/projects/test/instances/vm-1",
                        "assetType": "compute.googleapis.com/Instance",
                    },
                    "windows": [
                        {
                            "startTime": "2024-01-01T00:00:00Z",
                            "endTime": "2024-01-02T00:00:00Z",
                            "deleted": False,
                            "asset": {"resource": {"data": {"status": "RUNNING"}}},
                        }
                    ],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await get_asset_history(
            asset_names=["//compute.googleapis.com/projects/test/instances/vm-1"],
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["asset_count"] == 1
        assert len(result.result["assets"][0]["windows"]) == 1

    @pytest.mark.asyncio
    async def test_get_history_no_assets(self):
        """Test history without asset names."""
        result = await get_asset_history(
            asset_names=[],
            project_id="test-project",
        )

        assert result.status == ToolStatus.ERROR
        assert "required" in result.error.lower()


class TestGetResourceConfig:
    """Tests for get_resource_config function."""

    @pytest.mark.asyncio
    async def test_get_config_success(self, mock_session):
        """Test successful resource config retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "asset": {
                        "name": "//compute.googleapis.com/projects/test/instances/vm-1",
                        "assetType": "compute.googleapis.com/Instance",
                        "updateTime": "2024-01-01T00:00:00Z",
                        "resource": {
                            "version": "v1",
                            "data": {
                                "name": "vm-1",
                                "machineType": "n1-standard-1",
                                "status": "RUNNING",
                            },
                        },
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await get_resource_config(
            resource_name="//compute.googleapis.com/projects/test/instances/vm-1",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "resource" in result.result

    @pytest.mark.asyncio
    async def test_get_config_not_found(self, mock_session):
        """Test resource not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"assets": []}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await get_resource_config(
            resource_name="//compute.googleapis.com/projects/test/instances/nonexistent",
            project_id="test-project",
        )

        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error.lower()


class TestSearchIamPolicies:
    """Tests for search_iam_policies function."""

    @pytest.mark.asyncio
    async def test_search_policies_success(self, mock_session):
        """Test successful IAM policy search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "resource": "//storage.googleapis.com/projects/test/buckets/bucket-1",
                    "assetType": "storage.googleapis.com/Bucket",
                    "project": "projects/test",
                    "policy": {
                        "bindings": [
                            {
                                "role": "roles/owner",
                                "members": ["user:admin@example.com"],
                            }
                        ]
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await search_iam_policies(
            query="policy:roles/owner",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["policy_count"] == 1
