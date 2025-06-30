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

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Don't add multiple handlers to prevent duplication
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

logger.setLevel(logging.INFO)


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
        logger.info("🚀 Starting AppConfig initialization...")
        try:
            # Get the prefix first
            prefix = os.getenv("AZURE_COSMOS_DB_PREFIX", "voice_")
            logger.info(f"Using Cosmos DB prefix: {prefix}")
            
            # Initialize cosmos configuration
            self.cosmos = {
                "endpoint": get_required_env_var("AZURE_COSMOS_ENDPOINT"),
                "database": os.getenv("AZURE_COSMOS_DB", "VoiceDB"),
                "containers": {
                    "auth": f"{prefix}auth",
                    "jobs": f"{prefix}jobs",
                    "prompts": f"{prefix}prompts",
                    # Analytics containers
                    "analytics": f"{prefix}analytics",
                    "events": f"{prefix}events",
                    "user_sessions": f"{prefix}user_sessions",
                },
            }
            logger.info(f"✓ Cosmos configuration initialized")

            # Initialize auth configuration
            self.auth = {
                "jwt_secret_key": get_required_env_var("JWT_SECRET_KEY"),
                "jwt_algorithm": "HS256",
                "jwt_access_token_expire_minutes": int(
                    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
                ),
            }
            logger.info("✓ Auth configuration initialized")

            # Initialize storage configuration
            self.storage = StorageConfig(
                account_url=get_required_env_var("AZURE_STORAGE_ACCOUNT_URL"),
                recordings_container=get_required_env_var(
                    "AZURE_STORAGE_RECORDINGS_CONTAINER"
                ),
            )
            logger.info("✓ Storage configuration initialized")

            # Initialize Azure Functions configuration
            self.azure_functions = {
                "base_url": os.getenv("AZURE_FUNCTIONS_BASE_URL", "http://localhost:7071"),
                "key": os.getenv("AZURE_FUNCTIONS_KEY", "")
            }
            logger.info("✓ Azure Functions configuration initialized")

            logger.info("✅ AppConfig initialization completed successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing AppConfig: {str(e)}")
            raise


class DatabaseError(Exception):
    """Custom exception for database errors"""
    pass


class CosmosDB:
    """Singleton CosmosDB connection manager"""
    _instance = None
    _initialized = False
    
    def __new__(cls, config: AppConfig = None):
        if cls._instance is None:
            cls._instance = super(CosmosDB, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config: AppConfig = None):
        # Prevent multiple initialization of the same instance
        if self._initialized:
            return
            
        self.logger = logging.getLogger(f"{__name__}.CosmosDB")
        self.logger.info("🔧 Initializing CosmosDB singleton...")
        
        self.config = config

        # Always use DefaultAzureCredential
        try:
            credential = DefaultAzureCredential(logging_enable=False)  # Disable Azure SDK logging to reduce noise
            self.logger.info("✓ Azure credentials initialized successfully")

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
            self.logger.info("✓ Cosmos client initialized")

            # Create database if it doesn't exist
            database_name = config.cosmos["database"]
            self.database = self.client.get_database_client(database_name)
            self.logger.info(f"✓ Database {database_name} is ready")

            # Create containers if they don't exist
            containers = config.cosmos["containers"]

            # Auth container
            auth_container_name = containers["auth"]
            self.auth_container = self.database.get_container_client(
                auth_container_name
            )
            self.logger.info(f"✓ Auth container {auth_container_name} is ready")

            # Jobs container
            jobs_container_name = containers["jobs"]
            self.jobs_container = self.database.get_container_client(
                jobs_container_name
            )
            self.logger.info(f"✓ Jobs container {jobs_container_name} is ready")

            # Prompts container
            prompts_container_name = containers["prompts"]
            self.prompts_container = self.database.get_container_client(
                prompts_container_name
            )
            self.logger.info(f"✓ Prompts container {prompts_container_name} is ready")

            # Analytics containers
            analytics_container_name = containers["analytics"]
            self.analytics_container = self.database.get_container_client(
                analytics_container_name
            )
            self.logger.info(f"✓ Analytics container {analytics_container_name} is ready")

            events_container_name = containers["events"]
            self.events_container = self.database.get_container_client(
                events_container_name
            )
            self.logger.info(f"✓ Events container {events_container_name} is ready")

            sessions_container_name = containers["user_sessions"]
            self.sessions_container = self.database.get_container_client(
                sessions_container_name
            )
            self.logger.info(f"✓ User sessions container {sessions_container_name} is ready")

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
        
        # Initialize permission cache using new settings
        self.logger.info("Initializing permission cache...")
        from app.utils.permission_cache import get_permission_cache
        try:
            from app.core.settings import get_settings
            settings = get_settings()
            self.permission_cache = get_permission_cache(settings)
            self.logger.info("✓ Permission cache initialized with custom settings")
        except Exception as e:
            # Fallback to default cache if settings are not available
            self.logger.warning(f"Using default permission cache due to settings error: {e}")
            self.permission_cache = get_permission_cache()
            self.logger.info("✓ Permission cache initialized with defaults")
        
        # Initialize permission service with this CosmosDB instance
        self.logger.info("Initializing permission service...")
        self._initialize_permission_service()
        
        # Mark as initialized to prevent re-initialization
        self._initialized = True
        self.logger.info("✅ CosmosDB singleton initialization completed successfully")

    def _initialize_permission_service(self):
        """Initialize permission service with this CosmosDB instance"""
        try:
            from app.services.permissions import permission_service
            permission_service.set_cosmos_db(self)
            self.logger.info("✓ Permission service initialized with CosmosDB integration")
        except Exception as e:
            self.logger.warning(f"Failed to initialize permission service: {e}")
            # Don't raise exception here to allow app to continue

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
            # Import here to avoid circular imports
            from app.models.permissions import PermissionLevel
            
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

    # JOB SHARING METHODS
    
    def share_job(self, job_id: str, target_user_id: str, permission_level: str, shared_by: str, message: str = None) -> Dict[str, Any]:
        """Share a job with another user"""
        try:
            job = self.get_job(job_id)
            if not job:
                raise ValueError(f"Job with id {job_id} not found")
            
            # Initialize shared_with array if it doesn't exist
            if "shared_with" not in job:
                job["shared_with"] = []
            
            # Check if already shared with this user
            existing_share = next((s for s in job["shared_with"] if s["user_id"] == target_user_id), None)
            
            if existing_share:
                # Update existing share
                existing_share["permission_level"] = permission_level
                existing_share["shared_at"] = int(datetime.now(timezone.utc).timestamp() * 1000)
                existing_share["shared_by"] = shared_by
                if message:
                    existing_share["message"] = message
            else:
                # Add new share
                share_entry = {
                    "user_id": target_user_id,
                    "permission_level": permission_level,
                    "shared_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "shared_by": shared_by,
                }
                if message:
                    share_entry["message"] = message
                job["shared_with"].append(share_entry)
            
            # Update the job
            update_fields = {
                "shared_with": job["shared_with"],
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            return self.update_job(job_id, update_fields)
            
        except Exception as e:
            self.logger.error(f"Error sharing job {job_id}: {str(e)}")
            raise
    
    def unshare_job(self, job_id: str, target_user_id: str) -> Dict[str, Any]:
        """Remove job sharing with a specific user"""
        try:
            job = self.get_job(job_id)
            if not job:
                raise ValueError(f"Job with id {job_id} not found")
            
            # Remove from shared_with array
            if "shared_with" in job:
                job["shared_with"] = [s for s in job["shared_with"] if s["user_id"] != target_user_id]
                
                # Update the job
                update_fields = {
                    "shared_with": job["shared_with"],
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                return self.update_job(job_id, update_fields)
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error unsharing job {job_id}: {str(e)}")
            raise
    
    def get_jobs_shared_with_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all jobs shared with a specific user"""
        try:
            query = """
            SELECT * FROM c 
            WHERE c.type = 'job' 
            AND ARRAY_CONTAINS(c.shared_with, {'user_id': @user_id}, true)
            """
            parameters = [{"name": "@user_id", "value": user_id}]
            
            jobs = list(
                self.jobs_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error getting shared jobs for user {user_id}: {str(e)}")
            raise
    
    def get_user_shared_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all jobs owned by user that are shared with others"""
        try:
            query = """
            SELECT * FROM c 
            WHERE c.type = 'job' 
            AND c.user_id = @user_id 
            AND IS_DEFINED(c.shared_with) 
            AND ARRAY_LENGTH(c.shared_with) > 0
            """
            parameters = [{"name": "@user_id", "value": user_id}]
            
            jobs = list(
                self.jobs_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error getting user's shared jobs for user {user_id}: {str(e)}")
            raise

    async def delete_user(self, user_id: str):
        """Delete user and invalidate related caches"""
        try:
            # First get the user to retrieve their information
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
            user_permission = user.get("permission")
            
            # Debug: Log user document structure (remove sensitive data)
            user_debug = {k: v for k, v in user.items() if k not in ['password', 'hashed_password']}
            self.logger.info(f"User document structure for deletion: {user_debug}")

            # Delete the user - try different partition key approaches
            try:
                # First try with email as partition key
                self.auth_container.delete_item(item=user_id, partition_key=user["email"])
            except Exception as e1:
                self.logger.warning(f"Failed to delete with email partition key: {str(e1)}")
                try:
                    # Try with user_id as partition key
                    self.auth_container.delete_item(item=user_id, partition_key=user_id)
                except Exception as e2:
                    self.logger.warning(f"Failed to delete with user_id partition key: {str(e2)}")
                    try:
                        # Try with id field as partition key
                        self.auth_container.delete_item(item=user["id"], partition_key=user["id"])
                    except Exception as e3:
                        self.logger.error(f"All delete attempts failed: email={e1}, user_id={e2}, id={e3}")
                        raise e3

            # Invalidate related caches
            await self.permission_cache.invalidate_user_cache(user_id)
            if user_permission:
                await self.permission_cache.invalidate_permission_level_cache(user_permission)

            self.logger.info(f"User {user_id} deleted successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting user: {str(e)}")
            raise


# Create the config instance
config = AppConfig()

# Global singleton instance variable
_cosmos_db_instance = None

def get_cosmos_db(config: AppConfig = None) -> CosmosDB:
    """
    Get the CosmosDB singleton instance.
    
    Args:
        config: AppConfig instance (only used for first initialization)
        
    Returns:
        CosmosDB singleton instance
    """
    global _cosmos_db_instance
    
    if _cosmos_db_instance is None:
        logger.info("🔧 Creating new CosmosDB singleton instance...")
        _cosmos_db_instance = CosmosDB(config)
        logger.info("✅ CosmosDB singleton instance created and cached")
    else:
        logger.debug("♻️ Returning existing CosmosDB singleton instance")
    
    return _cosmos_db_instance


def reset_cosmos_db():
    """Reset the singleton instance (for testing purposes)"""
    global _cosmos_db_instance
    if _cosmos_db_instance is not None:
        CosmosDB._instance = None
        CosmosDB._initialized = False
        _cosmos_db_instance = None
        logger.info("CosmosDB singleton instance reset")
