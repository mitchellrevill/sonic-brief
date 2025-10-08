from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, List, Optional
import logging

from ...core.dependencies import get_current_user, get_job_management_service, get_error_handler
from ...services.jobs.job_management_service import JobManagementService
from ...services.jobs.job_permissions import JobPermissions
from ...core.errors import ApplicationError, ErrorCode, ErrorHandler, PermissionError, ResourceNotFoundError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/jobs", tags=["job-admin"])


def get_job_permissions() -> JobPermissions:
    """Dependency provider for JobPermissions."""
    return JobPermissions()


def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        error_code=error_code,
        extra=details,
    )


async def verify_admin_access(
    current_user: str = Depends(get_current_user),
    permissions: JobPermissions = Depends(get_job_permissions),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Verify that the current user has admin privileges."""
    try:
        is_admin = await permissions.check_user_admin_privileges(current_user)
        if not is_admin:
            raise PermissionError("Admin privileges required")
        return current_user
    except ApplicationError:
        raise
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "verify admin access",
            exc,
            details={"user": getattr(current_user, "id", current_user)},
        )





@router.put("/{job_id}/restore")
async def restore_job(
    job_id: str,
    current_user: str = Depends(verify_admin_access),
    management_service: JobManagementService = Depends(get_job_management_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Restore a soft-deleted job (admin only).
    
    Args:
        job_id: ID of the job to restore
        current_user: Current admin user ID
        management_service: Job management service
    """
    try:
        user_id = current_user.get("id") if isinstance(current_user, dict) else current_user
        result = await management_service.restore_job(job_id, user_id, is_admin=True)

        if result["status"] == "error":
            if "not found" in result["message"]:
                raise ResourceNotFoundError(result["message"])
            if "Access denied" in result.get("message", ""):
                raise PermissionError(result["message"])
            raise ValidationError(result["message"])

        return {"status": "success", "message": f"Job {job_id} restored successfully", "job_id": job_id}

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "admin restore job",
            exc,
            details={
                "job_id": job_id,
                "user": getattr(current_user, "id", current_user),
            },
        )


@router.delete("/{job_id}/permanent")
async def permanent_delete_job(
    job_id: str,
    current_user: str = Depends(verify_admin_access),
    management_service: JobManagementService = Depends(get_job_management_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Permanently delete a job and all associated data (admin only).
    
    Args:
        job_id: ID of the job to permanently delete
        current_user: Current admin user ID
        management_service: Job management service
    """
    try:
        user_id = current_user.get("id") if isinstance(current_user, dict) else current_user
        result = await management_service.permanent_delete_job(job_id, user_id, is_admin=True)

        if result["status"] == "error":
            if "not found" in result["message"]:
                raise ResourceNotFoundError(result["message"])
            if "Access denied" in result.get("message", ""):
                raise PermissionError(result["message"])
            raise ValidationError(result["message"])

        return {"status": "success", "message": f"Job {job_id} permanently deleted", "job_id": job_id}

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "admin permanent delete job",
            exc,
            details={
                "job_id": job_id,
                "user": getattr(current_user, "id", current_user),
            },
        )


@router.get("")
async def get_all_jobs(
    current_user: str = Depends(verify_admin_access),
    management_service: JobManagementService = Depends(get_job_management_service),
    limit: int = Query(50, description="Maximum number of jobs to return"),
    offset: int = Query(0, description="Number of jobs to skip"),
    include_deleted: bool = Query(False, description="Include soft-deleted jobs"),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get all jobs (admin only).
    """
    try:
        result = await management_service.get_all_jobs(limit=limit, offset=offset, include_deleted=include_deleted)

        if result.get("error"):
            raise ValidationError(result.get("error"))

        return {
            "status": "success",
            "jobs": result.get("jobs", []),
            "total_count": result.get("total_count", 0),
            "limit": limit,
            "offset": offset,
            "include_deleted": include_deleted
        }

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "admin get all jobs",
            exc,
            details={
                "limit": limit,
                "offset": offset,
                "include_deleted": include_deleted,
            },
        )


@router.get("/deleted")
async def get_deleted_jobs(
    current_user: str = Depends(verify_admin_access),
    management_service: JobManagementService = Depends(get_job_management_service),
    limit: int = Query(50, description="Maximum number of jobs to return"),
    offset: int = Query(0, description="Number of jobs to skip"),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get all soft-deleted jobs (admin only).
    
    Args:
        current_user: Current admin user ID
        management_service: Job management service
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip for pagination
    """
    try:
        user_id = current_user.get("id") if isinstance(current_user, dict) else current_user
        result = await management_service.get_deleted_jobs(user_id, limit=limit, offset=offset, is_admin=True)

        if result.get("status") == "error":
            if "Access denied" in result.get("message", ""):
                raise PermissionError(result.get("message"))
            raise ValidationError(result.get("message"))

        return {
            "status": "success",
            "deleted_jobs": result.get("deleted_jobs", []),
            "total_count": result.get("total_count", 0),
            "limit": limit,
            "offset": offset
        }

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "admin get deleted jobs",
            exc,
            details={
                "limit": limit,
                "offset": offset,
            },
        )


@router.post("/{job_id}/reprocess")
async def trigger_analysis_processing(
    job_id: str,
    current_user: str = Depends(verify_admin_access),
    management_service: JobManagementService = Depends(get_job_management_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Trigger reprocessing of job analysis (admin only).
    
    Args:
        job_id: ID of the job to reprocess
        current_user: Current admin user ID
        management_service: Job management service
    """
    try:
        user_id = current_user.get("id") if isinstance(current_user, dict) else current_user
        result = await management_service.trigger_analysis_processing(job_id, user_id, is_admin=True)

        if result["status"] == "error":
            if "not found" in result["message"]:
                raise ResourceNotFoundError(result["message"])
            if "Access denied" in result.get("message", ""):
                raise PermissionError(result["message"])
            raise ValidationError(result["message"])

        return {"status": "success", "message": f"Analysis processing triggered for job {job_id}", "job_id": job_id, "processing_id": result.get("processing_id")}

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "admin trigger analysis processing",
            exc,
            details={
                "job_id": job_id,
                "user": getattr(current_user, "id", current_user),
            },
        )


@router.get("/user/{user_id}")
async def get_user_jobs(
    user_id: str,
    current_user: str = Depends(verify_admin_access),
    management_service: JobManagementService = Depends(get_job_management_service),
    limit: int = Query(50, description="Maximum number of jobs to return"),
    offset: int = Query(0, description="Number of jobs to skip"),
    include_deleted: bool = Query(False, description="Include soft-deleted jobs"),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get all jobs for a specific user (admin only).
    
    Args:
        user_id: ID of the user whose jobs to retrieve
        current_user: Current admin user ID
        management_service: Job management service
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip for pagination
        include_deleted: Whether to include soft-deleted jobs
    """
    try:
        result = await management_service.get_my_jobs(
            user_id=user_id,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted
        )
        
        if result["status"] == "error":
            raise ValidationError(result["message"])
        
        return {
            "status": "success",
            "user_id": user_id,
            "jobs": result.get("jobs", []),
            "total_count": result.get("total_count", 0),
            "limit": limit,
            "offset": offset,
            "include_deleted": include_deleted
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "admin get user jobs",
            exc,
            details={
                "target_user_id": user_id,
                "limit": limit,
                "offset": offset,
                "include_deleted": include_deleted,
            },
        )


@router.get("/stats")
async def get_job_statistics(
    current_user: str = Depends(verify_admin_access),
    management_service: JobManagementService = Depends(get_job_management_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get system-wide job statistics (admin only).
    
    Args:
        current_user: Current admin user ID
        management_service: Job management service
    """
    try:
        # This would be implemented as a method in JobManagementService
        # For now, return basic stats structure
        return {
            "status": "success",
            "stats": {
                "total_jobs": 0,
                "active_jobs": 0,
                "deleted_jobs": 0,
                "shared_jobs": 0,
                "processing_jobs": 0
            },
            "message": "Job statistics endpoint - implementation pending"
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "admin get job statistics",
            exc,
            details={"user": getattr(current_user, "id", current_user)},
        )
