"""ECS service for cluster and service operations."""

from typing import Any, Optional

from app.services.aws.base import AWSBaseService
from app.models.schemas import ResourceResponse


class ECSService(AWSBaseService):
    """Service for ECS operations."""

    async def list_clusters(self) -> list[str]:
        """List all ECS cluster ARNs."""
        async with await self.get_client("ecs") as ecs:
            cluster_arns = []
            paginator = ecs.get_paginator("list_clusters")
            async for page in paginator.paginate():
                cluster_arns.extend(page.get("clusterArns", []))
            return cluster_arns

    async def list_services(self, cluster: str) -> list[ResourceResponse]:
        """List all services in a cluster."""
        resources = []
        async with await self.get_client("ecs") as ecs:
            # Get service ARNs
            service_arns = []
            paginator = ecs.get_paginator("list_services")
            async for page in paginator.paginate(cluster=cluster):
                service_arns.extend(page.get("serviceArns", []))

            if not service_arns:
                return resources

            # Get service details (max 10 at a time)
            for i in range(0, len(service_arns), 10):
                batch = service_arns[i : i + 10]
                response = await ecs.describe_services(
                    cluster=cluster,
                    services=batch,
                )
                for service in response.get("services", []):
                    resources.append(self._service_to_resource(cluster, service))

        return resources

    def _service_to_resource(self, cluster: str, service: dict) -> ResourceResponse:
        """Convert ECS service to ResourceResponse."""
        tags = {tag["key"]: tag["value"] for tag in service.get("tags", [])}

        # Extract cluster name from ARN
        cluster_name = cluster.split("/")[-1] if "/" in cluster else cluster

        return ResourceResponse(
            resource_id=f"{cluster_name}/{service['serviceName']}",
            resource_type="ecs",
            name=service["serviceName"],
            region=self.region,
            aws_account_id="",
            state=service.get("status"),
            tags=tags,
            metadata={
                "cluster": cluster_name,
                "service_arn": service.get("serviceArn"),
                "desired_count": service.get("desiredCount"),
                "running_count": service.get("runningCount"),
                "pending_count": service.get("pendingCount"),
                "launch_type": service.get("launchType"),
                "platform_version": service.get("platformVersion"),
                "task_definition": service.get("taskDefinition"),
                "load_balancers": [
                    {
                        "target_group_arn": lb.get("targetGroupArn"),
                        "container_name": lb.get("containerName"),
                        "container_port": lb.get("containerPort"),
                    }
                    for lb in service.get("loadBalancers", [])
                ],
                "deployment_configuration": {
                    "maximum_percent": service.get("deploymentConfiguration", {}).get(
                        "maximumPercent"
                    ),
                    "minimum_healthy_percent": service.get(
                        "deploymentConfiguration", {}
                    ).get("minimumHealthyPercent"),
                },
                "created_at": service.get("createdAt").isoformat() if service.get("createdAt") else None,
            },
        )

    async def get_service(
        self, cluster: str, service_name: str
    ) -> Optional[ResourceResponse]:
        """Get details for a specific service."""
        async with await self.get_client("ecs") as ecs:
            response = await ecs.describe_services(
                cluster=cluster,
                services=[service_name],
            )
            services = response.get("services", [])
            if services:
                return self._service_to_resource(cluster, services[0])
        return None

    async def scale_service(
        self,
        cluster: str,
        service: str,
        desired_count: int,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Scale an ECS service to desired count."""
        if dry_run:
            current_service = await self.get_service(cluster, service)
            if current_service:
                return {
                    "would_scale": f"{cluster}/{service}",
                    "current_count": current_service.metadata.get("desired_count"),
                    "desired_count": desired_count,
                    "dry_run": True,
                }
            return {"error": "Service not found", "dry_run": True}

        async with await self.get_client("ecs") as ecs:
            response = await ecs.update_service(
                cluster=cluster,
                service=service,
                desiredCount=desired_count,
            )
            svc = response.get("service", {})
            return {
                "service": svc.get("serviceName"),
                "cluster": cluster,
                "desired_count": svc.get("desiredCount"),
                "running_count": svc.get("runningCount"),
                "status": svc.get("status"),
            }

    async def delete_service(
        self,
        cluster: str,
        service: str,
        force: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Delete an ECS service."""
        if dry_run:
            current_service = await self.get_service(cluster, service)
            if current_service:
                return {
                    "would_delete": f"{cluster}/{service}",
                    "current_count": current_service.metadata.get("running_count"),
                    "force": force,
                    "dry_run": True,
                }
            return {"error": "Service not found", "dry_run": True}

        async with await self.get_client("ecs") as ecs:
            # Scale to 0 first if not forcing
            if not force:
                await ecs.update_service(
                    cluster=cluster,
                    service=service,
                    desiredCount=0,
                )

            response = await ecs.delete_service(
                cluster=cluster,
                service=service,
                force=force,
            )
            svc = response.get("service", {})
            return {
                "deleted": svc.get("serviceName"),
                "cluster": cluster,
                "status": svc.get("status"),
            }

    async def list_tasks(self, cluster: str, service: str = None) -> list[dict]:
        """List tasks in a cluster/service."""
        async with await self.get_client("ecs") as ecs:
            list_kwargs = {"cluster": cluster}
            if service:
                list_kwargs["serviceName"] = service

            task_arns = []
            paginator = ecs.get_paginator("list_tasks")
            async for page in paginator.paginate(**list_kwargs):
                task_arns.extend(page.get("taskArns", []))

            if not task_arns:
                return []

            # Get task details
            response = await ecs.describe_tasks(cluster=cluster, tasks=task_arns)
            return [
                {
                    "task_arn": task.get("taskArn"),
                    "task_definition": task.get("taskDefinitionArn"),
                    "last_status": task.get("lastStatus"),
                    "desired_status": task.get("desiredStatus"),
                    "launch_type": task.get("launchType"),
                    "started_at": task.get("startedAt").isoformat() if task.get("startedAt") else None,
                    "cpu": task.get("cpu"),
                    "memory": task.get("memory"),
                }
                for task in response.get("tasks", [])
            ]
