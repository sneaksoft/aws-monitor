"""Safety controls for destructive operations."""

from typing import Optional

from fastapi import HTTPException, status

from app.config import get_settings
from app.services.aws.ec2 import EC2Service
from app.services.aws.rds import RDSService
from app.services.aws.s3 import S3Service
from app.services.aws.ecs import ECSService

settings = get_settings()


class SafetyService:
    """Service for safety controls and protection checks."""

    def __init__(self):
        self.protected_tags = settings.protected_tags
        self.admin_override_code = settings.admin_override_code

    async def check_production_protection(
        self,
        resource_type: str,
        resource_id: str,
        override_code: Optional[str] = None,
    ) -> None:
        """
        Check if resource is protected from modification.

        Raises HTTPException if resource is protected and no valid override.
        """
        # Get resource tags
        tags = await self._get_resource_tags(resource_type, resource_id)

        # Check for protected environment tags
        env_tag = tags.get("Environment", "").lower()
        if env_tag in self.protected_tags:
            if not self._verify_override(override_code):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cannot modify production resource. Environment tag: {env_tag}. "
                    f"Provide admin override code to proceed.",
                )

        # Check for explicit protection tag
        protection_tag = tags.get("Protected", "").lower()
        if protection_tag in ("true", "yes", "1"):
            if not self._verify_override(override_code):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Resource has explicit protection tag. "
                    "Provide admin override code to proceed.",
                )

    async def _get_resource_tags(
        self, resource_type: str, resource_id: str
    ) -> dict[str, str]:
        """Get tags for a resource."""
        try:
            if resource_type == "ec2":
                service = EC2Service()
                instance = await service.get_instance(resource_id)
                return instance.tags if instance else {}

            elif resource_type == "ebs":
                service = EC2Service()
                volumes = await service.list_volumes()
                volume = next(
                    (v for v in volumes if v.resource_id == resource_id), None
                )
                return volume.tags if volume else {}

            elif resource_type == "rds":
                service = RDSService()
                instance = await service.get_instance(resource_id)
                return instance.tags if instance else {}

            elif resource_type == "s3":
                service = S3Service()
                bucket = await service.get_bucket(resource_id)
                return bucket.tags if bucket else {}

            elif resource_type == "ecs":
                # ECS resource_id format: cluster/service
                if "/" in resource_id:
                    cluster, service_name = resource_id.split("/", 1)
                    service = ECSService()
                    ecs_service = await service.get_service(cluster, service_name)
                    return ecs_service.tags if ecs_service else {}

            return {}

        except Exception:
            # If we can't get tags, allow the operation but log warning
            return {}

    def _verify_override(self, override_code: Optional[str]) -> bool:
        """Verify admin override code."""
        if not self.admin_override_code:
            # No override configured, protection cannot be bypassed
            return False

        return override_code == self.admin_override_code

    async def check_dependencies(
        self,
        resource_type: str,
        resource_id: str,
    ) -> list[dict]:
        """
        Check for resource dependencies before deletion.

        Returns list of dependent resources.
        """
        dependencies = []

        if resource_type == "ec2":
            dependencies.extend(
                await self._check_ec2_dependencies(resource_id)
            )
        elif resource_type == "ebs":
            dependencies.extend(
                await self._check_ebs_dependencies(resource_id)
            )
        elif resource_type == "rds":
            dependencies.extend(
                await self._check_rds_dependencies(resource_id)
            )

        return dependencies

    async def _check_ec2_dependencies(self, instance_id: str) -> list[dict]:
        """Check EC2 instance dependencies."""
        dependencies = []

        # Check for attached EBS volumes
        service = EC2Service()
        volumes = await service.list_volumes()

        for volume in volumes:
            if volume.metadata.get("attached_to") == instance_id:
                dependencies.append({
                    "type": "ebs",
                    "id": volume.resource_id,
                    "relationship": "attached_volume",
                    "message": f"EBS volume {volume.resource_id} is attached to this instance",
                })

        return dependencies

    async def _check_ebs_dependencies(self, volume_id: str) -> list[dict]:
        """Check EBS volume dependencies."""
        dependencies = []

        service = EC2Service()
        volumes = await service.list_volumes()

        volume = next((v for v in volumes if v.resource_id == volume_id), None)
        if volume:
            attached_to = volume.metadata.get("attached_to")
            if attached_to:
                dependencies.append({
                    "type": "ec2",
                    "id": attached_to,
                    "relationship": "attached_instance",
                    "message": f"Volume is attached to instance {attached_to}",
                })

        return dependencies

    async def _check_rds_dependencies(self, db_instance_id: str) -> list[dict]:
        """Check RDS instance dependencies."""
        dependencies = []

        # Check for read replicas
        service = RDSService()
        instances = await service.list_instances()

        for instance in instances:
            source = instance.metadata.get("read_replica_source_db_instance_identifier")
            if source == db_instance_id:
                dependencies.append({
                    "type": "rds",
                    "id": instance.resource_id,
                    "relationship": "read_replica",
                    "message": f"Instance {instance.resource_id} is a read replica of this database",
                })

        return dependencies

    def validate_action(
        self,
        action: str,
        user_role: str,
    ) -> bool:
        """Validate if user role can perform action."""
        admin_only_actions = [
            "ec2:terminate",
            "rds:delete",
            "s3:delete",
            "ebs:delete",
            "ecs:delete",
        ]

        operator_actions = [
            "ec2:start",
            "ec2:stop",
            "rds:start",
            "rds:stop",
            "ecs:scale",
        ]

        if action in admin_only_actions:
            return user_role == "admin"

        if action in operator_actions:
            return user_role in ("admin", "operator")

        # Read-only actions allowed for all authenticated users
        return True
