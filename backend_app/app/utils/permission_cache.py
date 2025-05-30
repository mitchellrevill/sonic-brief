# Redis-based Permission Caching Strategy
import redis
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class PermissionCache:
    """
    Redis-based caching system for user permissions and access control.
    Provides efficient caching with TTL, batch operations, and cache invalidation.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 300):
        """
        Initialize permission cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.default_ttl = default_ttl
        self.key_prefix = "permission:"
        
    # BASIC PERMISSION CACHING
    
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """Get cached user permission."""
        try:
            key = f"{self.key_prefix}user:{user_id}"
            permission = self.redis_client.get(key)
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
            self.redis_client.setex(key, ttl, permission)
            logger.debug(f"Cached permission for user {user_id}: {permission} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error caching permission for user {user_id}: {e}")
            return False
    
    async def delete_user_permission(self, user_id: str) -> bool:
        """Remove user permission from cache."""
        try:
            key = f"{self.key_prefix}user:{user_id}"
            deleted = self.redis_client.delete(key)
            logger.debug(f"Deleted cached permission for user {user_id}: {bool(deleted)}")
            return bool(deleted)
        except Exception as e:
            logger.error(f"Error deleting cached permission for user {user_id}: {e}")
            return False
    
    # BATCH OPERATIONS
    
    async def get_multiple_permissions(self, user_ids: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple user permissions in a single operation."""
        try:
            if not user_ids:
                return {}
            
            keys = [f"{self.key_prefix}user:{user_id}" for user_id in user_ids]
            permissions = self.redis_client.mget(keys)
            
            result = {}
            for user_id, permission in zip(user_ids, permissions):
                result[user_id] = permission
            
            cache_hits = sum(1 for p in permissions if p is not None)
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
            pipe = self.redis_client.pipeline()
            
            for user_id, permission in user_permissions.items():
                key = f"{self.key_prefix}user:{user_id}"
                pipe.setex(key, ttl, permission)
            
            pipe.execute()
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
            stats_json = self.redis_client.get(key)
            if stats_json:
                return json.loads(stats_json)
            return None
        except Exception as e:
            logger.error(f"Error getting cached permission stats: {e}")
            return None
    
    async def set_permission_stats(self, stats: Dict[str, Any], ttl: int = 600) -> bool:
        """Cache permission statistics (default 10 minutes TTL)."""
        try:
            key = f"{self.key_prefix}stats"
            stats_json = json.dumps(stats)
            self.redis_client.setex(key, ttl, stats_json)
            logger.debug(f"Cached permission stats (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error caching permission stats: {e}")
            return False
    
    async def get_users_by_permission(self, permission_level: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached list of users by permission level."""
        try:
            key = f"{self.key_prefix}users_by:{permission_level}"
            users_json = self.redis_client.get(key)
            if users_json:
                return json.loads(users_json)
            return None
        except Exception as e:
            logger.error(f"Error getting cached users by permission {permission_level}: {e}")
            return None
    
    async def set_users_by_permission(self, permission_level: str, users: List[Dict[str, Any]], ttl: int = 300) -> bool:
        """Cache list of users by permission level."""
        try:
            key = f"{self.key_prefix}users_by:{permission_level}"
            users_json = json.dumps(users)
            self.redis_client.setex(key, ttl, users_json)
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
            resources_json = self.redis_client.get(key)
            if resources_json:
                return json.loads(resources_json)
            return None
        except Exception as e:
            logger.error(f"Error getting cached accessible resources for user {user_id}: {e}")
            return None
    
    async def set_user_accessible_resources(self, user_id: str, resource_ids: List[str], resource_type: str = "all", ttl: int = 600) -> bool:
        """Cache list of resource IDs accessible to user."""
        try:
            key = f"{self.key_prefix}resources:{user_id}:{resource_type}"
            resources_json = json.dumps(resource_ids)
            self.redis_client.setex(key, ttl, resources_json)
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
                f"{self.key_prefix}resources:{user_id}:*",
            ]
            
            deleted_count = 0
            for pattern in patterns:
                if "*" in pattern:
                    # Use scan for pattern matching
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        deleted_count += self.redis_client.delete(*keys)
                else:
                    deleted_count += self.redis_client.delete(pattern)
            
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
            
            deleted_count = self.redis_client.delete(*keys_to_delete)
            logger.debug(f"Invalidated {deleted_count} cache entries for permission level {permission_level}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for permission level {permission_level}: {e}")
            return False
    
    async def invalidate_all_permission_cache(self) -> bool:
        """Invalidate all permission-related cache."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"Invalidated all permission cache: {deleted_count} entries deleted")
            return True
        except Exception as e:
            logger.error(f"Error invalidating all permission cache: {e}")
            return False
    
    # CACHE STATISTICS AND MONITORING
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        try:
            info = self.redis_client.info()
            pattern = f"{self.key_prefix}*"
            permission_keys = self.redis_client.keys(pattern)
            
            return {
                "total_permission_keys": len(permission_keys),
                "redis_memory_used": info.get("used_memory_human"),
                "redis_memory_peak": info.get("used_memory_peak_human"),
                "redis_connected_clients": info.get("connected_clients"),
                "redis_total_commands_processed": info.get("total_commands_processed"),
                "permission_key_prefix": self.key_prefix,
                "default_ttl": self.default_ttl,
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
permission_cache = PermissionCache("redis://localhost:6379")

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
        "redis_url": "redis://localhost:6379",
        "default_ttl": 300,  # 5 minutes
    }
    
    PRODUCTION = {
        "redis_url": "redis://production-redis:6379",
        "default_ttl": 600,  # 10 minutes
    }
    
    TESTING = {
        "redis_url": "redis://localhost:6380",
        "default_ttl": 60,   # 1 minute
    }
