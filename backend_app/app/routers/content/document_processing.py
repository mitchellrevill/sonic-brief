"""
Document Processing Router - Analysis, refinement, and export operations
Handles document analysis, talking points, export formats, and content refinement
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
    Response,
)
from pydantic import BaseModel, Field
import logging
from urllib.parse import urlparse
import io
import zipfile
import json

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB
from ...services.storage import StorageService
from ...services.content import AnalyticsService
from ...services.content.document_service import DocumentService
from ...services.content.export_service import ExportService
from ...core.dependencies import get_current_user, require_job_owner_or_admin, require_job_view, require_job_edit, require_job_download, require_job_export
from ...models.permissions import PermissionLevel, PermissionCapability, can_user_perform_action
from ...core.permissions import user_has_capability_for_job

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["document-processing"])


class AnalysisRefineRequest(BaseModel):
    refined_content: str = Field(..., description="Refined analysis content")
    analysis_type: Optional[str] = Field(default="refined", description="Type of analysis refinement")
    preserve_original: bool = Field(default=True, description="Whether to preserve original analysis")


class TalkingPointsRequest(BaseModel):
    key_themes: List[str] = Field(default_factory=list, description="Key themes to focus on")
    audience_type: Optional[str] = Field(default="general", description="Target audience type")
    format_style: Optional[str] = Field(default="bullet", description="Format style for talking points")


class ExportRequest(BaseModel):
    format: str = Field(..., description="Export format (pdf, docx, txt, json)")
    include_analysis: bool = Field(default=True, description="Include analysis in export")
    include_transcription: bool = Field(default=False, description="Include transcription in export")
    include_talking_points: bool = Field(default=False, description="Include talking points in export")


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


@router.post("/jobs/{job_id}/analysis/refine")
async def refine_analysis(
    job_id: str,
    refine_request: AnalysisRefineRequest,
    job: Dict[str, Any] = Depends(require_job_edit),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Refine or update the analysis content for a job"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)

        # job provided by require_job_edit
        if not job.get("analysis_content"):
            raise HTTPException(status_code=400, detail="Job does not have analysis content to refine")

        # Preserve original analysis if requested
        update_fields = {}
        if refine_request.preserve_original and not job.get("original_analysis_content"):
            update_fields["original_analysis_content"] = job["analysis_content"]
            update_fields["original_analysis_at"] = datetime.now(timezone.utc).isoformat()

        # Update analysis content
        update_fields.update({
            "analysis_content": refine_request.refined_content,
            "analysis_type": refine_request.analysis_type,
            "refined_by": current_user["id"],
            "refined_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        })

        cosmos_db.update_job(job_id, update_fields)

        logger.info(f"Analysis refined for job {job_id} by user {current_user['id']}")

        return {
            "status": "success",
            "message": "Analysis refined successfully",
            "job_id": job_id,
            "analysis_type": refine_request.analysis_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refining analysis for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error refining analysis")


@router.post("/jobs/{job_id}/talking-points")
async def generate_talking_points(
    job_id: str,
    talking_points_request: TalkingPointsRequest,
    job: Dict[str, Any] = Depends(require_job_edit),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate talking points from job content"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        analytics_service = AnalyticsService(config)
        # job provided by require_job_edit
        
        content_to_analyze = job.get("analysis_content") or job.get("text_content")
        if not content_to_analyze:
            raise HTTPException(status_code=400, detail="Job does not have content for talking points generation")
        
        # Generate talking points
        talking_points_result = await analytics_service.generate_talking_points(
            content=content_to_analyze,
            key_themes=talking_points_request.key_themes,
            audience_type=talking_points_request.audience_type,
            format_style=talking_points_request.format_style
        )
        
        # Update job with talking points
        update_fields = {
            "talking_points": talking_points_result["talking_points"],
            "talking_points_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": current_user["id"],
                "key_themes": talking_points_request.key_themes,
                "audience_type": talking_points_request.audience_type,
                "format_style": talking_points_request.format_style
            },
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        cosmos_db.update_job(job_id, update_fields)
        logger.info(f"Talking points generated for job {job_id} by user {current_user['id']}")

        return {
            "status": "success",
            "message": "Talking points generated successfully",
            "job_id": job_id,
            "talking_points": talking_points_result["talking_points"],
            "metadata": update_fields["talking_points_metadata"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating talking points for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating talking points")


@router.get("/jobs/{job_id}/talking-points")
async def get_talking_points(
    job_id: str,
    job: Dict[str, Any] = Depends(require_job_view),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get talking points for a job"""
    try:
        # job provided by require_job_view
        talking_points = job.get("talking_points")
        if not talking_points:
            raise HTTPException(status_code=404, detail="Talking points not found for this job")
        
        return {
            "status": "success",
            "job_id": job_id,
            "talking_points": talking_points,
            "metadata": job.get("talking_points_metadata", {})
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving talking points for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving talking points")


@router.post("/jobs/{job_id}/export")
async def export_job_content(
    job_id: str,
    export_request: ExportRequest,
    job: Dict[str, Any] = Depends(require_job_export),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Export job content in specified format"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        export_service = ExportService(config)
        # job provided by require_job_export
        
        # Prepare content for export
        export_content = {
            "job_id": job_id,
            "title": job.get("original_filename", "Untitled Document"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at")
        }
        
        if export_request.include_transcription and job.get("text_content"):
            export_content["transcription"] = job["text_content"]
        
        if export_request.include_analysis and job.get("analysis_content"):
            export_content["analysis"] = job["analysis_content"]
        
        if export_request.include_talking_points and job.get("talking_points"):
            export_content["talking_points"] = job["talking_points"]
        
        # Generate export
        export_result = await export_service.export_content(
            content=export_content,
            format=export_request.format,
            filename=f"{job.get('original_filename', 'document')}_{job_id}"
        )
        
        # Return appropriate response based on format
        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "json": "application/json"
        }
        
        file_extensions = {
            "pdf": "pdf",
            "docx": "docx", 
            "txt": "txt",
            "json": "json"
        }
        
        content_type = content_types.get(export_request.format, "application/octet-stream")
        file_extension = file_extensions.get(export_request.format, "bin")
        filename = f"{job.get('original_filename', 'document')}_{job_id}.{file_extension}"
        
        logger.info(f"Job {job_id} exported as {export_request.format} by user {current_user['id']}")
        
        return Response(
            content=export_result["content"],
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error exporting job content")


@router.get("/jobs/{job_id}/download")
async def download_original_file(
    job_id: str,
    job: Dict[str, Any] = Depends(require_job_download),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Download the original uploaded file"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        storage_service = StorageService(config)
        # job provided by require_job_download
        
        if not job.get("file_path"):
            raise HTTPException(status_code=404, detail="Original file not found")
        
        # Get file content from storage
        file_content = await storage_service.download_file_content(job["file_path"])
        if not file_content:
            raise HTTPException(status_code=404, detail="File content not accessible")
        
        # Determine content type and filename
        original_filename = job.get("original_filename", "download")
        content_type = job.get("content_type", "application/octet-stream")
        
        logger.info(f"Original file downloaded for job {job_id} by user {current_user['id']}")
        
        return Response(
            content=file_content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{original_filename}"'}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading original file for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error downloading file")


@router.post("/jobs/{job_id}/archive")
async def archive_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_job_owner_or_admin),
) -> Dict[str, Any]:
    """Archive a job (move to archived state)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        job = cosmos_db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check access permissions
        user_permission = get_user_job_permission(job, current_user)
        if user_permission not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Only job owner or admin can archive jobs")
        
        # Archive the job
        update_fields = {
            "archived": True,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "archived_by": current_user["id"],
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} archived by user {current_user['id']}")
        
        return {
            "status": "success",
            "message": "Job archived successfully",
            "job_id": job_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error archiving job")


@router.post("/jobs/{job_id}/restore")
async def restore_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_job_owner_or_admin),
) -> Dict[str, Any]:
    """Restore an archived job"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        job = cosmos_db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check access permissions
        user_permission = get_user_job_permission(job, current_user)
        if user_permission not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Only job owner or admin can restore jobs")
        
        if not job.get("archived"):
            raise HTTPException(status_code=400, detail="Job is not archived")
        
        # Restore the job
        update_fields = {
            "archived": False,
            "restored_at": datetime.now(timezone.utc).isoformat(),
            "restored_by": current_user["id"],
            "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        cosmos_db.update_job(job_id, update_fields)
        
        logger.info(f"Job {job_id} restored by user {current_user['id']}")
        
        return {
            "status": "success",
            "message": "Job restored successfully",
            "job_id": job_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error restoring job")
