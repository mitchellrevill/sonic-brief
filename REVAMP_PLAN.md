# Permission System Revamp Plan

This document outlines a comprehensive plan to revamp the configuration management, permission system, and caching mechanisms in the Sonic Brief backend application.

## Current Issues

After analyzing the codebase, we've identified several issues:

1. **Duplicate Cache Implementations**: `SimplePermissionCache` in `config.py` and `PermissionCache` in `permission_cache.py` have overlapping functionality.

2. **Inconsistent Permission Levels**: Default permission in `create_user` is `"Viewer"`, but the hierarchy in `permission_middleware.py` uses `"User"`, `"Editor"`, and `"Admin"`.

3. **Config Management**: Configuration is scattered and uses direct environment variable access.

4. **Mixed Cache Usage**: Some methods bypass the cache and directly query the database.

5. **Error Handling**: Inconsistent error handling patterns across the codebase.

6. **Partition Key Handling**: Multiple partition keys are tried in operations like `delete_user`.

## Implementation Plan

### 1. Unify Permission Models and Constants

**Create `app/models/permissions.py`:**
```python
from enum import Enum
from typing import Dict, Any

class PermissionLevel(str, Enum):
    """Permission levels in hierarchical order"""
    USER = "User"
    EDITOR = "Editor" 
    ADMIN = "Admin"

# Permission hierarchy (higher number = more permissions)
PERMISSION_HIERARCHY = {
    PermissionLevel.USER: 1,
    PermissionLevel.EDITOR: 2,
    PermissionLevel.ADMIN: 3,
}

# Permission capabilities
PERMISSION_CAPABILITIES = {
    PermissionLevel.USER: {
        "can_view_own_jobs": True,
        "can_create_jobs": True,
        "can_edit_own_jobs": True,
        "can_delete_own_jobs": True,
        "can_view_shared_jobs": True,
    },
    PermissionLevel.EDITOR: {
        "can_view_own_jobs": True,
        "can_create_jobs": True,
        "can_edit_own_jobs": True,
        "can_delete_own_jobs": True,
        "can_view_shared_jobs": True,
        "can_edit_shared_jobs": True,
        "can_create_templates": True,
    },
    PermissionLevel.ADMIN: {
        "can_view_own_jobs": True,
        "can_create_jobs": True,
        "can_edit_own_jobs": True,
        "can_delete_own_jobs": True,
        "can_view_shared_jobs": True,
        "can_edit_shared_jobs": True,
        "can_create_templates": True,
        "can_view_all_jobs": True,
        "can_edit_all_jobs": True,
        "can_delete_all_jobs": True,
        "can_manage_users": True,
    },
}
```

### 2. Centralize Configuration with Pydantic

**Create `app/core/settings.py`:**
```python
from pydantic import BaseSettings, Field
from typing import Dict, Any, Optional
import os
from functools import lru_cache

class CosmosSettings(BaseSettings):
    endpoint: str = Field(..., env="AZURE_COSMOS_ENDPOINT")
    database: str = Field("VoiceDB", env="AZURE_COSMOS_DB")
    prefix: str = Field("voice_", env="AZURE_COSMOS_DB_PREFIX")
    
    @property
    def containers(self) -> Dict[str, str]:
        return {
            "auth": f"{self.prefix}auth",
            "jobs": f"{self.prefix}jobs",
            "prompts": f"{self.prefix}prompts",
            "analytics": f"{self.prefix}analytics",
            "events": f"{self.prefix}events",
            "user_sessions": f"{self.prefix}user_sessions",
        }

class AuthSettings(BaseSettings):
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256")
    jwt_access_token_expire_minutes: int = Field(60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    # Add other auth settings as needed

class CacheSettings(BaseSettings):
    cache_type: str = Field("in_memory", env="CACHE_TYPE")  # "in_memory" or "redis"
    default_ttl: int = Field(300, env="CACHE_DEFAULT_TTL")  # 5 minutes
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    key_prefix: str = Field("permission:", env="CACHE_KEY_PREFIX")

class Settings(BaseSettings):
    environment: str = Field("development", env="ENVIRONMENT")
    cosmos: CosmosSettings = CosmosSettings()
    auth: AuthSettings = AuthSettings()
    cache: CacheSettings = CacheSettings()
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 3. Create Unified Permission Cache

**Update `app/utils/permission_cache.py`:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
import time
import json
from functools import wraps

from app.core.settings import get_settings, CacheSettings

logger = logging.getLogger(__name__)

class BasePermissionCache(ABC):
    """Abstract base class for permission caching implementations"""
    
    @abstractmethod
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """Get a user's permission level from cache."""
        pass
        
    @abstractmethod
    async def set_user_permission(self, user_id: str, permission: str, ttl: Optional[int] = None):
        """Set a user's permission level in cache."""
        pass
    
    @abstractmethod
    async def get_users_by_permission(self, permission: str) -> Optional[List[Dict[str, Any]]]:
        """Get all users with a specific permission level."""
        pass
    
    @abstractmethod
    async def set_users_by_permission(self, permission: str, users: List[Dict[str, Any]], ttl: Optional[int] = None):
        """Cache users by permission level."""
        pass
    
    @abstractmethod
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user."""
        pass
    
    @abstractmethod
    async def invalidate_permission_level_cache(self, permission: str):
        """Invalidate cache for a permission level."""
        pass
    
    @abstractmethod
    async def get_multiple_permissions(self, user_ids: List[str]) -> Dict[str, Optional[str]]:
        """Get permissions for multiple users."""
        pass
    
    @abstractmethod
    async def set_multiple_permissions(self, permissions: Dict[str, str], ttl: Optional[int] = None):
        """Set permissions for multiple users."""
        pass
    
    @abstractmethod
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache."""
        pass

class InMemoryPermissionCache(BasePermissionCache):
    """In-memory implementation of permission cache."""
    
    def __init__(self, settings: CacheSettings = None):
        if settings is None:
            settings = get_settings().cache
            
        self.cache = {}
        self.key_prefix = settings.key_prefix
        self.default_ttl = settings.default_ttl
        logger.info(f"Initialized in-memory permission cache with TTL: {self.default_ttl}s")
    
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """Get a user's permission from cache."""
        key = f"{self.key_prefix}user:{user_id}"
        entry = self.cache.get(key)
        
        if not entry:
            return None
            
        # Check if entry is expired
        if time.time() > entry["expires"]:
            self.cache.pop(key, None)
            return None
            
        return entry["value"]
    
    async def set_user_permission(self, user_id: str, permission: str, ttl: Optional[int] = None):
        """Set a user's permission in cache."""
        if ttl is None:
            ttl = self.default_ttl
            
        key = f"{self.key_prefix}user:{user_id}"
        self.cache[key] = {
            "value": permission,
            "expires": time.time() + ttl
        }
    
    async def get_users_by_permission(self, permission: str) -> Optional[List[Dict[str, Any]]]:
        """Get all users with a specific permission level."""
        key = f"{self.key_prefix}permission_group:{permission}"
        entry = self.cache.get(key)
        
        if not entry:
            return None
            
        if time.time() > entry["expires"]:
            self.cache.pop(key, None)
            return None
            
        return entry["value"]
    
    async def set_users_by_permission(self, permission: str, users: List[Dict[str, Any]], ttl: Optional[int] = None):
        """Cache users by permission level."""
        if ttl is None:
            ttl = self.default_ttl
            
        key = f"{self.key_prefix}permission_group:{permission}"
        self.cache[key] = {
            "value": users,
            "expires": time.time() + ttl
        }
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user."""
        keys_to_remove = [key for key in self.cache.keys() if f"user:{user_id}" in key]
        for key in keys_to_remove:
            self.cache.pop(key, None)
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")
    
    async def invalidate_permission_level_cache(self, permission: str):
        """Invalidate cache for a permission level."""
        keys_to_remove = [key for key in self.cache.keys() if f"permission_group:{permission}" in key]
        for key in keys_to_remove:
            self.cache.pop(key, None)
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for permission {permission}")
    
    async def get_multiple_permissions(self, user_ids: List[str]) -> Dict[str, Optional[str]]:
        """Get permissions for multiple users."""
        result = {}
        for user_id in user_ids:
            result[user_id] = await self.get_user_permission(user_id)
        return result
    
    async def set_multiple_permissions(self, permissions: Dict[str, str], ttl: Optional[int] = None):
        """Set permissions for multiple users."""
        for user_id, permission in permissions.items():
            await self.set_user_permission(user_id, permission, ttl)
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache."""
        try:
            current_time = time.time()
            permission_keys = [k for k in self.cache.keys() if k.startswith(self.key_prefix)]
            
            # Calculate valid entries
            valid_entries = sum(1 for k in permission_keys if current_time <= self.cache[k]["expires"])
            
            # Estimate memory usage
            total_size = 0
            for key in permission_keys:
                entry = self.cache[key]
                # Rough estimate of memory size
                key_size = len(key)
                value_size = len(json.dumps(entry["value"])) if entry["value"] else 0
                entry_size = key_size + value_size + 16  # 16 bytes for overhead
                total_size += entry_size
            
            return {
                "total_permission_keys": len(permission_keys),
                "valid_entries": valid_entries,
                "expired_entries": len(permission_keys) - valid_entries,
                "memory_usage_estimate_bytes": total_size,
                "permission_key_prefix": self.key_prefix,
                "default_ttl": self.default_ttl,
                "cache_type": "in_memory",
            }
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {"error": str(e)}
    
    # DECORATOR FOR AUTOMATIC CACHING
    
    def cache_permission_check(self, ttl: Optional[int] = None):
        """Decorator to automatically cache permission check results."""
        def decorator(func):
            @wraps(func)
            async def wrapper(user_id: str, *args, **kwargs):
                # Try to get from cache first
                cached_result = await self.get_user_permission(user_id)
                if cached_result is not None:
                    return cached_result
                
                # Call the original function
                result = await func(user_id, *args, **kwargs)
                
                # Cache the result if it's valid
                if result is not None:
                    await self.set_user_permission(user_id, result, ttl)
                
                return result
            return wrapper
        return decorator

# Optionally implement RedisPermissionCache if needed
# class RedisPermissionCache(BasePermissionCache):
#     ...

def get_permission_cache() -> BasePermissionCache:
    """Factory function to get the appropriate cache implementation based on settings."""
    settings = get_settings()
    
    if settings.cache.cache_type == "redis" and settings.cache.redis_url:
        # return RedisPermissionCache(settings.cache)
        # Fall back to in-memory if Redis is not implemented yet
        logger.warning("Redis cache requested but not implemented, falling back to in-memory cache")
        return InMemoryPermissionCache(settings.cache)
    else:
        return InMemoryPermissionCache(settings.cache)

# Global cache instance (for backwards compatibility)
permission_cache = get_permission_cache()
```

### 4. Create Permission Service

**Create `app/services/permissions.py`:**
```python
from typing import Dict, Any, List, Optional, Callable, TypeVar, Awaitable
from functools import wraps
import logging
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

from app.models.permissions import PermissionLevel, PERMISSION_HIERARCHY, PERMISSION_CAPABILITIES
from app.utils.permission_cache import get_permission_cache, BasePermissionCache
from app.core.settings import get_settings

logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Type definitions for better type hinting
T = TypeVar('T')
RouteFunc = TypeVar('RouteFunc', bound=Callable[..., Awaitable[Any]])

class PermissionService:
    """
    Service for checking, validating, and enforcing permissions.
    Uses cache-first strategy with database fallback.
    """
    
    def __init__(self, permission_cache: BasePermissionCache = None):
        self.permission_cache = permission_cache or get_permission_cache()
    
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """
        Get a user's permission level from cache or database.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            The user's permission level or None if not found
        """
        # Check cache first
        cached_permission = await self.permission_cache.get_user_permission(user_id)
        if cached_permission:
            return cached_permission
        
        # TODO: If not in cache, query database (this will need to be injected)
        # For now, return None to indicate not found
        return None
    
    def has_permission_level(self, user_permission: str, required_permission: PermissionLevel) -> bool:
        """
        Check if user permission meets or exceeds the required permission level.
        
        Args:
            user_permission: The user's current permission level
            required_permission: The minimum permission level required
            
        Returns:
            True if user has sufficient permission, False otherwise
        """
        if not user_permission or not required_permission:
            return False
            
        user_level = PERMISSION_HIERARCHY.get(user_permission, 0)
        required_level = PERMISSION_HIERARCHY.get(required_permission, 0)
        
        return user_level >= required_level
    
    def get_user_capabilities(self, permission: str) -> Dict[str, bool]:
        """
        Get capabilities for a user based on permission level.
        
        Args:
            permission: The user's permission level
            
        Returns:
            Dictionary of capabilities and boolean values
        """
        if not permission or permission not in PERMISSION_CAPABILITIES:
            # Default to the lowest permission level
            return PERMISSION_CAPABILITIES[PermissionLevel.USER]
            
        return PERMISSION_CAPABILITIES[permission]
    
    # DECORATORS FOR PERMISSION ENFORCEMENT
    
    def require_permission(self, required_permission: PermissionLevel):
        """
        Decorator to enforce minimum permission level on a route.
        
        Args:
            required_permission: The minimum permission level required
            
        Returns:
            Decorator function
        """
        def decorator(func: RouteFunc) -> RouteFunc:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user_id from kwargs
                user_id = kwargs.get("user_id")
                if not user_id:
                    for arg in args:
                        if isinstance(arg, dict) and "user_id" in arg:
                            user_id = arg["user_id"]
                            break
                
                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Could not validate credentials",
                    )
                
                # Get user permission
                user_permission = await self.get_user_permission(user_id)
                if not user_permission:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found or not authenticated",
                    )
                
                # Check permission level
                if not self.has_permission_level(user_permission, required_permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied. Requires {required_permission} permission.",
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    # FastAPI dependencies for permission checking
    
    async def require_admin(self, user_id: str) -> str:
        """
        FastAPI dependency that ensures a user has Admin permissions.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            The user ID if authorized
            
        Raises:
            HTTPException: If user is not authorized
        """
        user_permission = await self.get_user_permission(user_id)
        if not user_permission or not self.has_permission_level(user_permission, PermissionLevel.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )
        return user_id
    
    async def require_editor(self, user_id: str) -> str:
        """FastAPI dependency that ensures a user has at least Editor permissions."""
        user_permission = await self.get_user_permission(user_id)
        if not user_permission or not self.has_permission_level(user_permission, PermissionLevel.EDITOR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editor permission required",
            )
        return user_id
    
    async def require_user(self, user_id: str) -> str:
        """FastAPI dependency that ensures a user has at least User permissions."""
        user_permission = await self.get_user_permission(user_id)
        if not user_permission or not self.has_permission_level(user_permission, PermissionLevel.USER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User permission required",
            )
        return user_id

# Create a global instance for easy access
permission_service = PermissionService()

# Convenience decorators
require_admin_permission = permission_service.require_permission(PermissionLevel.ADMIN)
require_editor_permission = permission_service.require_permission(PermissionLevel.EDITOR)
require_user_permission = permission_service.require_permission(PermissionLevel.USER)

# Convenience dependencies
require_admin = permission_service.require_admin
require_editor = permission_service.require_editor
require_user = permission_service.require_user
```

### 5. Update CosmosDB with Dependency Injection

**Update `app/core/config.py` (partial example):**
```python
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from app.core.settings import get_settings
from app.utils.permission_cache import get_permission_cache, BasePermissionCache
from app.models.permissions import PermissionLevel

# Setup logging
logger = logging.getLogger(__name__)

class CosmosDB:
    def __init__(self, settings=None, permission_cache: BasePermissionCache = None):
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(__name__)
        
        self._permission_cache = permission_cache or get_permission_cache()
        
        # Initialize Azure Cosmos DB client
        try:
            # ... (rest of initialization)
        except Exception as e:
            self.logger.error(f"Error initializing Cosmos DB: {str(e)}")
            raise
    
    async def create_user(self, user_data: dict):
        """Create user with default permission level and caching support"""
        try:
            user_data["type"] = "user"

            # Set default permission if not specified - using proper PermissionLevel.USER now
            if "permission" not in user_data:
                user_data["permission"] = PermissionLevel.USER

            # Add permission tracking fields
            user_data["permission_changed_at"] = datetime.now(timezone.utc).isoformat()
            user_data["permission_changed_by"] = "system"
            user_data["permission_history"] = []
            user_data["is_active"] = True

            created_user = self.auth_container.create_item(body=user_data)

            # Cache the user's permission
            await self._permission_cache.set_user_permission(
                created_user["id"], created_user["permission"]
            )

            self.logger.info(f"User created with permission {created_user['permission']}: {created_user['id']}")
            return created_user

        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            raise
    
    # Other methods follow similar pattern of using the injected permission cache
    # ...
```

### 6. Integration Tests

**Create `tests/test_permission_system.py`:**
```python
import pytest
from fastapi.testclient import TestClient
import asyncio
from unittest.mock import patch, MagicMock

from app.models.permissions import PermissionLevel
from app.utils.permission_cache import InMemoryPermissionCache
from app.services.permissions import PermissionService
from app.core.config import CosmosDB

# Mock database for testing
class MockCosmosDB:
    def __init__(self):
        self.users = {
            "user1": {"id": "user1", "permission": PermissionLevel.USER, "email": "user@example.com"},
            "editor1": {"id": "editor1", "permission": PermissionLevel.EDITOR, "email": "editor@example.com"},
            "admin1": {"id": "admin1", "permission": PermissionLevel.ADMIN, "email": "admin@example.com"},
        }
    
    async def get_user_by_id(self, user_id):
        return self.users.get(user_id)
    
    # Other methods as needed

@pytest.fixture
def permission_cache():
    cache = InMemoryPermissionCache()
    return cache

@pytest.fixture
def permission_service(permission_cache):
    return PermissionService(permission_cache)

@pytest.fixture
def mock_db():
    return MockCosmosDB()

class TestPermissionSystem:
    @pytest.mark.asyncio
    async def test_permission_hierarchy(self, permission_service):
        # Test permission hierarchy checks
        assert permission_service.has_permission_level(PermissionLevel.ADMIN, PermissionLevel.USER) == True
        assert permission_service.has_permission_level(PermissionLevel.ADMIN, PermissionLevel.EDITOR) == True
        assert permission_service.has_permission_level(PermissionLevel.ADMIN, PermissionLevel.ADMIN) == True
        
        assert permission_service.has_permission_level(PermissionLevel.EDITOR, PermissionLevel.USER) == True
        assert permission_service.has_permission_level(PermissionLevel.EDITOR, PermissionLevel.EDITOR) == True
        assert permission_service.has_permission_level(PermissionLevel.EDITOR, PermissionLevel.ADMIN) == False
        
        assert permission_service.has_permission_level(PermissionLevel.USER, PermissionLevel.USER) == True
        assert permission_service.has_permission_level(PermissionLevel.USER, PermissionLevel.EDITOR) == False
        assert permission_service.has_permission_level(PermissionLevel.USER, PermissionLevel.ADMIN) == False
    
    @pytest.mark.asyncio
    async def test_permission_cache(self, permission_cache):
        # Test basic cache operations
        await permission_cache.set_user_permission("test_user", PermissionLevel.ADMIN)
        result = await permission_cache.get_user_permission("test_user")
        assert result == PermissionLevel.ADMIN
        
        # Test cache invalidation
        await permission_cache.invalidate_user_cache("test_user")
        result = await permission_cache.get_user_permission("test_user")
        assert result is None
    
    # Add more tests as needed
```

### 7. Migration Plan

**Step 1: Create the new models and utils**
- Create `app/models/permissions.py`
- Create `app/core/settings.py`
- Update `app/utils/permission_cache.py`
- Create `app/services/permissions.py`

**Step 2: Update configuration handling**
- Update `main.py` to use the new settings
- Create configuration factory functions

**Step 3: Refactor CosmosDB class**
- Update `app/core/config.py` to use the new Permission cache
- Ensure dependency injection is used
- Use the PermissionLevel enum everywhere

**Step 4: Update endpoints**
- Refactor all endpoints to use the new permission services
- Ensure proper RESTful conventions
- Update error handling

**Step 5: Remove legacy code**
- Remove `SimplePermissionCache` from `config.py`
- Remove duplicate permission checking logic
- Update import statements throughout the codebase

**Step 6: Test thoroughly**
- Run unit and integration tests 
- Test all endpoints and permission checks
- Verify cache is working correctly

## Permission System Documentation

### Overview

The permission system is hierarchical with three levels:

1. **User** - Basic access to own content and shared resources
2. **Editor** - Extended access to create templates and edit shared content
3. **Admin** - Full system access including user management

### Implementation Components

#### 1. Permission Models
- `PermissionLevel` enum defines the available permission levels
- `PERMISSION_HIERARCHY` maps each level to a numeric value for comparison
- `PERMISSION_CAPABILITIES` maps each level to specific capabilities

#### 2. Permission Cache
- Abstract `BasePermissionCache` class defines the caching interface
- `InMemoryPermissionCache` provides a lightweight implementation for development
- Optional `RedisPermissionCache` could be implemented for production environments
- Cache-first strategy with database fallback ensures performance

#### 3. Permission Service
- Central service for permission checks and validation
- Provides decorators for securing endpoints
- Offers FastAPI dependencies for permission requirements
- Implements hierarchical permission checking

#### 4. Integration with FastAPI
- OAuth2 authentication flow
- Permission-based dependencies
- Proper HTTP status codes for authorization failures

### Usage Examples

**1. Securing an endpoint with permission decorators:**
```python
@router.get("/admin/reports")
@require_admin_permission
async def get_admin_reports(current_user: Dict[str, Any] = Depends(get_current_user)):
    # Only admins can access this endpoint
    return {"reports": []}
```

**2. Using permission dependencies:**
```python
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: str = Depends(require_admin)
):
    # Only admins can delete users
    pass
```

**3. Checking permissions manually:**
```python
# In a service or utility function
user_permission = await permission_service.get_user_permission(user_id)
if permission_service.has_permission_level(user_permission, PermissionLevel.EDITOR):
    # User has at least editor permissions
    pass
else:
    # User does not have sufficient permissions
    pass
```

**4. Checking specific capabilities:**
```python
user_permission = await permission_service.get_user_permission(user_id)
capabilities = permission_service.get_user_capabilities(user_permission)

if capabilities["can_create_templates"]:
    # User can create templates
    pass
```

## Integration with Existing Code

This revamp approach is designed to integrate smoothly with the existing codebase while gradually improving it. Here's how the integration will work:

### Backwards Compatibility

1. **Permission Middleware Compatibility**
   - The new `PermissionService` implements the same interface as the current `PermissionChecker`
   - Existing decorators like `require_admin_permission` will point to new implementations but keep the same signatures
   - All existing endpoints will continue to work without modification

2. **Cache Integration**
   - A backward compatibility layer ensures the existing cache calls still work
   - Old `SimplePermissionCache` methods will be mapped to the new unified cache

3. **Gradual Migration Example**

   ```python
   # In app/middleware/permission_middleware.py
   
   # Import the new service, but keep the original interface
   from app.services.permissions import permission_service, PermissionLevel
   
   # Update but keep the same function signature for existing endpoints
   async def require_admin(current_user_id: str = Depends(get_current_user_id)) -> str:
       return await permission_service.require_admin(current_user_id)
   ```

### Migration Path for Existing Components

1. **Existing Endpoints**: No immediate changes needed; can be migrated one by one

2. **CosmosDB Usage**:
   ```python
   # Old pattern (still works)
   config = AppConfig()
   cosmos_db = CosmosDB(config)
   
   # New pattern (preferred for new code)
   settings = get_settings()
   permission_cache = get_permission_cache()
   cosmos_db = CosmosDB(settings, permission_cache)
   ```

3. **Mixed Cache/DB Approach**:
   - Current methods that mix cache and DB access will be updated to use a consistent pattern
   - New pattern will always check cache first, fall back to DB, then update cache

### Implementation Timeline

1. **Phase 1: Core Infrastructure** (1-2 days)
   - Add `models/permissions.py` with the standardized Enum
   - Add `core/settings.py` for configuration
   - Implement the unified `permission_cache.py`

2. **Phase 2: Service Layer** (1 day)
   - Implement `services/permissions.py`
   - Add backward compatibility layers

3. **Phase 3: Gradual Migration** (2-3 days)
   - Update CosmosDB class to use the new permission system
   - Add tests to verify functionality

4. **Phase 4: Endpoint Updates** (ongoing)
   - Gradually update endpoints to use the new system
   - Remove deprecated code when no longer referenced

This phased approach ensures minimal disruption to your existing code while improving the architecture over time.

## Frontend Integration

The backend permission system changes will require minimal updates to the frontend:

1. **Permission Types**: Update TypeScript types to match the standardized permission levels
   ```typescript
   export enum PermissionLevel {
     USER = "User",
     EDITOR = "Editor",
     ADMIN = "Admin"
   }
   ```

2. **Permission Checking**: Frontend components that check permissions will continue to work as expected

3. **New Capabilities**: The capabilities system allows for more granular permission checks:
   ```typescript
   // Before
   if (userPermission === "Admin") {
     // show admin features
   }
   
   // After - more granular
   if (capabilities.can_manage_users) {
     // show user management UI
   }
   ```

4. **API Responses**: The API response format will remain consistent, so most frontend code won't need changes

## Conclusion

This revamp will improve the structure, maintainability, and reliability of the permission system. By centralizing configuration, standardizing permission levels, and implementing a cache-first approach, we'll achieve better performance and code clarity while following RESTful best practices. The integration approach ensures minimal disruption to existing functionality while providing a clear path for improvements.