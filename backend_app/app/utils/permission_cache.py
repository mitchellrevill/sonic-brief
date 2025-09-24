from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
import time
import json
from functools import wraps

logger = logging.getLogger(__name__)

class BasePermissionCache(ABC):
    """Abstract base class for permission caching implementations"""
    @abstractmethod
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        pass
    @abstractmethod
    async def set_user_permission(self, user_id: str, permission: str, ttl: Optional[int] = None):
        pass
    @abstractmethod
    async def get_users_by_permission(self, permission: str) -> Optional[List[Dict[str, Any]]]:
        pass
    @abstractmethod
    async def set_users_by_permission(self, permission: str, users: List[Dict[str, Any]], ttl: Optional[int] = None):
        pass
    @abstractmethod
    async def invalidate_user_cache(self, user_id: str):
        pass
    @abstractmethod
    async def invalidate_permission_level_cache(self, permission: str):
        pass
    @abstractmethod
    async def get_multiple_permissions(self, user_ids: List[str]) -> Dict[str, Optional[str]]:
        pass
    @abstractmethod
    async def set_multiple_permissions(self, permissions: Dict[str, str], ttl: Optional[int] = None):
        pass
    @abstractmethod
    async def get_cache_info(self) -> Dict[str, Any]:
        pass

class InMemoryPermissionCache(BasePermissionCache):
    """In-memory implementation of permission cache."""
    def __init__(self, key_prefix: str = "permission:", default_ttl: int = 300):
        self.cache = {}
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        logger.info(f"Initialized in-memory permission cache with TTL: {self.default_ttl}s")
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        key = f"{self.key_prefix}user:{user_id}"
        entry = self.cache.get(key)
        if not entry:
            return None
        if time.time() > entry["expires"]:
            self.cache.pop(key, None)
            return None
        return entry["value"]
    async def set_user_permission(self, user_id: str, permission: str, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl
        key = f"{self.key_prefix}user:{user_id}"
        self.cache[key] = {
            "value": permission,
            "expires": time.time() + ttl
        }
    async def get_users_by_permission(self, permission: str) -> Optional[List[Dict[str, Any]]]:
        key = f"{self.key_prefix}permission_group:{permission}"
        entry = self.cache.get(key)
        if not entry:
            return None
        if time.time() > entry["expires"]:
            self.cache.pop(key, None)
            return None
        return entry["value"]
    async def set_users_by_permission(self, permission: str, users: List[Dict[str, Any]], ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl
        key = f"{self.key_prefix}permission_group:{permission}"
        self.cache[key] = {
            "value": users,
            "expires": time.time() + ttl
        }
    async def invalidate_user_cache(self, user_id: str):
        keys_to_remove = [key for key in self.cache.keys() if f"user:{user_id}" in key]
        for key in keys_to_remove:
            self.cache.pop(key, None)
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")
    async def invalidate_permission_level_cache(self, permission: str):
        keys_to_remove = [key for key in self.cache.keys() if f"permission_group:{permission}" in key]
        for key in keys_to_remove:
            self.cache.pop(key, None)
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for permission {permission}")
    async def get_multiple_permissions(self, user_ids: List[str]) -> Dict[str, Optional[str]]:
        result = {}
        for user_id in user_ids:
            result[user_id] = await self.get_user_permission(user_id)
        return result
    async def set_multiple_permissions(self, permissions: Dict[str, str], ttl: Optional[int] = None):
        for user_id, permission in permissions.items():
            await self.set_user_permission(user_id, permission, ttl)
    async def get_cache_info(self) -> Dict[str, Any]:
        try:
            current_time = time.time()
            permission_keys = [k for k in self.cache.keys() if k.startswith(self.key_prefix)]
            valid_entries = sum(1 for k in permission_keys if current_time <= self.cache[k]["expires"])
            total_size = 0
            for key in permission_keys:
                entry = self.cache[key]
                key_size = len(key)
                value_size = len(json.dumps(entry["value"])) if entry["value"] else 0
                entry_size = key_size + value_size + 16
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
    def cache_permission_check(self, ttl: Optional[int] = None):
        def decorator(func):
            @wraps(func)
            async def wrapper(user_id: str, *args, **kwargs):
                cached_result = await self.get_user_permission(user_id)
                if cached_result is not None:
                    return cached_result
                result = await func(user_id, *args, **kwargs)
                if result is not None:
                    await self.set_user_permission(user_id, result, ttl)
                return result
            return wrapper
        return decorator

def get_permission_cache(settings=None) -> BasePermissionCache:
    """
    Get a permission cache instance based on configuration.
    Falls back to in-memory cache if Redis is not available.
    """
    try:
        if settings is None:
            # Import here to avoid circular imports
            from app.core.config import get_config
            settings = get_config()
        
        cache_settings = settings.cache
        
        if cache_settings.cache_type.lower() == "redis" and cache_settings.redis_url:
            # Future implementation for Redis cache
            logger.warning("Redis cache requested but not implemented yet, falling back to in-memory cache")
            return InMemoryPermissionCache(
                key_prefix=cache_settings.key_prefix,
                default_ttl=cache_settings.default_ttl
            )
        else:
            return InMemoryPermissionCache(
                key_prefix=cache_settings.key_prefix,
                default_ttl=cache_settings.default_ttl
            )
    except Exception as e:
        logger.warning(f"Error initializing permission cache with settings: {e}, falling back to defaults")
        return InMemoryPermissionCache()

# Global cache instance (for backwards compatibility)
permission_cache = get_permission_cache()
