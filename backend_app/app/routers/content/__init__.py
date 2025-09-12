"""
Content Router Module - Central import and routing registration for content domain
Provides unified access to all content-related router endpoints
"""
from fastapi import APIRouter
from .file_upload import router as file_upload_router
from .job_management import router as job_management_router
from .document_processing import router as document_processing_router

# Create main content router
content_router = APIRouter(prefix="/api/content", tags=["content"])

# Include all content domain routers
content_router.include_router(file_upload_router, prefix="", tags=["file-upload"])
content_router.include_router(job_management_router, prefix="", tags=["job-management"])  
content_router.include_router(document_processing_router, prefix="", tags=["document-processing"])

# Export individual routers for selective inclusion if needed
__all__ = [
    "content_router",
    "file_upload_router", 
    "job_management_router",
    "document_processing_router"
]
