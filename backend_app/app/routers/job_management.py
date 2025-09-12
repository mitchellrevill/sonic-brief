# Job Management Router - Extracted from upload.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from app.core.dependencies import require_job_management, require_admin, get_current_user
from app.services.job_service import job_service
from app.utils.logging_config import get_logger

router = APIRouter(prefix="/jobs", tags=["Job Management"])
logger = get_logger(__name__)

@router.get("")
async def get_jobs(
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(require_job_management)
):
    """Get all jobs (admin/editor access)"""
    try:
        return await job_service.get_jobs(skip=skip, limit=limit, user_id=current_user["user_id"])
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")

@router.get("/my")
async def get_my_jobs(
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get jobs for current user"""
    try:
        return await job_service.get_user_jobs(current_user["user_id"], skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error getting user jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user jobs")

@router.get("/shared")
async def get_shared_jobs(
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get jobs shared with current user"""
    try:
        return await job_service.get_shared_jobs(current_user["user_id"], skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error getting shared jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve shared jobs")

@router.get("/{job_id}")
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific job details"""
    try:
        return await job_service.get_job(job_id, current_user["user_id"])
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job")

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a job"""
    try:
        await job_service.delete_job(job_id, current_user["user_id"])
        return {"message": "Job deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete job")

# Admin endpoints
@router.get("/admin/deleted")
async def get_deleted_jobs(
    current_user: dict = Depends(require_admin)
):
    """Get all deleted jobs (admin only)"""
    try:
        return await job_service.get_deleted_jobs()
    except Exception as e:
        logger.error(f"Error getting deleted jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve deleted jobs")

@router.delete("/{job_id}/permanent")
async def permanently_delete_job(
    job_id: str,
    current_user: dict = Depends(require_admin)
):
    """Permanently delete a job (admin only)"""
    try:
        await job_service.permanently_delete_job(job_id)
        return {"message": "Job permanently deleted"}
    except Exception as e:
        logger.error(f"Error permanently deleting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to permanently delete job")
