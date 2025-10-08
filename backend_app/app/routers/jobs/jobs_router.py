from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
import logging
from pydantic import BaseModel

from ...core.dependencies import (
    get_current_user,
    get_analytics_service,
    get_job_service,
    get_job_management_service,
    get_job_sharing_service,
    get_storage_service,
    get_config,
    AppConfig,
    get_error_handler,
)
from ...core.errors import ApplicationError, ErrorCode, ErrorHandler, PermissionError, ResourceNotFoundError, ResourceNotReadyError, ValidationError
from ...services.jobs import JobService
from ...services.jobs import check_job_access
from ...services.jobs.job_management_service import JobManagementService
from ...services.jobs.job_sharing_service import JobSharingService
from ...services.storage.blob_service import StorageService
from ...services.interfaces import AnalyticsServiceInterface, StorageServiceInterface
from fastapi import File, UploadFile, BackgroundTasks, Form
import json
import tempfile, shutil, os
from ...services.jobs.job_permissions import JobPermissions
from ...services.jobs.job_management_service import JobManagementService
from ...services.analytics.analytics_service import AnalyticsService
from ...utils.file_utils import FileUtils

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])


class JobUpdateRequest(BaseModel):
    displayname: str


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


@router.get("/jobs")
async def get_jobs(
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_svc: JobService = Depends(get_job_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    # Build a minimal query using provided filters. This keeps behaviour close to legacy.
    try:
        # Prefer higher-level service methods if available to avoid query logic in router
        # Fallback to the JobService query_jobs if needed
        filters = {"job_id": job_id, "status": status}
        # Intentionally ignore can_view_all capability for this endpoint so that
        # even admins only see their own jobs here. The all-jobs view remains
        # available under /api/admin/jobs.
        can_view_all = False

        # Build query string and parameters for Cosmos. Use async_query_jobs to avoid blocking.
        query = "SELECT * FROM c WHERE c.type = 'job' AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)"
        params = []
        if job_id:
            query += " AND c.id = @job_id"
            params.append({"name": "@job_id", "value": job_id})
        if status:
            query += " AND c.status = @status"
            params.append({"name": "@status", "value": status})

        # Always scope to the current user's own jobs only (owner filter).
        query += " AND c.user_id = @user_id"
        params.append({"name": "@user_id", "value": current_user["id"]})

        # Debug: log current user and constructed query/params to diagnose filtering issues
        try:
            logger.debug("get_jobs: user_id=%s can_view_all=%s capability_map=%s", current_user.get("id"), can_view_all, current_user.get("capability_map"))
            logger.debug("get_jobs: sql=%s params=%s", query, params)
        except Exception:
            # Ensure logging never fails the endpoint
            logger.exception("Failed to log get_jobs debug info")

        # Order by created_at desc and fetch via async_query_jobs then apply pagination slice
        query += " ORDER BY c.created_at DESC"

        jobs_all = await job_svc.async_query_jobs(query, params)
        total = len(jobs_all)
        jobs = jobs_all[offset: offset + limit]

        for job in jobs:
            job["is_owned"] = job.get("user_id") == current_user["id"]
            job["user_permission"] = job_svc.cosmos.get_user_permission(job.get("user_id")) if hasattr(job_svc.cosmos, 'get_user_permission') else None
            job["shared_with_count"] = len(job.get("shared_with", []))
            job_svc.enrich_job_file_urls(job)

        return {"status": 200, "count": total, "jobs": jobs}
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "list jobs",
            exc,
            details={
                "user_id": current_user.get("id"),
                "filters": {"job_id": job_id, "status": status},
                "limit": limit,
                "offset": offset,
            },
        )


@router.get("/jobs/{job_id}")
async def get_job_by_id(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_svc: JobService = Depends(get_job_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        job = job_svc.get_job(job_id)
        if not job:
            raise ResourceNotFoundError(f"Job {job_id} not found")
        if not check_job_access(job, current_user, "view"):
            raise PermissionError("Access denied to job")
        job["is_owned"] = job.get("user_id") == current_user["id"]
        job["user_permission"] = (
            job_svc.cosmos.get_user_permission(job.get("user_id"))
            if hasattr(job_svc.cosmos, "get_user_permission")
            else None
        )
        job["shared_with_count"] = len(job.get("shared_with", []))
        job_svc.enrich_job_file_urls(job)
        return {"status": 200, "job": job}
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get job",
            exc,
            details={
                "job_id": job_id,
                "user_id": current_user.get("id"),
            },
        )


@router.get("/jobs/{job_id}/transcription")
async def get_job_transcription(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_svc: JobService = Depends(get_job_service),
    storage_service: StorageServiceInterface = Depends(get_storage_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    try:
        job = job_svc.get_job(job_id)
        if not job:
            raise ResourceNotFoundError("Job", job_id)
        if not check_job_access(job, current_user, "view"):
            raise PermissionError("Access denied to job")

        # Prefer inline text content
        if job.get("text_content"):
            def stream_text():
                yield job["text_content"].encode("utf-8")

            return StreamingResponse(stream_text(), media_type="text/plain")

        transcription_url = job.get("transcription_file_path")
        if not transcription_url:
            raise ResourceNotReadyError(
                "Transcription not available for job",
                {"job_id": job_id, "job_status": job.get("status")}
            )

        stream = storage_service.stream_blob_content(transcription_url)
        return StreamingResponse(stream, media_type="text/plain")
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get job transcription",
            exc,
            details={
                "job_id": job_id,
                "user_id": current_user.get("id"),
            },
        )






@router.post("/jobs")
async def create_job(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    prompt_category_id: Optional[str] = Form(None),
    prompt_subcategory_id: Optional[str] = Form(None),
    pre_session_form_data: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_svc: JobService = Depends(get_job_service),
    analytics_service: AnalyticsServiceInterface = Depends(get_analytics_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Create a new job by uploading a media file.
    
    RESTful endpoint for job creation. Returns 201 Created with Location header.
    """
    # Save upload to a temp file then call the service
    tmp_dir = tempfile.mkdtemp(prefix="sonic_upload_")
    tmp_path = os.path.join(tmp_dir, file.filename)
    try:
        with open(tmp_path, "wb") as out_file:
            shutil.copyfileobj(file.file, out_file)

        # Build metadata from optional form fields so the job document contains
        # prompt and pre-session form data for downstream processing (e.g. blob
        # trigger that looks for prompt_subcategory_id).
        metadata: Dict[str, Any] = {}
        if prompt_category_id:
            metadata["prompt_category_id"] = prompt_category_id
        if prompt_subcategory_id:
            metadata["prompt_subcategory_id"] = prompt_subcategory_id
        if pre_session_form_data:
            # Expect JSON string from client; try to parse, otherwise store raw
            try:
                metadata["pre_session_form_data"] = json.loads(pre_session_form_data)
            except Exception:
                metadata["pre_session_form_data"] = pre_session_form_data

        # Try to extract audio duration from the temp file and include in metadata
        try:
            file_ext = FileUtils.get_extension(file.filename) if file is not None else ""
            if file_ext.lower() in FileUtils.AUDIO_EXTENSIONS:
                audio_secs = FileUtils.get_audio_duration(tmp_path)
                if audio_secs is not None:
                    metadata["audio_duration_seconds"] = float(audio_secs)
                    metadata["audio_duration_minutes"] = float(audio_secs) / 60.0
                    logger.info(f"Extracted audio duration: {metadata['audio_duration_minutes']:.2f} minutes for upload")
        except Exception:
            logger.exception("Failed to extract audio duration before creating job")

        created_job = job_svc.upload_and_create_job(tmp_path, file.filename, current_user, metadata=metadata)

        # Track job creation analytics (best-effort)
        try:
            file_size_bytes = 0
            try:
                file_size_bytes = os.path.getsize(tmp_path)
            except Exception:
                pass
            # Enrich analytics metadata with file and duration info when available
            analytics_meta = {
                "has_file": True,
                "file_size_bytes": file_size_bytes,
                "prompt_category_id": metadata.get("prompt_category_id"),
                "prompt_subcategory_id": metadata.get("prompt_subcategory_id"),
                "job_status": created_job.get("status"),
                "file_name": file.filename if file is not None else None,
                "file_extension": os.path.splitext(file.filename)[1].lstrip('.') if file is not None else None,
            }
            # Include audio durations from created_job if present
            if created_job.get("audio_duration_seconds") is not None:
                analytics_meta["audio_duration_seconds"] = created_job.get("audio_duration_seconds")
            if created_job.get("audio_duration_minutes") is not None:
                analytics_meta["audio_duration_minutes"] = created_job.get("audio_duration_minutes")

            await analytics_service.track_job_event(
                job_id=created_job.get("id"),
                user_id=current_user.get("id"),
                event_type="job_created",
                metadata=analytics_meta,
            )
        except Exception:
            logger.exception("Failed to track job creation analytics")

        # RESTful response: 201 Created with Location header
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=201,
            content=created_job,
            headers={"Location": f"/api/jobs/{created_job['id']}"}
        )
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "create job",
            exc,
            details={
                "filename": getattr(file, "filename", None),
                "user_id": current_user.get("id"),
            },
        )
    finally:
        try:
            # schedule cleanup
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_dir):
                os.rmdir(tmp_dir)
        except Exception:
            pass


@router.patch("/jobs/{job_id}")
async def update_job(
    job_id: str,
    update_request: JobUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_svc: JobService = Depends(get_job_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Update job properties like displayname.
    
    Currently supports updating the displayname field only.
    """
    try:
        # Get the job and verify access
        job = job_svc.get_job(job_id)
        if not job:
            raise ResourceNotFoundError(f"Job {job_id} not found")
        if not check_job_access(job, current_user, "edit"):
            raise PermissionError("Access denied to job")
        
        # Update the displayname
        job["displayname"] = update_request.displayname.strip()
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Save to Cosmos
        updated_job = job_svc.cosmos.update_job(job_id, job)
        
        # Enrich and return
        job_svc.enrich_job_file_urls(updated_job)
        return {"status": 200, "job": updated_job}
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "update job",
            exc,
            details={
                "job_id": job_id,
                "user_id": current_user.get("id"),
            },
        )


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_svc: JobService = Depends(get_job_service),
    management_service: JobManagementService = Depends(get_job_management_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Soft-delete a job for its owner (or admin). This provides a non-admin
    equivalent to the admin-only endpoint under /api/admin/jobs.
    """
    try:
        user_id = current_user if isinstance(current_user, str) else current_user.get("id")

        # Determine admin status using the permissions wrapper
        permissions = JobPermissions()
        is_admin = await permissions.check_user_admin_privileges(current_user)

        result = await management_service.soft_delete_job(job_id, user_id, is_admin=is_admin)

        if result.get("status") == "error":
            msg = result.get("message", "Error deleting job")
            if "not found" in msg:
                raise ResourceNotFoundError(msg)
            if "Access denied" in msg:
                raise PermissionError(msg)
            raise ValidationError(msg)

        return {"status": "success", "message": f"Job {job_id} soft deleted", "job_id": job_id}

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "delete job",
            exc,
            details={
                "job_id": job_id,
                "user_id": current_user.get("id") if isinstance(current_user, dict) else current_user,
            },
        )


@router.post("/jobs/{job_id}/restore")
async def restore_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    management_service: JobManagementService = Depends(get_job_management_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Restore a soft-deleted job (admin only) via public jobs path.

    This endpoint mirrors the admin restore behaviour but is placed under
    the non-admin `/api/jobs` prefix to match frontend expectations. It
    requires the caller to have admin privileges.
    """
    try:
        user_id = current_user if isinstance(current_user, str) else current_user.get("id")

        # Determine admin status using the permissions wrapper
        permissions = JobPermissions()
        is_admin = await permissions.check_user_admin_privileges(current_user)

        if not is_admin:
            raise PermissionError("Admin privileges required")

        result = await management_service.restore_job(job_id, user_id, is_admin=is_admin)

        if result.get("status") == "error":
            msg = result.get("message", "Error restoring job")
            if "not found" in msg:
                raise ResourceNotFoundError(msg)
            if "Access denied" in msg:
                raise PermissionError(msg)
            raise ValidationError(msg)

        return {"status": "success", "message": f"Job {job_id} restored", "job_id": job_id}

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "restore job",
            exc,
            details={
                "job_id": job_id,
                "user_id": current_user.get("id") if isinstance(current_user, dict) else current_user,
            },
        )


# Note: legacy /upload endpoint removed on request; use POST /api/jobs instead.


