"""S3 service for bucket operations."""

from typing import Any, Optional

from app.services.aws.base import AWSBaseService
from app.models.schemas import ResourceResponse


class S3Service(AWSBaseService):
    """Service for S3 operations."""

    async def list_buckets(self) -> list[ResourceResponse]:
        """List all S3 buckets."""
        resources = []
        async with await self.get_client("s3") as s3:
            response = await s3.list_buckets()
            for bucket in response.get("Buckets", []):
                resource = await self._bucket_to_resource(s3, bucket)
                resources.append(resource)
        return resources

    async def _bucket_to_resource(self, s3, bucket: dict) -> ResourceResponse:
        """Convert S3 bucket to ResourceResponse."""
        bucket_name = bucket["Name"]

        # Get bucket location
        try:
            location_response = await s3.get_bucket_location(Bucket=bucket_name)
            region = location_response.get("LocationConstraint") or "us-east-1"
        except Exception:
            region = "unknown"

        # Get tags
        tags = {}
        try:
            tags_response = await s3.get_bucket_tagging(Bucket=bucket_name)
            tags = {
                tag["Key"]: tag["Value"]
                for tag in tags_response.get("TagSet", [])
            }
        except Exception:
            pass  # Bucket may not have tags

        # Get bucket size (approximate from metrics or inventory)
        metadata = {
            "creation_date": bucket.get("CreationDate").isoformat() if bucket.get("CreationDate") else None,
            "region": region,
        }

        # Get versioning status
        try:
            versioning = await s3.get_bucket_versioning(Bucket=bucket_name)
            metadata["versioning"] = versioning.get("Status", "Disabled")
        except Exception:
            metadata["versioning"] = "Unknown"

        # Get encryption status
        try:
            encryption = await s3.get_bucket_encryption(Bucket=bucket_name)
            rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            if rules:
                metadata["encryption"] = rules[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm")
            else:
                metadata["encryption"] = "None"
        except Exception as e:
            if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                metadata["encryption"] = "None"
            else:
                metadata["encryption"] = "Unknown"

        # Get public access block
        try:
            public_access = await s3.get_public_access_block(Bucket=bucket_name)
            config = public_access.get("PublicAccessBlockConfiguration", {})
            metadata["block_public_access"] = all([
                config.get("BlockPublicAcls", False),
                config.get("IgnorePublicAcls", False),
                config.get("BlockPublicPolicy", False),
                config.get("RestrictPublicBuckets", False),
            ])
        except Exception:
            metadata["block_public_access"] = "Unknown"

        return ResourceResponse(
            resource_id=bucket_name,
            resource_type="s3",
            name=bucket_name,
            region=region,
            aws_account_id="",
            state="available",
            tags=tags,
            metadata=metadata,
        )

    async def get_bucket(self, bucket_name: str) -> Optional[ResourceResponse]:
        """Get detailed information about a specific bucket."""
        async with await self.get_client("s3") as s3:
            try:
                # Check bucket exists
                await s3.head_bucket(Bucket=bucket_name)
                bucket = {"Name": bucket_name}
                return await self._bucket_to_resource(s3, bucket)
            except Exception:
                return None

    async def get_bucket_size(self, bucket_name: str) -> dict[str, Any]:
        """Get bucket size using CloudWatch metrics."""
        async with await self.get_client("cloudwatch") as cloudwatch:
            from datetime import datetime, timedelta

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)

            # Get bucket size
            size_response = await cloudwatch.get_metric_statistics(
                Namespace="AWS/S3",
                MetricName="BucketSizeBytes",
                Dimensions=[
                    {"Name": "BucketName", "Value": bucket_name},
                    {"Name": "StorageType", "Value": "StandardStorage"},
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=["Average"],
            )

            # Get object count
            count_response = await cloudwatch.get_metric_statistics(
                Namespace="AWS/S3",
                MetricName="NumberOfObjects",
                Dimensions=[
                    {"Name": "BucketName", "Value": bucket_name},
                    {"Name": "StorageType", "Value": "AllStorageTypes"},
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=["Average"],
            )

            size_bytes = 0
            object_count = 0

            if size_response.get("Datapoints"):
                size_bytes = size_response["Datapoints"][0].get("Average", 0)

            if count_response.get("Datapoints"):
                object_count = int(count_response["Datapoints"][0].get("Average", 0))

            return {
                "bucket_name": bucket_name,
                "size_bytes": size_bytes,
                "size_gb": round(size_bytes / (1024**3), 2),
                "object_count": object_count,
            }

    async def delete_bucket(
        self,
        bucket_name: str,
        force_delete: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Delete an S3 bucket."""
        async with await self.get_client("s3") as s3:
            # Check if bucket is empty
            try:
                response = await s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                has_objects = response.get("KeyCount", 0) > 0
            except Exception as e:
                return {"error": str(e)}

            if dry_run:
                return {
                    "would_delete": bucket_name,
                    "has_objects": has_objects,
                    "force_delete": force_delete,
                    "dry_run": True,
                }

            if has_objects and not force_delete:
                return {
                    "error": "Bucket is not empty. Use force_delete=True to delete contents first.",
                    "bucket_name": bucket_name,
                }

            if has_objects and force_delete:
                # Delete all objects first
                await self._empty_bucket(s3, bucket_name)

            # Delete the bucket
            await s3.delete_bucket(Bucket=bucket_name)
            return {"deleted": bucket_name}

    async def _empty_bucket(self, s3, bucket_name: str):
        """Delete all objects in a bucket."""
        paginator = s3.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=bucket_name):
            objects = page.get("Contents", [])
            if objects:
                delete_objects = [{"Key": obj["Key"]} for obj in objects]
                await s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": delete_objects},
                )

        # Also delete versions if versioning enabled
        try:
            version_paginator = s3.get_paginator("list_object_versions")
            async for page in version_paginator.paginate(Bucket=bucket_name):
                versions = page.get("Versions", [])
                delete_markers = page.get("DeleteMarkers", [])

                to_delete = []
                for v in versions:
                    to_delete.append({"Key": v["Key"], "VersionId": v["VersionId"]})
                for d in delete_markers:
                    to_delete.append({"Key": d["Key"], "VersionId": d["VersionId"]})

                if to_delete:
                    await s3.delete_objects(
                        Bucket=bucket_name,
                        Delete={"Objects": to_delete},
                    )
        except Exception:
            pass  # Versioning might not be enabled

    async def has_lifecycle_policy(self, bucket_name: str) -> bool:
        """Check if bucket has a lifecycle policy configured."""
        async with await self.get_client("s3") as s3:
            try:
                response = await s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                rules = response.get("Rules", [])
                return len(rules) > 0
            except Exception as e:
                # NoSuchLifecycleConfiguration means no policy
                if "NoSuchLifecycleConfiguration" in str(e):
                    return False
                # Other errors, assume no policy
                return False

    async def get_bucket_metrics(self, bucket_name: str) -> dict[str, Any]:
        """Get bucket size and object count from CloudWatch."""
        async with await self.get_client("cloudwatch") as cloudwatch:
            from datetime import datetime, timedelta

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=2)

            size_bytes = 0
            object_count = 0

            try:
                # Get bucket size
                size_response = await cloudwatch.get_metric_statistics(
                    Namespace="AWS/S3",
                    MetricName="BucketSizeBytes",
                    Dimensions=[
                        {"Name": "BucketName", "Value": bucket_name},
                        {"Name": "StorageType", "Value": "StandardStorage"},
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=["Average"],
                )

                if size_response.get("Datapoints"):
                    size_bytes = size_response["Datapoints"][-1].get("Average", 0)

                # Get object count
                count_response = await cloudwatch.get_metric_statistics(
                    Namespace="AWS/S3",
                    MetricName="NumberOfObjects",
                    Dimensions=[
                        {"Name": "BucketName", "Value": bucket_name},
                        {"Name": "StorageType", "Value": "AllStorageTypes"},
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=["Average"],
                )

                if count_response.get("Datapoints"):
                    object_count = int(count_response["Datapoints"][-1].get("Average", 0))

            except Exception:
                pass

            return {
                "size_bytes": size_bytes,
                "object_count": object_count,
            }
