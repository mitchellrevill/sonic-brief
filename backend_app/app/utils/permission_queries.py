# Optimized Cosmos DB Permission Queries
import asyncio
from typing import List, Dict, Any, Optional
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
import time
from functools import lru_cache
import json

class PermissionQueryOptimizer:
    """
    Optimized queries for permission-based operations in Cosmos DB.
    Includes caching, indexing strategies, and efficient query patterns.
    """
    
    def __init__(self, cosmos_client: CosmosClient, database_name: str, container_name: str):
        self.client = cosmos_client
        self.database = self.client.get_database_client(database_name)
        self.container = self.database.get_container_client(container_name)
        self._permission_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    # 1. OPTIMIZED PERMISSION QUERIES
    
    async def get_users_by_permission(self, permission_level: str, limit: int = 100) -> List[Dict]:
        """
        Efficiently query users by permission level.
        Uses indexed queries for optimal performance.
        """
        query = """
        SELECT u.id, u.email, u.first_name, u.last_name, u.permission, u.created_at
        FROM users u 
        WHERE u.permission = @permission_level
        ORDER BY u.created_at DESC
        OFFSET 0 LIMIT @limit
        """
        
        parameters = [
            {"name": "@permission_level", "value": permission_level},
            {"name": "@limit", "value": limit}
        ]
        
        items = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True,
            max_item_count=limit
        ))
        
        return items
    
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
        current_time = time.time()
        
        # Check cache first
        if cache_key in self._permission_cache:
            cached_data = self._permission_cache[cache_key]
            if current_time - cached_data['timestamp'] < self._cache_ttl:
                return cached_data['permission']
        
        # Query from database
        try:
            user = self.container.read_item(item=user_id, partition_key=user_id)
            permission = user.get('permission', 'Viewer')
            
            # Cache the result
            self._permission_cache[cache_key] = {
                'permission': permission,
                'timestamp': current_time
            }
            
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
            self._permission_cache.pop(cache_key, None)
        else:
            self._permission_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1 for data in self._permission_cache.values()
            if current_time - data['timestamp'] < self._cache_ttl
        )
        
        return {
            "total_entries": len(self._permission_cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._permission_cache) - valid_entries,
            "cache_ttl_seconds": self._cache_ttl
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
