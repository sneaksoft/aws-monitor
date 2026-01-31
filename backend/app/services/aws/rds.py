"""RDS service for database instance operations."""

from typing import Any, Optional

from app.services.aws.base import AWSBaseService
from app.models.schemas import ResourceResponse


class RDSService(AWSBaseService):
    """Service for RDS operations."""

    async def list_instances(self) -> list[ResourceResponse]:
        """List all RDS instances."""
        resources = []
        async with await self.get_client("rds") as rds:
            paginator = rds.get_paginator("describe_db_instances")
            async for page in paginator.paginate():
                for db in page.get("DBInstances", []):
                    resources.append(self._instance_to_resource(db))
        return resources

    def _instance_to_resource(self, db: dict) -> ResourceResponse:
        """Convert RDS instance to ResourceResponse."""
        # RDS uses TagList, need to fetch separately or use ARN
        tags = {}
        if "TagList" in db:
            tags = {tag["Key"]: tag["Value"] for tag in db.get("TagList", [])}

        return ResourceResponse(
            resource_id=db["DBInstanceIdentifier"],
            resource_type="rds",
            name=db["DBInstanceIdentifier"],
            region=self.region,
            aws_account_id="",
            state=db.get("DBInstanceStatus"),
            tags=tags,
            metadata={
                "engine": db.get("Engine"),
                "engine_version": db.get("EngineVersion"),
                "instance_class": db.get("DBInstanceClass"),
                "allocated_storage": db.get("AllocatedStorage"),
                "storage_type": db.get("StorageType"),
                "multi_az": db.get("MultiAZ"),
                "endpoint": db.get("Endpoint", {}).get("Address"),
                "port": db.get("Endpoint", {}).get("Port"),
                "vpc_id": db.get("DBSubnetGroup", {}).get("VpcId"),
                "availability_zone": db.get("AvailabilityZone"),
                "publicly_accessible": db.get("PubliclyAccessible"),
                "storage_encrypted": db.get("StorageEncrypted"),
                "backup_retention_period": db.get("BackupRetentionPeriod"),
                "created_time": db.get("InstanceCreateTime").isoformat() if db.get("InstanceCreateTime") else None,
            },
        )

    async def get_instance(self, db_instance_identifier: str) -> Optional[ResourceResponse]:
        """Get details for a specific RDS instance."""
        async with await self.get_client("rds") as rds:
            response = await rds.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier
            )
            instances = response.get("DBInstances", [])
            if instances:
                return self._instance_to_resource(instances[0])
        return None

    async def start_instance(
        self,
        db_instance_identifier: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Start an RDS instance."""
        if dry_run:
            # RDS doesn't support dry-run, simulate it
            instance = await self.get_instance(db_instance_identifier)
            if instance:
                return {
                    "would_start": db_instance_identifier,
                    "current_state": instance.state,
                    "dry_run": True,
                }
            return {"error": "Instance not found", "dry_run": True}

        async with await self.get_client("rds") as rds:
            response = await rds.start_db_instance(
                DBInstanceIdentifier=db_instance_identifier
            )
            db = response.get("DBInstance", {})
            return {
                "instance_id": db.get("DBInstanceIdentifier"),
                "status": db.get("DBInstanceStatus"),
            }

    async def stop_instance(
        self,
        db_instance_identifier: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Stop an RDS instance."""
        if dry_run:
            instance = await self.get_instance(db_instance_identifier)
            if instance:
                return {
                    "would_stop": db_instance_identifier,
                    "current_state": instance.state,
                    "dry_run": True,
                }
            return {"error": "Instance not found", "dry_run": True}

        async with await self.get_client("rds") as rds:
            response = await rds.stop_db_instance(
                DBInstanceIdentifier=db_instance_identifier
            )
            db = response.get("DBInstance", {})
            return {
                "instance_id": db.get("DBInstanceIdentifier"),
                "status": db.get("DBInstanceStatus"),
            }

    async def delete_instance(
        self,
        db_instance_identifier: str,
        skip_final_snapshot: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Delete an RDS instance."""
        if dry_run:
            instance = await self.get_instance(db_instance_identifier)
            if instance:
                return {
                    "would_delete": db_instance_identifier,
                    "current_state": instance.state,
                    "skip_final_snapshot": skip_final_snapshot,
                    "dry_run": True,
                }
            return {"error": "Instance not found", "dry_run": True}

        async with await self.get_client("rds") as rds:
            delete_kwargs = {
                "DBInstanceIdentifier": db_instance_identifier,
                "SkipFinalSnapshot": skip_final_snapshot,
            }
            if not skip_final_snapshot:
                delete_kwargs["FinalDBSnapshotIdentifier"] = (
                    f"{db_instance_identifier}-final-snapshot"
                )

            response = await rds.delete_db_instance(**delete_kwargs)
            db = response.get("DBInstance", {})
            return {
                "instance_id": db.get("DBInstanceIdentifier"),
                "status": db.get("DBInstanceStatus"),
            }

    async def list_clusters(self) -> list[ResourceResponse]:
        """List Aurora clusters."""
        resources = []
        async with await self.get_client("rds") as rds:
            paginator = rds.get_paginator("describe_db_clusters")
            async for page in paginator.paginate():
                for cluster in page.get("DBClusters", []):
                    resources.append(self._cluster_to_resource(cluster))
        return resources

    def _cluster_to_resource(self, cluster: dict) -> ResourceResponse:
        """Convert Aurora cluster to ResourceResponse."""
        tags = {}
        if "TagList" in cluster:
            tags = {tag["Key"]: tag["Value"] for tag in cluster.get("TagList", [])}

        return ResourceResponse(
            resource_id=cluster["DBClusterIdentifier"],
            resource_type="aurora",
            name=cluster["DBClusterIdentifier"],
            region=self.region,
            aws_account_id="",
            state=cluster.get("Status"),
            tags=tags,
            metadata={
                "engine": cluster.get("Engine"),
                "engine_version": cluster.get("EngineVersion"),
                "engine_mode": cluster.get("EngineMode"),
                "allocated_storage": cluster.get("AllocatedStorage"),
                "multi_az": cluster.get("MultiAZ"),
                "endpoint": cluster.get("Endpoint"),
                "reader_endpoint": cluster.get("ReaderEndpoint"),
                "port": cluster.get("Port"),
                "vpc_id": cluster.get("DBSubnetGroup"),
                "storage_encrypted": cluster.get("StorageEncrypted"),
                "backup_retention_period": cluster.get("BackupRetentionPeriod"),
                "cluster_members": [
                    m.get("DBInstanceIdentifier")
                    for m in cluster.get("DBClusterMembers", [])
                ],
            },
        )
