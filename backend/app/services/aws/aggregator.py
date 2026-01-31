"""Resource aggregator service for combining resources from multiple services."""

import asyncio
from typing import Optional

from app.models.schemas import ResourceResponse, ResourceListResponse, ResourceFilters
from app.services.aws.ec2 import EC2Service
from app.services.aws.rds import RDSService
from app.services.aws.s3 import S3Service
from app.services.aws.ecs import ECSService
from app.services.aws.lambda_ import LambdaService
from app.config import get_settings

settings = get_settings()


class ResourceAggregator:
    """Aggregates resources from multiple AWS services."""

    def __init__(self, region: Optional[str] = None):
        self.region = region or settings.aws_region

    async def get_resources(
        self,
        filters: ResourceFilters,
        page: int = 1,
        page_size: int = 50,
    ) -> ResourceListResponse:
        """Get all resources matching filters with pagination."""
        # Determine which services to query
        resource_types = self._get_resource_types(filters.resource_type)

        # Fetch resources concurrently
        all_resources = await self._fetch_all_resources(resource_types)

        # Apply filters
        filtered = self._apply_filters(all_resources, filters)

        # Sort by name/id
        filtered.sort(key=lambda r: r.name or r.resource_id)

        # Paginate
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        return ResourceListResponse(
            items=paginated,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
        )

    def _get_resource_types(self, filter_type: Optional[str]) -> list[str]:
        """Get list of resource types to query."""
        all_types = ["ec2", "ebs", "rds", "s3", "ecs", "lambda"]

        if filter_type:
            if filter_type in all_types:
                return [filter_type]
            return []

        return all_types

    async def _fetch_all_resources(
        self, resource_types: list[str]
    ) -> list[ResourceResponse]:
        """Fetch resources from all specified services concurrently."""
        tasks = []

        if "ec2" in resource_types:
            tasks.append(self._fetch_ec2())
        if "ebs" in resource_types:
            tasks.append(self._fetch_ebs())
        if "rds" in resource_types:
            tasks.append(self._fetch_rds())
        if "s3" in resource_types:
            tasks.append(self._fetch_s3())
        if "ecs" in resource_types:
            tasks.append(self._fetch_ecs())
        if "lambda" in resource_types:
            tasks.append(self._fetch_lambda())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_resources = []
        for result in results:
            if isinstance(result, Exception):
                # Log error but continue with other resources
                continue
            all_resources.extend(result)

        return all_resources

    async def _fetch_ec2(self) -> list[ResourceResponse]:
        """Fetch EC2 instances."""
        service = EC2Service(region=self.region)
        return await service.list_instances()

    async def _fetch_ebs(self) -> list[ResourceResponse]:
        """Fetch EBS volumes."""
        service = EC2Service(region=self.region)
        return await service.list_volumes()

    async def _fetch_rds(self) -> list[ResourceResponse]:
        """Fetch RDS instances."""
        service = RDSService(region=self.region)
        instances = await service.list_instances()
        clusters = await service.list_clusters()
        return instances + clusters

    async def _fetch_s3(self) -> list[ResourceResponse]:
        """Fetch S3 buckets."""
        service = S3Service(region=self.region)
        return await service.list_buckets()

    async def _fetch_ecs(self) -> list[ResourceResponse]:
        """Fetch ECS services."""
        service = ECSService(region=self.region)
        clusters = await service.list_clusters()

        all_services = []
        for cluster in clusters:
            services = await service.list_services(cluster)
            all_services.extend(services)

        return all_services

    async def _fetch_lambda(self) -> list[ResourceResponse]:
        """Fetch Lambda functions."""
        service = LambdaService(region=self.region)
        return await service.list_functions()

    def _apply_filters(
        self,
        resources: list[ResourceResponse],
        filters: ResourceFilters,
    ) -> list[ResourceResponse]:
        """Apply filters to resource list."""
        filtered = resources

        if filters.resource_type:
            filtered = [r for r in filtered if r.resource_type == filters.resource_type]

        if filters.region:
            filtered = [r for r in filtered if r.region == filters.region]

        if filters.state:
            filtered = [r for r in filtered if r.state == filters.state]

        if filters.tag_key:
            if filters.tag_value:
                filtered = [
                    r for r in filtered
                    if r.tags.get(filters.tag_key) == filters.tag_value
                ]
            else:
                filtered = [r for r in filtered if filters.tag_key in r.tags]

        if filters.search:
            search_lower = filters.search.lower()
            filtered = [
                r for r in filtered
                if search_lower in r.resource_id.lower()
                or (r.name and search_lower in r.name.lower())
            ]

        return filtered

    async def get_resource_by_id(self, resource_id: str) -> Optional[ResourceResponse]:
        """Get a specific resource by its ID."""
        # Determine resource type from ID pattern
        if resource_id.startswith("i-"):
            service = EC2Service(region=self.region)
            return await service.get_instance(resource_id)
        elif resource_id.startswith("vol-"):
            # EBS volume
            service = EC2Service(region=self.region)
            volumes = await service.list_volumes()
            return next((v for v in volumes if v.resource_id == resource_id), None)
        elif "/" in resource_id and not resource_id.startswith("arn:"):
            # ECS service (cluster/service format)
            parts = resource_id.split("/")
            if len(parts) == 2:
                service = ECSService(region=self.region)
                return await service.get_service(parts[0], parts[1])
        elif not resource_id.startswith(("arn:", "i-", "vol-")):
            # Could be RDS, S3, or Lambda
            # Try each service
            rds = RDSService(region=self.region)
            rds_instance = await rds.get_instance(resource_id)
            if rds_instance:
                return rds_instance

            s3 = S3Service(region=self.region)
            bucket = await s3.get_bucket(resource_id)
            if bucket:
                return bucket

            lambda_svc = LambdaService(region=self.region)
            func = await lambda_svc.get_function(resource_id)
            if func:
                return func

        return None
