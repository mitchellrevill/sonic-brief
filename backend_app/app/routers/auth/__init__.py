"""
Auth Router Module - Central import and routing registration for auth domain
Provides unified access to all auth-related router endpoints
"""
from fastapi import APIRouter
from .authentication import router as authentication_router
from .user_management import router as user_management_router
from .permissions import router as permissions_router
# Auth Router Module - central routing for auth domain
from fastapi import APIRouter
from .authentication import router as authentication_router
from .user_management import router as user_management_router
from .permissions import router as permissions_router

# Create main auth router
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# Include all auth domain routers
auth_router.include_router(authentication_router, prefix="", tags=["authentication"])
auth_router.include_router(user_management_router, prefix="", tags=["user-management"]) 
auth_router.include_router(permissions_router, prefix="", tags=["permissions"])

# Export routers only. Shared dependency helpers live in `app.core.dependencies`.
__all__ = [
    "auth_router",
    "authentication_router",
    "user_management_router",
    "permissions_router",
]
