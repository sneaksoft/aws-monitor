"""Resource action endpoints with safety controls."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.dependencies import RequireAdmin, RequireOperator, get_cache_service
from app.cache import CacheService
from app.models.schemas import (
    ActionResponse,
    EC2ActionRequest,
    RDSActionRequest,
    ECSScaleRequest,
    S3DeleteRequest,
)
from app.services.aws.ec2 import EC2Service
from app.services.aws.rds import RDSService
from app.services.aws.ecs import ECSService
from app.services.aws.s3 import S3Service
from app.services.audit import AuditService
from app.services.safety import SafetyService

router = APIRouter()


# EC2 Actions
@router.post("/ec2/start", response_model=ActionResponse)
async def start_ec2_instances(
    request: EC2ActionRequest,
    user: RequireOperator,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
):
    """Start EC2 instances."""
    ec2 = EC2Service()
    audit = AuditService()

    try:
        result = await ec2.start_instances(
            instance_ids=request.resource_ids,
            dry_run=request.dry_run,
        )
        action_status = "dry_run" if request.dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="ec2:start",
            resource_type="ec2",
            resource_ids=request.resource_ids,
            request=http_request,
            status=action_status,
            request_data=request.model_dump(),
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    await audit.log_action(
        user=user,
        action="ec2:start",
        resource_type="ec2",
        resource_ids=request.resource_ids,
        request=http_request,
        status=action_status,
        request_data=request.model_dump(),
        response_data=response_data,
    )

    if not request.dry_run:
        await cache.invalidate_resources("ec2")

    return ActionResponse(
        status=action_status,
        action="start",
        resource_ids=request.resource_ids,
        dry_run=request.dry_run,
        details=result,
    )


@router.post("/ec2/stop", response_model=ActionResponse)
async def stop_ec2_instances(
    request: EC2ActionRequest,
    user: RequireOperator,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
):
    """Stop EC2 instances."""
    safety = SafetyService()
    ec2 = EC2Service()
    audit = AuditService()

    # Check production protection
    for instance_id in request.resource_ids:
        await safety.check_production_protection(
            resource_type="ec2",
            resource_id=instance_id,
            override_code=request.override_code,
        )

    try:
        result = await ec2.stop_instances(
            instance_ids=request.resource_ids,
            dry_run=request.dry_run,
        )
        action_status = "dry_run" if request.dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="ec2:stop",
            resource_type="ec2",
            resource_ids=request.resource_ids,
            request=http_request,
            status=action_status,
            request_data=request.model_dump(),
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Build request_data with override flag
    audit_request_data = request.model_dump()
    if request.override_code:
        audit_request_data["override_used"] = True

    await audit.log_action(
        user=user,
        action="ec2:stop",
        resource_type="ec2",
        resource_ids=request.resource_ids,
        request=http_request,
        status=action_status,
        request_data=audit_request_data,
        response_data=response_data,
    )

    if not request.dry_run:
        await cache.invalidate_resources("ec2")

    return ActionResponse(
        status=action_status,
        action="stop",
        resource_ids=request.resource_ids,
        dry_run=request.dry_run,
        details=result,
    )


@router.post("/ec2/terminate", response_model=ActionResponse)
async def terminate_ec2_instances(
    request: EC2ActionRequest,
    user: RequireAdmin,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
):
    """Terminate EC2 instances (admin only)."""
    safety = SafetyService()
    ec2 = EC2Service()
    audit = AuditService()

    # Check production protection
    for instance_id in request.resource_ids:
        await safety.check_production_protection(
            resource_type="ec2",
            resource_id=instance_id,
            override_code=request.override_code,
        )

    try:
        result = await ec2.terminate_instances(
            instance_ids=request.resource_ids,
            dry_run=request.dry_run,
        )
        action_status = "dry_run" if request.dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="ec2:terminate",
            resource_type="ec2",
            resource_ids=request.resource_ids,
            request=http_request,
            status=action_status,
            request_data=request.model_dump(),
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Build request_data with override flag
    audit_request_data = request.model_dump()
    if request.override_code:
        audit_request_data["override_used"] = True

    await audit.log_action(
        user=user,
        action="ec2:terminate",
        resource_type="ec2",
        resource_ids=request.resource_ids,
        request=http_request,
        status=action_status,
        request_data=audit_request_data,
        response_data=response_data,
    )

    if not request.dry_run:
        await cache.invalidate_resources("ec2")

    return ActionResponse(
        status=action_status,
        action="terminate",
        resource_ids=request.resource_ids,
        dry_run=request.dry_run,
        details=result,
    )


# RDS Actions
@router.post("/rds/start", response_model=ActionResponse)
async def start_rds_instance(
    request: RDSActionRequest,
    user: RequireOperator,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
):
    """Start RDS instance."""
    rds = RDSService()
    audit = AuditService()

    try:
        result = await rds.start_instance(
            db_instance_identifier=request.db_instance_identifier,
            dry_run=request.dry_run,
        )
        action_status = "dry_run" if request.dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="rds:start",
            resource_type="rds",
            resource_ids=[request.db_instance_identifier],
            request=http_request,
            status=action_status,
            request_data=request.model_dump(),
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    await audit.log_action(
        user=user,
        action="rds:start",
        resource_type="rds",
        resource_ids=[request.db_instance_identifier],
        request=http_request,
        status=action_status,
        request_data=request.model_dump(),
        response_data=response_data,
    )

    if not request.dry_run:
        await cache.invalidate_resources("rds")

    return ActionResponse(
        status=action_status,
        action="start",
        resource_ids=[request.db_instance_identifier],
        dry_run=request.dry_run,
        details=result,
    )


@router.post("/rds/stop", response_model=ActionResponse)
async def stop_rds_instance(
    request: RDSActionRequest,
    user: RequireOperator,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
):
    """Stop RDS instance."""
    safety = SafetyService()
    rds = RDSService()
    audit = AuditService()

    await safety.check_production_protection(
        resource_type="rds",
        resource_id=request.db_instance_identifier,
        override_code=request.override_code,
    )

    try:
        result = await rds.stop_instance(
            db_instance_identifier=request.db_instance_identifier,
            dry_run=request.dry_run,
        )
        action_status = "dry_run" if request.dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="rds:stop",
            resource_type="rds",
            resource_ids=[request.db_instance_identifier],
            request=http_request,
            status=action_status,
            request_data=request.model_dump(),
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Build request_data with override flag
    audit_request_data = request.model_dump()
    if request.override_code:
        audit_request_data["override_used"] = True

    await audit.log_action(
        user=user,
        action="rds:stop",
        resource_type="rds",
        resource_ids=[request.db_instance_identifier],
        request=http_request,
        status=action_status,
        request_data=audit_request_data,
        response_data=response_data,
    )

    if not request.dry_run:
        await cache.invalidate_resources("rds")

    return ActionResponse(
        status=action_status,
        action="stop",
        resource_ids=[request.db_instance_identifier],
        dry_run=request.dry_run,
        details=result,
    )


@router.delete("/rds/{db_instance_identifier}", response_model=ActionResponse)
async def delete_rds_instance(
    db_instance_identifier: str,
    user: RequireAdmin,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
    dry_run: bool = Query(default=True),
    skip_final_snapshot: bool = Query(default=False),
    override_code: str = Query(default=None),
):
    """Delete RDS instance (admin only)."""
    safety = SafetyService()
    rds = RDSService()
    audit = AuditService()

    await safety.check_production_protection(
        resource_type="rds",
        resource_id=db_instance_identifier,
        override_code=override_code,
    )

    request_data = {"skip_final_snapshot": skip_final_snapshot}

    try:
        result = await rds.delete_instance(
            db_instance_identifier=db_instance_identifier,
            skip_final_snapshot=skip_final_snapshot,
            dry_run=dry_run,
        )
        action_status = "dry_run" if dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="rds:delete",
            resource_type="rds",
            resource_ids=[db_instance_identifier],
            request=http_request,
            status=action_status,
            request_data=request_data,
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Build request_data with override flag
    audit_request_data = {"skip_final_snapshot": skip_final_snapshot}
    if override_code:
        audit_request_data["override_used"] = True

    await audit.log_action(
        user=user,
        action="rds:delete",
        resource_type="rds",
        resource_ids=[db_instance_identifier],
        request=http_request,
        status=action_status,
        request_data=audit_request_data,
        response_data=response_data,
    )

    if not dry_run:
        await cache.invalidate_resources("rds")

    return ActionResponse(
        status=action_status,
        action="delete",
        resource_ids=[db_instance_identifier],
        dry_run=dry_run,
        details=result,
    )


# ECS Actions
@router.put("/ecs/scale", response_model=ActionResponse)
async def scale_ecs_service(
    request: ECSScaleRequest,
    user: RequireOperator,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
):
    """Scale ECS service."""
    safety = SafetyService()
    ecs = ECSService()
    audit = AuditService()

    await safety.check_production_protection(
        resource_type="ecs",
        resource_id=f"{request.cluster}/{request.service}",
        override_code=request.override_code,
    )

    resource_id = f"{request.cluster}/{request.service}"

    try:
        result = await ecs.scale_service(
            cluster=request.cluster,
            service=request.service,
            desired_count=request.desired_count,
            dry_run=request.dry_run,
        )
        action_status = "dry_run" if request.dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="ecs:scale",
            resource_type="ecs",
            resource_ids=[resource_id],
            request=http_request,
            status=action_status,
            request_data=request.model_dump(),
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Build request_data with override flag
    audit_request_data = request.model_dump()
    if request.override_code:
        audit_request_data["override_used"] = True

    await audit.log_action(
        user=user,
        action="ecs:scale",
        resource_type="ecs",
        resource_ids=[resource_id],
        request=http_request,
        status=action_status,
        request_data=audit_request_data,
        response_data=response_data,
    )

    if not request.dry_run:
        await cache.invalidate_resources("ecs")

    return ActionResponse(
        status=action_status,
        action="scale",
        resource_ids=[resource_id],
        dry_run=request.dry_run,
        details=result,
    )


# S3 Actions
@router.delete("/s3/{bucket_name}", response_model=ActionResponse)
async def delete_s3_bucket(
    bucket_name: str,
    user: RequireAdmin,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
    dry_run: bool = Query(default=True),
    force_delete: bool = Query(default=False, description="Delete bucket contents first"),
    override_code: str = Query(default=None),
):
    """Delete S3 bucket (admin only)."""
    safety = SafetyService()
    s3 = S3Service()
    audit = AuditService()

    await safety.check_production_protection(
        resource_type="s3",
        resource_id=bucket_name,
        override_code=override_code,
    )

    request_data = {"force_delete": force_delete}

    try:
        result = await s3.delete_bucket(
            bucket_name=bucket_name,
            force_delete=force_delete,
            dry_run=dry_run,
        )
        action_status = "dry_run" if dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="s3:delete",
            resource_type="s3",
            resource_ids=[bucket_name],
            request=http_request,
            status=action_status,
            request_data=request_data,
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Build request_data with override flag
    audit_request_data = {"force_delete": force_delete}
    if override_code:
        audit_request_data["override_used"] = True

    await audit.log_action(
        user=user,
        action="s3:delete",
        resource_type="s3",
        resource_ids=[bucket_name],
        request=http_request,
        status=action_status,
        request_data=audit_request_data,
        response_data=response_data,
    )

    if not dry_run:
        await cache.invalidate_resources("s3")

    return ActionResponse(
        status=action_status,
        action="delete",
        resource_ids=[bucket_name],
        dry_run=dry_run,
        details=result,
    )


# EBS Actions
@router.delete("/ebs/{volume_id}", response_model=ActionResponse)
async def delete_ebs_volume(
    volume_id: str,
    user: RequireAdmin,
    cache: Annotated[CacheService, Depends(get_cache_service)],
    http_request: Request,
    dry_run: bool = Query(default=True),
    override_code: str = Query(default=None),
):
    """Delete EBS volume (admin only)."""
    safety = SafetyService()
    ec2 = EC2Service()
    audit = AuditService()

    await safety.check_production_protection(
        resource_type="ebs",
        resource_id=volume_id,
        override_code=override_code,
    )

    try:
        result = await ec2.delete_volume(
            volume_id=volume_id,
            dry_run=dry_run,
        )
        action_status = "dry_run" if dry_run else "success"
        response_data = result
    except Exception as e:
        action_status = "failed"
        response_data = {"error": str(e), "error_type": type(e).__name__}
        await audit.log_action(
            user=user,
            action="ebs:delete",
            resource_type="ebs",
            resource_ids=[volume_id],
            request=http_request,
            status=action_status,
            response_data=response_data,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Build request_data with override flag
    audit_request_data = {}
    if override_code:
        audit_request_data["override_used"] = True

    await audit.log_action(
        user=user,
        action="ebs:delete",
        resource_type="ebs",
        resource_ids=[volume_id],
        request=http_request,
        status=action_status,
        request_data=audit_request_data if audit_request_data else None,
        response_data=response_data,
    )

    if not dry_run:
        await cache.invalidate_resources("ebs")

    return ActionResponse(
        status=action_status,
        action="delete",
        resource_ids=[volume_id],
        dry_run=dry_run,
        details=result,
    )
