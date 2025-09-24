"""
System Router Module - Central import and routing registration for system domain
Provides unified access to all system-related router endpoints
"""
from fastapi import APIRouter
from .health import router as health_router

# Create main system router
system_router = APIRouter(prefix="/api/system")

# Include all system domain routers. Do NOT re-apply tags here so subrouters keep their own tags
system_router.include_router(health_router, prefix="")
# Export individual routers for selective inclusion if needed
__all__ = [
    "system_router",
    "health_router",
]
