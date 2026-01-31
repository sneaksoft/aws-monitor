"""Lambda service for function operations."""

from typing import Any, Optional

from app.services.aws.base import AWSBaseService
from app.models.schemas import ResourceResponse


class LambdaService(AWSBaseService):
    """Service for Lambda operations."""

    async def list_functions(self) -> list[ResourceResponse]:
        """List all Lambda functions."""
        resources = []
        async with await self.get_client("lambda") as lambda_client:
            paginator = lambda_client.get_paginator("list_functions")
            async for page in paginator.paginate():
                for func in page.get("Functions", []):
                    resources.append(self._function_to_resource(func))
        return resources

    def _function_to_resource(self, func: dict) -> ResourceResponse:
        """Convert Lambda function to ResourceResponse."""
        return ResourceResponse(
            resource_id=func["FunctionName"],
            resource_type="lambda",
            name=func["FunctionName"],
            region=self.region,
            aws_account_id="",
            state=func.get("State", "Active"),
            tags={},  # Tags fetched separately
            metadata={
                "function_arn": func.get("FunctionArn"),
                "runtime": func.get("Runtime"),
                "handler": func.get("Handler"),
                "code_size": func.get("CodeSize"),
                "memory_size": func.get("MemorySize"),
                "timeout": func.get("Timeout"),
                "description": func.get("Description"),
                "last_modified": func.get("LastModified"),
                "role": func.get("Role"),
                "vpc_config": {
                    "vpc_id": func.get("VpcConfig", {}).get("VpcId"),
                    "subnets": func.get("VpcConfig", {}).get("SubnetIds", []),
                    "security_groups": func.get("VpcConfig", {}).get(
                        "SecurityGroupIds", []
                    ),
                }
                if func.get("VpcConfig")
                else None,
                "environment": list(func.get("Environment", {}).get("Variables", {}).keys()),
                "architectures": func.get("Architectures", ["x86_64"]),
                "ephemeral_storage": func.get("EphemeralStorage", {}).get("Size"),
            },
        )

    async def get_function(self, function_name: str) -> Optional[ResourceResponse]:
        """Get details for a specific function."""
        async with await self.get_client("lambda") as lambda_client:
            try:
                response = await lambda_client.get_function(FunctionName=function_name)
                func = response.get("Configuration", {})
                resource = self._function_to_resource(func)

                # Get tags
                tags_response = await lambda_client.list_tags(
                    Resource=func.get("FunctionArn")
                )
                resource.tags = tags_response.get("Tags", {})

                return resource
            except Exception:
                return None

    async def get_function_metrics(
        self,
        function_name: str,
        hours: int = 168,  # 7 days
    ) -> dict[str, Any]:
        """Get CloudWatch metrics for a function."""
        from datetime import datetime, timedelta

        async with await self.get_client("cloudwatch") as cloudwatch:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            period = 3600  # 1 hour

            metrics = {}

            # Invocations
            invocations = await cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=["Sum"],
            )
            metrics["invocations"] = sum(
                dp.get("Sum", 0) for dp in invocations.get("Datapoints", [])
            )

            # Errors
            errors = await cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Errors",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=["Sum"],
            )
            metrics["errors"] = sum(
                dp.get("Sum", 0) for dp in errors.get("Datapoints", [])
            )

            # Duration
            duration = await cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Duration",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=["Average", "Maximum"],
            )
            if duration.get("Datapoints"):
                metrics["avg_duration_ms"] = sum(
                    dp.get("Average", 0) for dp in duration["Datapoints"]
                ) / len(duration["Datapoints"])
                metrics["max_duration_ms"] = max(
                    dp.get("Maximum", 0) for dp in duration["Datapoints"]
                )

            # Throttles
            throttles = await cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Throttles",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=["Sum"],
            )
            metrics["throttles"] = sum(
                dp.get("Sum", 0) for dp in throttles.get("Datapoints", [])
            )

            return metrics

    async def update_function_configuration(
        self,
        function_name: str,
        memory_size: Optional[int] = None,
        timeout: Optional[int] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Update Lambda function configuration."""
        if dry_run:
            func = await self.get_function(function_name)
            if func:
                return {
                    "would_update": function_name,
                    "current_memory": func.metadata.get("memory_size"),
                    "current_timeout": func.metadata.get("timeout"),
                    "new_memory": memory_size,
                    "new_timeout": timeout,
                    "dry_run": True,
                }
            return {"error": "Function not found", "dry_run": True}

        async with await self.get_client("lambda") as lambda_client:
            update_kwargs = {"FunctionName": function_name}
            if memory_size:
                update_kwargs["MemorySize"] = memory_size
            if timeout:
                update_kwargs["Timeout"] = timeout

            response = await lambda_client.update_function_configuration(
                **update_kwargs
            )
            return {
                "function_name": response.get("FunctionName"),
                "memory_size": response.get("MemorySize"),
                "timeout": response.get("Timeout"),
                "last_modified": response.get("LastModified"),
            }
