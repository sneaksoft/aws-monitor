"""Base AWS service with common functionality."""

import asyncio
from typing import Any, AsyncGenerator, Optional

import aioboto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()


class AWSBaseService:
    """Base class for AWS service operations."""

    def __init__(
        self,
        region: Optional[str] = None,
        role_arn: Optional[str] = None,
        external_id: Optional[str] = None,
    ):
        self.region = region or settings.aws_region
        self.role_arn = role_arn or settings.aws_role_arn
        self.external_id = external_id or settings.aws_external_id
        self.session = aioboto3.Session()
        self.config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )

    async def get_client(self, service_name: str):
        """Get async boto3 client for a service."""
        if self.role_arn:
            # Assume role for cross-account access
            async with self.session.client(
                "sts",
                region_name=self.region,
                config=self.config,
            ) as sts:
                assume_kwargs = {
                    "RoleArn": self.role_arn,
                    "RoleSessionName": "aws-monitor-session",
                    "DurationSeconds": 3600,
                }
                if self.external_id:
                    assume_kwargs["ExternalId"] = self.external_id

                response = await sts.assume_role(**assume_kwargs)
                credentials = response["Credentials"]

                return self.session.client(
                    service_name,
                    region_name=self.region,
                    config=self.config,
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                )
        else:
            # Use default credentials
            return self.session.client(
                service_name,
                region_name=self.region,
                config=self.config,
            )

    async def verify_role_access(
        self,
        role_arn: str,
        external_id: Optional[str] = None,
    ) -> bool:
        """Test if we can assume a role."""
        async with self.session.client(
            "sts",
            region_name=self.region,
            config=self.config,
        ) as sts:
            assume_kwargs = {
                "RoleArn": role_arn,
                "RoleSessionName": "aws-monitor-verify",
                "DurationSeconds": 900,
            }
            if external_id:
                assume_kwargs["ExternalId"] = external_id

            await sts.assume_role(**assume_kwargs)
            return True

    async def paginate(
        self,
        client,
        method: str,
        result_key: str,
        **kwargs,
    ) -> AsyncGenerator[list[Any], None]:
        """Paginate through AWS API responses."""
        paginator = client.get_paginator(method)
        async for page in paginator.paginate(**kwargs):
            yield page.get(result_key, [])

    async def paginate_all(
        self,
        client,
        method: str,
        result_key: str,
        **kwargs,
    ) -> list[Any]:
        """Get all results from paginated AWS API call."""
        results = []
        async for items in self.paginate(client, method, result_key, **kwargs):
            results.extend(items)
        return results

    def parse_arn(self, arn: str) -> dict[str, str]:
        """Parse an ARN into its components."""
        parts = arn.split(":")
        return {
            "partition": parts[1] if len(parts) > 1 else "",
            "service": parts[2] if len(parts) > 2 else "",
            "region": parts[3] if len(parts) > 3 else "",
            "account": parts[4] if len(parts) > 4 else "",
            "resource": ":".join(parts[5:]) if len(parts) > 5 else "",
        }

    def get_tag_value(self, tags: list[dict], key: str) -> Optional[str]:
        """Get value from AWS tags list."""
        for tag in tags or []:
            if tag.get("Key") == key:
                return tag.get("Value")
        return None

    def tags_to_dict(self, tags: list[dict]) -> dict[str, str]:
        """Convert AWS tags list to dictionary."""
        return {tag["Key"]: tag["Value"] for tag in tags or [] if "Key" in tag}

    async def get_account_id(self) -> str:
        """Get current AWS account ID."""
        async with await self.get_client("sts") as sts:
            response = await sts.get_caller_identity()
            return response["Account"]

    async def list_regions(self) -> list[str]:
        """Get list of enabled regions."""
        async with await self.get_client("ec2") as ec2:
            response = await ec2.describe_regions(
                Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}]
            )
            return [r["RegionName"] for r in response["Regions"]]
