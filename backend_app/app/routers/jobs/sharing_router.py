from fastapi import APIRouter, Depends, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from ...core.dependencies import (
    get_current_user,
    get_job_sharing_service,
    get_job_service,
    get_error_handler,
)
from ...services.jobs.job_sharing_service import JobSharingService
from ...services.jobs.job_permissions import JobPermissions
from ...services.jobs import JobService
from ...core.errors import (
    ApplicationError,
    ErrorCode,
    ErrorHandler,
    PermissionError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["job-sharing"])


def get_job_permissions() -> JobPermissions:
    """Dependency provider for JobPermissions."""
    return JobPermissions()


def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        error_code=error_code,
        status_code=status_code,
        extra=details,
    )


class ShareRequest(BaseModel):
    # Accept both names from different frontends: `shared_user_email` (canonical) and
    # `target_user_email` (legacy/alternate). We'll read either but normalize to
    # `shared_user_email` internally.
    shared_user_email: str | None = None
    target_user_email: str | None = None
    # Use 'view' to align with the permission levels used by JobPermissions
    permission_level: str = "view"

    def get_shared_email(self) -> str:
        """Return the effective shared user email, preferring `shared_user_email`."""
        return self.shared_user_email or self.target_user_email


@router.post("/{job_id}/share")
async def share_job(
    job_id: str,
    share_request: ShareRequest = Body(..., description="Share request payload"),
    current_user: Any = Depends(get_current_user),
    sharing_service: JobSharingService = Depends(get_job_sharing_service),
    job_service: JobService = Depends(get_job_service),
    permissions: JobPermissions = Depends(get_job_permissions),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Share a job with another user.
    
    Args:
        job_id: ID of the job to share
        shared_user_email: Email of user to share with
        permission_level: Permission level (read, write, admin)
        current_user: Current user ID from auth
        sharing_service: Job sharing service
        permissions: Job permissions service
    """
    try:
        # Normalize current user: keep both the full object (if provided) and the id string
        user_obj = current_user
        user_id = user_obj if isinstance(user_obj, str) else user_obj.get("id")

        # Extract payload values (shared_user_email and permission_level)
        shared_user_email = share_request.get_shared_email()
        permission_level = share_request.permission_level or "view"

        # Validate presence of email
        if not shared_user_email:
            raise ValidationError(
                "shared_user_email is required",
                field="shared_user_email",
                details={"job_id": job_id},
            )

        # Fetch the job to check permissions
        job = await job_service.async_get_job(job_id)
        if not job:
            raise ResourceNotFoundError("Job", job_id)

        # Check if user can share this job
        # Pass the full user object to the permissions helper so it can check ownership and shared entries
        has_access = await permissions.check_job_access(job, user_obj, "admin")
        if not has_access:
            raise PermissionError(
                "You don't have permission to share this job",
                details={"job_id": job_id, "user_id": user_id},
            )

        # Validate permission level
        valid_permissions = ["view", "edit", "admin"]
        if permission_level not in valid_permissions:
            raise ValidationError(
                "Invalid permission level",
                field="permission_level",
                details={"allowed": valid_permissions, "received": permission_level},
            )

        result = await sharing_service.share_job(
            job_id=job_id,
            owner_user_id=user_id,
            target_user_email=shared_user_email,
            permission_level=permission_level
        )
        
        if result["status"] == "error":
            message = result.get("message", "Unable to share job")
            lowered = message.lower()
            details = {
                "job_id": job_id,
                "target_email": shared_user_email,
                "permission_level": permission_level,
            }
            if "not found" in lowered:
                raise ResourceNotFoundError("Job share target", shared_user_email, details)
            if "already shared" in lowered:
                raise ApplicationError(
                    message,
                    ErrorCode.RESOURCE_CONFLICT,
                    status_code=409,
                    details=details,
                )
            raise ApplicationError(
                message,
                ErrorCode.INVALID_INPUT,
                status_code=400,
                details=details,
            )
        
        return {
            "status": "success",
            "message": f"Job shared successfully with {shared_user_email}",
            "sharing_id": result.get("sharing_id"),
            "permission_level": permission_level
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "share job",
            exc,
            details={
                "job_id": job_id,
                "shared_with": share_request.get_shared_email(),
                "permission_level": share_request.permission_level,
            },
        )


@router.delete("/{job_id}/share/{shared_user_email}")
async def unshare_job(
    job_id: str,
    shared_user_email: str,
    current_user: Any = Depends(get_current_user),
    sharing_service: JobSharingService = Depends(get_job_sharing_service),
    job_service: JobService = Depends(get_job_service),
    permissions: JobPermissions = Depends(get_job_permissions),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Remove sharing access for a user.
    
    Args:
        job_id: ID of the job
        shared_user_email: Email of user to remove access from
        current_user: Current user ID from auth
        sharing_service: Job sharing service
        permissions: Job permissions service
    """
    try:
        # Normalize current user: keep both object and id
        user_obj = current_user
        user_id = user_obj if isinstance(user_obj, str) else user_obj.get("id")

        # Fetch the job to check permissions
        job = await job_service.async_get_job(job_id)
        if not job:
            raise ResourceNotFoundError("Job", job_id)

        # Check if user can manage sharing for this job
        has_access = await permissions.check_job_access(job, user_obj, "admin")
        if not has_access:
            raise PermissionError(
                "You don't have permission to manage sharing for this job",
                details={"job_id": job_id, "user_id": user_id},
            )
        
        result = await sharing_service.unshare_job(
            job_id=job_id,
            owner_user_id=user_id,
            target_user_email=shared_user_email
        )
        
        if result["status"] == "error":
            message = result.get("message", "Unable to unshare job")
            lowered = message.lower()
            details = {
                "job_id": job_id,
                "target_email": shared_user_email,
            }
            if "not found" in lowered:
                raise ResourceNotFoundError("Job share", shared_user_email, details)
            raise ApplicationError(
                message,
                ErrorCode.INVALID_INPUT,
                status_code=400,
                details=details,
            )
        
        return {
            "status": "success",
            "message": f"Sharing removed for {shared_user_email}"
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "unshare job",
            exc,
            details={
                "job_id": job_id,
                "shared_user_email": shared_user_email,
            },
        )


@router.get("/{job_id}/sharing")
async def get_job_sharing_info(
    job_id: str,
    current_user: Any = Depends(get_current_user),
    sharing_service: JobSharingService = Depends(get_job_sharing_service),
    job_service: JobService = Depends(get_job_service),
    permissions: JobPermissions = Depends(get_job_permissions),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get sharing information for a job.
    
    Args:
        job_id: ID of the job
        current_user: Current user ID from auth
        sharing_service: Job sharing service
        job_service: Job service
        permissions: Job permissions service
    """

    try:
        # Normalize current user: keep both object and id
        user_obj = current_user
        user_id = user_obj if isinstance(user_obj, str) else user_obj.get("id")

        # Fetch the job to check permissions
        job = await job_service.async_get_job(job_id)
        if not job:
            raise ResourceNotFoundError("Job", job_id)

        # Check if user can view sharing info for this job
        has_access = await permissions.check_job_access(job, user_obj, "view")
        if not has_access:
            raise PermissionError(
                "You don't have permission to view this job",
                details={"job_id": job_id, "user_id": user_id},
            )

        # Pass the current user's id into the service
        result = await sharing_service.get_job_sharing_info(job_id, user_id)

        if isinstance(result, dict) and result.get("status") == "error":
            message = result.get("message", "Unable to fetch job sharing info")
            lowered = message.lower()
            details = {"job_id": job_id, "user_id": user_id}
            if "not found" in lowered:
                raise ResourceNotFoundError("Job", job_id, details)
            raise ApplicationError(
                message,
                ErrorCode.INVALID_INPUT,
                status_code=400,
                details=details,
            )

        # Expecting a dict-like sharing info on success
        sharing_info = result.get("sharing_info") if isinstance(result, dict) else {}
        shared_with = sharing_info.get("shared_with") if isinstance(sharing_info, dict) else []
        total_shares = sharing_info.get("shared_with_count") if isinstance(sharing_info, dict) else 0
        is_owner = sharing_info.get("is_owner") if isinstance(sharing_info, dict) else False

        # Determine user permission based on ownership and sharing
        user_permission = "admin" if is_owner else "view"  # Default to view for shared users

        # If not owner, check the actual permission level from shared_with
        if not is_owner and isinstance(shared_with, list):
            user_share = next(
                (share for share in shared_with if share.get("user_id") == user_id),
                None
            )
            if user_share:
                user_permission = user_share.get("permission_level", "view")

        return {
            "status": "success",
            "job_id": job_id,
            "is_owner": is_owner,
            "user_permission": user_permission,
            "shared_with": shared_with or [],
            "total_shares": total_shares or 0
        }

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get job sharing info",
            exc,
            details={
                "job_id": job_id,
                "user_id": getattr(current_user, "id", current_user),
            },
        )


@router.get("/shared")
async def get_shared_jobs(
    current_user: dict = Depends(get_current_user),
    sharing_service: JobSharingService = Depends(get_job_sharing_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get all jobs shared with the current user.
    
    Args:
        current_user: Current user ID from auth
        sharing_service: Job sharing service
    """
    try:
        # get_shared_jobs returns a list of job dicts
        user_id = current_user if isinstance(current_user, str) else current_user.get("id")
        jobs = await sharing_service.get_shared_jobs(user_id)
        if not isinstance(jobs, list):
            if isinstance(jobs, dict) and jobs.get("status") == "error":
                raise ApplicationError(
                    jobs.get("message", "Error fetching shared jobs"),
                    ErrorCode.INVALID_INPUT,
                    status_code=400,
                    details={"user_id": user_id},
                )
            raise ApplicationError(
                "Unexpected response from sharing service",
                ErrorCode.INTERNAL_ERROR,
                status_code=500,
                details={"user_id": user_id, "response_type": type(jobs).__name__},
            )

        return {
            "status": "success",
            "shared_jobs": jobs,
            "total_count": len(jobs)
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get shared jobs",
            exc,
            details={"user_id": user_id},
        )
