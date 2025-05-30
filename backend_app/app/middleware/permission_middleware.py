# Simple Permission Middleware (No Redis)
from enum import Enum
from functools import wraps
from typing import Callable, Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import logging

# Setup logging
logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class PermissionLevel(str, Enum):
    """Permission levels in hierarchical order"""
    VIEWER = "Viewer"
    USER = "User" 
    ADMIN = "Admin"

# Permission hierarchy (higher number = more permissions)
PERMISSION_HIERARCHY = {
    PermissionLevel.VIEWER: 1,
    PermissionLevel.USER: 2,
    PermissionLevel.ADMIN: 3,
}

class PermissionChecker:
    """Simple permission checker that queries Cosmos DB directly"""
    
    def __init__(self):
        from app.core.config import config, CosmosDB
        self.cosmos_db = CosmosDB(config)
    
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """Get user permission directly from Cosmos DB with fallback caching"""
        try:
            user = await self.cosmos_db.get_user_by_id(user_id)
            if user:
                return user.get("permission", "Viewer")
            return None
        except Exception as e:
            logger.error(f"Error getting user permission for {user_id}: {str(e)}")
            return None
    
    async def check_permission(self, user_id: str, required_permission: PermissionLevel) -> bool:
        """Check if user has required permission level or higher"""
        try:
            user_permission = await self.get_user_permission(user_id)
            if not user_permission:
                return False
            
            user_level = PERMISSION_HIERARCHY.get(user_permission, 0)
            required_level = PERMISSION_HIERARCHY.get(required_permission, 0)
            
            return user_level >= required_level
        except Exception as e:
            logger.error(f"Error checking permission for {user_id}: {str(e)}")
            return False

# Global permission checker instance
permission_checker = PermissionChecker()

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """Extract user ID from JWT token"""
    from app.core.config import config
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, config.auth["jwt_secret_key"], algorithms=[config.auth["jwt_algorithm"]])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

async def get_current_user_permission(user_id: str = Depends(get_current_user_id)) -> str:
    """Get current user's permission level"""
    permission = await permission_checker.get_user_permission(user_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return permission

# Permission requirement decorators
def require_permission(required_permission: PermissionLevel):
    """Decorator to require specific permission level"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from function dependencies
            user_id = None
            for key, value in kwargs.items():
                if key == "current_user_id" or (hasattr(value, '__class__') and 'user' in str(value.__class__).lower()):
                    user_id = value if isinstance(value, str) else getattr(value, 'id', None)
                    break
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User authentication required"
                )
            
            has_permission = await permission_checker.check_permission(user_id, required_permission)
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Convenience decorators for common permission levels
def require_admin_permission(func: Callable):
    """Require Admin permission"""
    return require_permission(PermissionLevel.ADMIN)(func)

def require_user_permission(func: Callable):
    """Require User permission or higher"""
    return require_permission(PermissionLevel.USER)(func)

def require_viewer_permission(func: Callable):
    """Require Viewer permission or higher (basically any authenticated user)"""
    return require_permission(PermissionLevel.VIEWER)(func)

# FastAPI dependencies for permission checking
async def require_admin(current_user_id: str = Depends(get_current_user_id)) -> str:
    """FastAPI dependency to require admin permission"""
    has_permission = await permission_checker.check_permission(current_user_id, PermissionLevel.ADMIN)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    return current_user_id

async def require_user(current_user_id: str = Depends(get_current_user_id)) -> str:
    """FastAPI dependency to require user permission or higher"""
    has_permission = await permission_checker.check_permission(current_user_id, PermissionLevel.USER)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User permission or higher required"
        )
    return current_user_id

async def require_viewer(current_user_id: str = Depends(get_current_user_id)) -> str:
    """FastAPI dependency to require viewer permission or higher"""
    has_permission = await permission_checker.check_permission(current_user_id, PermissionLevel.VIEWER)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    return current_user_id

# Utility functions for permission checks
def has_permission_level(user_permission: str, required_permission: PermissionLevel) -> bool:
    """Check if a permission level meets requirements"""
    user_level = PERMISSION_HIERARCHY.get(user_permission, 0)
    required_level = PERMISSION_HIERARCHY.get(required_permission, 0)
    return user_level >= required_level

def get_user_capabilities(permission: str) -> dict:
    """Get user capabilities based on permission level"""
    permission_level = PERMISSION_HIERARCHY.get(permission, 0)
    
    return {
        "can_view": permission_level >= 1,
        "can_edit": permission_level >= 2,
        "can_admin": permission_level >= 3,
        "can_manage_users": permission_level >= 3,
        "can_create_content": permission_level >= 2,
        "can_delete_content": permission_level >= 3,
    }