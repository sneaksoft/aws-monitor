"""EC2 service for instance and volume operations."""

from typing import Any, Optional

from app.services.aws.base import AWSBaseService
from app.models.schemas import ResourceResponse


class EC2Service(AWSBaseService):
    """Service for EC2 operations."""

    async def list_instances(
        self,
        filters: Optional[list[dict]] = None,
    ) -> list[ResourceResponse]:
        """List all EC2 instances."""
        resources = []
        async with await self.get_client("ec2") as ec2:
            paginator = ec2.get_paginator("describe_instances")
            async for page in paginator.paginate(Filters=filters or []):
                for reservation in page.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        resources.append(self._instance_to_resource(instance))
        return resources

    def _instance_to_resource(self, instance: dict) -> ResourceResponse:
        """Convert EC2 instance to ResourceResponse."""
        tags = self.tags_to_dict(instance.get("Tags", []))
        return ResourceResponse(
            resource_id=instance["InstanceId"],
            resource_type="ec2",
            name=tags.get("Name"),
            region=self.region,
            aws_account_id=instance.get("OwnerId", ""),
            state=instance.get("State", {}).get("Name"),
            tags=tags,
            metadata={
                "instance_type": instance.get("InstanceType"),
                "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                "private_ip": instance.get("PrivateIpAddress"),
                "public_ip": instance.get("PublicIpAddress"),
                "vpc_id": instance.get("VpcId"),
                "subnet_id": instance.get("SubnetId"),
                "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                "platform": instance.get("Platform", "linux"),
                "architecture": instance.get("Architecture"),
            },
        )

    async def get_instance(self, instance_id: str) -> Optional[ResourceResponse]:
        """Get details for a specific instance."""
        async with await self.get_client("ec2") as ec2:
            response = await ec2.describe_instances(InstanceIds=[instance_id])
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    return self._instance_to_resource(instance)
        return None

    async def start_instances(
        self,
        instance_ids: list[str],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Start EC2 instances."""
        async with await self.get_client("ec2") as ec2:
            try:
                response = await ec2.start_instances(
                    InstanceIds=instance_ids,
                    DryRun=dry_run,
                )
                return {
                    "starting_instances": [
                        {
                            "instance_id": i["InstanceId"],
                            "current_state": i["CurrentState"]["Name"],
                            "previous_state": i["PreviousState"]["Name"],
                        }
                        for i in response.get("StartingInstances", [])
                    ]
                }
            except ec2.exceptions.ClientError as e:
                if "DryRunOperation" in str(e):
                    return {"would_start": instance_ids, "dry_run": True}
                raise

    async def stop_instances(
        self,
        instance_ids: list[str],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Stop EC2 instances."""
        async with await self.get_client("ec2") as ec2:
            try:
                response = await ec2.stop_instances(
                    InstanceIds=instance_ids,
                    DryRun=dry_run,
                )
                return {
                    "stopping_instances": [
                        {
                            "instance_id": i["InstanceId"],
                            "current_state": i["CurrentState"]["Name"],
                            "previous_state": i["PreviousState"]["Name"],
                        }
                        for i in response.get("StoppingInstances", [])
                    ]
                }
            except ec2.exceptions.ClientError as e:
                if "DryRunOperation" in str(e):
                    return {"would_stop": instance_ids, "dry_run": True}
                raise

    async def terminate_instances(
        self,
        instance_ids: list[str],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Terminate EC2 instances."""
        async with await self.get_client("ec2") as ec2:
            try:
                response = await ec2.terminate_instances(
                    InstanceIds=instance_ids,
                    DryRun=dry_run,
                )
                return {
                    "terminating_instances": [
                        {
                            "instance_id": i["InstanceId"],
                            "current_state": i["CurrentState"]["Name"],
                            "previous_state": i["PreviousState"]["Name"],
                        }
                        for i in response.get("TerminatingInstances", [])
                    ]
                }
            except ec2.exceptions.ClientError as e:
                if "DryRunOperation" in str(e):
                    return {"would_terminate": instance_ids, "dry_run": True}
                raise

    async def list_volumes(self) -> list[ResourceResponse]:
        """List all EBS volumes."""
        resources = []
        async with await self.get_client("ec2") as ec2:
            paginator = ec2.get_paginator("describe_volumes")
            async for page in paginator.paginate():
                for volume in page.get("Volumes", []):
                    resources.append(self._volume_to_resource(volume))
        return resources

    def _volume_to_resource(self, volume: dict) -> ResourceResponse:
        """Convert EBS volume to ResourceResponse."""
        tags = self.tags_to_dict(volume.get("Tags", []))
        attachments = volume.get("Attachments", [])
        return ResourceResponse(
            resource_id=volume["VolumeId"],
            resource_type="ebs",
            name=tags.get("Name"),
            region=self.region,
            aws_account_id="",
            state=volume.get("State"),
            tags=tags,
            metadata={
                "size_gb": volume.get("Size"),
                "volume_type": volume.get("VolumeType"),
                "iops": volume.get("Iops"),
                "throughput": volume.get("Throughput"),
                "encrypted": volume.get("Encrypted"),
                "availability_zone": volume.get("AvailabilityZone"),
                "attached_to": attachments[0].get("InstanceId") if attachments else None,
                "attachment_state": attachments[0].get("State") if attachments else "unattached",
            },
        )

    async def delete_volume(
        self,
        volume_id: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Delete an EBS volume."""
        async with await self.get_client("ec2") as ec2:
            try:
                await ec2.delete_volume(VolumeId=volume_id, DryRun=dry_run)
                return {"deleted": volume_id}
            except ec2.exceptions.ClientError as e:
                if "DryRunOperation" in str(e):
                    return {"would_delete": volume_id, "dry_run": True}
                raise

    async def list_snapshots(self, owner_ids: list[str] = None) -> list[ResourceResponse]:
        """List EBS snapshots."""
        resources = []
        async with await self.get_client("ec2") as ec2:
            # Get account ID if not provided
            if not owner_ids:
                account_id = await self.get_account_id()
                owner_ids = [account_id]

            paginator = ec2.get_paginator("describe_snapshots")
            async for page in paginator.paginate(OwnerIds=owner_ids):
                for snapshot in page.get("Snapshots", []):
                    resources.append(self._snapshot_to_resource(snapshot))
        return resources

    def _snapshot_to_resource(self, snapshot: dict) -> ResourceResponse:
        """Convert EBS snapshot to ResourceResponse."""
        tags = self.tags_to_dict(snapshot.get("Tags", []))
        return ResourceResponse(
            resource_id=snapshot["SnapshotId"],
            resource_type="ebs_snapshot",
            name=tags.get("Name") or snapshot.get("Description"),
            region=self.region,
            aws_account_id=snapshot.get("OwnerId", ""),
            state=snapshot.get("State"),
            tags=tags,
            metadata={
                "volume_id": snapshot.get("VolumeId"),
                "size_gb": snapshot.get("VolumeSize"),
                "encrypted": snapshot.get("Encrypted"),
                "start_time": snapshot.get("StartTime").isoformat() if snapshot.get("StartTime") else None,
                "progress": snapshot.get("Progress"),
            },
        )

    async def get_instance_metrics(
        self,
        instance_id: str,
        metric_name: str = "CPUUtilization",
        period: int = 3600,
        hours: int = 168,  # 7 days
    ) -> list[dict]:
        """Get CloudWatch metrics for an instance."""
        from datetime import datetime, timedelta

        async with await self.get_client("cloudwatch") as cloudwatch:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            response = await cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=["Average", "Maximum"],
            )

            return [
                {
                    "timestamp": dp["Timestamp"].isoformat(),
                    "average": dp.get("Average"),
                    "maximum": dp.get("Maximum"),
                }
                for dp in response.get("Datapoints", [])
            ]
