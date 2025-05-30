import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.identity import DefaultAzureCredential, CredentialUnavailableError
from azure.cosmos import PartitionKey
import azure.cosmos.cosmos_client as cosmos_client
from datetime import datetime, timezone
import asyncio

# Import permission utilities
from app.utils.permission_queries import PermissionQueryOptimizer

# Simple in-memory cache for permissions (Redis replacement)
class SimplePermissionCache:
    """Simple in-memory cache for permissions to replace Redis dependency"""
    
    def __init__(self):
        self._cache = {}
        import time
        self._time = time
    
    async def get_user_permission(self, user_id: str) -> Optional[str]:
        """Get cached user permission"""
        cache_key = f"user:{user_id}:permission"
        data = self._cache.get(cache_key)
        if data and self._time.time() - data['timestamp'] < 300:  # 5 min TTL
            return data['value']
        return None
    
    async def set_user_permission(self, user_id: str, permission: str):
        """Cache user permission"""
        cache_key = f"user:{user_id}:permission"
        self._cache[cache_key] = {
            'value': permission,
            'timestamp': self._time.time()
        }
    
    async def get_users_by_permission(self, permission: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached users by permission"""
        cache_key = f"permission:{permission}:users"
        data = self._cache.get(cache_key)
        if data and self._time.time() - data['timestamp'] < 300:
            return data['value']
        return None
    
    async def set_users_by_permission(self, permission: str, users: List[Dict[str, Any]]):
        """Cache users by permission"""
        cache_key = f"permission:{permission}:users"
        self._cache[cache_key] = {
            'value': users,
            'timestamp': self._time.time()
        }
    
    async def get_permission_stats(self) -> Optional[Dict[str, Any]]:
        """Get cached permission statistics"""
        cache_key = "permission:stats"
        data = self._cache.get(cache_key)
        if data and self._time.time() - data['timestamp'] < 300:
            return data['value']
        return None
    
    async def set_permission_stats(self, stats: Dict[str, Any]):
        """Cache permission statistics"""
        cache_key = "permission:stats"
        self._cache[cache_key] = {
            'value': stats,
            'timestamp': self._time.time()
        }
    
    async def get_multiple_permissions(self, user_ids: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple user permissions from cache"""
        result = {}
        for user_id in user_ids:
            result[user_id] = await self.get_user_permission(user_id)
        return result
    
    async def set_multiple_permissions(self, permissions: Dict[str, str]):
        """Set multiple user permissions in cache"""
        for user_id, permission in permissions.items():
            await self.set_user_permission(user_id, permission)
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        keys_to_remove = [key for key in self._cache.keys() if f"user:{user_id}" in key]
        for key in keys_to_remove:
            self._cache.pop(key, None)
    
    async def invalidate_permission_level_cache(self, permission: str):
        """Invalidate cache for a permission level"""
        keys_to_remove = [key for key in self._cache.keys() if f"permission:{permission}" in key]
        for key in keys_to_remove:
            self._cache.pop(key, None)

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Ensure logs are visible on the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def get_required_env_var(var_name: str) -> str:
    """Get a required environment variable or raise an error with a helpful message"""
    value = os.getenv(var_name)
    if not value:
        logger.error(f"Required environment variable {var_name} is not set")
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value


class StorageConfig:
    def __init__(self, account_url: str, recordings_container: str):
        self.account_url = account_url
        self.recordings_container = recordings_container


class AppConfig:
    def __init__(self):
        logger.debug("Initializing AppConfig")
        try:
            # Get the prefix first
            prefix = os.getenv("AZURE_COSMOS_DB_PREFIX", "voice_")

            # Initialize cosmos configuration
            self.cosmos = {
                "endpoint": get_required_env_var("AZURE_COSMOS_ENDPOINT"),
                "database": os.getenv("AZURE_COSMOS_DB", "VoiceDB"),
                "containers": {
                    "auth": f"{prefix}auth",
                    "jobs": f"{prefix}jobs",
                    "prompts": f"{prefix}prompts",
                },
            }
            logger.debug(f"Cosmos config initialized: {self.cosmos}")

            # Initialize auth configuration
            self.auth = {
                "jwt_secret_key": get_required_env_var("JWT_SECRET_KEY"),
                "jwt_algorithm": "HS256",
                "jwt_access_token_expire_minutes": int(
                    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
                ),
            }

            # Initialize storage configuration
            self.storage = StorageConfig(
                account_url=get_required_env_var("AZURE_STORAGE_ACCOUNT_URL"),
                recordings_container=get_required_env_var(
                    "AZURE_STORAGE_RECORDINGS_CONTAINER"
                ),
            )

            logger.debug("AppConfig initialization completed successfully")
        except Exception as e:
            logger.error(f"Error initializing AppConfig: {str(e)}")
            raise


class DatabaseError(Exception):
    """Custom exception for database errors"""

    pass


class CosmosDB:
    def __init__(self, config: AppConfig = None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.config = config

        # Always use DefaultAzureCredential
        try:
            credential = DefaultAzureCredential(logging_enable=True)
            self.logger.debug("DefaultAzureCredential initialized successfully")

        except CredentialUnavailableError as e:
            self.logger.error(f"Credential unavailable: {str(e)}")
            raise DatabaseError(
                "Failed to authenticate with Azure: Credential unavailable."
            )
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {str(e)}")
            raise DatabaseError(f"Authentication error: {str(e)}")

        try:
            self.client = cosmos_client.CosmosClient(
                url=config.cosmos["endpoint"], credential=credential
            )

            # Create database if it doesn't exist
            database_name = config.cosmos["database"]
            self.database = self.client.get_database_client(database_name)
            self.logger.info(f"Database {database_name} is ready")

            # Create containers if they don't exist
            containers = config.cosmos["containers"]

            # Auth container
            auth_container_name = containers["auth"]
            self.auth_container = self.database.get_container_client(
                auth_container_name
            )
            self.logger.info(f"Auth container {auth_container_name} is ready")

            # Jobs container
            jobs_container_name = containers["jobs"]
            self.jobs_container = self.database.get_container_client(
                jobs_container_name
            )
            self.logger.info(f"Jobs container {jobs_container_name} is ready")

            # Prompts container
            prompts_container_name = containers["prompts"]
            self.prompts_container = self.database.get_container_client(
                prompts_container_name
            )
            self.logger.info(f"Prompts container {prompts_container_name} is ready")

        except KeyError as e:
            self.logger.error(f"Missing configuration key: {str(e)}")
            raise
        except CosmosHttpResponseError as e:
            self.logger.error(f"Cosmos DB HTTP error: {str(e)}")
            raise DatabaseError(f"Cosmos DB error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error initializing Cosmos DB: {str(e)}")
            raise

        # Initialize permission utilities
        self._permission_optimizer = None
        self._permission_cache = None

    @property
    def permission_optimizer(self) -> PermissionQueryOptimizer:
        """Lazy initialization of permission query optimizer"""
        if self._permission_optimizer is None:
            self._permission_optimizer = PermissionQueryOptimizer(
                self.client,
                self.config.cosmos["database"],
                self.config.cosmos["containers"]["auth"],
            )
        return self._permission_optimizer

    @property
    def permission_cache(self) -> SimplePermissionCache:
        """Lazy initialization of permission cache"""
        if self._permission_cache is None:
            self._permission_cache = SimplePermissionCache()
        return self._permission_cache

    async def get_all_users(self):
        """Get all users from the auth container, regardless of type."""
        try:
            query = "SELECT * FROM c"
            users = list(
                self.auth_container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            )
            return users
        except Exception as e:
            self.logger.error(f"Error retrieving all users: {str(e)}")
            raise

    async def create_user(self, user_data: dict):
        """Create user with default permission level and caching support"""
        try:
            user_data["type"] = "user"

            # Set default permission if not specified
            if "permission" not in user_data:
                user_data["permission"] = "Viewer"  # Default permission level

            # Add permission tracking fields
            user_data["permission_changed_at"] = datetime.now(timezone.utc).isoformat()
            user_data["permission_changed_by"] = "system"
            user_data["permission_history"] = []
            user_data["is_active"] = True

            created_user = self.auth_container.create_item(body=user_data)

            # Cache the user's permission
            await self.permission_cache.set_user_permission(
                created_user["id"], created_user["permission"]
            )

            self.logger.info(f"User created with permission {created_user['permission']}: {created_user['id']}")
            return created_user

        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            raise

    async def update_user(self, user_id: str, update_data: dict):
        """Update user with permission change tracking and cache invalidation"""
        try:
            query = "SELECT * FROM c WHERE c.id = @id AND c.type = 'user'"
            parameters = [{"name": "@id", "value": user_id}]
            results = list(
                self.auth_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            if not results:
                self.logger.error(f"User with id {user_id} not found.")
                raise ValueError(f"User with id {user_id} not found.")

            user = results[0]
            old_permission = user.get("permission")

            # Update user data
            user.update(update_data)
            user["updated_at"] = datetime.now(timezone.utc).isoformat()

            updated_user = self.auth_container.upsert_item(body=user)

            # Handle permission changes
            new_permission = updated_user.get("permission")
            if old_permission != new_permission:
                # Update cache
                await self.permission_cache.set_user_permission(user_id, new_permission)

                # Invalidate related caches
                await self.permission_cache.invalidate_permission_level_cache(old_permission)
                await self.permission_cache.invalidate_permission_level_cache(new_permission)

                self.logger.info(f"Permission changed for user {user_id}: {old_permission} -> {new_permission}")

            return updated_user

        except Exception as e:
            self.logger.error(f"Error updating user: {str(e)}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID with permission caching"""
        try:
            # Try cache first for permission
            cached_permission = await self.permission_cache.get_user_permission(user_id)

            query = "SELECT * FROM c WHERE c.id = @id AND c.type = 'user'"
            parameters = [{"name": "@id", "value": user_id}]
            results = list(
                self.auth_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            if not results:
                return None

            user = results[0]

            # Update cache if permission wasn't cached or differs
            current_permission = user.get("permission", "Viewer")
            if cached_permission != current_permission:
                await self.permission_cache.set_user_permission(user_id, current_permission)

            return user

        except Exception as e:
            self.logger.error(f"Error getting user by id {user_id}: {str(e)}")
            raise

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address"""
        try:
            query = "SELECT * FROM c WHERE c.email = @email AND c.type = 'user'"
            parameters = [{"name": "@email", "value": email}]
            results = list(
                self.auth_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            
            if not results:
                return None
                
            user = results[0]
            
            # Update cache with user's permission
            user_id = user.get("id")
            permission = user.get("permission", "Viewer")
            if user_id:
                await self.permission_cache.set_user_permission(user_id, permission)
            
            return user
            
        except Exception as e:
            self.logger.error(f"Error getting user by email {email}: {str(e)}")
            raise

    # JOB-RELATED METHODS

    def create_job(self, job_data: dict) -> Dict[str, Any]:
        """Create a new job document"""
        try:
            # Ensure the job has the correct type
            job_data["type"] = "job"
            
            # Create the job in the jobs container
            created_job = self.jobs_container.create_item(body=job_data)
            self.logger.info(f"Job created successfully: {created_job['id']}")
            return created_job
            
        except Exception as e:
            self.logger.error(f"Error creating job: {str(e)}")
            raise

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        try:
            job = self.jobs_container.read_item(item=job_id, partition_key=job_id)
            return job if job else None
        except CosmosHttpResponseError as e:
            if e.status_code == 404:
                return None
            self.logger.error(f"Error getting job {job_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting job {job_id}: {str(e)}")
            raise

    def update_job(self, job_id: str, update_fields: dict) -> Dict[str, Any]:
        """Update job with new fields"""
        try:
            # Get the existing job
            job = self.get_job(job_id)
            if not job:
                raise ValueError(f"Job with id {job_id} not found")

            # Update job data
            job.update(update_fields)
            
            # Upsert the job back to the container
            updated_job = self.jobs_container.upsert_item(body=job)
            self.logger.info(f"Job updated successfully: {job_id}")
            return updated_job
            
        except Exception as e:
            self.logger.error(f"Error updating job {job_id}: {str(e)}")
            raise

    # PERMISSION-SPECIFIC QUERY METHODS

    async def get_users_by_permission_level(self, permission_level: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get users by permission level with caching"""
        try:
            # Try cache first
            cached_users = await self.permission_cache.get_users_by_permission(permission_level)
            if cached_users:
                return cached_users[:limit]

            # Query database
            users = await self.permission_optimizer.get_users_by_permission(permission_level, limit)

            # Cache results
            await self.permission_cache.set_users_by_permission(permission_level, users)

            return users

        except Exception as e:
            self.logger.error(f"Error getting users by permission {permission_level}: {str(e)}")
            raise

    async def get_permission_distribution(self) -> Dict[str, int]:
        """Get permission level distribution with caching"""
        try:
            # Try cache first
            cached_stats = await self.permission_cache.get_permission_stats()
            if cached_stats and "counts" in cached_stats:
                return cached_stats["counts"]

            # Query database
            counts = await self.permission_optimizer.get_permission_counts()

            # Cache results
            stats = {
                "counts": counts,
                "total_users": sum(counts.values()),
                "percentages": {
                    perm: round((count / sum(counts.values())) * 100, 2) if sum(counts.values()) > 0 else 0
                    for perm, count in counts.items()
                },
            }
            await self.permission_cache.set_permission_stats(stats)

            return counts

        except Exception as e:
            self.logger.error(f"Error getting permission distribution: {str(e)}")
            raise

    async def bulk_check_user_permissions(self, user_ids: List[str]) -> Dict[str, str]:
        """Efficiently check permissions for multiple users"""
        try:
            # Try cache first
            cached_permissions = await self.permission_cache.get_multiple_permissions(user_ids)

            # Find users not in cache
            missing_users = [uid for uid, perm in cached_permissions.items() if perm is None]

            if missing_users:
                # Query database for missing users
                db_permissions = await self.permission_optimizer.bulk_check_permissions(missing_users)

                # Update cache
                await self.permission_cache.set_multiple_permissions(db_permissions)

                # Merge results
                cached_permissions.update(db_permissions)

            # Remove None values and return only valid permissions
            return {uid: perm for uid, perm in cached_permissions.items() if perm is not None}

        except Exception as e:
            self.logger.error(f"Error bulk checking permissions: {str(e)}")
            raise

    async def deactivate_user(self, user_id: str, deactivated_by: str) -> Dict[str, Any]:
        """Deactivate user and clear caches"""
        try:
            update_data = {
                "is_active": False,
                "deactivated_at": datetime.now(timezone.utc).isoformat(),
                "deactivated_by": deactivated_by,
            }

            updated_user = await self.update_user(user_id, update_data)

            # Clear all caches for this user
            await self.permission_cache.invalidate_user_cache(user_id)

            self.logger.info(f"User {user_id} deactivated by {deactivated_by}")
            return updated_user

        except Exception as e:
            self.logger.error(f"Error deactivating user {user_id}: {str(e)}")
            raise

    async def get_user_permission_with_fallback(self, user_id: str) -> str:
        """Get user permission with cache fallback and default"""
        try:
            # Try cache first
            permission = await self.permission_cache.get_user_permission(user_id)
            if permission:
                return permission

            # Fallback to database
            user = await self.get_user_by_id(user_id)
            if user:
                permission = user.get("permission", "Viewer")
                # Cache for next time
                await self.permission_cache.set_user_permission(user_id, permission)
                return permission

            # Default fallback
            return "Viewer"

        except Exception as e:
            self.logger.error(f"Error getting user permission {user_id}: {str(e)}")
            return "Viewer"  # Safe default


# Create the config instance
config = AppConfig()
