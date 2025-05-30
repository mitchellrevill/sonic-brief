
import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class PermissionCache:
    """
    In-memory caching system for user permissions and access control.
    Provides efficient caching with TTL, batch operations, and cache invalidation.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 300):
        """
        Initialize permission cache.
        
        Args:
            redis_url: Ignored - kept for compatibility
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.key_prefix = "permission:"
        
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry has expired."""
        return time.time() > entry.get('expires_at', 0)
    
    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [key for key, entry in self.cache.items() if current_time > entry.get('expires_at', 0)]
        for key in expired_keys:
            del self.cache[key]
    
    def _set_with_ttl(self, key: str, value: Any, ttl: int):
        """Set cache entry with TTL."""
        expires_at = time.time() + ttl
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
    
    def _get_if_valid(self, key: str) -> Optional[Any]:
        """Get cache entry if not expired."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if self._is_expired(entry):
            del self.cache[key]
            return None
        
        return entry['value']
        
    # BASIC PERMISSION CACHING
    
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """Get cached user permission."""
        try:
            key = f"{self.key_prefix}user:{user_id}"
            permission = self._get_if_valid(key)
            if permission:
                logger.debug(f"Cache hit for user {user_id}: {permission}")
                return permission
            logger.debug(f"Cache miss for user {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting cached permission for user {user_id}: {e}")
            return None
    
    async def set_user_permission(self, user_id: str, permission: str, ttl: Optional[int] = None) -> bool:
        """Cache user permission with TTL."""
        try:
            key = f"{self.key_prefix}user:{user_id}"
            ttl = ttl or self.default_ttl
            self._set_with_ttl(key, permission, ttl)
            logger.debug(f"Cached permission for user {user_id}: {permission} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error caching permission for user {user_id}: {e}")
            return False
    
    async def delete_user_permission(self, user_id: str) -> bool:
        """Remove user permission from cache."""
        try:
            key = f"{self.key_prefix}user:{user_id}"
            deleted = key in self.cache
            if deleted:
                del self.cache[key]
            logger.debug(f"Deleted cached permission for user {user_id}: {deleted}")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting cached permission for user {user_id}: {e}")
            return False
    
    # BATCH OPERATIONS
    
    async def get_multiple_permissions(self, user_ids: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple user permissions in a single operation."""
        try:
            if not user_ids:
                return {}
            
            self._cleanup_expired()
            
            result = {}
            cache_hits = 0
            
            for user_id in user_ids:
                key = f"{self.key_prefix}user:{user_id}"
                permission = self._get_if_valid(key)
                result[user_id] = permission
                if permission is not None:
                    cache_hits += 1
            
            logger.debug(f"Batch permission lookup: {cache_hits}/{len(user_ids)} cache hits")
            
            return result
        except Exception as e:
            logger.error(f"Error getting multiple cached permissions: {e}")
            return {user_id: None for user_id in user_ids}
    
    async def set_multiple_permissions(self, user_permissions: Dict[str, str], ttl: Optional[int] = None) -> bool:
        """Set multiple user permissions in a single operation."""
        try:
            if not user_permissions:
                return True
            
            ttl = ttl or self.default_ttl
            
            for user_id, permission in user_permissions.items():
                key = f"{self.key_prefix}user:{user_id}"
                self._set_with_ttl(key, permission, ttl)
            
            logger.debug(f"Batch cached {len(user_permissions)} permissions (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error batch caching permissions: {e}")
            return False
    
    # PERMISSION GROUPS AND STATS CACHING
    
    async def get_permission_stats(self) -> Optional[Dict[str, Any]]:
        """Get cached permission statistics."""
        try:
            key = f"{self.key_prefix}stats"
            stats = self._get_if_valid(key)
            if stats:
                return stats
            return None
        except Exception as e:
            logger.error(f"Error getting cached permission stats: {e}")
            return None
    
    async def set_permission_stats(self, stats: Dict[str, Any], ttl: int = 600) -> bool:
        """Cache permission statistics (default 10 minutes TTL)."""
        try:
            key = f"{self.key_prefix}stats"
            self._set_with_ttl(key, stats, ttl)
            logger.debug(f"Cached permission stats (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error caching permission stats: {e}")
            return False
    
    async def get_users_by_permission(self, permission_level: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached list of users by permission level."""
        try:
            key = f"{self.key_prefix}users_by:{permission_level}"
            users = self._get_if_valid(key)
            if users:
                return users
            return None
        except Exception as e:
            logger.error(f"Error getting cached users by permission {permission_level}: {e}")
            return None
    
    async def set_users_by_permission(self, permission_level: str, users: List[Dict[str, Any]], ttl: int = 300) -> bool:
        """Cache list of users by permission level."""
        try:
            key = f"{self.key_prefix}users_by:{permission_level}"
            self._set_with_ttl(key, users, ttl)
            logger.debug(f"Cached {len(users)} users for permission {permission_level} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error caching users by permission {permission_level}: {e}")
            return False
    
    # RESOURCE ACCESS CACHING
    
    async def get_user_accessible_resources(self, user_id: str, resource_type: str = "all") -> Optional[List[str]]:
        """Get cached list of resource IDs accessible to user."""
        try:
            key = f"{self.key_prefix}resources:{user_id}:{resource_type}"
            resources = self._get_if_valid(key)
            if resources:
                return resources
            return None
        except Exception as e:
            logger.error(f"Error getting cached accessible resources for user {user_id}: {e}")
            return None
    
    async def set_user_accessible_resources(self, user_id: str, resource_ids: List[str], resource_type: str = "all", ttl: int = 600) -> bool:
        """Cache list of resource IDs accessible to user."""
        try:
            key = f"{self.key_prefix}resources:{user_id}:{resource_type}"
            self._set_with_ttl(key, resource_ids, ttl)
            logger.debug(f"Cached {len(resource_ids)} accessible resources for user {user_id} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error caching accessible resources for user {user_id}: {e}")
            return False
    
    # CACHE INVALIDATION
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate all cached data for a specific user."""
        try:
            patterns = [
                f"{self.key_prefix}user:{user_id}",
                f"{self.key_prefix}resources:{user_id}:",
            ]
            
            deleted_count = 0
            keys_to_delete = []
            
            for pattern in patterns:
                if pattern.endswith(':'):
                    # Find keys that start with the pattern
                    keys_to_delete.extend([key for key in self.cache.keys() if key.startswith(pattern)])
                else:
                    # Exact match
                    if pattern in self.cache:
                        keys_to_delete.append(pattern)
            
            for key in keys_to_delete:
                if key in self.cache:
                    del self.cache[key]
                    deleted_count += 1
            
            logger.debug(f"Invalidated {deleted_count} cache entries for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {e}")
            return False
    
    async def invalidate_permission_level_cache(self, permission_level: str) -> bool:
        """Invalidate cached data for a specific permission level."""
        try:
            keys_to_delete = [
                f"{self.key_prefix}users_by:{permission_level}",
                f"{self.key_prefix}stats",
            ]
            
            deleted_count = 0
            for key in keys_to_delete:
                if key in self.cache:
                    del self.cache[key]
                    deleted_count += 1
            
            logger.debug(f"Invalidated {deleted_count} cache entries for permission level {permission_level}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for permission level {permission_level}: {e}")
            return False
    
    async def invalidate_all_permission_cache(self) -> bool:
        """Invalidate all permission-related cache."""
        try:
            keys_to_delete = [key for key in self.cache.keys() if key.startswith(self.key_prefix)]
            deleted_count = len(keys_to_delete)
            
            for key in keys_to_delete:
                del self.cache[key]
            
            logger.info(f"Invalidated all permission cache: {deleted_count} entries deleted")
            return True
        except Exception as e:
            logger.error(f"Error invalidating all permission cache: {e}")
            return False
    
    # CACHE STATISTICS AND MONITORING
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        try:
            self._cleanup_expired()
            permission_keys = [key for key in self.cache.keys() if key.startswith(self.key_prefix)]
            
            # Calculate memory usage estimate
            total_size = 0
            for key, entry in self.cache.items():
                if key.startswith(self.key_prefix):
                    # Rough estimate of memory usage
                    total_size += len(str(key)) + len(str(entry.get('value', '')))
            
            return {
                "total_permission_keys": len(permission_keys),
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

# USAGE EXAMPLES

# Initialize cache
permission_cache = PermissionCache()

# Decorator usage example
@permission_cache.cache_permission_check(ttl=600)
async def get_user_permission_from_db(user_id: str) -> Optional[str]:
    """Example function that gets permission from database with automatic caching."""
    # This would normally query your Cosmos DB
    # For demonstration purposes:
    pass

# Integration with FastAPI dependency
async def get_cached_user_permission(user_id: str) -> Optional[str]:
    """Get user permission with caching fallback."""
    # Try cache first
    permission = await permission_cache.get_user_permission(user_id)
    if permission:
        return permission
    
    # Fallback to database
    # cosmos_db = CosmosDB()
    # user = await cosmos_db.get_user_by_id(user_id)
    # if user:
    #     permission = user.get("permission", "Viewer")
    #     await permission_cache.set_user_permission(user_id, permission)
    #     return permission
    
    return None

# Cache warming function
async def warm_permission_cache(user_ids: List[str]):
    """Pre-populate cache with frequently accessed user permissions."""
    try:
        # Get permissions from database
        # cosmos_db = CosmosDB()
        # permissions = await cosmos_db.get_multiple_user_permissions(user_ids)
        
        # Cache them all at once
        # await permission_cache.set_multiple_permissions(permissions)
        
        logger.info(f"Warmed permission cache for {len(user_ids)} users")
    except Exception as e:
        logger.error(f"Error warming permission cache: {e}")

# Background cache maintenance
async def maintain_permission_cache():
    """Background task to maintain cache health."""
    try:
        # Get cache statistics
        cache_info = await permission_cache.get_cache_info()
        logger.info(f"Permission cache maintenance: {cache_info}")
        
        # Optionally refresh frequently accessed permissions
        # Could implement LRU tracking here
        
    except Exception as e:
        logger.error(f"Error in cache maintenance: {e}")

# Configuration for different environments
class CacheConfig:
    DEVELOPMENT = {
        "default_ttl": 300,  # 5 minutes
    }
    
    PRODUCTION = {
        "default_ttl": 600,  # 10 minutes
    }
    
    TESTING = {
        "default_ttl": 60,   # 1 minute
    }
