"""
Auth Router Module - Central import and routing registration for auth domain
Provides unified access to all auth-related router endpoints
"""
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Defensive imports: if a submodule is not present during the migration we
# should not fail application startup. Import what exists and include it.
user_management_router = None
permissions_router = None
authentication_router = None

try:
    from .user_management import router as user_management_router
except Exception as e:
    logger.warning("user_management router unavailable: %s", e)

try:
    from .permissions import router as permissions_router
except Exception as e:
    logger.warning("permissions router unavailable: %s", e)

try:
    from .authentication import router as authentication_router
except Exception as e:
    logger.warning("authentication router unavailable: %s", e)

# Create main auth router
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

if user_management_router is not None:
    auth_router.include_router(user_management_router, prefix="", tags=["user-management"]) 
if permissions_router is not None:
    auth_router.include_router(permissions_router, prefix="", tags=["permissions"])
if authentication_router is not None:
    auth_router.include_router(authentication_router, prefix="", tags=["authentication"])

# Backwards-compatibility: some modules import `get_current_user` from
# `app.routers.auth`. Re-export the centralized dependency from core.
try:
    from ...core.dependencies import get_current_user
except Exception:
    get_current_user = None

__all__ = ["auth_router", "get_current_user"]
