from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
import uuid

from ...core.config import get_config, DatabaseError
from ...core.dependencies import CosmosService
from ..storage.blob_service import StorageService
from ...core.async_utils import run_sync
from .job_service import JobService

logger = logging.getLogger(__name__)


class JobManagementService:
    """Service for job lifecycle management operations (soft delete, restore, admin operations)."""
    
    def __init__(self, cosmos_service: CosmosService, storage_service: StorageService):
        self.cosmos = cosmos_service
        self.job_service = JobService(cosmos_service, storage_service)

    async def soft_delete_job(self, job_id: str, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Soft delete a job (mark as deleted but keep in database).
        
        Args:
            job_id: ID of the job to delete
            user_id: ID of the user performing the deletion
            is_admin: Whether the user is an admin
            
        Returns:
            Dict containing delete result
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check permissions
            if not is_admin and job.get("user_id") != user_id:
                return {"status": "error", "message": "Access denied: not job owner"}
            
            # Check if already deleted
            if job.get("deleted", False):
                return {"status": "error", "message": "Job is already deleted"}
            
            # Mark as deleted
            job["deleted"] = True
            job["deleted_at"] = datetime.now(timezone.utc).isoformat()
            job["deleted_by"] = user_id
            
            # Update the job in database (use async wrapper)
            await self.cosmos.update_job_async(job_id, job)
            
            return {
                "status": "success",
                "message": "Job deleted successfully",
                "job_id": job_id,
                "deleted_at": job["deleted_at"]
            }
            
        except DatabaseError as e:
            logger.error(f"Database error soft deleting job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error soft deleting job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def restore_job(self, job_id: str, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Restore a soft deleted job (admin only).
        
        Args:
            job_id: ID of the job to restore
            user_id: ID of the user performing the restoration
            is_admin: Whether the user is an admin
            
        Returns:
            Dict containing restore result
        """
        try:
            if not is_admin:
                return {"status": "error", "message": "Access denied: admin privileges required"}
            
            # Get the job (including deleted ones)
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check if it's actually deleted
            if not job.get("deleted", False):
                return {"status": "error", "message": "Job is not deleted"}
            
            # Restore the job
            job["deleted"] = False
            job["restored_at"] = datetime.now(timezone.utc).isoformat()
            job["restored_by"] = user_id
            
            # Remove deletion metadata
            if "deleted_at" in job:
                del job["deleted_at"]
            if "deleted_by" in job:
                del job["deleted_by"]
            
            # Update the job in database (use async wrapper)
            await self.cosmos.update_job_async(job_id, job)
            
            return {
                "status": "success",
                "message": "Job restored successfully",
                "job_id": job_id,
                "restored_at": job["restored_at"]
            }
            
        except DatabaseError as e:
            logger.error(f"Database error restoring job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error restoring job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def permanent_delete_job(self, job_id: str, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Permanently delete a job from database (admin only).
        
        Args:
            job_id: ID of the job to permanently delete
            user_id: ID of the user performing the deletion
            is_admin: Whether the user is an admin
            
        Returns:
            Dict containing permanent delete result
        """
        try:
            if not is_admin:
                return {"status": "error", "message": "Access denied: admin privileges required"}
            
            # Get the job first to verify it exists
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Delete the job permanently (use async wrapper)
            await self.cosmos.delete_job(job_id)
            
            logger.info(f"Job {job_id} permanently deleted by admin user {user_id}")
            
            return {
                "status": "success",
                "message": "Job permanently deleted",
                "job_id": job_id,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
            
        except DatabaseError as e:
            logger.error(f"Database error permanently deleting job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error permanently deleting job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_deleted_jobs(self, user_id: str, limit: int = 50, offset: int = 0, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get all soft deleted jobs (admin only).

        Args:
            user_id: ID of the user requesting deleted jobs
            limit: maximum number of jobs to return
            offset: pagination offset
            is_admin: Whether the user is an admin

        Returns:
            Dict containing deleted_jobs list and total_count
        """
        try:
            if not is_admin:
                return {"status": "error", "message": "Access denied: admin privileges required", "deleted_jobs": [], "total_count": 0}

            # Query for all deleted jobs
            query = """
            SELECT * FROM c 
            WHERE c.type = 'job' 
            AND c.deleted = true
            ORDER BY c.deleted_at DESC
            """

            items = await run_sync(lambda: list(
                self.cosmos.jobs_container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            ))

            total = len(items)
            sliced = items[offset: offset + limit]
            
            # Enrich deleted jobs with display names and file URLs
            enriched_jobs = []
            for job in sliced:
                enriched_job = self.job_service.enrich_job_file_urls(job)
                enriched_jobs.append(enriched_job)

            return {"status": "success", "deleted_jobs": enriched_jobs, "total_count": total}

        except DatabaseError as e:
            logger.error(f"Database error getting deleted jobs: {str(e)}")
            return {"status": "error", "message": "Database service unavailable", "deleted_jobs": [], "total_count": 0}
        except Exception as e:
            logger.error(f"Error getting deleted jobs: {str(e)}")
            return {"status": "error", "message": str(e), "deleted_jobs": [], "total_count": 0}

    async def get_my_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get only the jobs owned by the current user.
        
        Args:
            user_id: ID of the current user
            
        Returns:
            List of user's jobs
        """
        try:
            query = """
            SELECT * FROM c 
            WHERE c.type = 'job' 
            AND c.user_id = @user_id 
            AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
            ORDER BY c.created_at DESC
            """
            params = [{"name": "@user_id", "value": user_id}]
            
            jobs = await run_sync(lambda: list(
                self.cosmos.jobs_container.query_items(
                    query=query,
                    parameters=params,
                    enable_cross_partition_query=True,
                )
            ))
            
            return jobs
            
        except DatabaseError as e:
            logger.error(f"Database error getting jobs for user {user_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting jobs for user {user_id}: {str(e)}")
            raise

    async def trigger_analysis_processing(self, job_id: str, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Trigger analysis processing for text-only submissions.
        
        Args:
            job_id: ID of the job to process
            user_id: ID of the user requesting processing
            
        Returns:
            Dict containing processing status
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check if user has access to this job (admins bypass owner check)
            if not is_admin and job.get("user_id") != user_id:
                return {"status": "error", "message": "Access denied"}
            
            # Check if job has text content to analyze
            if not job.get("text_content") and not job.get("transcription_file_path"):
                return {"status": "error", "message": "No text content available for analysis"}
            
            # Update job status to indicate processing
            job["status"] = "processing_analysis"
            job["analysis_started_at"] = datetime.now(timezone.utc).isoformat()
            
            await self.cosmos.update_job_async(job_id, job)
            
            # Here you would typically trigger background analysis processing
            # For now, just return success status
            
            return {
                "status": "success",
                "message": "Analysis processing initiated",
                "job_id": job_id,
                "processing_started_at": job["analysis_started_at"]
            }
            
        except DatabaseError as e:
            logger.error(f"Database error triggering analysis for job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error triggering analysis for job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_all_jobs(self, limit: int = 100, offset: int = 0, include_deleted: bool = False) -> Dict[str, Any]:
        """
        Retrieve all jobs across the system (admin access).

        Returns a dict with 'jobs' and 'total_count'.
        """
        try:
            # Build base query
            query = """
            SELECT * FROM c
            WHERE c.type = 'job'
            """
            if not include_deleted:
                query += "\nAND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)"

            query += "\nORDER BY c.created_at DESC"

            # Cosmos SDK doesn't support OFFSET directly; use continuation or manual slicing
            items = await run_sync(lambda: list(
                self.cosmos.jobs_container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            ))

            total = len(items)
            sliced = items[offset: offset + limit]
            
            # Enrich jobs with display names and file URLs
            enriched_jobs = []
            for job in sliced:
                enriched_job = self.job_service.enrich_job_file_urls(job)
                enriched_jobs.append(enriched_job)

            return {"jobs": enriched_jobs, "total_count": total}

        except DatabaseError as e:
            logger.error(f"Database error getting all jobs: {str(e)}")
            return {"jobs": [], "total_count": 0, "error": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error getting all jobs: {str(e)}")
            return {"jobs": [], "total_count": 0, "error": str(e)}

    def close(self):
        """Close any resources - placeholder for consistency"""
        logger.info("JobManagementService.close: no resources to close")
