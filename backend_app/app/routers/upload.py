from datetime import datetime, timezone, date
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
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import tempfile
import os
from urllib.parse import urlparse

from app.core.config import AppConfig, CosmosDB, DatabaseError
from app.services.storage_service import StorageService
from app.routers.auth import get_current_user
import logging
import traceback
from azure.core.exceptions import AzureError

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    prompt_category_id: str = Form(None),
    prompt_subcategory_id: str = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Upload a file to Azure Blob Storage and create a job record.

    Args:
        file: The file to upload
        prompt_category_id: Category ID for the prompt
        prompt_subcategory_id: Subcategory ID for the prompt
        current_user: Authenticated user from token

    Returns:
        Dict containing job ID and status
    """
    print(f"Received prompt_category_id: {prompt_category_id}")
    print(f"Received prompt_subcategory_id: {prompt_subcategory_id}")

    if not prompt_category_id or not prompt_subcategory_id:
        raise HTTPException(
            status_code=400, detail="Category and Subcategory IDs cannot be null"
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

        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(file.filename)[1]
            ) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            # Upload file to blob storage
            storage_service = StorageService(config)
            blob_url = storage_service.upload_file(temp_file_path, file.filename)
            logger.debug(f"File uploaded to blob storage: {blob_url}")

            # Clean up temporary file
            os.unlink(temp_file_path)

        except AzureError as e:
            logger.error(f"Storage error: {str(e)}")
            return {"status": 504, "message": "Storage service unavailable"}
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return {"status": 505, "message": f"Error uploading file: {str(e)}"}

        # Create job document
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        job_id = f"job_{timestamp}"
        job_data = {
            "id": job_id,
            "type": "job",
            "user_id": current_user["id"],
            "file_path": blob_url,
            "transcription_file_path": None,
            "analysis_file_path": None,
            "prompt_category_id": prompt_category_id,
            "prompt_subcategory_id": prompt_subcategory_id,
            "status": "uploaded",
            "transcription_id": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        job = cosmos_db.create_job(job_data)

        return {
            "job_id": job_id,
            "status": "uploaded",
            "message": "File uploaded successfully",
            "prompt_category_id": prompt_category_id,
            "prompt_subcategory_id": prompt_subcategory_id,
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

    Args:
        job_id: Filter by job ID
        status: Filter by job status
        file_path: Filter by file path
        created_at: Filter by creation date (YYYY-MM-DD)
        prompt_subcategory_id: Filter by prompt subcategory ID
        current_user: Authenticated user from token

    Returns:
        Dict containing jobs and status
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

        if prompt_subcategory_id:
            query += " AND c.prompt_subcategory_id = @subcategory"
            parameters.append({"name": "@subcategory", "value": prompt_subcategory_id})

        # Add user filter for security
        query += " AND c.user_id = @user_id"
        parameters.append({"name": "@user_id", "value": current_user["id"]})

        try:
            jobs = list(
                cosmos_db.jobs_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            # Add SAS tokens to file paths
            for job in jobs:
                if job.get("file_path"):
                    # Extract file name from the file path before adding SAS token
                    file_path = job["file_path"]
                    path_parts = urlparse(file_path).path.strip("/").split("/")
                    job["file_name"] = path_parts[-1] if path_parts else None
                    job["file_path"] = storage_service.add_sas_token_to_url(file_path)
                    job["transcription_file_path"] = (
                        storage_service.add_sas_token_to_url(
                            job["transcription_file_path"]
                        )
                    )
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
    # Initialize services (outside try-except for clarity)
    config = AppConfig()

    try:
        cosmos_db = CosmosDB(config)
        logger.debug("CosmosDB client initialized for transcription query")
        storage_service = StorageService(config)
    except DatabaseError as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database service unavailable")
    except Exception as e:
        logger.error(f"Service initialization error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error initializing services")

    # Query the job with proper error handling
    try:
        # Build query to get the specific job
        query = "SELECT * FROM c WHERE c.type = 'job' AND c.id = @job_id"
        parameters = [{"name": "@job_id", "value": job_id}]

        jobs = list(
            cosmos_db.jobs_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

        if not jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[0]

        # Check if transcription exists
        if not job.get("transcription_file_path"):
            raise HTTPException(
                status_code=404, detail="Transcription not available for this job"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving job information")

    # Stream the content
    try:
        # Get the blob URL
        transcription_url = job["transcription_file_path"]

        # Extract file name for the content-disposition header
        path_parts = urlparse(transcription_url).path.strip("/").split("/")
        file_name = path_parts[-1] if path_parts else "transcription.txt"

        # Determine content type based on file extension (optional improvement)
        content_type = "text/plain"  # Default
        if file_name.endswith(".json"):
            content_type = "application/json"
        elif file_name.endswith(".xml"):
            content_type = "application/xml"

        # Stream the blob content
        content_stream = storage_service.stream_blob_content(transcription_url)

        # Return as streaming response
        return StreamingResponse(
            content_stream,
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={file_name}"},
        )
    except Exception as e:
        logger.error(f"Error streaming transcription: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error streaming transcription file"
        )
