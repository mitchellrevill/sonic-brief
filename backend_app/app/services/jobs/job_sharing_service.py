from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from ...core.config import get_app_config, get_cosmos_db_cached, DatabaseError
from ...core.async_utils import run_sync

logger = logging.getLogger(__name__)


class JobSharingService:
    """Service for handling job sharing operations with Cosmos DB."""
    
    def __init__(self, cosmos_db=None):
        cfg = get_app_config()
        if cosmos_db is None:
            cosmos_db = get_cosmos_db_cached(cfg)
        self.cosmos = cosmos_db

    async def share_job(self, job_id: str, owner_user_id: str, target_user_email: str, permission_level: str = "view") -> Dict[str, Any]:
        """
        Share a job with another user.
        
        Args:
            job_id: ID of the job to share
            owner_user_id: ID of the user who owns the job
            target_user_email: Email of the user to share with
            permission_level: Permission level ("view", "edit", "admin")
            
        Returns:
            Dict containing share result
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Verify ownership
            if job.get("user_id") != owner_user_id:
                return {"status": "error", "message": "Access denied: not job owner"}
            
            # Get target user by email
            target_user = await self.cosmos.get_user_by_email(target_user_email)
            if not target_user:
                return {"status": "error", "message": "Target user not found"}
            
            # Initialize shared_with if not exists
            if "shared_with" not in job:
                job["shared_with"] = []
            
            # Check if already shared with this user
            existing_share = next(
                (share for share in job["shared_with"] if share.get("user_id") == target_user["id"]),
                None
            )
            
            if existing_share:
                # Update existing share
                existing_share["permission_level"] = permission_level
                existing_share["shared_at"] = datetime.now(timezone.utc).isoformat()
            else:
                # Add new share
                job["shared_with"].append({
                    "user_id": target_user["id"],
                    "user_email": target_user_email,
                    "permission_level": permission_level,
                    "shared_at": datetime.now(timezone.utc).isoformat(),
                    "shared_by": owner_user_id
                })
            
            # Update the job in database (use async wrapper)
            await self.cosmos.update_job_async(job_id, job)
            
            return {
                "status": "success",
                "message": f"Job shared with {target_user_email}",
                "permission_level": permission_level,
                "shared_with_count": len(job["shared_with"])
            }
            
        except DatabaseError as e:
            logger.error(f"Database error sharing job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error sharing job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def unshare_job(self, job_id: str, owner_user_id: str, target_user_email: str) -> Dict[str, Any]:
        """
        Remove job sharing with a specific user.
        
        Args:
            job_id: ID of the job to unshare
            owner_user_id: ID of the user who owns the job
            target_user_email: Email of the user to unshare from
            
        Returns:
            Dict containing unshare result
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Verify ownership
            if job.get("user_id") != owner_user_id:
                return {"status": "error", "message": "Access denied: not job owner"}
            
            # Remove share if exists
            if "shared_with" in job:
                original_count = len(job["shared_with"])
                job["shared_with"] = [
                    share for share in job["shared_with"] 
                    if share.get("user_email") != target_user_email
                ]
                
                if len(job["shared_with"]) < original_count:
                    # Update the job in database (use async wrapper)
                    await self.cosmos.update_job_async(job_id, job)
                    return {
                        "status": "success",
                        "message": f"Job unshared from {target_user_email}",
                        "shared_with_count": len(job["shared_with"])
                    }
                else:
                    return {"status": "error", "message": "Job was not shared with this user"}
            else:
                return {"status": "error", "message": "Job is not shared with anyone"}
                
        except DatabaseError as e:
            logger.error(f"Database error unsharing job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error unsharing job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_job_sharing_info(self, job_id: str, current_user_id: str) -> Dict[str, Any]:
        """
        Get sharing information for a specific job.
        
        Args:
            job_id: ID of the job
            current_user_id: ID of the current user
            
        Returns:
            Dict containing job sharing information
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check if user has access to this job
            is_owner = job.get("user_id") == current_user_id
            has_shared_access = False
            
            if "shared_with" in job:
                has_shared_access = any(
                    share.get("user_id") == current_user_id 
                    for share in job["shared_with"]
                )
            
            if not (is_owner or has_shared_access):
                return {"status": "error", "message": "Access denied"}
            
            sharing_info = {
                "job_id": job_id,
                "is_owner": is_owner,
                "shared_with": job.get("shared_with", []),
                "shared_with_count": len(job.get("shared_with", [])),
                "is_shared": len(job.get("shared_with", [])) > 0
            }
            
            return {"status": "success", "sharing_info": sharing_info}
            
        except DatabaseError as e:
            logger.error(f"Database error getting sharing info for job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error getting sharing info for job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_shared_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all jobs shared with the current user and jobs owned by current user that are shared with others.
        
        Args:
            user_id: ID of the current user
            
        Returns:
            List of shared jobs
        """
        try:
            # Query for jobs shared with this user. Some tokens use the user's
            # email as the identifier while shared entries store the internal
            # user id. To be tolerant, search for both `user_id` and
            # `user_email` inside shared_with.
            shared_query_by_id = """
            SELECT * FROM c
            WHERE c.type = 'job'
            AND ARRAY_CONTAINS(c.shared_with, {'user_id': @user_id}, false)
            AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
            """

            shared_query_by_email = """
            SELECT * FROM c
            WHERE c.type = 'job'
            AND ARRAY_CONTAINS(c.shared_with, {'user_email': @user_email}, false)
            AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
            """

            shared_params_id = [{"name": "@user_id", "value": user_id}]
            shared_params_email = [{"name": "@user_email", "value": user_id}]

            shared_jobs = await run_sync(lambda: list(
                self.cosmos.jobs_container.query_items(
                    query=shared_query_by_id,
                    parameters=shared_params_id,
                    enable_cross_partition_query=True,
                )
            ))

            # Also include matches where the shared entry contains the user's email
            try:
                shared_jobs_by_email = await run_sync(lambda: list(
                    self.cosmos.jobs_container.query_items(
                        query=shared_query_by_email,
                        parameters=shared_params_email,
                        enable_cross_partition_query=True,
                    )
                ))
            except Exception:
                shared_jobs_by_email = []

            # Merge both lists
            shared_jobs.extend(shared_jobs_by_email)
            
            # Query for jobs owned by current user that are shared with others
            owned_shared_query = """
            SELECT * FROM c 
            WHERE c.type = 'job' 
            AND c.user_id = @user_id 
            AND IS_DEFINED(c.shared_with) 
            AND ARRAY_LENGTH(c.shared_with) > 0
            AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
            """
            
            owned_shared_jobs = await run_sync(lambda: list(
                self.cosmos.jobs_container.query_items(
                    query=owned_shared_query,
                    parameters=shared_params_id,
                    enable_cross_partition_query=True,
                )
            ))
            
            # Combine and deduplicate
            all_jobs = shared_jobs + owned_shared_jobs
            seen_ids = set()
            unique_jobs = []
            
            for job in all_jobs:
                if job["id"] not in seen_ids:
                    seen_ids.add(job["id"])
                    unique_jobs.append(job)
            
            return unique_jobs
            
        except DatabaseError as e:
            logger.error(f"Database error getting shared jobs for user {user_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting shared jobs for user {user_id}: {str(e)}")
            raise

    def close(self):
        """Close any resources - placeholder for consistency"""
        logger.info("JobSharingService.close: no resources to close")
