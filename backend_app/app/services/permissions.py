from typing import Dict, Any, List, Optional, Callable, TypeVar, Awaitable
from functools import wraps
import logging
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

from app.models.permissions import (
    PermissionLevel, 
    PERMISSION_HIERARCHY, 
    PERMISSION_CAPABILITIES,
    PermissionCapability,
    can_user_perform_action,
    get_user_capabilities,
    merge_custom_capabilities
)
from app.utils.permission_cache import get_permission_cache, BasePermissionCache

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

T = TypeVar('T')
RouteFunc = TypeVar('RouteFunc', bound=Callable[..., Awaitable[Any]])

class PermissionService:
    """
    Service for checking, validating, and enforcing permissions.
    Uses cache-first strategy with database fallback.
    """
    def __init__(self, permission_cache: BasePermissionCache = None, cosmos_db = None):
        self.permission_cache = permission_cache or get_permission_cache()
        self.cosmos_db = cosmos_db  # Will be injected when needed

    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """Get user permission with cache-first strategy"""
        cached_permission = await self.permission_cache.get_user_permission(user_id)
        if cached_permission:
            return cached_permission
        
        # Fall back to database if cache miss
        if self.cosmos_db:
            try:
                user = await self.cosmos_db.get_user_by_id(user_id)
                if user and "permission" in user:
                    permission = user["permission"]
                    # Cache the result
                    await self.permission_cache.set_user_permission(user_id, permission)
                    return permission
            except Exception as e:
                logger.warning(f"Failed to get user permission from database for {user_id}: {e}")
        
        return None

    def set_cosmos_db(self, cosmos_db):
        """Set CosmosDB instance for database fallback"""
        self.cosmos_db = cosmos_db

    def has_permission_level(self, user_permission: str, required_permission: PermissionLevel) -> bool:
        if not user_permission or not required_permission:
            return False
        user_level = PERMISSION_HIERARCHY.get(user_permission, 0)
        required_level = PERMISSION_HIERARCHY.get(required_permission, 0)
        return user_level >= required_level

    def get_user_capabilities(self, permission: str, custom_capabilities: Dict[str, bool] = None) -> Dict[str, bool]:
        base_capabilities = get_user_capabilities(permission)
        return merge_custom_capabilities(base_capabilities, custom_capabilities)

    def can(self, user_permission: str, capability: str) -> bool:
        """
        Check if a user can perform a specific action.
        
        Args:
            user_permission: The user's permission level
            capability: The capability to check (use PermissionCapability enum values)
        
        Returns:
            bool: True if the user can perform the action
        """
        return can_user_perform_action(user_permission, capability)

    async def has_capability(self, user_permission: str, custom_capabilities: Dict[str, bool], capability: str) -> bool:
        """
        Check if a user can perform a specific action, considering custom capabilities.
        
        Args:
            user_permission: The user's permission level
            custom_capabilities: Custom capabilities that may override base capabilities
            capability: The capability to check (use PermissionCapability enum values)
        
        Returns:
            bool: True if the user can perform the action
        """
        base_capabilities = get_user_capabilities(user_permission)
        merged_capabilities = merge_custom_capabilities(base_capabilities, custom_capabilities)
        return merged_capabilities.get(capability, False)

    def require_permission(self, required_permission: PermissionLevel):
        def decorator(func: RouteFunc) -> RouteFunc:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # This decorator pattern could be used for method-level permissions
                # For now, we prefer dependency injection pattern with FastAPI
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    # FastAPI dependencies for permission checking
    async def require_admin(self, user_id: str) -> str:
        """FastAPI dependency that ensures a user has admin permissions."""
        user_permission = await self.get_user_permission(user_id)
        if not self.has_permission_level(user_permission, PermissionLevel.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin permission required. Current permission: {user_permission or 'None'}",
            )
        return user_id

    async def require_editor(self, user_id: str) -> str:
        """FastAPI dependency that ensures a user has at least editor permissions."""
        user_permission = await self.get_user_permission(user_id)
        if not self.has_permission_level(user_permission, PermissionLevel.EDITOR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Editor permission or higher required. Current permission: {user_permission or 'None'}",
            )
        return user_id
    
    async def require_user(self, user_id: str) -> str:
        """FastAPI dependency that ensures a user has at least user permissions."""
        user_permission = await self.get_user_permission(user_id)
        if not self.has_permission_level(user_permission, PermissionLevel.USER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User permission or higher required. Current permission: {user_permission or 'None'}",
            )
        return user_id

    async def set_user_permission_cache(self, user_id: str, permission: str, ttl: Optional[int] = None):
        """Cache a user's permission level"""
        await self.permission_cache.set_user_permission(user_id, permission, ttl)

    async def invalidate_user_permission_cache(self, user_id: str):
        """Invalidate cached permission for a user"""
        await self.permission_cache.invalidate_user_cache(user_id)

# Create a global instance for easy access
permission_service = PermissionService()

# Convenience dependencies
require_admin_permission = permission_service.require_permission(PermissionLevel.ADMIN)
require_editor_permission = permission_service.require_permission(PermissionLevel.EDITOR)
require_user_permission = permission_service.require_permission(PermissionLevel.USER)
