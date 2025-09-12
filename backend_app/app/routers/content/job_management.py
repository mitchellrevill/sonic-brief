"""
Job Management Router - Job operations and lifecycle management
Handles job retrieval, status updates, sharing, and processing
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Query,
    Body,
    BackgroundTasks,
)
from pydantic import BaseModel
import logging
from urllib.parse import urlparse

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB, DatabaseError
from ...services.storage import StorageService
from ...services.processing.background_service import get_background_service
from ...core.dependencies import get_current_user, require_job_owner_or_admin, require_job_view, require_job_edit, get_effective_capabilities
from ...models.permissions import (
    PermissionLevel,
    PermissionCapability,
    can_user_perform_action,
    get_user_capabilities,
    merge_custom_capabilities,
)
from ...core.permissions import user_has_capability_for_job

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["job-management"])


class JobShareRequest(BaseModel):
    target_user_id: str
    permission: str = "read"  # "read" or "write"


class JobShareResponse(BaseModel):
    status: str
    message: str
    job_id: str
    shared_with_count: int


class JobUnshareRequest(BaseModel):
    target_user_id: str


class JobSoftDeleteRequest(BaseModel):
    reason: Optional[str] = None


class SharedJobsResponse(BaseModel):
    status: str
    shared_jobs: List[Dict[str, Any]]
    count: int


def get_user_job_permission(job: Dict[str, Any], user: Dict[str, Any]) -> str:
    """Determine user's permission level for a specific job"""
    if job["user_id"] == user["id"]:
        return "owner"
    
    shared_with = job.get("shared_with", [])
    for share in shared_with:
        if share.get("user_id") == user["id"]:
            return share.get("permission", "read")
    
    # Check if user has admin access
    user_permission = user.get("permission")
    if user_permission == PermissionLevel.ADMIN.value:
        return "admin"
    
    return "none"


def _user_has_capability_for_job(user: Dict[str, Any], job: Dict[str, Any], capability: str) -> bool:
    return user_has_capability_for_job(user, job, capability)


@router.get("/jobs")
async def get_jobs(
    include_shared: bool = Query(default=True, description="Include jobs shared with user"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of jobs to return"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    effective_capabilities: Dict[str, bool] = Depends(get_effective_capabilities),
) -> Dict[str, Any]:
    """Get jobs for the current user, including shared jobs if requested"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        storage_service = StorageService(config)

        # Determine effective capabilities for the current user (provided by dependency)
        can_view_all = effective_capabilities.get(PermissionCapability.CAN_VIEW_ALL_JOBS, False)

        # Build query based on permissions
        if can_view_all:
            query = "SELECT * FROM c WHERE c.type = 'job'"
            parameters = []
        else:
            query = "SELECT * FROM c WHERE c.type = 'job' AND c.user_id = @user_id"
            parameters = [{"name": "@user_id", "value": current_user["id"]}]
            # Add shared jobs if requested
            if include_shared:
                user_access_filter = (
                    " AND (c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_with, {'user_id': @user_id}, true))"
                )
                query += user_access_filter
                parameters.append({"name": "@user_id", "value": current_user["id"]})

        # Exclude soft-deleted jobs
        query += " AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)"

        try:
            jobs = list(
                cosmos_db.jobs_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            # Annotate jobs with capability hints and SAS tokens
            for job in jobs:
                job["is_owned"] = job["user_id"] == current_user["id"]
                job["shared_with_count"] = len(job.get("shared_with", []))
                job["can_download"] = _user_has_capability_for_job(
                    current_user, job, PermissionCapability.CAN_DOWNLOAD_FILES.value
                )
                job["can_edit"] = _user_has_capability_for_job(
                    current_user, job, PermissionCapability.CAN_EDIT_OWN_JOBS.value
                )

                if job.get("file_path"):
                    file_path = job["file_path"]
                    path_parts = urlparse(file_path).path.strip("/").split("/")
                    job["file_name"] = path_parts[-1] if path_parts else None
                    job["file_path"] = storage_service.add_sas_token_to_url(file_path)
                if job.get("transcription_file_path"):
                    job["transcription_file_path"] = storage_service.add_sas_token_to_url(
                        job["transcription_file_path"]
                    )
                if job.get("analysis_file_path"):
                    job["analysis_file_path"] = storage_service.add_sas_token_to_url(
                        job["analysis_file_path"]
                    )

            # Apply pagination
            total_count = len(jobs)
            jobs = jobs[offset:offset + limit]

            logger.info(f"Retrieved {len(jobs)} jobs for user {current_user['id']}")
            return {
                "status": "success",
                "jobs": jobs,
                "count": len(jobs),
                "total": total_count,
                "offset": offset,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Database error retrieving jobs: {str(e)}", exc_info=True)
            return {"status": 500, "message": f"Database error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error getting jobs: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}


@router.get("/jobs/{job_id}")
async def get_job_by_id(
    job_id: str,
    job: Dict[str, Any] = Depends(require_job_view),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a specific job by ID"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        storage_service = StorageService(config)
        
    # job is provided by require_job_view dependency
        
        # Add SAS tokens to file paths
        if job.get("file_path"):
            job["file_path"] = storage_service.add_sas_token_to_url(job["file_path"])
        if job.get("transcription_file_path"):
            job["transcription_file_path"] = storage_service.add_sas_token_to_url(
                job["transcription_file_path"]
            )
        if job.get("analysis_file_path"):
            job["analysis_file_path"] = storage_service.add_sas_token_to_url(
                job["analysis_file_path"]
            )

        # Add metadata
        job["is_owned"] = job["user_id"] == current_user["id"]
        job["shared_with_count"] = len(job.get("shared_with", []))
        job["can_download"] = _user_has_capability_for_job(
            current_user, job, PermissionCapability.CAN_DOWNLOAD_FILES.value
        )
        job["can_edit"] = _user_has_capability_for_job(
            current_user, job, PermissionCapability.CAN_EDIT_OWN_JOBS.value
        )

        return {
            "status": "success",
            "job": job
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving job")


@router.post("/jobs/{job_id}/process-analysis")
async def process_text_analysis(
    job_id: str,
    background_tasks: BackgroundTasks,
    job: Dict[str, Any] = Depends(require_job_edit),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Start background text analysis for a job"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
    # job provided by require_job_edit
        
        if not job.get("text_content"):
            raise HTTPException(
                status_code=400, 
                detail="Job does not have text content for processing"
            )
        
        if job.get("status") not in ["transcribed", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not ready for analysis. Current status: {job.get('status')}"
            )
        
        # Update job status to processing
        update_fields = {
            "status": "processing",
            "message": "Analysis queued for processing...",
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
        cosmos_db.update_job(job_id, update_fields)
        
        # Start background analysis
        background_service = get_background_service()
        task = await background_service.submit_task(
            task_id=f"analysis_{job_id}",
            task_type="text_analysis",
            user_id=current_user["id"],
            task_func=background_service.perform_text_analysis,
            background_tasks=background_tasks,
            metadata={
                "job_id": job_id,
                "analysis_type": "text_analysis"
            },
            job_id=job_id
        )
        
        logger.info(f"Background analysis task submitted: {task.task_id} for job_id: {job_id}")
        
        return {
            "status": "processing", 
            "message": "Analysis started in background. Check job status for updates.",
            "task_id": task.task_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis for job_id {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error starting text analysis")


@router.post("/jobs/{job_id}/share")
async def share_job(
    job_id: str,
    share_request: JobShareRequest,
    current_user: Dict[str, Any] = Depends(require_job_owner_or_admin),
) -> JobShareResponse:
    """Share a job with another user"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        job = cosmos_db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if current user owns the job
        if job["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only job owner can share jobs")
        
        # Validate target user exists
        target_user = await cosmos_db.get_user_by_id(share_request.target_user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        # Check if already shared
        shared_with = job.get("shared_with", [])
        for share in shared_with:
            if share.get("user_id") == share_request.target_user_id:
                # Update existing share
                share["permission"] = share_request.permission
                share["updated_at"] = datetime.now(timezone.utc).isoformat()
                break
        else:
            # Add new share
            shared_with.append({
                "user_id": share_request.target_user_id,
                "user_email": target_user.get("email"),
                "permission": share_request.permission,
                "shared_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Update job
        update_fields = {
            "shared_with": shared_with,
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} shared with user {share_request.target_user_id} by {current_user['id']}")
        
        return JobShareResponse(
            status="success",
            message=f"Job shared successfully with {target_user.get('email', 'user')}",
            job_id=job_id,
            shared_with_count=len(shared_with)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error sharing job")


@router.delete("/jobs/{job_id}/share")
async def unshare_job(
    job_id: str,
    unshare_request: JobUnshareRequest,
    current_user: Dict[str, Any] = Depends(require_job_owner_or_admin),
) -> Dict[str, Any]:
    """Remove sharing for a job"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        job = cosmos_db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if current user owns the job
        if job["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only job owner can unshare jobs")
        
        # Remove from shared_with list
        shared_with = job.get("shared_with", [])
        original_count = len(shared_with)
        shared_with = [s for s in shared_with if s.get("user_id") != unshare_request.target_user_id]
        
        if len(shared_with) == original_count:
            raise HTTPException(status_code=404, detail="Job was not shared with this user")
        
        # Update job
        update_fields = {
            "shared_with": shared_with,
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} unshared from user {unshare_request.target_user_id} by {current_user['id']}")
        
        return {
            "status": "success",
            "message": "Job unshared successfully",
            "job_id": job_id,
            "shared_with_count": len(shared_with)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsharing job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error unsharing job")


@router.delete("/jobs/{job_id}")
async def soft_delete_job(
    job_id: str,
    delete_request: JobSoftDeleteRequest = Body(...),
    current_user: Dict[str, Any] = Depends(require_job_owner_or_admin),
) -> Dict[str, Any]:
    """Soft delete a job (mark as deleted rather than permanent removal)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        job = cosmos_db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check permissions: only owner or admin can delete
        if not (job.get("user_id") == current_user.get("id") or current_user.get("permission") == PermissionLevel.ADMIN.value):
            raise HTTPException(status_code=403, detail="Only job owner or admin can delete jobs")
        
        # Soft delete the job
        update_fields = {
            "deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": current_user["id"],
            "deletion_reason": delete_request.reason or "User requested deletion",
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} soft deleted by user {current_user['id']}")
        
        return {
            "status": "success",
            "message": "Job deleted successfully",
            "job_id": job_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting job")
