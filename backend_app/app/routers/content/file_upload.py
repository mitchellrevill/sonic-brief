"""
File Upload Router - File processing and job management
Handles file uploads, text content processing, and job creation
"""
from datetime import datetime, timezone
import json
from typing import Dict, Any, Optional
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
    BackgroundTasks,
)
from pydantic import BaseModel
import tempfile
import os
from urllib.parse import urlparse
import logging

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB, DatabaseError
from ...services.storage import StorageService, FileSecurityService
from ...services.processing.background_service import get_background_service
from ...services.content import AnalyticsService
from ...core.dependencies import get_current_user, require_can_upload
from ...models.permissions import (
    PermissionLevel,
    PermissionCapability,
    get_user_capabilities,
    merge_custom_capabilities,
    can_user_perform_action,
)
from app.utils.file_utils import FileUtils
from azure.core.exceptions import AzureError

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["file-upload"])


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_can_upload),
    file: UploadFile = File(None),
    text_content: str = Form(None),
    prompt_category_id: str = Form(None),
    prompt_subcategory_id: str = Form(None),
    pre_session_form_data: str = Form(None),
) -> Dict[str, Any]:
    """
    Upload a file or process text content and create a job record.
    Uses background tasks for improved performance on large files.
    """
    print(f"Received prompt_category_id: {prompt_category_id}")
    print(f"Received prompt_subcategory_id: {prompt_subcategory_id}")
    print(f"Received file: {file.filename if file else None}")
    print(f"Received text_content: {'Yes' if text_content else 'No'}")
    print(f"Received pre_session_form_data: {'Yes' if pre_session_form_data else 'No'}")

    # Parse pre-session form data if provided
    parsed_form_data = {}
    if pre_session_form_data:
        try:
            parsed_form_data = json.loads(pre_session_form_data)
            print(f"Parsed pre-session form data: {parsed_form_data}")
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse pre_session_form_data: {e}")
            parsed_form_data = {}

    if not prompt_category_id or not prompt_subcategory_id:
        raise HTTPException(
            status_code=400, detail="Category and Subcategory IDs cannot be null"
        )
    
    if not file and not text_content:
        raise HTTPException(
            status_code=400, detail="Either a file or text content must be provided"
        )

    config = get_app_config()
    try:
        cosmos_db = get_cosmos_db_cached(config)
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

    # Validate file if provided before creating job document
    file_security = FileSecurityService()
    validation_result = None
    if file:
        validation_result = await file_security.validate(file)

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
        "message": "Job created, processing...",
        "transcription_id": None,
        "text_content": text_content if text_content else None,
        "pre_session_form_data": parsed_form_data,  # Store the parsed form data
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    job = cosmos_db.create_job(job_data)

    # Calculate file size for analytics (non-fatal if this fails)
    file_size_bytes = 0
    try:
        if file:
            file_content = await file.read()
            file_size_bytes = len(file_content)
            await file.seek(0)
        elif text_content:
            file_size_bytes = len(text_content.encode('utf-8'))
    except Exception as e:
        logger.warning(f"Failed to determine file size for analytics: {e}")

    # Attempt to track analytics but don't fail request if it breaks
    try:
        analytics_service = AnalyticsService(cosmos_db)
        event_id = await analytics_service.track_job_event(
            job_id=job_id,
            user_id=current_user["id"],
            event_type="job_created",
            metadata={
                "has_file": file is not None,
                "has_text": text_content is not None,
                "file_size_bytes": file_size_bytes,
                "prompt_category_id": prompt_category_id,
                "prompt_subcategory_id": prompt_subcategory_id,
                "job_status": job_status,
            },
        )
        if event_id:
            logger.info(f"✓ Job creation analytics tracked for job {job_id}")
        else:
            logger.error(f"✗ Failed to track job creation analytics for job {job_id}")
    except Exception as e:
        logger.error(
            f"CRITICAL: Failed to track job creation analytics for job {job_id}: {str(e)}",
            exc_info=True,
        )

    # Process file or text submission
    message = ""
    background_service = get_background_service()

    if file:
        storage_service = StorageService(config)
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[1]
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Extract audio duration if applicable
        audio_duration_seconds = None
        audio_duration_minutes = None
        try:
            file_extension = FileUtils.get_extension(file.filename)
            if file_extension.lower() in FileUtils.AUDIO_EXTENSIONS:
                audio_duration_seconds = FileUtils.get_audio_duration(temp_file_path)
                if audio_duration_seconds:
                    audio_duration_minutes = audio_duration_seconds / 60.0
                    logger.info(
                        f"Extracted audio duration: {audio_duration_minutes:.2f} minutes for job {job_id}"
                    )
                else:
                    logger.warning(
                        f"Could not extract audio duration for file: {file.filename}"
                    )
        except Exception as e:
            logger.warning(f"Error extracting audio duration: {str(e)}")

        try:
            blob_url = storage_service.upload_file(temp_file_path, file.filename)
            logger.info(f"File uploaded to blob storage: {blob_url}")
            os.unlink(temp_file_path)

            update_fields = {
                "status": "uploaded",
                "message": "File uploaded successfully, processing in background",
                "file_path": blob_url,
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            if audio_duration_seconds is not None:
                update_fields["audio_duration_seconds"] = audio_duration_seconds
                update_fields["audio_duration_minutes"] = audio_duration_minutes

            cosmos_db.update_job(job_id, update_fields)
            logger.info(f"File upload completed synchronously for job {job_id}")
            message = "File uploaded successfully"
        except AzureError as e:
            logger.error(f"Storage error for job {job_id}: {str(e)}")
            update_fields = {
                "status": "failed",
                "message": f"Storage service unavailable: {str(e)}",
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            cosmos_db.update_job(job_id, update_fields)
            raise HTTPException(status_code=503, detail="Storage service unavailable")
        except Exception as e:
            logger.error(f"Error uploading file for job {job_id}: {str(e)}")
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            update_fields = {
                "status": "failed",
                "message": f"File upload failed: {str(e)}",
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            cosmos_db.update_job(job_id, update_fields)
            raise HTTPException(status_code=500, detail="File upload failed")
    else:
        # Text-only submission
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
