"""Resource inventory endpoints."""

from typing import Annotated, Optional
import csv
import io
import json

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse

from app.dependencies import RequireReadonly, get_cache_service
from app.cache import CacheService
from app.models.schemas import ResourceListResponse, ResourceResponse, ResourceFilters
from app.services.aws.aggregator import ResourceAggregator

router = APIRouter()


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    region: Optional[str] = Query(None, description="Filter by region"),
    state: Optional[str] = Query(None, description="Filter by state"),
    tag_key: Optional[str] = Query(None, description="Filter by tag key"),
    tag_value: Optional[str] = Query(None, description="Filter by tag value"),
    search: Optional[str] = Query(None, description="Search in name/id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
):
    """List AWS resources with filtering and pagination."""
    filters = ResourceFilters(
        resource_type=resource_type,
        region=region,
        state=state,
        tag_key=tag_key,
        tag_value=tag_value,
        search=search,
    )

    # Try cache first
    cache_key = f"resources:list:{hash(str(filters.model_dump()))}:{page}:{page_size}"
    cached = await cache.get(cache_key)
    if cached:
        return ResourceListResponse(**cached)

    # Fetch from AWS
    aggregator = ResourceAggregator()
    result = await aggregator.get_resources(
        filters=filters,
        page=page,
        page_size=page_size,
    )

    # Cache result
    await cache.set(cache_key, result.model_dump())

    return result


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    user: RequireReadonly,
    cache: Annotated[CacheService, Depends(get_cache_service)],
):
    """Get detailed information about a specific resource."""
    cache_key = f"resources:detail:{resource_id}"
    cached = await cache.get(cache_key)
    if cached:
        return ResourceResponse(**cached)

    aggregator = ResourceAggregator()
    resource = await aggregator.get_resource_by_id(resource_id)

    await cache.set(cache_key, resource.model_dump())
    return resource


@router.get("/export/csv")
async def export_resources_csv(
    user: RequireReadonly,
    resource_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    """Export resources as CSV."""
    aggregator = ResourceAggregator()
    filters = ResourceFilters(resource_type=resource_type, region=region)
    result = await aggregator.get_resources(filters=filters, page=1, page_size=10000)

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Resource ID", "Type", "Name", "Region", "State", "Tags", "Monthly Cost"
    ])

    for resource in result.items:
        writer.writerow([
            resource.resource_id,
            resource.resource_type,
            resource.name or "",
            resource.region,
            resource.state or "",
            json.dumps(resource.tags),
            resource.monthly_cost or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aws_resources.csv"},
    )


@router.get("/export/json")
async def export_resources_json(
    user: RequireReadonly,
    resource_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    """Export resources as JSON."""
    aggregator = ResourceAggregator()
    filters = ResourceFilters(resource_type=resource_type, region=region)
    result = await aggregator.get_resources(filters=filters, page=1, page_size=10000)

    return Response(
        content=json.dumps([r.model_dump() for r in result.items], default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=aws_resources.json"},
    )
