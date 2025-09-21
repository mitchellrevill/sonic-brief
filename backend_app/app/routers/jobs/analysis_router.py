from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from ...core.dependencies import get_current_user, get_analysis_refinement_service
from ...services.jobs.analysis_refinement_service import AnalysisRefinementService
from ...services.jobs.job_permissions import JobPermissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["job-analysis"])


class RefinementRequest(BaseModel):
    """Request model for analysis refinement."""
    user_request: str
    
    class Config:
        schema_extra = {
            "example": {
                "user_request": "Can you provide more specific recommendations from this analysis?"
            }
        }


class DocumentUpdateRequest(BaseModel):
    """Request model for document updates."""
    content: str
    format_type: Optional[str] = "docx"
    
    class Config:
        schema_extra = {
            "example": {
                "content": "Updated analysis content...",
                "format_type": "docx"
            }
        }


def get_job_permissions() -> JobPermissions:
    """Dependency provider for JobPermissions."""
    return JobPermissions()


@router.post("/{job_id}/refinements")
async def create_refinement(
    job_id: str,
    request: RefinementRequest,
    stream: bool = False,
    current_user: dict = Depends(get_current_user),
    refinement_service: AnalysisRefinementService = Depends(get_analysis_refinement_service),
    permissions: JobPermissions = Depends(get_job_permissions)
):
    """
    Create a new analysis refinement for a job.
    
    RESTful endpoint that creates a refinement resource.
    Returns 201 Created with refinement data.
    """
    try:
        # Load the job early so permission checks can verify ownership/shared access
        job = await refinement_service.cosmos.get_job_by_id_async(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check if user can read this job (pass job dict so owner checks work)
        has_access = await permissions.check_job_access(job, current_user, "read")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this job"
            )
        
        # If client requested streaming, proxy the function response as SSE
        if stream:
            async def sse_generator():
                # Fetch job and permission already validated above
                job = await refinement_service.cosmos.get_job_by_id_async(job_id)
                if not job:
                    yield f"data: {json.dumps({'error':'job not found'})}\n\n"
                    return

                # Prepare request payload
                request_data = {
                    "original_text": job.get("text_content", ""),
                    "current_analysis": job.get("analysis_content", ""),
                    "user_request": request.user_request,
                    "conversation_history": job.get("refinement_history", [])
                }

                buffer_parts = []

                # Use the service streaming helper which proxies Azure OpenAI streaming
                async for chunk in refinement_service.stream_model_provider(request_data):
                    # The helper yields raw chunks (may already include 'data:' prefixes).
                    # Normalize into SSE `data: "..."` format by JSON-encoding the chunk.
                    if chunk.startswith("ERROR:"):
                        yield f"data: {json.dumps({'error': chunk})}\n\n"
                        continue

                    # forward chunk as event
                    for line in str(chunk).splitlines() or [str(chunk)]:
                        yield f"data: {json.dumps(line)}\n\n"
                        buffer_parts.append(line)

                # After stream ends, persist final assembled text
                final_text = "".join(buffer_parts).strip()
                final_result = None
                try:
                    final_result = json.loads(final_text)
                except Exception:
                    final_result = {"refined_analysis": final_text, "status": "success"}

                ai_response = final_result.get("refined_analysis") if isinstance(final_result, dict) else str(final_result)

                refinement_entry = {
                    "id": __import__('uuid').uuid4().hex,
                    "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                    "user_request": request.user_request,
                    "ai_response": ai_response,
                    "status": final_result.get("status", "success") if isinstance(final_result, dict) else "success"
                }

                if "refinement_history" not in job:
                    job["refinement_history"] = []
                job["refinement_history"].append(refinement_entry)
                job["last_refined_at"] = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
                await refinement_service.cosmos.update_job_async(job_id, job)

                return

            return StreamingResponse(sse_generator(), media_type="text/event-stream")

        # Non-streaming (default) path
        result = await refinement_service.refine_analysis(
            job_id=job_id,
            user_id=current_user["id"],
            user_request=request.user_request
        )
        
        if result["status"] == "error":
            if "not found" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            elif "Access denied" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "refinement_id": result.get("refinement_id"),
                "ai_response": result.get("ai_response"),
                "timestamp": result.get("timestamp"),
                "message": "Analysis refinement created successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating refinement for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{job_id}/refine")
async def refine_analysis(
    job_id: str,
    request: RefinementRequest,
    current_user: dict = Depends(get_current_user),
    refinement_service: AnalysisRefinementService = Depends(get_analysis_refinement_service),
    permissions: JobPermissions = Depends(get_job_permissions)
):
    """
    Legacy refinement endpoint. Use POST /api/jobs/{job_id}/refinements instead.
    
    Args:
        job_id: ID of the job to refine
        request: Refinement request containing user's request
        current_user: Current user ID from auth
        refinement_service: Analysis refinement service
        permissions: Job permissions service
    """
    try:
        # Load the job so permission logic can verify owner/shared access
        job = await refinement_service.cosmos.get_job_by_id_async(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check if user can read this job
        has_access = await permissions.check_job_access(job, current_user, "read")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this job"
            )

        result = await refinement_service.refine_analysis(
            job_id=job_id,
            user_id=current_user["id"],
            user_request=request.user_request
        )
        
        if result["status"] == "error":
            if "not found" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            elif "Access denied" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        return {
            "status": "success",
            "refinement_id": result.get("refinement_id"),
            "ai_response": result.get("ai_response"),
            "timestamp": result.get("timestamp"),
            "message": "Analysis refined successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refining analysis for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Legacy endpoint /{job_id}/refine removed; use POST /api/jobs/{job_id}/refinements instead.


@router.get("/{job_id}/refinements")
async def get_refinement_history(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    refinement_service: AnalysisRefinementService = Depends(get_analysis_refinement_service),
    permissions: JobPermissions = Depends(get_job_permissions)
):
    """
    Get refinement history for a job.
    
    Args:
        job_id: ID of the job
        current_user: Current user ID from auth
        refinement_service: Analysis refinement service
        permissions: Job permissions service
    """
    try:
        # Load job first so permission checks can validate ownership/shared access
        job = await refinement_service.cosmos.get_job_by_id_async(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check if user can read this job
        has_access = await permissions.check_job_access(job, current_user, "read")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this job"
            )

        result = await refinement_service.get_refinement_history(job_id, current_user["id"])
        
        if result["status"] == "error":
            if "not found" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            elif "Access denied" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        return {
            "status": "success",
            "job_id": job_id,
            "refinement_history": result.get("refinement_history", []),
            "total_refinements": result.get("total_refinements", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting refinement history for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{job_id}/refinements/suggestions")
async def get_refinement_suggestions(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    refinement_service: AnalysisRefinementService = Depends(get_analysis_refinement_service),
    permissions: JobPermissions = Depends(get_job_permissions)
):
    """
    Get suggested refinement questions for a job.
    
    Args:
        job_id: ID of the job
        current_user: Current user ID from auth
        refinement_service: Analysis refinement service
        permissions: Job permissions service
    """
    try:
        # Load job first so permission checks can validate ownership/shared access
        job = await refinement_service.cosmos.get_job_by_id_async(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check if user can read this job
        has_access = await permissions.check_job_access(job, current_user, "read")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this job"
            )

        result = await refinement_service.get_refinement_suggestions(job_id, current_user["id"])
        
        if result["status"] == "error":
            if "not found" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            elif "Access denied" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        return {
            "status": "success",
            "job_id": job_id,
            "suggestions": result.get("suggestions", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting refinement suggestions for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{job_id}/analysis")
async def update_analysis_document(
    job_id: str,
    request: DocumentUpdateRequest,
    current_user: dict = Depends(get_current_user),
    refinement_service: AnalysisRefinementService = Depends(get_analysis_refinement_service),
    permissions: JobPermissions = Depends(get_job_permissions)
):
    """
    Update the analysis document for a job.
    
    Args:
        job_id: ID of the job
        request: Document update request
        current_user: Current user from auth
        refinement_service: Analysis refinement service
        permissions: Job permissions service
    """
    try:
        # Load job first so permission checks can validate ownership/shared access
        job = await refinement_service.cosmos.get_job_by_id_async(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check if user can write to this job
        has_access = await permissions.check_job_access(job, current_user, "write")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this job"
            )

        result = await refinement_service.update_analysis_document(
            job_id=job_id,
            user_id=current_user["id"],
            new_content=request.content,
            format_type=request.format_type
        )
        
        if result["status"] == "error":
            if "not found" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            elif "Access denied" in result["message"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        return {
            "status": "success",
            "message": "Analysis document updated successfully",
            "job_id": job_id,
            "updated_at": result.get("updated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating analysis document for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
