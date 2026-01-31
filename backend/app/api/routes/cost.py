"""Cost analysis endpoints."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import RequireReadonly, get_cache_service
from app.cache import CacheService
from app.models.schemas import (
    CostSummaryResponse,
    CostBreakdownResponse,
    CostForecastResponse,
    CostRecommendationsResponse,
)
from app.services.aws.cost_explorer import CostExplorerService

router = APIRouter()


@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
):
    """Get cost summary (MTD, last month, YTD)."""
    cache_key = "cost:summary"
    cached = await cache.get(cache_key)
    if cached:
        return CostSummaryResponse(**cached)

    cost_service = CostExplorerService()
    result = await cost_service.get_cost_summary()

    await cache.set(cache_key, result.model_dump(), ttl=3600)  # Cache for 1 hour
    return result


@router.get("/breakdown", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    start_date: Optional[datetime] = Query(None, description="Start date for cost period"),
    end_date: Optional[datetime] = Query(None, description="End date for cost period"),
    granularity: str = Query("MONTHLY", description="DAILY, MONTHLY, or YEARLY"),
):
    """Get cost breakdown by service and region."""
    cache_key = f"cost:breakdown:{start_date}:{end_date}:{granularity}"
    cached = await cache.get(cache_key)
    if cached:
        return CostBreakdownResponse(**cached)

    cost_service = CostExplorerService()
    result = await cost_service.get_cost_breakdown(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )

    await cache.set(cache_key, result.model_dump(), ttl=3600)
    return result


@router.get("/forecast", response_model=CostForecastResponse)
async def get_cost_forecast(
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
):
    """Get forecasted costs for current month."""
    cache_key = "cost:forecast"
    cached = await cache.get(cache_key)
    if cached:
        return CostForecastResponse(**cached)

    cost_service = CostExplorerService()
    result = await cost_service.get_cost_forecast()

    await cache.set(cache_key, result.model_dump(), ttl=3600)
    return result


@router.get("/recommendations", response_model=CostRecommendationsResponse)
async def get_cost_recommendations(
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
):
    """Get cost optimization recommendations."""
    cache_key = "cost:recommendations"
    cached = await cache.get(cache_key)
    if cached:
        return CostRecommendationsResponse(**cached)

    cost_service = CostExplorerService()
    result = await cost_service.get_recommendations()

    await cache.set(cache_key, result.model_dump(), ttl=1800)  # 30 minutes
    return result


@router.get("/daily")
async def get_daily_costs(
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    days: int = Query(30, ge=1, le=90),
):
    """Get daily costs for the last N days."""
    cache_key = f"cost:daily:{days}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cost_service = CostExplorerService()
    result = await cost_service.get_daily_costs(days=days)

    await cache.set(cache_key, result, ttl=3600)
    return result


@router.get("/by-tag")
async def get_costs_by_tag(
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    tag_key: str = Query(..., description="Tag key to group by"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """Get costs grouped by tag value."""
    cache_key = f"cost:bytag:{tag_key}:{start_date}:{end_date}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cost_service = CostExplorerService()
    result = await cost_service.get_costs_by_tag(
        tag_key=tag_key,
        start_date=start_date,
        end_date=end_date,
    )

    await cache.set(cache_key, result, ttl=3600)
    return result
