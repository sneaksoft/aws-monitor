"""Integration tests for cost endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from httpx import AsyncClient

from app.models.schemas import CostSummaryResponse, CostBreakdownResponse, CostByService


@pytest.mark.asyncio
async def test_get_cost_summary(client: AsyncClient):
    """Test getting cost summary."""
    mock_summary = CostSummaryResponse(
        mtd_cost=1234.56,
        mtd_forecast=2000.00,
        last_month_cost=3000.00,
        ytd_cost=15000.00,
        period_start=datetime.now(),
        period_end=datetime.now(),
    )

    with patch(
        "app.api.routes.cost.CostExplorerService"
    ) as mock_cost_class:
        mock_cost = AsyncMock()
        mock_cost.get_cost_summary.return_value = mock_summary
        mock_cost_class.return_value = mock_cost

        response = await client.get("/api/cost/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["mtd_cost"] == 1234.56
        assert data["ytd_cost"] == 15000.00


@pytest.mark.asyncio
async def test_get_cost_breakdown(client: AsyncClient):
    """Test getting cost breakdown."""
    mock_breakdown = CostBreakdownResponse(
        by_service=[
            CostByService(service="Amazon EC2", cost=500.00, percentage=50.0),
            CostByService(service="Amazon RDS", cost=300.00, percentage=30.0),
        ],
        by_region=[],
        total=1000.00,
        period_start=datetime.now(),
        period_end=datetime.now(),
    )

    with patch(
        "app.api.routes.cost.CostExplorerService"
    ) as mock_cost_class:
        mock_cost = AsyncMock()
        mock_cost.get_cost_breakdown.return_value = mock_breakdown
        mock_cost_class.return_value = mock_cost

        response = await client.get("/api/cost/breakdown")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1000.00
        assert len(data["by_service"]) == 2


@pytest.mark.asyncio
async def test_get_daily_costs(client: AsyncClient):
    """Test getting daily costs."""
    mock_daily = [
        {"date": "2024-01-01", "cost": 100.00},
        {"date": "2024-01-02", "cost": 150.00},
    ]

    with patch(
        "app.api.routes.cost.CostExplorerService"
    ) as mock_cost_class:
        mock_cost = AsyncMock()
        mock_cost.get_daily_costs.return_value = mock_daily
        mock_cost_class.return_value = mock_cost

        response = await client.get("/api/cost/daily?days=30")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["cost"] == 100.00
