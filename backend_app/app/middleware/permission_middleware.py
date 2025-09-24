# Simple Permission Middleware (Clean Architecture - Hierarchical Only)
from functools import wraps
from typing import Callable
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import logging
from ..models.permissions import PermissionLevel, has_permission_level

# Setup logging
logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Dependency to extract user_id from JWT token
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    from jose import jwt, JWTError
    from ..core.config import get_config
    
    config = get_config()
    jwt_secret_key = config.jwt_secret_key
    jwt_algorithm = config.jwt_algorithm
    
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

# Decorator to gate debug-only endpoints
def debug_endpoint_required(func: Callable):
    """Decorator to require debug endpoints to be enabled"""
    import os
    
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