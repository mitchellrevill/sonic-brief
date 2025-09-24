from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from ...core.dependencies import get_current_user, get_job_sharing_service
from ...services.jobs.job_sharing_service import JobSharingService
from ...services.jobs.job_permissions import JobPermissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["job-sharing"])


def get_job_permissions() -> JobPermissions:
    """Dependency provider for JobPermissions."""
    return JobPermissions()


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
    permissions: JobPermissions = Depends(get_job_permissions)
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
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[{"loc": ["body", "shared_user_email"], "msg": "Field required", "type": "value_error.missing"}]
            )

        # Check if user can share this job
        # Pass the full user object to the permissions helper so it can check ownership and shared entries
        has_access = await permissions.check_job_access(job_id, user_obj, "admin")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to share this job"
            )

        # Validate permission level
        valid_permissions = ["view", "edit", "admin"]
        if permission_level not in valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level. Must be one of: {valid_permissions}"
            )

        result = await sharing_service.share_job(
            job_id=job_id,
            owner_user_id=user_id,
            target_user_email=shared_user_email,
            permission_level=permission_level
        )
        
        if result["status"] == "error":
            if "not found" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            elif "already shared" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        return {
            "status": "success",
            "message": f"Job shared successfully with {shared_user_email}",
            "sharing_id": result.get("sharing_id"),
            "permission_level": permission_level
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{job_id}/share/{shared_user_email}")
async def unshare_job(
    job_id: str,
    shared_user_email: str,
    current_user: Any = Depends(get_current_user),
    sharing_service: JobSharingService = Depends(get_job_sharing_service),
    permissions: JobPermissions = Depends(get_job_permissions)
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

        # Check if user can manage sharing for this job
        has_access = await permissions.check_job_access(job_id, user_obj, "admin")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage sharing for this job"
            )
        
        result = await sharing_service.unshare_job(
            job_id=job_id,
            owner_user_id=user_id,
            target_user_email=shared_user_email
        )
        
        if result["status"] == "error":
            if "not found" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        return {
            "status": "success",
            "message": f"Sharing removed for {shared_user_email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsharing job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{job_id}/sharing")
async def get_job_sharing_info(
    job_id: str,
    current_user: Any = Depends(get_current_user),
    sharing_service: JobSharingService = Depends(get_job_sharing_service),
    permissions: JobPermissions = Depends(get_job_permissions)
):
    """
    Get sharing information for a job.
    
    Args:
        job_id: ID of the job
        current_user: Current user ID from auth
        sharing_service: Job sharing service
        permissions: Job permissions service
    """

    try:
        # Normalize current user: keep both object and id
        user_obj = current_user
        user_id = user_obj if isinstance(user_obj, str) else user_obj.get("id")

        # Check if user can view sharing info for this job
        has_access = await permissions.check_job_access(job_id, user_obj, "view")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this job"
            )

        # Pass the current user's id into the service
        result = await sharing_service.get_job_sharing_info(job_id, user_id)

        if isinstance(result, dict) and result.get("status") == "error":
            if "not found" in result.get("message", ""):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.get("message")
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("message")
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sharing info for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/shared")
async def get_shared_jobs(
    current_user: dict = Depends(get_current_user),
    sharing_service: JobSharingService = Depends(get_job_sharing_service)
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
            # Defensive: if service returns an error dict, surface as HTTP 400
            if isinstance(jobs, dict) and jobs.get("status") == "error":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=jobs.get("message", "Error fetching shared jobs")
                )
            # Unexpected shape
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response from sharing service"
            )

        return {
            "status": "success",
            "shared_jobs": jobs,
            "total_count": len(jobs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shared jobs for user {current_user}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
