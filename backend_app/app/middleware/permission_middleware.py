# Simple Permission Middleware (Refactored)
from functools import wraps
from typing import Callable, Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import logging
from ..models.permissions import PermissionLevel, PermissionCapability, PERMISSION_HIERARCHY, get_user_capabilities as model_get_user_capabilities
from ..utils.audit_logger import audit_logger, AuditEventType
from ..core.config import get_app_config, get_cosmos_db_cached

# Setup logging
logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Dependency to extract user_id from JWT token using secure settings
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    from jose import jwt, JWTError
    from ..core.settings import get_settings
    
    settings = get_settings()
    jwt_secret_key = settings.auth.jwt_secret_key
    jwt_algorithm = settings.auth.jwt_algorithm
    
    # Validate that secret key exists
    if not jwt_secret_key:
        logger.error("JWT_SECRET_KEY is not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service misconfigured"
        )
    
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

# (No shim) Permission utilities should be used via `app.models.permissions` or
# `app.core.permissions`. This module provides authentication-related
# dependencies (token decoding) and small permission-level dependencies that
# query the Cosmos DB directly where needed.

# FastAPI dependencies for permission checking
async def require_admin(user_id: str = Depends(get_current_user_id)) -> str:
    config = get_app_config()
    cosmos = get_cosmos_db_cached(config)
    user = await cosmos.get_user_by_id(user_id)
    perm = user.get("permission") if user else None
    if not perm or PERMISSION_HIERARCHY.get(perm, 0) < PERMISSION_HIERARCHY.get(PermissionLevel.ADMIN.value, 0):
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
    config = get_app_config()
    cosmos = get_cosmos_db_cached(config)
    user = await cosmos.get_user_by_id(user_id)
    perm = user.get("permission") if user else None
    if not perm or PERMISSION_HIERARCHY.get(perm, 0) < PERMISSION_HIERARCHY.get(PermissionLevel.EDITOR.value, 0):
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
    config = get_app_config()
    cosmos = get_cosmos_db_cached(config)
    user = await cosmos.get_user_by_id(user_id)
    perm = user.get("permission") if user else None
    if not perm or PERMISSION_HIERARCHY.get(perm, 0) < PERMISSION_HIERARCHY.get(PermissionLevel.USER.value, 0):
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
    if not user_permission:
        return False
    return PERMISSION_HIERARCHY.get(user_permission, 0) >= PERMISSION_HIERARCHY.get(required_permission.value, 0)


def get_user_capabilities(permission: str, custom: dict = None) -> dict:
    return model_get_user_capabilities(permission, custom or {})


# Decorator to gate debug-only endpoints. Default enabled in local/dev via
# ENABLE_DEBUG_ENDPOINTS env var. Use conservatively; production should set
# ENABLE_DEBUG_ENDPOINTS=false to prevent access.
def debug_endpoint_required(func: Callable):
    from functools import wraps
    import os
    from fastapi import HTTPException, status

    @wraps(func)
    async def wrapper(*args, **kwargs):
        enabled = os.environ.get("ENABLE_DEBUG_ENDPOINTS", "true").lower()
        if enabled in ("1", "true", "yes"):
            return await func(*args, **kwargs)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are disabled in this environment"
        )

    return wrapper