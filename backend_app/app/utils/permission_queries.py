# Optimized Cosmos DB Permission Queries
import asyncio
from typing import List, Dict, Any, Optional
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
import time
from functools import lru_cache
import json
import logging
from app.utils.permission_cache import get_permission_cache
from app.models.permissions import PermissionLevel, PERMISSION_HIERARCHY

logger = logging.getLogger(__name__)

class PermissionQueryOptimizer:
    """
    Optimized queries for permission-based operations in Cosmos DB.
    Includes caching, indexing strategies, and efficient query patterns.
    """
    
    def __init__(self, cosmos_client: CosmosClient = None, database_name: str = None, container_name: str = None):
        """Initialize with optional parameters for dependency injection"""
        self.client = cosmos_client
        self.database = self.client.get_database_client(database_name) if cosmos_client and database_name else None
        self.container = self.database.get_container_client(container_name) if self.database and container_name else None
        self._permission_cache = get_permission_cache()
        self.logger = logging.getLogger(__name__)
    
    def build_user_permission_query(self, user_id: str) -> tuple[str, List[Dict[str, Any]]]:
        """
        Build optimized query for getting user permission
        
        Args:
            user_id: The user ID to query
            
        Returns:
            Tuple of (query_string, parameters)
        """
        query = "SELECT c.permission FROM c WHERE c.id = @user_id AND c.type = 'user'"
        parameters = [{"name": "@user_id", "value": user_id}]
        return query, parameters
    
    def build_users_by_permission_query(self, permission: str, limit: Optional[int] = None) -> tuple[str, List[Dict[str, Any]]]:
        """
        Build optimized query for getting users by permission level
        
        Args:
            permission: The permission level to filter by
            limit: Optional limit on number of results
            
        Returns:
            Tuple of (query_string, parameters)
        """
        query = "SELECT c.id, c.email, c.permission, c.created_at FROM c WHERE c.permission = @permission AND c.type = 'user'"
        if limit:
            query += f" OFFSET 0 LIMIT {limit}"
            
        parameters = [{"name": "@permission", "value": permission}]
        return query, parameters
    
    async def get_permission_counts(self) -> Dict[str, int]:
        """
        Get count of users for each permission level.
        Optimized aggregation query.
        """
        query = """
        SELECT u.permission, COUNT(1) as count
        FROM users u
        GROUP BY u.permission
        """
        
        items = list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        return {item['permission']: item['count'] for item in items}
    
    async def check_user_permission_cached(self, user_id: str) -> Optional[str]:
        """
        Check user permission with caching for frequently accessed users.
        """
        cache_key = f"permission_{user_id}"
        
        # Check cache first
        cached_data = self._permission_cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Query from database
        try:
            user = self.container.read_item(item=user_id, partition_key=user_id)
            permission = user.get('permission', 'Viewer')
            
            # Cache the result
            self._permission_cache.set(cache_key, permission)
            
            return permission
        except CosmosResourceNotFoundError:
            return None
    
    async def bulk_check_permissions(self, user_ids: List[str]) -> Dict[str, str]:
        """
        Efficiently check permissions for multiple users in a single query.
        """
        if not user_ids:
            return {}
        
        # Create IN clause for bulk query
        user_ids_str = ', '.join([f"'{user_id}'" for user_id in user_ids])
        
        query = f"""
        SELECT u.id, u.permission
        FROM users u
        WHERE u.id IN ({user_ids_str})
        """
        
        items = list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        return {item['id']: item.get('permission', 'Viewer') for item in items}
    
    # 2. PERMISSION-BASED RESOURCE QUERIES
    
    async def get_user_accessible_resources(self, user_permission: str, resource_type: str = None) -> List[Dict]:
        """
        Get resources accessible to a user based on their permission level.
        Assumes resources have a 'min_permission_required' field.
        """
        permission_hierarchy = {"Viewer": 1, "User": 2, "Admin": 3}
        user_level = permission_hierarchy.get(user_permission, 1)
        
        # Build query based on permission hierarchy
        base_query = """
        SELECT r.id, r.name, r.type, r.min_permission_required, r.created_at
        FROM resources r
        WHERE (
            r.min_permission_required = 'Viewer' 
            OR (r.min_permission_required = 'User' AND @user_level >= 2)
            OR (r.min_permission_required = 'Admin' AND @user_level >= 3)
        )
        """
        
        if resource_type:
            base_query += " AND r.type = @resource_type"
        
        base_query += " ORDER BY r.created_at DESC"
        
        parameters = [{"name": "@user_level", "value": user_level}]
        if resource_type:
            parameters.append({"name": "@resource_type", "value": resource_type})
        
        items = list(self.container.query_items(
            query=base_query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        return items
    
    # 3. ADVANCED PERMISSION PATTERNS
    
    async def get_users_with_elevated_permissions(self, base_permission: str) -> List[Dict]:
        """
        Get users with permissions higher than the specified base permission.
        """
        permission_hierarchy = {"Viewer": 1, "User": 2, "Admin": 3}
        base_level = permission_hierarchy.get(base_permission, 1)
        
        elevated_permissions = [
            perm for perm, level in permission_hierarchy.items() 
            if level > base_level
        ]
        
        if not elevated_permissions:
            return []
        
        permissions_str = ', '.join([f"'{perm}'" for perm in elevated_permissions])
        
        query = f"""
        SELECT u.id, u.email, u.permission, u.first_name, u.last_name
        FROM users u
        WHERE u.permission IN ({permissions_str})
        ORDER BY u.permission DESC, u.email ASC
        """
        
        items = list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        return items
    
    async def audit_permission_changes(self, days_back: int = 30) -> List[Dict]:
        """
        Audit recent permission changes (requires audit trail in documents).
        """
        import datetime
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
        cutoff_timestamp = cutoff_date.isoformat()
        
        query = """
        SELECT u.id, u.email, u.permission, u.permission_changed_at, u.permission_changed_by
        FROM users u
        WHERE u.permission_changed_at >= @cutoff_date
        ORDER BY u.permission_changed_at DESC
        """
        
        parameters = [{"name": "@cutoff_date", "value": cutoff_timestamp}]
        
        items = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        return items
    
    # 4. CACHING UTILITIES
    
    def clear_permission_cache(self, user_id: str = None):
        """Clear permission cache for specific user or all users."""
        if user_id:
            cache_key = f"permission_{user_id}"
            self._permission_cache.delete(cache_key)
        else:
            self._permission_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        # Note: Implementing cache stats would depend on the underlying cache implementation
        # For example, if using Redis, you could query Redis for info
        return {
            "note": "Cache statistics implementation depends on the underlying cache system."
        }

# Usage Examples:
async def example_usage():
    """Example usage of the permission query optimizer."""
    
    # Initialize (you would use your existing cosmos client)
    # optimizer = PermissionQueryOptimizer(cosmos_client, "your_db", "users")
    
    # Get all admin users
    # admins = await optimizer.get_users_by_permission("Admin")
    
    # Get permission distribution
    # counts = await optimizer.get_permission_counts()
    # print(f"Permission distribution: {counts}")
    
    # Check permission with caching
    # user_permission = await optimizer.check_user_permission_cached("user123")
    
    # Bulk permission check
    # permissions = await optimizer.bulk_check_permissions(["user1", "user2", "user3"])
    
    pass
