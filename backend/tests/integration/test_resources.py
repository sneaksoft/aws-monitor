"""Integration tests for resources endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.models.schemas import ResourceListResponse, ResourceResponse


@pytest.mark.asyncio
async def test_list_resources(client: AsyncClient):
    """Test listing resources endpoint."""
    mock_response = ResourceListResponse(
        items=[
            ResourceResponse(
                resource_id="i-1234567890",
                resource_type="ec2",
                name="test-instance",
                region="us-east-1",
                aws_account_id="123456789012",
                state="running",
                tags={"Name": "test-instance"},
                metadata={},
            )
        ],
        total=1,
        page=1,
        page_size=50,
        has_more=False,
    )

    with patch(
        "app.api.routes.resources.ResourceAggregator"
    ) as mock_aggregator_class:
        mock_aggregator = AsyncMock()
        mock_aggregator.get_resources.return_value = mock_response
        mock_aggregator_class.return_value = mock_aggregator

        response = await client.get("/api/resources")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["resource_id"] == "i-1234567890"


@pytest.mark.asyncio
async def test_list_resources_with_filters(client: AsyncClient):
    """Test listing resources with filters."""
    mock_response = ResourceListResponse(
        items=[],
        total=0,
        page=1,
        page_size=50,
        has_more=False,
    )

    with patch(
        "app.api.routes.resources.ResourceAggregator"
    ) as mock_aggregator_class:
        mock_aggregator = AsyncMock()
        mock_aggregator.get_resources.return_value = mock_response
        mock_aggregator_class.return_value = mock_aggregator

        response = await client.get(
            "/api/resources?resource_type=ec2&state=running&search=test"
        )

        assert response.status_code == 200
        mock_aggregator.get_resources.assert_called_once()


@pytest.mark.asyncio
async def test_get_resource_detail(client: AsyncClient):
    """Test getting resource details."""
    mock_resource = ResourceResponse(
        resource_id="i-1234567890",
        resource_type="ec2",
        name="test-instance",
        region="us-east-1",
        aws_account_id="123456789012",
        state="running",
        tags={"Name": "test-instance"},
        metadata={"instance_type": "t2.micro"},
    )

    with patch(
        "app.api.routes.resources.ResourceAggregator"
    ) as mock_aggregator_class:
        mock_aggregator = AsyncMock()
        mock_aggregator.get_resource_by_id.return_value = mock_resource
        mock_aggregator_class.return_value = mock_aggregator

        response = await client.get("/api/resources/i-1234567890")

        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == "i-1234567890"
        assert data["metadata"]["instance_type"] == "t2.micro"
