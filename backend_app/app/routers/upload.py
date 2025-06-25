from datetime import datetime, timezone, date
import json
from typing import Dict, Any, Optional, List
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Request,
    File,
    UploadFile,
    Query,
    Form,
    Response,
    BackgroundTasks,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import tempfile
import os
from urllib.parse import urlparse

from app.core.config import AppConfig, CosmosDB, DatabaseError
from app.services.storage_service import StorageService
from app.services.analysis_refinement_service import AnalysisRefinementService
from app.services.background_processing_service import get_background_service
from app.routers.auth import get_current_user
import logging
import traceback
from azure.core.exceptions import AzureError

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/api", tags=["upload"])

# Pydantic models for request/response
class AnalysisRefinementRequest(BaseModel):
    message: str

class AnalysisRefinementResponse(BaseModel):
    status: str
    message: str
    response: str
    refinement_id: str
    timestamp: int

class JobShareRequest(BaseModel):
    target_user_email: str
    permission_level: str = "view"  # "view", "edit", "admin"
    message: Optional[str] = None

class JobShareResponse(BaseModel):
    status: str
    message: str
    shared_job_id: str
    target_user_id: str
    permission_level: str

class JobUnshareRequest(BaseModel):
    target_user_email: str

class JobSoftDeleteRequest(BaseModel):
    permanent: bool = False  # For admin permanent delete

class SharedJobsResponse(BaseModel):
    status: str
    message: str
    shared_jobs: List[Dict[str, Any]]
    owned_jobs_shared_with_others: List[Dict[str, Any]]


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    file: UploadFile = File(None),
    text_content: str = Form(None),
    prompt_category_id: str = Form(None),
    prompt_subcategory_id: str = Form(None),
) -> Dict[str, Any]:
    """
    Upload a file or process text content and create a job record.
    Uses background tasks for improved performance on large files.

    Args:
        file: The file to upload (optional)
        text_content: Direct text content for processing (optional)
        prompt_category_id: Category ID for the prompt
        prompt_subcategory_id: Subcategory ID for the prompt
        background_tasks: FastAPI background tasks for async processing
        current_user: Authenticated user from token

    Returns:
        Dict containing job ID and status
    """
    print(f"Received prompt_category_id: {prompt_category_id}")
    print(f"Received prompt_subcategory_id: {prompt_subcategory_id}")
    print(f"Received file: {file.filename if file else None}")
    print(f"Received text_content: {'Yes' if text_content else 'No'}")

    if not prompt_category_id or not prompt_subcategory_id:
        raise HTTPException(
            status_code=400, detail="Category and Subcategory IDs cannot be null"
        )
    
    if not file and not text_content:
        raise HTTPException(
            status_code=400, detail="Either a file or text content must be provided"
        )

    try:
        config = AppConfig()
        try:
            cosmos_db = CosmosDB(config)
            logger.debug("CosmosDB client initialized for upload")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        # Validate prompt category and subcategory if provided
        if prompt_category_id:
            category_query = (
                "SELECT * FROM c WHERE c.type = 'prompt_category' AND c.id = @id"
            )
            categories = list(
                cosmos_db.prompts_container.query_items(
                    query=category_query,
                    parameters=[{"name": "@id", "value": prompt_category_id}],
                    enable_cross_partition_query=True,
                )
            )
            if not categories:
                return {
                    "status": 400,
                    "message": f"Invalid prompt_category_id: {prompt_category_id}",
                }

            if prompt_subcategory_id:
                subcategory_query = """
                    SELECT * FROM c
                    WHERE c.type = 'prompt_subcategory'
                    AND c.id = @id
                    AND c.category_id = @category_id
                """
                subcategories = list(
                    cosmos_db.prompts_container.query_items(
                        query=subcategory_query,
                        parameters=[
                            {"name": "@id", "value": prompt_subcategory_id},
                            {"name": "@category_id", "value": prompt_category_id},
                        ],
                        enable_cross_partition_query=True,
                    )
                )
                if not subcategories:
                    return {
                        "status": 400,
                        "message": f"Invalid prompt_subcategory_id: {prompt_subcategory_id} for category: {prompt_category_id}",
                    }

        # Create job document first for immediate response
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        job_id = f"job_{timestamp}"
          # Determine job status based on submission type
        if file:
            job_status = "processing"  # File upload in progress
        else:
            job_status = "transcribed"  # Text is already available for analysis
        
        job_data = {
            "id": job_id,
            "type": "job",
            "user_id": current_user["id"],
            "file_path": None,  # Will be updated immediately after upload for files
            "transcription_file_path": None,
            "analysis_file_path": None,
            "prompt_category_id": prompt_category_id,
            "prompt_subcategory_id": prompt_subcategory_id,
            "status": job_status,
            "transcription_id": None,
            "text_content": text_content if text_content else None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        job = cosmos_db.create_job(job_data)        # Get background service for task submission
        background_service = get_background_service()

        # Handle file upload or text content 
        if file:
            # Upload file to storage synchronously to get blob URL immediately
            storage_service = StorageService(config)
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(file.filename)[1]
            ) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                # Upload file to blob storage synchronously
                blob_url = storage_service.upload_file(temp_file_path, file.filename)
                logger.info(f"File uploaded to blob storage: {blob_url}")
                
                # Clean up temporary file
                os.unlink(temp_file_path)
                
                # Update job with file path immediately
                update_fields = {
                    "status": "uploaded",
                    "message": "File uploaded successfully, processing in background",
                    "file_path": blob_url,
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                cosmos_db.update_job(job_id, update_fields)
                
                # Now submit any additional background processing if needed
                # (like transcription or analysis) - for now we just mark as uploaded
                logger.info(f"File upload completed synchronously for job {job_id}")
                message = "File uploaded successfully"
                
            except AzureError as e:
                logger.error(f"Storage error for job {job_id}: {str(e)}")
                # Update job with error status
                update_fields = {
                    "status": "failed",
                    "message": f"Storage service unavailable: {str(e)}",
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                cosmos_db.update_job(job_id, update_fields)
                raise HTTPException(status_code=503, detail="Storage service unavailable")
                
            except Exception as e:
                logger.error(f"Error uploading file for job {job_id}: {str(e)}")
                # Clean up temp file if it exists
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                # Update job with error status
                update_fields = {
                    "status": "failed", 
                    "message": f"File upload failed: {str(e)}",
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                cosmos_db.update_job(job_id, update_fields)
                raise HTTPException(status_code=500, detail="File upload failed")
        else:
            # For text-only submissions, process immediately since it's lightweight
            transcript_content = text_content
            logger.debug("Processing text-only submission")
            message = "Text content submitted successfully"

        return {
            "job_id": job_id,
            "status": job_status,
            "message": message,
            "prompt_category_id": prompt_category_id,
            "prompt_subcategory_id": prompt_subcategory_id,
            "submission_type": "file" if file else "text",
        }

    except Exception as e:
        logger.error(f"Unexpected error during upload: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Failed to upload file: {str(e)}"}


@router.get("/jobs")
async def get_jobs(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    created_at: Optional[str] = Query(
        None, description="Filter by creation date in YYYY-MM-DD format"
    ),
    prompt_subcategory_id: Optional[str] = Query(
        None, description="Filter by prompt subcategory ID"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get job details with optional filters.
    If the user is an admin, return all jobs. Otherwise, only return jobs owned by or shared with the user.
    """
    try:
        config = AppConfig()
        try:
            cosmos_db = CosmosDB(config)
            logger.debug("CosmosDB client initialized for job query")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        # Initialize storage service for SAS token generation
        storage_service = StorageService(config)

        # Build query
        query = "SELECT * FROM c WHERE c.type = 'job'"
        parameters = []

        if job_id:
            query += " AND c.id = @job_id"
            parameters.append({"name": "@job_id", "value": job_id})

        if status:
            query += " AND c.status = @status"
            parameters.append({"name": "@status", "value": status})

        if file_path:
            query += " AND c.file_path = @file_path"
            parameters.append({"name": "@file_path", "value": file_path})

        if created_at:
            try:
                parsed_date = datetime.strptime(created_at, "%Y-%m-%d").date()
                # Convert date to start and end of day timestamps
                start_of_day = int(
                    datetime.combine(parsed_date, datetime.min.time())
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                    * 1000
                )
                end_of_day = int(
                    datetime.combine(parsed_date, datetime.max.time())
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                    * 1000
                )
                query += (
                    " AND c.created_at >= @start_date AND c.created_at <= @end_date"
                )
                parameters.extend(
                    [
                        {"name": "@start_date", "value": start_of_day},
                        {"name": "@end_date", "value": end_of_day},
                    ]
                )
            except ValueError:
                logger.warning("Invalid created_at format")
                return {
                    "status": 400,
                    "message": "Invalid created_at date. Expected format: YYYY-MM-DD.",
                }

        # Only apply user access filter if not admin
        is_admin = False
        if "permission" in current_user:
            # Accepts 'Admin' or 'admin' (case-insensitive)
            is_admin = str(current_user["permission"]).lower() == "admin"
        elif "permissions" in current_user:
            # Some user objects may use 'permissions' as a list
            perms = current_user["permissions"]
            if isinstance(perms, list):
                is_admin = any(str(p).lower() == "admin" for p in perms)

        if not is_admin:
            user_access_filter = f" AND (c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_with, {{'user_id': @user_id}}, true))"
            query += user_access_filter
            parameters.append({"name": "@user_id", "value": current_user["id"]})

        # Exclude soft-deleted jobs for regular users (admins can see all jobs via admin endpoints)
        query += " AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)"

        try:
            jobs = list(
                cosmos_db.jobs_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )            # Add SAS tokens to file paths and sharing metadata
            for job in jobs:
                # Add sharing metadata
                job["is_owned"] = job["user_id"] == current_user["id"]
                job["user_permission"] = get_user_job_permission(job, current_user)
                job["shared_with_count"] = len(job.get("shared_with", []))
                
                if job.get("file_path"):
                    # Extract file name from the file path before adding SAS token
                    file_path = job["file_path"]
                    path_parts = urlparse(file_path).path.strip("/").split("/")
                    job["file_name"] = path_parts[-1] if path_parts else None
                    job["file_path"] = storage_service.add_sas_token_to_url(file_path)
                    if job.get("transcription_file_path"):                        job["transcription_file_path"] = (
                            storage_service.add_sas_token_to_url(
                                job["transcription_file_path"]
                            )
                        )
                    if job.get("analysis_file_path"):
                        job["analysis_file_path"] = storage_service.add_sas_token_to_url(
                            job["analysis_file_path"]
                        )

            return {
                "status": 200,
                "message": "Jobs retrieved successfully",
                "count": len(jobs),
                "jobs": jobs,
            }
        except Exception as e:
            logger.error(f"Error querying jobs: {str(e)}")
            return {"status": 500, "message": f"Error retrieving jobs: {str(e)}"}
            
    except Exception as e:
        logger.error(f"Unexpected error getting jobs: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}


@router.get("/jobs/my")
async def get_my_jobs(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get only the jobs owned by the current user (for user's audio recording page).
    """
    try:
        config = AppConfig()
        try:
            cosmos_db = CosmosDB(config)
            logger.debug("CosmosDB client initialized for my jobs query")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        storage_service = StorageService(config)

        query = "SELECT * FROM c WHERE c.type = 'job' AND c.user_id = @user_id AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)"
        parameters = [{"name": "@user_id", "value": current_user["id"]}]

        try:
            jobs = list(
                cosmos_db.jobs_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            for job in jobs:
                job["is_owned"] = True
                job["user_permission"] = get_user_job_permission(job, current_user)
                job["shared_with_count"] = len(job.get("shared_with", []))
                if job.get("file_path"):
                    file_path = job["file_path"]
                    path_parts = urlparse(file_path).path.strip("/").split("/")
                    job["file_name"] = path_parts[-1] if path_parts else None
                    job["file_path"] = storage_service.add_sas_token_to_url(file_path)
                    if job.get("transcription_file_path"):
                        job["transcription_file_path"] = storage_service.add_sas_token_to_url(job["transcription_file_path"])
                    if job.get("analysis_file_path"):
                        job["analysis_file_path"] = storage_service.add_sas_token_to_url(job["analysis_file_path"])
            return {
                "status": 200,
                "message": "User jobs retrieved successfully",
                "count": len(jobs),
                "jobs": jobs,
            }
        except Exception as e:
            logger.error(f"Error querying my jobs: {str(e)}")
            return {"status": 500, "message": f"Error retrieving jobs: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error getting my jobs: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}


@router.get("/jobs/shared")
async def get_shared_jobs(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get all jobs shared with the current user and jobs owned by current user that are shared with others.
    """
    # Add immediate logging to confirm endpoint is being reached
    logger.error("=== SHARED JOBS ENDPOINT CALLED ===")
    logger.error(f"Current user: {current_user}")
    logger.error(f"User ID: {current_user.get('id')}")
    logger.error(f"User Email: {current_user.get('email')}")
    
    try:
        logger.error("=== INITIALIZING SERVICES ===")
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        storage_service = StorageService(config)
        logger.error("=== SERVICES INITIALIZED SUCCESSFULLY ===")        # Query for jobs shared with current user
        logger.error("=== STARTING SHARED JOBS QUERY ===")
        shared_query = """
        SELECT * FROM c 
        WHERE c.type = 'job' 
        AND ARRAY_CONTAINS(c.shared_with, {'user_id': @user_id}, false)
        AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
        """
        shared_parameters = [{"name": "@user_id", "value": current_user["id"]}]
        
        logger.error(f"Query: {shared_query}")
        logger.error(f"Parameters: {shared_parameters}")
        
        shared_jobs = list(
            cosmos_db.jobs_container.query_items(
                query=shared_query,
                parameters=shared_parameters,
                enable_cross_partition_query=True,
            )
        )
        
        logger.error(f"=== SHARED JOBS QUERY RESULT: {len(shared_jobs)} jobs found ===")
        
        # Try alternative query if first one fails
        if len(shared_jobs) == 0:
            logger.error("=== TRYING ALTERNATIVE SHARED JOBS QUERY ===")
            alt_shared_query = """
            SELECT * FROM c 
            WHERE c.type = 'job'
            AND IS_DEFINED(c.shared_with)
            AND EXISTS(SELECT VALUE s FROM s IN c.shared_with WHERE s.user_id = @user_id)
            AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
            """
            logger.error(f"Alternative query: {alt_shared_query}")
            
            shared_jobs = list(
                cosmos_db.jobs_container.query_items(
                    query=alt_shared_query,
                    parameters=shared_parameters,
                    enable_cross_partition_query=True,
                )
            )
            logger.error(f"=== ALTERNATIVE SHARED JOBS QUERY RESULT: {len(shared_jobs)} jobs found ===")
        
        # Let's also try a simpler query to debug
        logger.error("=== RUNNING DEBUG QUERY ===")
        debug_query = """
        SELECT c.id, c.shared_with FROM c 
        WHERE c.type = 'job' 
        AND IS_DEFINED(c.shared_with)
        AND ARRAY_LENGTH(c.shared_with) > 0
        """
        
        debug_jobs = list(
            cosmos_db.jobs_container.query_items(
                query=debug_query,
                enable_cross_partition_query=True,
            )
        )
        logger.error(f"=== DEBUG QUERY RESULT: {len(debug_jobs)} jobs with sharing found ===")
        
        for i, job in enumerate(debug_jobs[:3]):  # Log first 3 for debugging
            logger.error(f"DEBUG Job {i+1}: {job.get('id')} shared_with: {job.get('shared_with')}")
            # Check if current user is in any of these
            for j, share in enumerate(job.get('shared_with', [])):
                logger.error(f"  Share {j+1}: user_id='{share.get('user_id')}' vs current='{current_user['id']}'")
                if share.get('user_id') == current_user['id']:
                    logger.error(f"*** MATCH FOUND! Current user {current_user['id']} is in job {job.get('id')} ***")
                else:
                    logger.error(f"No match: '{share.get('user_id')}' != '{current_user['id']}'")
                    
            # Also check if this specific job should be in shared_jobs
            should_match = any(str(s.get('user_id')) == str(current_user['id']) for s in job.get('shared_with', []))
            if should_match:
                logger.error(f"*** JOB {job.get('id')} SHOULD BE IN SHARED_JOBS BUT QUERY MISSED IT ***")
        
        # Query for jobs owned by current user that are shared with others
        logger.error("=== STARTING OWNED SHARED JOBS QUERY ===")
        owned_shared_query = """
        SELECT * FROM c 
        WHERE c.type = 'job' 
        AND c.user_id = @user_id 
        AND IS_DEFINED(c.shared_with) 
        AND ARRAY_LENGTH(c.shared_with) > 0
        AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
        """
        owned_shared_parameters = [{"name": "@user_id", "value": current_user["id"]}]
        
        logger.error(f"Owned query: {owned_shared_query}")
        logger.error(f"Owned parameters: {owned_shared_parameters}")
        
        owned_shared_jobs = list(
            cosmos_db.jobs_container.query_items(
                query=owned_shared_query,
                parameters=owned_shared_parameters,
                enable_cross_partition_query=True,
            )
        )
        
        logger.error(f"=== OWNED SHARED JOBS QUERY RESULT: {len(owned_shared_jobs)} jobs found ===")
        
        # Add SAS tokens and enhance job data
        logger.error("=== ADDING SAS TOKENS ===")
        for job in shared_jobs + owned_shared_jobs:
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
        
        logger.error(f"=== FINAL RESULT: {len(shared_jobs)} shared + {len(owned_shared_jobs)} owned = {len(shared_jobs) + len(owned_shared_jobs)} total ===")
        
        result = {
            "status": 200,
            "message": "Shared jobs retrieved successfully",
            "count": len(shared_jobs) + len(owned_shared_jobs),
            "shared_jobs": shared_jobs,
            "owned_jobs_shared_with_others": owned_shared_jobs
        }
        
        logger.error(f"=== RETURNING RESULT: {result} ===")
        return result
        
    except Exception as e:
        logger.error(f"=== EXCEPTION IN SHARED JOBS ENDPOINT: {str(e)} ===", exc_info=True)
        return {"status": 500, "message": f"Error retrieving shared jobs: {str(e)}"}


@router.get("/jobs/{job_id}")
async def get_job_by_id(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get a single job by ID with proper access control.
    Admins can access any job, regular users can only access jobs they own or have shared access to.
    """
    try:
        config = AppConfig()
        try:
            cosmos_db = CosmosDB(config)
            logger.debug(f"CosmosDB client initialized for job query: {job_id}")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        storage_service = StorageService(config)

        # Check if user is admin
        is_admin = False
        if "permission" in current_user:
            is_admin = str(current_user["permission"]).lower() == "admin"
        elif "permissions" in current_user:
            perms = current_user["permissions"]
            if isinstance(perms, list):
                is_admin = any(str(p).lower() == "admin" for p in perms)

        # Build query based on user permissions
        if is_admin:
            # Admin can access any job
            query = "SELECT * FROM c WHERE c.type = 'job' AND c.id = @job_id"
            parameters = [{"name": "@job_id", "value": job_id}]
        else:
            # Regular user can only access owned jobs or jobs shared with them
            query = """SELECT * FROM c WHERE c.type = 'job' AND c.id = @job_id 
                      AND (c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_with, {'user_id': @user_id}, true))
                      AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)"""
            parameters = [
                {"name": "@job_id", "value": job_id},
                {"name": "@user_id", "value": current_user["id"]}
            ]

        try:
            jobs = list(
                cosmos_db.jobs_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            if not jobs:
                return {
                    "status": 404,
                    "message": "Job not found or access denied"
                }

            job = jobs[0]

            # Add sharing metadata
            job["is_owned"] = job["user_id"] == current_user["id"]
            job["user_permission"] = get_user_job_permission(job, current_user)
            job["shared_with_count"] = len(job.get("shared_with", []))

            # Add SAS tokens to file paths
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

            return {
                "status": 200,
                "message": "Job retrieved successfully",
                "job": job,
            }

        except Exception as e:
            logger.error(f"Error querying job by ID: {str(e)}")
            return {"status": 500, "message": f"Error retrieving job: {str(e)}"}

    except Exception as e:
        logger.error(f"Unexpected error getting job by ID: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}


@router.get("/jobs/transcription/{job_id}")
async def get_job_transcription(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream the transcription file content for a specific job.

    Args:
        job_id: The ID of the job
        current_user: Authenticated user from token

    Returns:
        StreamingResponse containing the transcription file content
    """
    request_id = f"transcription_req_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{job_id[:8]}"
    logger.info(
        f"[{request_id}] Transcription request received for job_id: {job_id} by user: {current_user.get('username')}"
    )

    # Initialize services (outside try-except for clarity)
    config = AppConfig()
    logger.debug(
        f"[{request_id}] AppConfig initialized with environment: {config.environment if hasattr(config, 'environment') else 'not specified'}"
    )

    try:
        logger.debug(
            f"[{request_id}] Initializing CosmosDB connection for job: {job_id}"
        )
        cosmos_db = CosmosDB(config)
        logger.debug(
            f"[{request_id}] CosmosDB client initialized successfully. Container: {cosmos_db.jobs_container.container_link}"
        )

        logger.debug(f"[{request_id}] Initializing StorageService for job: {job_id}")
        storage_service = StorageService(config)
        logger.debug(
            f"[{request_id}] StorageService initialized successfully. Account: {storage_service.account_name if hasattr(storage_service, 'account_name') else 'unknown'}"
        )
    except DatabaseError as e:
        error_details = str(e)
        logger.error(
            f"[{request_id}] Database initialization failed: {error_details}",
            exc_info=True,
        )
        logger.error(f"[{request_id}] Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=503, detail="Database service unavailable")
    except Exception as e:
        error_details = str(e)
        logger.error(
            f"[{request_id}] Service initialization error: {error_details}",
            exc_info=True,
        )
        logger.error(f"[{request_id}] Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error initializing services")

    # Query the job with proper error handling
    try:        # Build query to get the specific job
        query = "SELECT * FROM c WHERE c.type = 'job' AND c.id = @job_id AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)"
        parameters = [{"name": "@job_id", "value": job_id}]
        logger.info(f"[{request_id}] Querying CosmosDB for job_id: {job_id}")
        logger.debug(
            f"[{request_id}] Query: {query}, Parameters: {json.dumps(parameters)}"
        )

        start_time = datetime.now(timezone.utc)
        jobs = list(
            cosmos_db.jobs_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        query_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.debug(
            f"[{request_id}] CosmosDB query completed in {query_duration:.3f} seconds"
        )

        if not jobs:
            logger.warning(f"[{request_id}] Job not found in database: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[0]
        
        # Verify user has access to this job
        if not check_job_access(job, current_user, "view"):
            logger.warning(f"[{request_id}] Access denied for user {current_user.get('email')} to job {job_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        logger.debug(
            f"[{request_id}] Job retrieved successfully. Job status: {job.get('status', 'unknown')}, Created: {job.get('created_at', 'unknown')}"
        )

        # Log job metadata for debugging (redacting sensitive information)
        safe_job_metadata = {
            k: v
            for k, v in job.items()
            if k not in ("user_details", "auth_token", "api_key", "password")
        }
        logger.debug(
            f"[{request_id}] Job metadata: {json.dumps(safe_job_metadata, default=str)}"
        )        # Check if transcription exists (either as file or text content)
        transcription_file_path = job.get("transcription_file_path")
        text_content = job.get("text_content")
        
        if not transcription_file_path and not text_content:
            logger.warning(
                f"[{request_id}] Neither transcription file path nor text content found for job: {job_id}"
            )
            raise HTTPException(
                status_code=404, detail="Transcription not available for this job"
            )

        if text_content:
            logger.info(
                f"[{request_id}] Found text content for text-only submission"
            )
            # For text-only submissions, return the text content directly
            from io import StringIO
            
            def generate_text_content():
                yield text_content.encode('utf-8')
            
            return StreamingResponse(
                generate_text_content(),
                media_type="text/plain",
                headers={"Content-Disposition": "inline; filename=transcription.txt"},
            )
        logger.info(
            f"[{request_id}] Found transcription file path: {transcription_file_path}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions without additional logging (already logged above)
        raise
    except Exception as e:
        error_details = str(e)
        logger.error(
            f"[{request_id}] Error retrieving job: {error_details}", exc_info=True
        )
        logger.error(f"[{request_id}] Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error retrieving job information")

    # Stream the file content (for file-based submissions)
    try:
        # Get the blob URL
        transcription_url = transcription_file_path
        logger.info(
            f"[{request_id}] Preparing to stream transcription from: {transcription_url}"
        )

        # Extract file name for the content-disposition header
        path_parts = urlparse(transcription_url).path.strip("/").split("/")
        file_name = path_parts[-1] if path_parts else "transcription.txt"
        logger.debug(f"[{request_id}] Extracted file name: {file_name} from URL path")

        # Determine content type based on file extension
        content_type = "text/plain"  # Default
        if file_name.endswith(".json"):
            content_type = "application/json"
        elif file_name.endswith(".xml"):
            content_type = "application/xml"
        logger.debug(f"[{request_id}] Content type determined as: {content_type}")

        # Stream the blob content
        logger.info(f"[{request_id}] Initiating blob streaming from Storage Service")
        start_time = datetime.now(timezone.utc)
        content_stream = storage_service.stream_blob_content(transcription_url)
        logger.debug(
            f"[{request_id}] Storage service returned stream handle in {(datetime.now(timezone.utc) - start_time).total_seconds():.3f} seconds"
        )

        # Return as streaming response
        logger.info(
            f"[{request_id}] Successfully preparing StreamingResponse for client with content-type: {content_type}"
        )
        response = StreamingResponse(
            content_stream,
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={file_name}"},
        )

        logger.info(
            f"[{request_id}] Transcription streaming response ready to be sent to client"
        )
        return response
    except AzureError as e:
        error_details = str(e)
        logger.error(
            f"[{request_id}] Azure storage error: {error_details}", exc_info=True
        )
        logger.error(
            f"[{request_id}] Azure error code: {getattr(e, 'error_code', 'unknown')}"
        )
        logger.error(f"[{request_id}] Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=502, detail="Error accessing storage service")
    except Exception as e:
        error_details = str(e)
        logger.error(
            f"[{request_id}] Error streaming transcription: {error_details}",
            exc_info=True,
        )
        logger.error(f"[{request_id}] Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Error streaming transcription file"
        )


@router.post("/jobs/{job_id}/process-analysis")
async def process_text_analysis(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger analysis processing for text-only submissions.
    
    Args:
        job_id: The ID of the job to process
        background_tasks: FastAPI background tasks
        current_user: Authenticated user from token
        
    Returns:
        Dict containing processing status
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        
        # Get the job
        job = cosmos_db.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user has edit access
        if not check_job_access(job, current_user, "edit"):
            raise HTTPException(status_code=403, detail="Access denied - edit permission required")
        
        # Check if job has text content and is in transcribed status
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
        cosmos_db.update_job(job_id, update_fields)        # Start background analysis using new pattern
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


@router.post("/jobs/{job_id}/refine-analysis")
async def refine_analysis(
    job_id: str,
    request: AnalysisRefinementRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> AnalysisRefinementResponse:
    """
    Refine the analysis for a job using AI chat interaction.
    
    Args:
        job_id: The ID of the job to refine
        request: The refinement request containing the user message
        current_user: Authenticated user from token
        
    Returns:
        AnalysisRefinementResponse containing the AI response and metadata    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        
        # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user has edit access
        if not check_job_access(job, current_user, "edit"):
            raise HTTPException(status_code=403, detail="Access denied - edit permission required")
        
        # Check if job has analysis available
        if not job.get("analysis_text") and not job.get("analysis_result"):
            raise HTTPException(
                status_code=400, 
                detail="No analysis available for refinement. Please complete analysis first."
            )
        
        # Get the current analysis text
        current_analysis = job.get("analysis_text", "")
        if not current_analysis and job.get("analysis_result"):
            current_analysis = str(job.get("analysis_result"))
        
        # Get the original text content
        original_text = job.get("text_content", "")
        
        # Prepare refinement context
        refinement_context = f"""
Original Content:
{original_text}

Current Analysis:
{current_analysis}

User Request:
{request.message}

Please provide a refined analysis based on the user's request. Focus on their specific question or request for modification.
"""
        
        # Initialize refinement history if it doesn't exist
        if "refinement_history" not in job:
            job["refinement_history"] = []
        
        # Create refinement entry
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        refinement_id = f"refinement_{timestamp}"        # Here we would call the AI service to get refined analysis
        analysis_service = AnalysisRefinementService(config)
        refinement_result = await analysis_service.refine_analysis(
            original_text=original_text,
            current_analysis=current_analysis,
            user_request=request.message,
            conversation_history=job.get("refinement_history", [])
        )
        
        if refinement_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"AI refinement failed: {refinement_result.get('error', 'Unknown error')}")
        
        ai_response = refinement_result["refined_analysis"]
        
        # Add to refinement history
        refinement_entry = {
            "id": refinement_id,
            "user_message": request.message,
            "ai_response": ai_response,
            "timestamp": timestamp,
            "user_id": current_user["id"]
        }
        
        job["refinement_history"].append(refinement_entry)
        
        # Update the job with new refinement history
        update_fields = {
            "refinement_history": job["refinement_history"],
            "updated_at": timestamp,
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Analysis refinement completed for job_id: {job_id}, refinement_id: {refinement_id}")
        
        return AnalysisRefinementResponse(
            status="success",
            message="Analysis refinement completed",
            response=ai_response,
            refinement_id=refinement_id,
            timestamp=timestamp
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refining analysis for job_id {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing analysis refinement")


@router.get("/jobs/{job_id}/refinement-history")
async def get_refinement_history(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the refinement history for a job.
    
    Args:
        job_id: The ID of the job
        current_user: Authenticated user from token
        
    Returns:
        Dict containing refinement history
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
          # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user has view access
        if not check_job_access(job, current_user, "view"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get refinement history
        refinement_history = job.get("refinement_history", [])
        
        return {
            "status": "success",
            "job_id": job_id,
            "history": refinement_history,
            "count": len(refinement_history)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting refinement history for job_id {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving refinement history")


@router.get("/jobs/{job_id}/refinement-suggestions")
async def get_refinement_suggestions(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get suggested refinement questions for a job's analysis.
    
    Args:
        job_id: The ID of the job
        current_user: Authenticated user from token
        
    Returns:
        Dict containing refinement suggestions
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
          # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user has view access
        if not check_job_access(job, current_user, "view"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if job has analysis available
        if not job.get("analysis_text") and not job.get("analysis_result"):
            return {
                "status": "success",
                "suggestions": [],
                "message": "No analysis available yet"
            }
        
        # Get analysis text
        analysis_text = job.get("analysis_text", "")
        if not analysis_text and job.get("analysis_result"):
            analysis_text = str(job.get("analysis_result"))
        
        # Get suggestions from the service
        analysis_service = AnalysisRefinementService(config)
        suggestions = analysis_service.generate_refinement_suggestions(analysis_text)
        
        return {
            "status": "success",
            "job_id": job_id,
            "suggestions": suggestions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting refinement suggestions for job_id {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving refinement suggestions")


# Job Sharing Endpoints

@router.post("/jobs/{job_id}/share")
async def share_job(
    job_id: str,
    request: JobShareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> JobShareResponse:
    """
    Share a job with another user.
    
    Args:
        job_id: The ID of the job to share
        request: Job sharing request with target user and permissions
        current_user: Authenticated user from token
        
    Returns:
        JobShareResponse containing sharing status and details
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
          # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job is deleted
        if job.get("deleted", False):
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user ownership - only job owner can share
        if job["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only job owner can share this job")
        
        # Find target user by email
        target_user = await cosmos_db.get_user_by_email(request.target_user_email)
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        # Don't allow sharing with yourself
        if target_user["id"] == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot share job with yourself")
        
        # Initialize shared_with array if it doesn't exist
        if "shared_with" not in job:
            job["shared_with"] = []
        
        # Check if already shared with this user
        existing_share = next((s for s in job["shared_with"] if s["user_id"] == target_user["id"]), None)
        
        if existing_share:
            # Update existing share
            existing_share["permission_level"] = request.permission_level
            existing_share["shared_at"] = int(datetime.now(timezone.utc).timestamp() * 1000)
            existing_share["shared_by"] = current_user["id"]
            if request.message:
                existing_share["message"] = request.message
        else:
            # Add new share
            share_entry = {
                "user_id": target_user["id"],
                "user_email": target_user["email"],
                "permission_level": request.permission_level,
                "shared_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                "shared_by": current_user["id"],
            }
            if request.message:
                share_entry["message"] = request.message
            job["shared_with"].append(share_entry)
        
        # Update the job
        update_fields = {
            "shared_with": job["shared_with"],
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} shared with user {target_user['email']} by {current_user['email']}")
        
        return JobShareResponse(
            status="success",
            message=f"Job shared successfully with {request.target_user_email}",
            shared_job_id=job_id,
            target_user_id=target_user["id"],
            permission_level=request.permission_level
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error sharing job")

@router.delete("/jobs/{job_id}/share")
async def unshare_job(
    job_id: str,
    request: JobUnshareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Remove job sharing with a specific user.
    
    Args:
        job_id: The ID of the job to unshare
        request: Job unshare request with target user email
        current_user: Authenticated user from token
        
    Returns:
        Dict containing unshare status
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
          # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job is deleted
        if job.get("deleted", False):
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user ownership - only job owner can unshare
        if job["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only job owner can unshare this job")
        
        # Find target user by email
        target_user = await cosmos_db.get_user_by_email(request.target_user_email)
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        # Remove from shared_with array
        if "shared_with" in job:
            job["shared_with"] = [s for s in job["shared_with"] if s["user_id"] != target_user["id"]]
            
            # Update the job
            update_fields = {
                "shared_with": job["shared_with"],
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} unshared with user {target_user['email']} by {current_user['email']}")
        
        return {
            "status": "success",
            "message": f"Job sharing removed for {request.target_user_email}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsharing job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error unsharing job")

@router.get("/jobs/{job_id}/sharing-info")
async def get_job_sharing_info(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get sharing information for a specific job.
    
    Args:
        job_id: The ID of the job
        current_user: Authenticated user from token
        
    Returns:
        Dict containing job sharing information
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
          # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job is deleted
        if job.get("deleted", False):
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if user has access to this job (owner or shared with)
        has_access = False
        user_permission = None
        
        if job["user_id"] == current_user["id"]:
            has_access = True
            user_permission = "owner"
        elif "shared_with" in job:
            for share in job["shared_with"]:
                if share["user_id"] == current_user["id"]:
                    has_access = True
                    user_permission = share["permission_level"]
                    break
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Return sharing info
        shared_with = job.get("shared_with", [])
        
        return {
            "status": "success",
            "job_id": job_id,
            "is_owner": job["user_id"] == current_user["id"],
            "user_permission": user_permission,
            "shared_with": shared_with,
            "total_shares": len(shared_with)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job sharing info for {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving job sharing information")



@router.delete("/jobs/{job_id}")
async def soft_delete_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Soft delete a job (mark as deleted but keep in database for admin access).
    
    Args:
        job_id: The ID of the job to delete
        current_user: Authenticated user from token
        
    Returns:
        Dict containing delete status
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        
        # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job is already deleted
        if job.get("deleted"):
            raise HTTPException(status_code=400, detail="Job is already deleted")
        
        # Verify user ownership - only job owner can delete
        if job["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only job owner can delete this job")
        
        # Soft delete the job
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        update_fields = {
            "deleted": True,
            "deleted_at": timestamp,
            "deleted_by": current_user["id"],
            "updated_at": timestamp,
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} soft deleted by {current_user['email']}")
        
        return {
            "status": "success",
            "message": "Job deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error soft deleting job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting job")


@router.post("/jobs/{job_id}/restore")
async def restore_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Restore a soft deleted job (admin only).
    
    Args:
        job_id: The ID of the job to restore
        current_user: Authenticated user from token
        
    Returns:
        Dict containing restore status
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        
        # Check if user is admin
        user_permission = await cosmos_db.get_user_permission_with_fallback(current_user["id"])
        if user_permission != "Admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get the job (including deleted ones)
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job is deleted
        if not job.get("deleted"):
            raise HTTPException(status_code=400, detail="Job is not deleted")
        
        # Restore the job
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        update_fields = {
            "deleted": False,
            "restored_at": timestamp,
            "restored_by": current_user["id"],
            "updated_at": timestamp,
        }
        # Remove deleted fields
        update_fields["deleted_at"] = None
        update_fields["deleted_by"] = None
        
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} restored by admin {current_user['email']}")
        
        return {
            "status": "success",
            "message": "Job restored successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error restoring job")


@router.get("/admin/deleted-jobs")
async def get_deleted_jobs(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get all soft deleted jobs (admin only).
    
    Args:
        current_user: Authenticated user from token
        
    Returns:
        Dict containing deleted jobs
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        storage_service = StorageService(config)
        
        # Check if user is admin
        user_permission = await cosmos_db.get_user_permission_with_fallback(current_user["id"])
        if user_permission != "Admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Query for deleted jobs
        query = """
        SELECT * FROM c 
        WHERE c.type = 'job' 
        AND c.deleted = true
        ORDER BY c.deleted_at DESC
        """
        
        deleted_jobs = list(
            cosmos_db.jobs_container.query_items(
                query=query,
                enable_cross_partition_query=True,
            )
        )
        
        # Add SAS tokens and enhance job data
        for job in deleted_jobs:
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
        
        return {
            "status": "success",
            "message": "Deleted jobs retrieved successfully",
            "count": len(deleted_jobs),
            "jobs": deleted_jobs,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deleted jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving deleted jobs")


@router.delete("/admin/jobs/{job_id}/permanent")
async def permanent_delete_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Permanently delete a job from database (admin only).
    
    Args:
        job_id: The ID of the job to permanently delete
        current_user: Authenticated user from token
        
    Returns:
        Dict containing permanent delete status
    """
    try:
        config = AppConfig()
        cosmos_db = CosmosDB(config)
        
        # Check if user is admin
        user_permission = await cosmos_db.get_user_permission_with_fallback(current_user["id"])
        if user_permission != "Admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get the job
        job = cosmos_db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Permanently delete the job
        cosmos_db.jobs_container.delete_item(item=job_id, partition_key=job_id)
        
        logger.info(f"Job {job_id} permanently deleted by admin {current_user['email']}")
        
        return {
            "status": "success",
            "message": "Job permanently deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error permanently deleting job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error permanently deleting job")


# Utility function for job access control
def check_job_access(job: Dict[str, Any], current_user: Dict[str, Any], required_permission: str = "view") -> bool:
    """
    Check if user has access to a job with the required permission level.
    Admins can access all jobs (except soft-deleted ones).
    """
    # Check if job is soft-deleted - only admins can access deleted jobs through admin endpoints
    if job.get("deleted", False):
        return False

    # Admins can access all jobs
    is_admin = False
    if "permission" in current_user:
        is_admin = str(current_user["permission"]).lower() == "admin"
    elif "permissions" in current_user:
        perms = current_user["permissions"]
        if isinstance(perms, list):
            is_admin = any(str(p).lower() == "admin" for p in perms)
    if is_admin:
        return True

    # Job owner has all permissions
    if job["user_id"] == current_user["id"]:
        return True

    # Check shared permissions
    if "shared_with" in job:
        for share in job["shared_with"]:
            if share["user_id"] == current_user["id"]:
                user_permission = share["permission_level"]
                
                # Permission hierarchy: view < edit < admin
                permission_levels = {"view": 1, "edit": 2, "admin": 3}
                user_level = permission_levels.get(user_permission, 0)
                required_level = permission_levels.get(required_permission, 0)
                
                return user_level >= required_level
    
    return False

def get_user_job_permission(job: Dict[str, Any], current_user: Dict[str, Any]) -> Optional[str]:
    """
    Get the user's permission level for a job.
    
    Args:
        job: Job document
        current_user: Current authenticated user
    
    Returns:
        Permission level string or None if no access
    """
    # Job owner has owner permission
    if job["user_id"] == current_user["id"]:
        return "owner"
    
    # Check shared permissions
    if "shared_with" in job:
        for share in job["shared_with"]:
            if share["user_id"] == current_user["id"]:
                return share["permission_level"]
    
    return None

@router.get("/jobs/shared/health")
async def health_check_shared_jobs():
    """Health check endpoint for shared jobs route"""
    return {"status": "ok", "message": "Shared jobs route is accessible", "timestamp": datetime.now(timezone.utc).isoformat()}
