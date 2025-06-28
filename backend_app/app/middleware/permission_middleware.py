# Simple Permission Middleware (Refactored)
from functools import wraps
from typing import Callable, Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import logging
from app.models.permissions import PermissionLevel, PermissionCapability
from app.utils.audit_logger import audit_logger, AuditEventType

# Setup logging
logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Dependency to extract user_id from JWT token (to be updated to use new settings)
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    from jose import jwt, JWTError
    import os
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

# Import permission service after defining dependencies to avoid circular imports
def get_permission_service():
    from app.services.permissions import permission_service
    return permission_service

# FastAPI dependencies for permission checking
async def require_admin(user_id: str = Depends(get_current_user_id)) -> str:
    permission_service = get_permission_service()
    perm = await permission_service.get_user_permission(user_id)
    if not permission_service.has_permission_level(perm, PermissionLevel.ADMIN):
        # Log access denied
        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="endpoint",
            resource_id="admin_endpoint",
            required_capability=PermissionCapability.CAN_MANAGE_USERS,
            user_permission=perm or "None"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Admin permission required. Current permission: {perm or 'None'}"
        )
    return user_id

async def require_editor(user_id: str = Depends(get_current_user_id)) -> str:
    permission_service = get_permission_service()
    perm = await permission_service.get_user_permission(user_id)
    if not permission_service.has_permission_level(perm, PermissionLevel.EDITOR):
        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="endpoint",
            resource_id="editor_endpoint",
            required_capability="editor_or_higher",
            user_permission=perm or "None"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Editor permission or higher required. Current permission: {perm or 'None'}"
        )
    return user_id

async def require_user(user_id: str = Depends(get_current_user_id)) -> str:
    permission_service = get_permission_service()
    perm = await permission_service.get_user_permission(user_id)
    if not permission_service.has_permission_level(perm, PermissionLevel.USER):
        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="endpoint", 
            resource_id="user_endpoint",
            required_capability="user_or_higher",
            user_permission=perm or "None"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"User permission or higher required. Current permission: {perm or 'None'}"
        )
    return user_id

# Utility functions for permission checks
def has_permission_level(user_permission: str, required_permission: PermissionLevel) -> bool:
    permission_service = get_permission_service()
    return permission_service.has_permission_level(user_permission, required_permission)

def get_user_capabilities(permission: str) -> dict:
    permission_service = get_permission_service()
    return permission_service.get_user_capabilities(permission)