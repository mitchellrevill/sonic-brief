"""
System Router Module - Central import and routing registration for system domain
Provides unified access to all system-related router endpoints
"""
from fastapi import APIRouter
from .health import router as health_router
from .admin import router as admin_router

# Create main system router
system_router = APIRouter(prefix="/api/system", tags=["system"])

# Include all system domain routers
system_router.include_router(health_router, prefix="", tags=["system-health"])
system_router.include_router(admin_router, prefix="", tags=["admin"])

# Export individual routers for selective inclusion if needed
__all__ = [
    "system_router",
    "health_router",
    "admin_router"
]
